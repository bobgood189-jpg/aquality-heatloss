-- ============================================================================
-- Aquality | WaterPro — Платный доступ (подписки + промокоды) — Фаза 1
-- Запустите ЦЕЛИКОМ в Supabase → SQL Editor → New query → Run.
-- Требует, чтобы schema.sql (profiles + public.is_admin) уже был применён.
-- Идемпотентно: можно выполнять повторно.
-- На клиенте — ТОЛЬКО anon-ключ; запись статуса/срока подписки закрыта RLS,
-- активация идёт через SECURITY DEFINER-функции ниже (владелец/админ).
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────
-- 1. SUBSCRIPTIONS — подписка пользователя (история; активная = status='active')
-- ─────────────────────────────────────────────────────────────────────────
create table if not exists public.subscriptions (
  id          uuid default gen_random_uuid() primary key,
  user_id     uuid references auth.users(id) on delete cascade not null,
  plan        text not null check (plan in ('m1','m6','m12')),
  status      text not null default 'pending' check (status in ('pending','active','expired','canceled')),
  started_at  timestamptz default now(),
  expires_at  timestamptz,
  amount      numeric,                       -- фактически оплачено (со скидкой), сум
  promo_code  text,
  source      text default 'manual',         -- 'manual' | 'telegram' | 'payme' | 'click'
  created_at  timestamptz default now()
);

create index if not exists subscriptions_user_idx on public.subscriptions(user_id, status, expires_at desc);

alter table public.subscriptions enable row level security;

drop policy if exists "own sub read"        on public.subscriptions;
drop policy if exists "admins all subs"      on public.subscriptions;

-- Пользователь видит ТОЛЬКО свои подписки; писать их сам не может.
create policy "own sub read" on public.subscriptions for select using (auth.uid() = user_id);
-- Владелец/админ — полный доступ (админ-панель «Подписки»).
create policy "admins all subs" on public.subscriptions for all
  using (public.is_admin(auth.uid())) with check (public.is_admin(auth.uid()));

-- ─────────────────────────────────────────────────────────────────────────
-- 2. PROMO_CODES — промокоды со скидкой 10/30/50/100 %
-- ─────────────────────────────────────────────────────────────────────────
create table if not exists public.promo_codes (
  code        text primary key,              -- хранится в ВЕРХНЕМ регистре
  discount    int  not null check (discount in (10,30,50,100)),
  max_uses    int,                           -- null = без лимита
  used_count  int  not null default 0,
  expires_at  timestamptz,                   -- null = бессрочно
  active      boolean not null default true,
  note        text,
  created_at  timestamptz default now()
);

alter table public.promo_codes enable row level security;

-- Список кодов наружу НЕ отдаём (проверка через RPC validate_promo).
drop policy if exists "admins all promos" on public.promo_codes;
create policy "admins all promos" on public.promo_codes for all
  using (public.is_admin(auth.uid())) with check (public.is_admin(auth.uid()));

-- ─────────────────────────────────────────────────────────────────────────
-- 3. PROMO_REDEMPTIONS — кто и какой код применил (один раз на пользователя)
-- ─────────────────────────────────────────────────────────────────────────
create table if not exists public.promo_redemptions (
  id        uuid default gen_random_uuid() primary key,
  code      text references public.promo_codes(code) on delete cascade,
  user_id   uuid references auth.users(id) on delete cascade,
  discount  int,
  used_at   timestamptz default now(),
  unique (code, user_id)
);

alter table public.promo_redemptions enable row level security;

drop policy if exists "own redemption read" on public.promo_redemptions;
drop policy if exists "admins all redemptions" on public.promo_redemptions;
create policy "own redemption read" on public.promo_redemptions for select using (auth.uid() = user_id);
create policy "admins all redemptions" on public.promo_redemptions for all
  using (public.is_admin(auth.uid())) with check (public.is_admin(auth.uid()));

-- ─────────────────────────────────────────────────────────────────────────
-- 4. PAYMENTS — журнал платежей (наполняется в Фазе 2 вебхуками Payme/Click)
-- ─────────────────────────────────────────────────────────────────────────
create table if not exists public.payments (
  id          uuid default gen_random_uuid() primary key,
  user_id     uuid references auth.users(id) on delete cascade,
  sub_id      uuid references public.subscriptions(id) on delete set null,
  provider    text,                          -- 'telegram' | 'payme' | 'click' | 'manual'
  amount      numeric,
  status      text default 'pending',        -- 'pending' | 'paid' | 'failed' | 'refunded'
  external_id text,
  raw         jsonb,
  created_at  timestamptz default now()
);

