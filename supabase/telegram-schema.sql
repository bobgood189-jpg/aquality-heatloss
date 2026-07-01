-- ============================================================================
-- Aquality Bot — Telegram integration schema
-- Требует schema.sql и payment-schema.sql быть применёнными первыми.
-- Идемпотентно: безопасно запускать повторно.
-- Бот использует service_role key, который обходит RLS.
-- ============================================================================

-- 1. Добавляем telegram_id в profiles
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS telegram_id   BIGINT UNIQUE,
  ADD COLUMN IF NOT EXISTS telegram_username TEXT;

CREATE INDEX IF NOT EXISTS profiles_telegram_idx
  ON public.profiles(telegram_id)
  WHERE telegram_id IS NOT NULL;

-- Обновляем триггер handle_new_user, чтобы подтягивать telegram_id из метаданных
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, phone, phone2, email, city, client_type, role, telegram_id)
  VALUES (
    new.id,
    COALESCE(new.raw_user_meta_data->>'full_name', new.email),
    new.raw_user_meta_data->>'phone',
    new.raw_user_meta_data->>'phone2',
    new.email,
    new.raw_user_meta_data->>'city',
    COALESCE(new.raw_user_meta_data->>'client_type', 'client'),
    'user',
    (new.raw_user_meta_data->>'telegram_id')::bigint
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN new;
END;
$$;

-- 2. Таблица одноразовых токенов для привязки (сайт → бот)
CREATE TABLE IF NOT EXISTS public.tg_link_tokens (
  token      TEXT PRIMARY KEY,
  user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ DEFAULT (now() + INTERVAL '15 minutes'),
  used       BOOLEAN NOT NULL DEFAULT false
);

ALTER TABLE public.tg_link_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "own link token" ON public.tg_link_tokens;
CREATE POLICY "own link token" ON public.tg_link_tokens
  FOR SELECT USING (auth.uid() = user_id);

-- ============================================================================
-- RPC: create_tg_link_token — сайт генерирует токен для пользователя
-- ============================================================================
CREATE OR REPLACE FUNCTION public.create_tg_link_token()
RETURNS TEXT LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_uid   UUID := auth.uid();
  v_token TEXT;
BEGIN
  IF v_uid IS NULL THEN RAISE EXCEPTION 'auth required'; END IF;
  DELETE FROM public.tg_link_tokens WHERE user_id = v_uid;
  v_token := UPPER(SUBSTRING(encode(gen_random_bytes(6), 'hex') FROM 1 FOR 8));
  INSERT INTO public.tg_link_tokens (token, user_id) VALUES (v_token, v_uid);
  RETURN v_token;
END;
$$;
GRANT EXECUTE ON FUNCTION public.create_tg_link_token() TO authenticated;

-- ============================================================================
-- RPC: link_tg_account — бот предъявляет токен и привязывает Telegram ID
-- Вызывается ботом с service_role (bypasses RLS).
-- ============================================================================
CREATE OR REPLACE FUNCTION public.link_tg_account(
  p_token TEXT, p_telegram_id BIGINT, p_username TEXT DEFAULT ''
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_token TEXT := UPPER(TRIM(p_token));
  v_tk    public.tg_link_tokens%ROWTYPE;
BEGIN
  SELECT * INTO v_tk FROM public.tg_link_tokens
  WHERE token = v_token AND NOT used AND expires_at > now();

  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'bad_token');
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.profiles
    WHERE telegram_id = p_telegram_id AND id <> v_tk.user_id
  ) THEN
    RETURN json_build_object('ok', false, 'reason', 'already_linked');
  END IF;

  UPDATE public.profiles
  SET telegram_id       = p_telegram_id,
      telegram_username = NULLIF(p_username, ''),
      updated_at        = now()
  WHERE id = v_tk.user_id;

  UPDATE public.tg_link_tokens SET used = true WHERE token = v_token;

  RETURN json_build_object('ok', true, 'user_id', v_tk.user_id);
END;
$$;

