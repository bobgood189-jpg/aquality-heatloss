-- ============================================================================
-- Aquality | WaterPro — Telegram ↔ Website integration schema
-- Запустите ПОСЛЕ schema.sql и payment-schema.sql.
-- Идемпотентно: можно выполнять повторно.
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────
-- 1. Добавляем Telegram-поля в profiles
-- ─────────────────────────────────────────────────────────────────────────
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS tg_user_id   BIGINT UNIQUE,
  ADD COLUMN IF NOT EXISTS tg_username  TEXT,
  ADD COLUMN IF NOT EXISTS tg_linked_at TIMESTAMPTZ;

-- ─────────────────────────────────────────────────────────────────────────
-- 2. Таблица одноразовых токенов для привязки Telegram-аккаунта
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.tg_link_tokens (
  token      TEXT PRIMARY KEY,
  user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ DEFAULT (now() + INTERVAL '15 minutes'),
  used       BOOLEAN NOT NULL DEFAULT false
);

ALTER TABLE public.tg_link_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "own token manage" ON public.tg_link_tokens;
CREATE POLICY "own token manage" ON public.tg_link_tokens
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────
-- 3. RPC: создать токен привязки для текущего пользователя
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.create_tg_link_token()
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  tok TEXT;
  uid UUID := auth.uid();
BEGIN
  IF uid IS NULL THEN RAISE EXCEPTION 'Not authenticated'; END IF;
  -- Сбрасываем старые токены этого пользователя
  DELETE FROM tg_link_tokens WHERE user_id = uid;
  -- Генерируем 12-символьный токен (uppercase hex)
  tok := upper(substring(replace(gen_random_uuid()::text, '-', ''), 1, 12));
  INSERT INTO tg_link_tokens(token, user_id) VALUES (tok, uid);
  RETURN tok;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────
-- 4. RPC: привязать Telegram-аккаунт (вызывается ботом через service_role)
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.link_tg_account(
  p_token       TEXT,
  p_tg_user_id  BIGINT,
  p_tg_username TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  tk RECORD;
BEGIN
  SELECT * INTO tk FROM tg_link_tokens
  WHERE token = upper(p_token) AND NOT used AND expires_at > now();

  IF NOT FOUND THEN
    RETURN '{"ok":false,"reason":"invalid_token"}'::JSONB;
  END IF;

  -- Проверяем, что этот tg_user_id ещё не привязан к другому аккаунту
  IF EXISTS (
    SELECT 1 FROM profiles
    WHERE tg_user_id = p_tg_user_id AND id != tk.user_id
  ) THEN
    RETURN '{"ok":false,"reason":"already_linked"}'::JSONB;
  END IF;

  UPDATE profiles SET
    tg_user_id    = p_tg_user_id,
    tg_username   = p_tg_username,
    tg_linked_at  = now(),
    updated_at    = now()
  WHERE id = tk.user_id;

  UPDATE tg_link_tokens SET used = true WHERE token = upper(p_token);

  RETURN jsonb_build_object('ok', true, 'user_id', tk.user_id::text);
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────
-- 5. RPC: отвязать Telegram от своего профиля (вызывается сайтом)
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.unlink_tg_account()
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE uid UUID := auth.uid();
BEGIN
  IF uid IS NULL THEN RAISE EXCEPTION 'Not authenticated'; END IF;
  UPDATE profiles SET
    tg_user_id    = NULL,
    tg_username   = NULL,
    tg_linked_at  = NULL,
    updated_at    = now()
  WHERE id = uid;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────
-- 6. RPC: активировать подписку по tg_user_id (вызывается ботом через service_role)
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.activate_sub_by_tg(
  p_tg_user_id BIGINT,
  p_plan        TEXT,
  p_days        INT,
  p_amount      NUMERIC DEFAULT NULL,
  p_promo       TEXT    DEFAULT NULL,
  p_source      TEXT    DEFAULT 'telegram'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_user_id    UUID;
  v_expires_at TIMESTAMPTZ;
  v_base       TIMESTAMPTZ;
  v_cur        RECORD;
BEGIN
  SELECT id INTO v_user_id FROM profiles WHERE tg_user_id = p_tg_user_id;
  IF NOT FOUND THEN
    RETURN '{"ok":false,"reason":"user_not_linked"}'::JSONB;
  END IF;

  IF p_plan NOT IN ('m1','m6','m12') THEN
    RETURN '{"ok":false,"reason":"invalid_plan"}'::JSONB;
  END IF;

  -- Продлеваем от текущей подписки, если она ещё не истекла
  SELECT expires_at INTO v_cur FROM subscriptions
  WHERE user_id = v_user_id AND status = 'active' AND expires_at > now()
  ORDER BY expires_at DESC LIMIT 1;

  v_base := COALESCE(v_cur.expires_at, now());
  v_expires_at := v_base + (p_days || ' days')::INTERVAL;

  INSERT INTO subscriptions(user_id, plan, status, started_at, expires_at, amount, promo_code, source)
  VALUES (v_user_id, p_plan, 'active', now(), v_expires_at, p_amount, p_promo, p_source);

  RETURN jsonb_build_object(
    'ok',         true,
    'user_id',    v_user_id::text,
    'expires_at', v_expires_at::text
  );
END;
$$;