alter table public.payments enable row level security;
drop policy if exists "own payment read" on public.payments;
drop policy if exists "admins all payments" on public.payments;
create policy "own payment read" on public.payments for select using (auth.uid() = user_id);
create policy "admins all payments" on public.payments for all
  using (public.is_admin(auth.uid())) with check (public.is_admin(auth.uid()));

-- ============================================================================
-- ФУНКЦИИ (RPC)
-- ============================================================================

-- Месяцы по коду плана.
create or replace function public.plan_months(p_plan text)
returns int language sql immutable as $$
  select case p_plan when 'm1' then 1 when 'm6' then 6 when 'm12' then 12 else 0 end;
$$;

-- ─────────────────────────────────────────────────────────────────────────
-- validate_promo — проверка промокода для ТЕКУЩЕГО пользователя (не списывает).
-- Возвращает {ok, discount, reason}. reason: invalid | exhausted | already_used.
-- SECURITY DEFINER — чтобы не раскрывать таблицу кодов наружу через RLS.
-- ─────────────────────────────────────────────────────────────────────────
create or replace function public.validate_promo(p_code text)
returns json
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  v_code  text := upper(trim(p_code));
  v_row   public.promo_codes%rowtype;
  v_uid   uuid := auth.uid();
begin
  if v_uid is null then
    return json_build_object('ok', false, 'reason', 'auth');
  end if;
  select * into v_row from public.promo_codes where code = v_code;
  if not found or v_row.active is false then
    return json_build_object('ok', false, 'reason', 'invalid');
  end if;
  if v_row.expires_at is not null and v_row.expires_at < now() then
    return json_build_object('ok', false, 'reason', 'invalid');
  end if;
  if v_row.max_uses is not null and v_row.used_count >= v_row.max_uses then
    return json_build_object('ok', false, 'reason', 'exhausted');
  end if;
  if exists (select 1 from public.promo_redemptions r where r.code = v_code and r.user_id = v_uid) then
    return json_build_object('ok', false, 'reason', 'already_used');
  end if;
  return json_build_object('ok', true, 'discount', v_row.discount);
end;
$$;

-- ─────────────────────────────────────────────────────────────────────────
-- admin_activate_sub — владелец/админ активирует подписку пользователю.
-- Создаёт активную подписку, продлевает срок и (если задан промокод)
-- фиксирует погашение + увеличивает счётчик использований. Всё в одной транзакции.
-- Возвращает строку подписки в json.
-- ─────────────────────────────────────────────────────────────────────────
create or replace function public.admin_activate_sub(
  p_user uuid, p_plan text, p_amount numeric default null,
  p_promo text default null, p_source text default 'manual'
) returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_months int := public.plan_months(p_plan);
  v_promo  text := nullif(upper(trim(coalesce(p_promo,''))), '');
  v_base   timestamptz;
  v_sub    public.subscriptions%rowtype;
begin
  if not public.is_admin(auth.uid()) then
    raise exception 'forbidden';
  end if;
  if v_months = 0 then
    raise exception 'bad plan %', p_plan;
  end if;

  -- продлеваем от текущего срока, если он ещё не истёк
  select max(expires_at) into v_base from public.subscriptions
    where user_id = p_user and status = 'active' and expires_at > now();
  if v_base is null then v_base := now(); end if;

  insert into public.subscriptions (user_id, plan, status, started_at, expires_at, amount, promo_code, source)
  values (p_user, p_plan, 'active', now(), v_base + (v_months || ' months')::interval, p_amount, v_promo, p_source)
  returning * into v_sub;

  if v_promo is not null then
    insert into public.promo_redemptions (code, user_id, discount)
    select v_promo, p_user, pc.discount from public.promo_codes pc where pc.code = v_promo
    on conflict (code, user_id) do nothing;
    update public.promo_codes set used_count = used_count + 1 where code = v_promo;
  end if;

  return row_to_json(v_sub);
end;
$$;

-- Доступ к RPC для залогиненных пользователей.
grant execute on function public.validate_promo(text)   to authenticated;
grant execute on function public.admin_activate_sub(uuid, text, numeric, text, text) to authenticated;
grant execute on function public.plan_months(text)       to authenticated;

-- ============================================================================
-- ГОТОВО. Включить paywall на сайте: в index.html (window.AQ_CONFIG)
-- добавить  PAYWALL: true  (или оставить авто — он включится сам, когда
-- заданы ключи Supabase). Промокоды и подписки управляются в админ-панели.
-- ============================================================================
