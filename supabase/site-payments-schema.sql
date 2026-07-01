-- ============================================================================
-- Мост «оплата на сайте» → «подтверждение в Telegram».
--
-- Пользователь жмёт «Я оплатил» на сайте (payIHavePaid() в index.html) —
-- это создаёт запись в public.payments (status='pending'). Раньше владелец
-- мог подтвердить её только из админки сайта (adminApprovePayment(), вызывает
-- admin_activate_sub — требует is_admin(auth.uid()), т.е. только залогиненный
-- на сайте админ). Этот файл добавляет второй путь подтверждения — прямо из
-- Telegram-бота, без входа на сайт.
--
-- Бот ходит в Supabase через SUPABASE_SERVICE_KEY (bot/app/supabase_db.py),
-- где auth.uid() всегда NULL — поэтому admin_activate_sub боту не подходит.
-- Решение то же, что уже используется для bot_activate_sub (см.
-- supabase/v2-improvements.sql): SECURITY DEFINER функции без проверки
-- auth.uid(), защищённые тем, что EXECUTE на них явно закрыт от
-- anon/authenticated — вызвать их может только держатель service_role key.
-- ============================================================================

-- 1. Флаг «владельцу уже отправлено уведомление в Telegram об этой заявке».
ALTER TABLE public.payments
  ADD COLUMN IF NOT EXISTS telegram_notified boolean NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS payments_pending_notify_idx
  ON public.payments (created_at)
  WHERE status = 'pending' AND telegram_notified = false;

-- ─────────────────────────────────────────────────────────────────────────
-- bot_list_pending_site_payments — заявки, ожидающие уведомления владельца,
-- сразу с email/именем покупателя (для текста сообщения в Telegram).
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.bot_list_pending_site_payments()
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_rows JSON;
BEGIN
  SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json) INTO v_rows FROM (
    SELECT p.id, p.user_id, p.provider, p.amount, p.raw, p.created_at,
           pr.email, pr.full_name
    FROM public.payments p
    LEFT JOIN public.profiles pr ON pr.id = p.user_id
    WHERE p.status = 'pending' AND p.telegram_notified = false
    ORDER BY p.created_at
  ) t;
  RETURN v_rows;
END;
$$;

REVOKE ALL ON FUNCTION public.bot_list_pending_site_payments() FROM PUBLIC;