-- ============================================================================
-- RPC: unlink_tg_account — сайт отвязывает Telegram аккаунт
-- ============================================================================
CREATE OR REPLACE FUNCTION public.unlink_tg_account()
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_uid UUID := auth.uid();
BEGIN
  IF v_uid IS NULL THEN RETURN false; END IF;
  UPDATE public.profiles
  SET telegram_id = NULL, telegram_username = NULL, updated_at = now()
  WHERE id = v_uid;
  RETURN true;
END;
$$;
GRANT EXECUTE ON FUNCTION public.unlink_tg_account() TO authenticated;

-- ============================================================================
-- RPC: bot_get_profile — бот получает профиль по telegram_id
-- ============================================================================
CREATE OR REPLACE FUNCTION public.bot_get_profile(p_telegram_id BIGINT)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_profile public.profiles%ROWTYPE;
BEGIN
  SELECT * INTO v_profile FROM public.profiles WHERE telegram_id = p_telegram_id;
  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'not_found');
  END IF;
  RETURN json_build_object(
    'ok',          true,
    'user_id',     v_profile.id,
    'email',       v_profile.email,
    'full_name',   v_profile.full_name,
    'telegram_id', v_profile.telegram_id,
    'role',        v_profile.role
  );
END;
$$;

-- ============================================================================
-- RPC: bot_link_telegram — регистрационный поток бота (email → привязка)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.bot_link_telegram(
  p_email TEXT, p_telegram_id BIGINT,
  p_name  TEXT DEFAULT '', p_phone TEXT DEFAULT ''
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_profile public.profiles%ROWTYPE;
BEGIN
  -- Уже привязан к этому же профилю?
  SELECT * INTO v_profile FROM public.profiles WHERE telegram_id = p_telegram_id;
  IF FOUND THEN
    RETURN json_build_object('ok', true, 'existed', true,
                             'user_id', v_profile.id, 'already_linked', true);
  END IF;

  -- Ищем профиль по email
  SELECT * INTO v_profile FROM public.profiles WHERE LOWER(email) = LOWER(TRIM(p_email));
  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'email_not_found');
  END IF;

  UPDATE public.profiles
  SET telegram_id       = p_telegram_id,
      telegram_username = NULL,
      full_name         = COALESCE(NULLIF(p_name,  ''), full_name),
      phone             = COALESCE(NULLIF(p_phone, ''), phone),
      updated_at        = now()
  WHERE id = v_profile.id;

  RETURN json_build_object('ok', true, 'existed', true, 'user_id', v_profile.id);
END;
$$;

-- ============================================================================
-- RPC: bot_get_active_sub — бот проверяет подписку по telegram_id
-- ============================================================================
CREATE OR REPLACE FUNCTION public.bot_get_active_sub(p_telegram_id BIGINT)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_user_id UUID;
  v_sub     public.subscriptions%ROWTYPE;
BEGIN
  SELECT id INTO v_user_id FROM public.profiles WHERE telegram_id = p_telegram_id;
  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'no_profile');
  END IF;

  SELECT * INTO v_sub FROM public.subscriptions
  WHERE user_id = v_user_id AND status = 'active' AND expires_at > now()
  ORDER BY expires_at DESC LIMIT 1;

  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'no_sub');
  END IF;

  RETURN json_build_object(
    'ok',        true,
    'plan',      v_sub.plan,
    'expires_at', v_sub.expires_at,
    'status',    v_sub.status
  );
END;
$$;

