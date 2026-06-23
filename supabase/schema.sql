-- ============================================================================
-- Aquality | WaterPro — Supabase schema (tables + RLS + triggers)
-- Запустите ЦЕЛИКОМ в Supabase → SQL Editor → New query → Run.
-- Идемпотентно: можно выполнять повторно.
-- На клиенте используется ТОЛЬКО anon-ключ; доступ ограничен политиками RLS ниже.
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────
-- Helper: безопасная проверка «админ/владелец» без рекурсии RLS.
-- SECURITY DEFINER обходит RLS внутри функции, поэтому её можно использовать
-- в политиках на самой таблице profiles, не вызывая бесконечной рекурсии.
-- ─────────────────────────────────────────────────────────────────────────
create or replace function public.is_admin(uid uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles p
    where p.id = uid and p.role in ('owner','admin')
  );
$$;

-- ============================================================================
-- 1. PROFILES — профиль пользователя (1:1 с auth.users)
-- ============================================================================
create table if not exists public.profiles (
  id          uuid references auth.users(id) on delete cascade primary key,
  full_name   text,
  phone       text,
  phone2      text,
  email       text,
  company     text,
  city        text,
  client_type text default 'client',
  role        text default 'user',          -- 'user' | 'admin' | 'owner'
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

alter table public.profiles enable row level security;

drop policy if exists "own profile read"   on public.profiles;
drop policy if exists "own profile insert" on public.profiles;
drop policy if exists "own profile update" on public.profiles;
drop policy if exists "admins read all profiles" on public.profiles;

create policy "own profile read"   on public.profiles for select using (auth.uid() = id);
create policy "own profile insert" on public.profiles for insert with check (auth.uid() = id);
create policy "own profile update" on public.profiles for update using (auth.uid() = id);
-- Владелец/админ может читать всех пользователей (для админ-панели):
create policy "admins read all profiles" on public.profiles for select using (public.is_admin(auth.uid()));

-- Запрет на самоповышение роли: обычный пользователь не может выдать себе admin/owner.
-- Роль меняется только из SQL-редактора или другим админом (через service_role на бэке).
drop policy if exists "no self role escalation" on public.profiles;
create policy "no self role escalation" on public.profiles for update
  using (auth.uid() = id)
  with check (
    auth.uid() = id
    and role = (select p.role from public.profiles p where p.id = auth.uid())
  );

-- ─────────────────────────────────────────────────────────────────────────
-- Триггер: при регистрации (signUp) автоматически создаём строку профиля,
-- подтягивая метаданные из raw_user_meta_data (их шлёт клиент в options.data).
-- ─────────────────────────────────────────────────────────────────────────
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, full_name, phone, phone2, email, city, client_type, role)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', new.email),
    new.raw_user_meta_data->>'phone',
    new.raw_user_meta_data->>'phone2',
    new.email,
    new.raw_user_meta_data->>'city',
    coalesce(new.raw_user_meta_data->>'client_type', 'client'),
    'user'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- auto-update updated_at
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end; $$;

drop trigger if exists profiles_touch on public.profiles;
create trigger profiles_touch before update on public.profiles
  for each row execute function public.touch_updated_at();

-- ============================================================================
-- 2. CALCULATIONS — сохранённые расчёты пользователя
-- ============================================================================
create table if not exists public.calculations (
  id         uuid default gen_random_uuid() primary key,
  user_id    uuid references auth.users(id) on delete cascade,
  name       text,
  payload    jsonb,            -- { state: <serializeState()>, summary: {...} }
  result_kw  numeric,
  created_at timestamptz default now()
);

create index if not exists calculations_user_idx on public.calculations(user_id, created_at desc);

alter table public.calculations enable row level security;

drop policy if exists "own calc read"   on public.calculations;
drop policy if exists "own calc insert" on public.calculations;
drop policy if exists "own calc delete" on public.calculations;
drop policy if exists "admins read all calcs" on public.calculations;

create policy "own calc read"   on public.calculations for select using (auth.uid() = user_id);
create policy "own calc insert" on public.calculations for insert with check (auth.uid() = user_id);
create policy "own calc delete" on public.calculations for delete using (auth.uid() = user_id);
create policy "admins read all calcs" on public.calculations for select using (public.is_admin(auth.uid()));

-- ============================================================================
-- 3. LEADS — заявки (приходят от НЕзалогиненных посетителей)
-- ============================================================================
create table if not exists public.leads (
  id             uuid default gen_random_uuid() primary key,
  name           text,
  phone          text,
  city           text,
  calc_result_kw numeric,
  source         text,         -- 'whatsapp' | 'telegram' | 'form'
  payload        jsonb,
  created_at     timestamptz default now()
);

create index if not exists leads_created_idx on public.leads(created_at desc);

alter table public.leads enable row level security;

drop policy if exists "anyone can submit lead" on public.leads;
drop policy if exists "admins read leads"      on public.leads;

-- Любой (в т.ч. anon) может ТОЛЬКО вставить заявку. SELECT для anon отсутствует —
-- чужие заявки прочитать нельзя.
create policy "anyone can submit lead" on public.leads for insert with check (true);
-- Читать заявки может только владелец/админ (для админ-панели):
create policy "admins read leads" on public.leads for select using (public.is_admin(auth.uid()));

-- ============================================================================
-- 4. НАЗНАЧИТЬ ВЛАДЕЛЬЦА (выполнить ОДИН раз после регистрации владельца)
-- ============================================================================
-- 1) Зарегистрируйтесь на сайте обычным образом (email + пароль владельца).
-- 2) Замените email ниже на свой и выполните:
--
-- update public.profiles set role = 'owner'
-- where email = 'owner@example.com';
--
-- После этого аккаунт получит доступ к админ-панели (Заявки, Пользователи).
-- ============================================================================
