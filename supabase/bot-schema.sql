-- ============================================================================
-- Aquality Bot — Supabase integration (already applied via MCP migration)
-- Adds telegram_id to profiles + bot_* RPC functions for the Telegram bot.
-- Run AFTER schema.sql and payment-schema.sql.
-- Идемпотентно: можно выполнять повторно.
-- ============================================================================

-- 1. Add telegram_id to profiles
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS telegram_id bigint UNIQUE;

CREATE INDEX IF NOT EXISTS profiles_telegram_idx
  ON public.profiles(telegram_id)
  WHERE telegram_id IS NOT NULL;

-- 2. Update handle_new_user trigger to capture telegram_id from user_metadata
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
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

-- 3–7. RPC functions for the bot (see applied migration bot_telegram_integration)
-- bot_get_profile(p_telegram_id)       — get profile by tg id
-- bot_link_telegram(email, tg_id, name, phone) — link tg id to profile
-- bot_get_active_sub(p_telegram_id)    — check active subscription
-- bot_validate_promo(tg_id, code)      — validate promo code
-- bot_activate_sub(tg_id, plan, amount, promo, source) — activate sub

-- ============================================================================
-- Bot .env configuration:
--   SUPABASE_URL=https://uhyomjdsswasmlycpoyh.supabase.co
--   SUPABASE_SERVICE_KEY=<service_role key from Supabase Dashboard → Settings → API>
--   PAYWALL=1
-- ============================================================================
