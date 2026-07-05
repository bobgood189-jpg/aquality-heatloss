-- ============================================================================
-- Восстановление пароля кодом по SMS через Eskiz.uz — третий канал сброса
-- пароля (рядом с email-OTP из assets/app.js и Telegram-ботом, см.
-- tg-reset-codes-schema.sql). Использует тот же клиент Eskiz, что и
-- otp-sms-schema.sql (подтверждение телефона при регистрации), но отдельная
-- таблица — там код привязан к телефону как таковому (до входа в аккаунт),
-- здесь — к user_id (телефон достаём из profiles по email).
--
-- Поток:
--  1. Сайт → Edge Function send-sms-reset(email) — находит профиль и его
--     телефон, генерирует код, шлёт SMS через Eskiz, кладёт сюда
--     sha256(phone:code) (код в открытом виде нигде не хранится).
--  2. Сайт → Edge Function verify-sms-reset(email, code, newPassword) —
--     сверяет хеш и меняет пароль через Admin API (auth.admin.updateUserById).
--
-- Идемпотентно. Применять после schema.sql (нужен profiles.phone — уже есть).
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.sms_reset_codes (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  phone        TEXT NOT NULL,              -- нормализовано: 998XXXXXXXXX
  code_hash    TEXT NOT NULL,              -- sha256(phone:code)
  attempts     INT NOT NULL DEFAULT 0,
  max_attempts INT NOT NULL DEFAULT 5,
  expires_at   TIMESTAMPTZ NOT NULL,
  used_at      TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS sms_reset_codes_user_idx
  ON public.sms_reset_codes (user_id, created_at DESC);

ALTER TABLE public.sms_reset_codes ENABLE ROW LEVEL SECURITY;
-- Политик нет намеренно: доступ только через service_role (Edge Functions).

-- ============================================================================
-- ГОТОВО. Применить (Supabase Dashboard → SQL Editor, проект
-- ocrgpmlhtjghiamhbrhv), после schema.sql.
--
-- Задеплоить функции:
--   supabase functions deploy send-sms-reset
--   supabase functions deploy verify-sms-reset
--
-- Секреты ESKIZ_* уже нужны для send-sms-otp/verify-sms-otp (см.
-- otp-sms-schema.sql) — для этой миграции дополнительно ничего настраивать
-- не нужно.
-- ============================================================================
