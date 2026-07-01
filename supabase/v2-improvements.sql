-- ============================================================
-- Aquality — Database v2 improvements
-- Применять ПОСЛЕ schema.sql + payment-schema.sql + telegram-schema.sql
-- Идемпотентно: можно запускать повторно.
-- ============================================================

-- ─── INDEXES ─────────────────────────────────────────────────────────────────

-- 1. Critical: case-insensitive email lookup (bot registration — 4x→1x round-trip)
CREATE UNIQUE INDEX IF NOT EXISTS profiles_email_lower_idx
  ON public.profiles (LOWER(email))
  WHERE email IS NOT NULL;

-- 2. Fast subscription expiry check (expiry notification loop)
CREATE INDEX IF NOT EXISTS subscriptions_expires_active_idx
  ON public.subscriptions (expires_at)
  WHERE status = 'active';

-- 3. Fast active-sub lookup per user
CREATE INDEX IF NOT EXISTS subscriptions_user_active_idx
  ON public.subscriptions (user_id)
  WHERE status = 'active';

-- 4. Promo code lookup (only active codes)
CREATE INDEX IF NOT EXISTS promo_codes_active_idx
  ON public.promo_codes (code)
  WHERE active = true;

-- 5. Expired token cleanup
CREATE INDEX IF NOT EXISTS tg_link_tokens_expires_idx
  ON public.tg_link_tokens (expires_at)
  WHERE used = false;

-- 6. Token lookup by user_id (delete-before-insert)
CREATE INDEX IF NOT EXISTS tg_link_tokens_user_idx
  ON public.tg_link_tokens (user_id);

-- 7. Payments by user
CREATE INDEX IF NOT EXISTS payments_user_idx
  ON public.payments (user_id, created_at DESC);

-- 8. Leads by source
CREATE INDEX IF NOT EXISTS leads_source_idx
  ON public.leads (source, created_at DESC);

-- ─── NEW TABLES ──────────────────────────────────────────────────────────────

