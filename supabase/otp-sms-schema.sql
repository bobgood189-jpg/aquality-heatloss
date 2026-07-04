-- ============================================================================
-- SMS-OTP через Eskiz.uz — подтверждение номера телефона (используется в
-- форме регистрации на сайте). Самостоятельная таблица, НЕ трогает
-- verification_codes из ideal-v1-stage1.sql (та миграция ещё не применена,
-- рассчитана на email/telegram-каналы — см. её §8, и её лучше не расширять
-- ради этой узкой задачи).
--
-- Поток:
--  1. Сайт → Edge Function send-sms-otp(phone) — генерирует код, шлёт SMS
--     через Eskiz, кладёт сюда sha256(phone:code) (код в открытом виде
--     нигде не хранится).
--  2. Сайт → Edge Function verify-sms-otp(phone, code) — сверяет хеш,
--     помечает used_at.
--  3. После успешной регистрации (или из профиля) сайт вызывает RPC
--     confirm_phone_verified(phone) от имени залогиненного пользователя —
--     она проверяет, что для этого phone есть свежая (< 30 мин) запись
--     с used_at, и только тогда выставляет profiles.phone_verified.
--     Это не даёт подтвердить чужой телефон произвольным вызовом RPC.
--
-- Идемпотентно: можно выполнять повторно. Применять после schema.sql.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.sms_otp_codes (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone        TEXT NOT NULL,              -- нормализовано: 998XXXXXXXXX
  code_hash    TEXT NOT NULL,              -- sha256(phone:code)
  attempts     INT NOT NULL DEFAULT 0,
  max_attempts INT NOT NULL DEFAULT 5,
  expires_at   TIMESTAMPTZ NOT NULL,
  used_at      TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS sms_otp_codes_phone_idx
  ON public.sms_otp_codes (phone, created_at DESC);

ALTER TABLE public.sms_otp_codes ENABLE ROW LEVEL SECURITY;
-- Политик нет намеренно: доступ только через service_role (Edge Functions).

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN NOT NULL DEFAULT FALSE;

-- ─────────────────────────────────────────────────────────────────────────
-- confirm_phone_verified — вызывается сайтом от имени залогиненного
-- пользователя сразу после успешной регистрации (или из профиля).
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.confirm_phone_verified(p_phone TEXT)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_uid    UUID := auth.uid();
  v_digits TEXT := regexp_replace(COALESCE(p_phone, ''), '\D', '', 'g');
  v_ok     BOOLEAN;
BEGIN
  IF v_uid IS NULL THEN
    RETURN json_build_object('ok', false, 'reason', 'not_authenticated');
  END IF;
  IF length(v_digits) = 9 THEN v_digits := '998' || v_digits; END IF;
  IF length(v_digits) <> 12 THEN
    RETURN json_build_object('ok', false, 'reason', 'bad_phone');
  END IF;

  SELECT EXISTS(
    SELECT 1 FROM public.sms_otp_codes
    WHERE phone = v_digits AND used_at IS NOT NULL
      AND used_at > now() - INTERVAL '30 minutes'
  ) INTO v_ok;

  IF NOT v_ok THEN
    RETURN json_build_object('ok', false, 'reason', 'not_verified');
  END IF;

  UPDATE public.profiles SET phone_verified = TRUE, updated_at = now() WHERE id = v_uid;
  RETURN json_build_object('ok', true);
END $$;

GRANT EXECUTE ON FUNCTION public.confirm_phone_verified(TEXT) TO authenticated;

-- ============================================================================
-- ГОТОВО. Применить (Supabase Dashboard → SQL Editor, проект
-- ocrgpmlhtjghiamhbrhv), ПОСЛЕ schema.sql. Порядок относительно
-- ideal-v1-stage1.sql не важен — файлы не пересекаются по объектам.
--
-- Задеплоить функции:
--   supabase functions deploy send-sms-otp
--   supabase functions deploy verify-sms-otp
--
-- Секреты (задать самостоятельно, пароль НЕ передавать в чат):
--   supabase secrets set ESKIZ_EMAIL=bobgood189@gmail.com
--   supabase secrets set ESKIZ_PASSWORD=...
--   supabase secrets set ESKIZ_FROM=4546
-- ============================================================================
