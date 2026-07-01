-- ============================================================================
-- Восстановление пароля кодом, доставленным в Telegram-бот — третий,
-- независимый путь сброса пароля (рядом с email-OTP из index.html и
-- «сбросом без кода» из /resetpass, см. telegram-schema.sql).
--
-- Поток: пользователь на сайте жмёт «Получить код в Telegram» в форме
-- забытого пароля → request_tg_reset_code() создаёт запись здесь. Бот
-- (service_role, короткий polling-цикл в bot.py) забирает необработанные
-- коды через bot_list_pending_reset_codes(), шлёт код в чат пользователя,
-- помечает bot_mark_reset_code_notified(). Пользователь вводит код + новый
-- пароль на сайте — Edge Function verify-tg-reset (service_role, Admin API)
-- проверяет код в этой таблице и меняет пароль.
--
-- Также здесь bot_unlink_telegram — отвязка Telegram из «Моего аккаунта» в
-- боте (unlink_tg_account из telegram-schema.sql требует auth.uid(), т.е.
-- вызывается только с сайта; боту нужен вариант по telegram_id).
--
-- Требует telegram-schema.sql (колонка profiles.telegram_id) применённым
-- первым. Идемпотентно: безопасно запускать повторно.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.tg_reset_codes (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  telegram_id  BIGINT NOT NULL,
  code         TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at   TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '10 minutes'),
  attempts     INT NOT NULL DEFAULT 0,
  used         BOOLEAN NOT NULL DEFAULT false,
  notified     BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS tg_reset_codes_pending_idx
  ON public.tg_reset_codes (created_at)
  WHERE notified = false;

CREATE INDEX IF NOT EXISTS tg_reset_codes_user_idx ON public.tg_reset_codes (user_id);

ALTER TABLE public.tg_reset_codes ENABLE ROW LEVEL SECURITY;
-- Никаких политик для anon/authenticated — таблица целиком закрыта.
-- Доступ только через SECURITY DEFINER RPC ниже и через service_role
-- (бот, Edge Function verify-tg-reset), которые обходят RLS.

-- ============================================================================
-- request_tg_reset_code — сайт запрашивает код ДО логина (по email).
-- Не палит существование email отдельным HTTP-статусом — только полем reason
-- в JSON, как и остальные auth RPC этого проекта (bot_link_telegram и т.п.).
-- ============================================================================
CREATE OR REPLACE FUNCTION public.request_tg_reset_code(p_email TEXT)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_profile public.profiles%ROWTYPE;
  v_last    TIMESTAMPTZ;
  v_code    TEXT;
BEGIN
  SELECT * INTO v_profile FROM public.profiles WHERE LOWER(email) = LOWER(TRIM(p_email));
  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'email_not_found');
  END IF;

  IF v_profile.telegram_id IS NULL THEN
    RETURN json_build_object('ok', false, 'reason', 'no_telegram_link');
  END IF;

  SELECT MAX(created_at) INTO v_last FROM public.tg_reset_codes
    WHERE user_id = v_profile.id AND NOT used AND expires_at > now();
  IF v_last IS NOT NULL AND v_last > now() - INTERVAL '30 seconds' THEN
    RETURN json_build_object('ok', false, 'reason', 'too_soon');
  END IF;

  DELETE FROM public.tg_reset_codes WHERE user_id = v_profile.id AND NOT used;

  v_code := LPAD(FLOOR(RANDOM() * 1000000)::TEXT, 6, '0');
  INSERT INTO public.tg_reset_codes (user_id, telegram_id, code)
  VALUES (v_profile.id, v_profile.telegram_id, v_code);

  RETURN json_build_object('ok', true);
END;
$$;

GRANT EXECUTE ON FUNCTION public.request_tg_reset_code(TEXT) TO anon, authenticated;

-- ============================================================================
-- bot_list_pending_reset_codes / bot_mark_reset_code_notified — бот забирает
-- код и доставляет его в чат пользователя. По образцу
-- bot_list_pending_site_payments/bot_mark_site_payment_notified
-- (site-payments-schema.sql). Только service_role — REVOKE ниже.
-- ============================================================================
CREATE OR REPLACE FUNCTION public.bot_list_pending_reset_codes()
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_rows JSON;
BEGIN
  SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json) INTO v_rows FROM (
    SELECT id, telegram_id, code
    FROM public.tg_reset_codes
    WHERE notified = false AND used = false AND expires_at > now()
    ORDER BY created_at
  ) t;
  RETURN v_rows;
END;
$$;

REVOKE ALL ON FUNCTION public.bot_list_pending_reset_codes() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.bot_list_pending_reset_codes() FROM anon;
REVOKE ALL ON FUNCTION public.bot_list_pending_reset_codes() FROM authenticated;

CREATE OR REPLACE FUNCTION public.bot_mark_reset_code_notified(p_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  UPDATE public.tg_reset_codes SET notified = true WHERE id = p_id;
END;
$$;

REVOKE ALL ON FUNCTION public.bot_mark_reset_code_notified(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.bot_mark_reset_code_notified(UUID) FROM anon;
REVOKE ALL ON FUNCTION public.bot_mark_reset_code_notified(UUID) FROM authenticated;

-- ============================================================================
-- bot_unlink_telegram — «Мой аккаунт» в боте: отвязать Telegram по
-- telegram_id (unlink_tg_account в telegram-schema.sql требует auth.uid(),
-- т.е. годится только для вызова с сайта залогиненным пользователем).
-- ============================================================================
CREATE OR REPLACE FUNCTION public.bot_unlink_telegram(p_telegram_id BIGINT)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_uid UUID;
BEGIN
  SELECT id INTO v_uid FROM public.profiles WHERE telegram_id = p_telegram_id;
  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'not_linked');
  END IF;

  UPDATE public.profiles
  SET telegram_id = NULL, telegram_username = NULL, updated_at = now()
  WHERE id = v_uid;

  RETURN json_build_object('ok', true);
END;
$$;

REVOKE ALL ON FUNCTION public.bot_unlink_telegram(BIGINT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.bot_unlink_telegram(BIGINT) FROM anon;
REVOKE ALL ON FUNCTION public.bot_unlink_telegram(BIGINT) FROM authenticated;

-- ============================================================================
-- ГОТОВО. Применить вручную (в этой сессии нет доступа к Supabase MCP/CLI):
-- 1. Supabase Dashboard → SQL Editor → выполнить этот файл ПОСЛЕ
--    telegram-schema.sql (проект ocrgpmlhtjghiamhbrhv).
-- 2. Задеплоить Edge Function supabase/functions/verify-tg-reset
--    (supabase functions deploy verify-tg-reset).
-- ============================================================================