CREATE OR REPLACE FUNCTION public.bot_mark_site_payment_notified(p_payment_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  UPDATE public.payments SET telegram_notified = true WHERE id = p_payment_id;
END;
$$;

REVOKE ALL ON FUNCTION public.bot_mark_site_payment_notified(UUID) FROM PUBLIC;

-- ─────────────────────────────────────────────────────────────────────────
-- bot_activate_site_payment — владелец подтвердил заявку в Telegram.
-- Атомарно: продлевает/создаёт подписку (как admin_activate_sub/
-- bot_activate_sub), помечает payments.status='paid' + payments.sub_id,
-- ставит just_activated=true (сайт уже поллит это поле через aqRefreshSub()/
-- payRefresh() в index.html и сам покажет экран поздравления — на сайте
-- ничего дополнительно не нужно), пишет запись в admin_audit.
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.bot_activate_site_payment(
  p_payment_id UUID, p_actor_tg BIGINT DEFAULT NULL
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_pay     public.payments%ROWTYPE;
  v_profile public.profiles%ROWTYPE;
  v_plan    TEXT;
  v_promo   TEXT;
  v_months  INT;
  v_base    TIMESTAMPTZ;
  v_sub     public.subscriptions%ROWTYPE;
BEGIN
  SELECT * INTO v_pay FROM public.payments WHERE id = p_payment_id FOR UPDATE;
  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'not_found');
  END IF;
  IF v_pay.status <> 'pending' THEN
    RETURN json_build_object('ok', false, 'reason', 'already_processed', 'status', v_pay.status);
  END IF;

  v_plan   := v_pay.raw->>'plan';
  v_promo  := NULLIF(UPPER(TRIM(COALESCE(v_pay.raw->>'promo', ''))), '');
  v_months := public.plan_months(v_plan);
  IF v_months = 0 THEN
    RETURN json_build_object('ok', false, 'reason', 'bad_plan', 'plan', v_plan);
  END IF;

  -- продлеваем от текущего срока, если подписка ещё активна
  SELECT MAX(expires_at) INTO v_base FROM public.subscriptions
    WHERE user_id = v_pay.user_id AND status = 'active' AND expires_at > NOW();
  IF v_base IS NULL THEN v_base := NOW(); END IF;

  INSERT INTO public.subscriptions
    (user_id, plan, status, started_at, expires_at, amount, promo_code, source, just_activated)
  VALUES
    (v_pay.user_id, v_plan, 'active', NOW(),
     v_base + (v_months || ' months')::INTERVAL,
     v_pay.amount, v_promo, 'telegram_site', TRUE)
  RETURNING * INTO v_sub;

  IF v_promo IS NOT NULL THEN
    INSERT INTO public.promo_redemptions (code, user_id, discount)
    SELECT v_promo, v_pay.user_id, pc.discount
    FROM public.promo_codes pc WHERE pc.code = v_promo
    ON CONFLICT (code, user_id) DO NOTHING;
    UPDATE public.promo_codes SET used_count = used_count + 1 WHERE code = v_promo;
  END IF;

  UPDATE public.payments SET status = 'paid', sub_id = v_sub.id WHERE id = p_payment_id;

  SELECT * INTO v_profile FROM public.profiles WHERE id = v_pay.user_id;

  INSERT INTO public.admin_audit (actor_tg, action, details)
  VALUES (p_actor_tg, 'confirm_site_payment',
          jsonb_build_object('payment_id', p_payment_id, 'plan', v_plan,
                             'amount', v_pay.amount, 'expires_at', v_sub.expires_at));

  RETURN json_build_object(
    'ok', true, 'sub_id', v_sub.id, 'user_id', v_pay.user_id,
    'email', v_profile.email, 'full_name', v_profile.full_name,
    'telegram_id', v_profile.telegram_id,
    'plan', v_sub.plan, 'amount', v_pay.amount, 'expires_at', v_sub.expires_at
  );
END;
$$;

REVOKE ALL ON FUNCTION public.bot_activate_site_payment(UUID, BIGINT) FROM PUBLIC;

-- ─────────────────────────────────────────────────────────────────────────
-- bot_reject_site_payment — владелец отклонил заявку (идемпотентно).
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.bot_reject_site_payment(
  p_payment_id UUID, p_actor_tg BIGINT DEFAULT NULL
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_pay public.payments%ROWTYPE;
BEGIN
  SELECT * INTO v_pay FROM public.payments WHERE id = p_payment_id FOR UPDATE;
  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'not_found');
  END IF;
  IF v_pay.status <> 'pending' THEN
    RETURN json_build_object('ok', false, 'reason', 'already_processed', 'status', v_pay.status);
  END IF;

  UPDATE public.payments SET status = 'failed' WHERE id = p_payment_id;

  INSERT INTO public.admin_audit (actor_tg, action, details)
  VALUES (p_actor_tg, 'reject_site_payment', jsonb_build_object('payment_id', p_payment_id));

  RETURN json_build_object('ok', true);
END;
$$;

REVOKE ALL ON FUNCTION public.bot_reject_site_payment(UUID, BIGINT) FROM PUBLIC;

-- ============================================================================
-- ГОТОВО. Применить через Supabase SQL Editor (или Supabase MCP apply_migration
-- если он подключён в сессии), проект ocrgpmlhtjghiamhbrhv. Функции доступны
-- ТОЛЬКО через service_role key (тот же, что уже в bot/.env как
-- SUPABASE_SERVICE_KEY) — ни anon, ни authenticated их вызвать не смогут.
-- ============================================================================