-- ============================================================================
-- RPC: bot_activate_sub — владелец активирует подписку через бот
-- ============================================================================
CREATE OR REPLACE FUNCTION public.bot_activate_sub(
  p_telegram_id BIGINT, p_plan TEXT,
  p_amount      NUMERIC  DEFAULT NULL,
  p_promo       TEXT     DEFAULT NULL,
  p_source      TEXT     DEFAULT 'telegram'
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_user_id UUID;
  v_months  INT;
  v_promo   TEXT;
  v_base    TIMESTAMPTZ;
  v_sub     public.subscriptions%ROWTYPE;
BEGIN
  SELECT id INTO v_user_id FROM public.profiles WHERE telegram_id = p_telegram_id;
  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'not_registered');
  END IF;

  v_months := public.plan_months(p_plan);
  IF v_months = 0 THEN
    RETURN json_build_object('ok', false, 'reason', 'bad_plan');
  END IF;

  v_promo := NULLIF(UPPER(TRIM(COALESCE(p_promo, ''))), '');

  SELECT MAX(expires_at) INTO v_base FROM public.subscriptions
    WHERE user_id = v_user_id AND status = 'active' AND expires_at > now();
  IF v_base IS NULL THEN v_base := now(); END IF;

  INSERT INTO public.subscriptions
    (user_id, plan, status, started_at, expires_at, amount, promo_code, source)
  VALUES
    (v_user_id, p_plan, 'active', now(),
     v_base + (v_months || ' months')::INTERVAL,
     p_amount, v_promo, p_source)
  RETURNING * INTO v_sub;

  IF v_promo IS NOT NULL THEN
    INSERT INTO public.promo_redemptions (code, user_id, discount)
    SELECT v_promo, v_user_id, pc.discount
    FROM public.promo_codes pc WHERE pc.code = v_promo
    ON CONFLICT (code, user_id) DO NOTHING;

    UPDATE public.promo_codes SET used_count = used_count + 1 WHERE code = v_promo;
  END IF;

  RETURN json_build_object(
    'ok',        true,
    'sub_id',    v_sub.id,
    'plan',      v_sub.plan,
    'expires_at', v_sub.expires_at
  );
END;
$$;

-- ============================================================================
-- RPC: bot_validate_promo — бот проверяет промокод (не списывает)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.bot_validate_promo(p_telegram_id BIGINT, p_code TEXT)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_user_id UUID;
  v_code    TEXT := UPPER(TRIM(p_code));
  v_row     public.promo_codes%ROWTYPE;
BEGIN
  SELECT id INTO v_user_id FROM public.profiles WHERE telegram_id = p_telegram_id;

  SELECT * INTO v_row FROM public.promo_codes WHERE code = v_code;
  IF NOT FOUND OR v_row.active IS FALSE THEN
    RETURN json_build_object('ok', false, 'reason', 'invalid');
  END IF;
  IF v_row.expires_at IS NOT NULL AND v_row.expires_at < now() THEN
    RETURN json_build_object('ok', false, 'reason', 'invalid');
  END IF;
  IF v_row.max_uses IS NOT NULL AND v_row.used_count >= v_row.max_uses THEN
    RETURN json_build_object('ok', false, 'reason', 'exhausted');
  END IF;
  IF v_user_id IS NOT NULL AND EXISTS (
    SELECT 1 FROM public.promo_redemptions r
    WHERE r.code = v_code AND r.user_id = v_user_id
  ) THEN
    RETURN json_build_object('ok', false, 'reason', 'already_used');
  END IF;
  RETURN json_build_object('ok', true, 'discount', v_row.discount);
END;
$$;

-- ============================================================================
-- Права доступа к публичным RPC (сайт вызывает через anon/authenticated)
-- bot_* функции вызываются ботом через service_role — явный GRANT не нужен.
-- ============================================================================
GRANT EXECUTE ON FUNCTION public.create_tg_link_token()             TO authenticated;
GRANT EXECUTE ON FUNCTION public.unlink_tg_account()                TO authenticated;

-- ============================================================================
-- ГОТОВО.
-- Следующие шаги:
-- 1. Применить этот файл в Supabase → SQL Editor → Run.
-- 2. Выставить переменные окружения бота:
--      SUPABASE_URL=https://ocrgpmlhtjghiamhbrhv.supabase.co
--      SUPABASE_SERVICE_KEY=<service_role key>
-- 3. Развернуть обновлённый бот на Railway/Render.
-- ============================================================================