-- bot_events: lightweight analytics (calc_start, calc_done, reg_start, etc.)
CREATE TABLE IF NOT EXISTS public.bot_events (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tg_id      BIGINT NOT NULL,
  event      TEXT   NOT NULL,
  payload    JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS bot_events_tg_idx    ON public.bot_events (tg_id, created_at DESC);
CREATE INDEX IF NOT EXISTS bot_events_event_idx ON public.bot_events (event, created_at DESC);

ALTER TABLE public.bot_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "no direct access to bot_events" ON public.bot_events;
CREATE POLICY "no direct access to bot_events" ON public.bot_events
  FOR ALL USING (false);

-- admin_audit: owner action journal (grant_sub, revoke_sub, add_promo, etc.)
CREATE TABLE IF NOT EXISTS public.admin_audit (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor_id   UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  actor_tg   BIGINT,
  action     TEXT NOT NULL,
  target_id  BIGINT,
  details    JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS admin_audit_actor_idx  ON public.admin_audit (actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS admin_audit_action_idx ON public.admin_audit (action, created_at DESC);

ALTER TABLE public.admin_audit ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "no direct access to admin_audit" ON public.admin_audit;
CREATE POLICY "no direct access to admin_audit" ON public.admin_audit
  FOR ALL USING (false);

-- ─── IMPROVED RPC FUNCTIONS ──────────────────────────────────────────────────

-- bot_upsert_user: atomic find-or-link in ONE round-trip
CREATE OR REPLACE FUNCTION public.bot_upsert_user(
  p_telegram_id BIGINT,
  p_email       TEXT,
  p_name        TEXT    DEFAULT '',
  p_phone       TEXT    DEFAULT '',
  p_username    TEXT    DEFAULT ''
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_profile public.profiles%ROWTYPE;
  v_email   TEXT := LOWER(TRIM(p_email));
BEGIN
  -- Already have a profile with this telegram_id?
  SELECT * INTO v_profile FROM public.profiles WHERE telegram_id = p_telegram_id;
  IF FOUND THEN
    RETURN json_build_object(
      'ok', true, 'status', 'already_linked',
      'user_id', v_profile.id, 'email', v_profile.email
    );
  END IF;

  -- Profile exists with this email — link telegram to it
  SELECT * INTO v_profile FROM public.profiles WHERE LOWER(email) = v_email;
  IF FOUND THEN
    UPDATE public.profiles
    SET telegram_id       = p_telegram_id,
        telegram_username = NULLIF(p_username, ''),
        full_name         = COALESCE(NULLIF(TRIM(p_name), ''), full_name),
        phone             = COALESCE(NULLIF(TRIM(p_phone), ''), phone),
        updated_at        = NOW()
    WHERE id = v_profile.id;
    RETURN json_build_object(
      'ok', true, 'status', 'linked_existing',
      'user_id', v_profile.id, 'email', v_profile.email
    );
  END IF;

  RETURN json_build_object('ok', false, 'reason', 'email_not_found');
END;
$$;

-- bot_create_profile: called after Admin API creates auth user
CREATE OR REPLACE FUNCTION public.bot_create_profile(
  p_user_id     UUID,
  p_telegram_id BIGINT,
  p_email       TEXT,
  p_name        TEXT  DEFAULT '',
  p_phone       TEXT  DEFAULT '',
  p_username    TEXT  DEFAULT ''
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles
    (id, email, full_name, phone, telegram_id, telegram_username, client_type, role)
  VALUES
    (p_user_id, LOWER(TRIM(p_email)),
     NULLIF(TRIM(p_name), ''), NULLIF(TRIM(p_phone), ''),
     p_telegram_id, NULLIF(TRIM(p_username), ''),
     'client', 'user')
  ON CONFLICT (id) DO UPDATE
    SET telegram_id       = COALESCE(profiles.telegram_id, EXCLUDED.telegram_id),
        telegram_username = COALESCE(profiles.telegram_username, EXCLUDED.telegram_username),
        full_name         = COALESCE(EXCLUDED.full_name, profiles.full_name),
        phone             = COALESCE(EXCLUDED.phone, profiles.phone),
        updated_at        = NOW();
  RETURN json_build_object('ok', true, 'user_id', p_user_id);
EXCEPTION WHEN unique_violation THEN
  RETURN json_build_object('ok', false, 'reason', 'telegram_already_linked');
END;
$$;

-- bot_get_profile: profile + active sub in one call
CREATE OR REPLACE FUNCTION public.bot_get_profile(p_telegram_id BIGINT)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_profile public.profiles%ROWTYPE;
  v_sub     public.subscriptions%ROWTYPE;
BEGIN
  SELECT * INTO v_profile FROM public.profiles WHERE telegram_id = p_telegram_id;
  IF NOT FOUND THEN
    RETURN json_build_object('ok', false, 'reason', 'not_found');
  END IF;
  SELECT * INTO v_sub FROM public.subscriptions
  WHERE user_id = v_profile.id AND status = 'active' AND expires_at > NOW()
  ORDER BY expires_at DESC LIMIT 1;
  RETURN json_build_object(
    'ok',          true,
    'user_id',     v_profile.id,
    'email',       v_profile.email,
    'full_name',   v_profile.full_name,
    'phone',       v_profile.phone,
    'telegram_id', v_profile.telegram_id,
    'role',        v_profile.role,
    'has_sub',     (v_sub.id IS NOT NULL),
    'sub_plan',    v_sub.plan,
    'sub_expires', v_sub.expires_at
  );
END;
$$;

-- bot_log_event: fire-and-forget analytics
CREATE OR REPLACE FUNCTION public.bot_log_event(
  p_tg_id BIGINT, p_event TEXT, p_data JSONB DEFAULT NULL
)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.bot_events (tg_id, event, payload) VALUES (p_tg_id, p_event, p_data);
END;
$$;

-- bot_activate_sub: now records admin_audit
CREATE OR REPLACE FUNCTION public.bot_activate_sub(
  p_telegram_id BIGINT, p_plan TEXT,
  p_amount      NUMERIC  DEFAULT NULL,
  p_promo       TEXT     DEFAULT NULL,
  p_source      TEXT     DEFAULT 'telegram',
  p_actor_tg    BIGINT   DEFAULT NULL
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
    WHERE user_id = v_user_id AND status = 'active' AND expires_at > NOW();
  IF v_base IS NULL THEN v_base := NOW(); END IF;
  INSERT INTO public.subscriptions
    (user_id, plan, status, started_at, expires_at, amount, promo_code, source)
  VALUES
    (v_user_id, p_plan, 'active', NOW(),
     v_base + (v_months || ' months')::INTERVAL, p_amount, v_promo, p_source)
  RETURNING * INTO v_sub;
  IF v_promo IS NOT NULL THEN
    INSERT INTO public.promo_redemptions (code, user_id, discount)
    SELECT v_promo, v_user_id, pc.discount FROM public.promo_codes pc WHERE pc.code = v_promo
    ON CONFLICT (code, user_id) DO NOTHING;
    UPDATE public.promo_codes SET used_count = used_count + 1 WHERE code = v_promo;
  END IF;
  INSERT INTO public.admin_audit (actor_tg, action, target_id, details)
  VALUES (p_actor_tg, 'grant_sub', p_telegram_id,
          jsonb_build_object('plan', p_plan, 'expires_at', v_sub.expires_at,
                             'amount', p_amount, 'promo', v_promo));
  RETURN json_build_object(
    'ok', true, 'sub_id', v_sub.id,
    'plan', v_sub.plan, 'expires_at', v_sub.expires_at
  );
END;
$$;

-- cleanup_expired_tokens: call periodically
CREATE OR REPLACE FUNCTION public.cleanup_expired_tokens()
RETURNS INT LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_count INT;
BEGIN
  DELETE FROM public.tg_link_tokens
  WHERE expires_at < NOW() - INTERVAL '1 hour' OR used = true;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$;

-- bot_get_stats: owner dashboard stats
CREATE OR REPLACE FUNCTION public.bot_get_stats()
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_users       INT; v_active_subs INT;
  v_revenue_30d NUMERIC; v_leads_30d INT; v_bot_users INT;
BEGIN
  SELECT COUNT(*) INTO v_users FROM public.profiles;
  SELECT COUNT(*) INTO v_bot_users FROM public.profiles WHERE telegram_id IS NOT NULL;
  SELECT COUNT(*) INTO v_active_subs FROM public.subscriptions
    WHERE status = 'active' AND expires_at > NOW();
  SELECT COALESCE(SUM(amount), 0) INTO v_revenue_30d FROM public.subscriptions
    WHERE status = 'active' AND started_at >= NOW() - INTERVAL '30 days';
  SELECT COUNT(*) INTO v_leads_30d FROM public.leads
    WHERE created_at >= NOW() - INTERVAL '30 days';
  RETURN json_build_object(
    'total_users', v_users, 'bot_users', v_bot_users,
    'active_subs', v_active_subs, 'revenue_30d', v_revenue_30d, 'leads_30d', v_leads_30d
  );
END;
$$;

-- ─── ADMIN VIEW ───────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW public.v_admin_subscribers AS
SELECT p.telegram_id, p.email, p.full_name, p.phone,
       s.plan, s.expires_at, s.amount, s.promo_code, s.source, s.started_at
FROM public.subscriptions s
JOIN public.profiles p ON p.id = s.user_id
WHERE s.status = 'active' AND s.expires_at > NOW()
ORDER BY s.expires_at DESC;
