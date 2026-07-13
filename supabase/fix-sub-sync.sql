-- ============================================================================
-- Фикс рассинхрона «оплата в TG подтверждена, сайт подписку не видит».
-- См. docs/fix-tg-sub-sync-prompt.md для полного разбора гипотез H1-H5.
--
-- Что делает:
--  1) Убирает устаревшую 5-аргументную перегрузку bot_activate_sub
--     (telegram-schema.sql) — с ней остаётся только 8-аргументная версия
--     (v2-improvements.sql), которую реально вызывает bot/app/supabase_db.py.
--     На практике PostgREST и так резолвил вызов в 8-арг версию однозначно
--     (бот всегда шлёт все 8 именованных параметров, которых нет в 5-арг
--     сигнатуре) — но держать в БД два bot_activate_sub с разной логикой
--     (5-арг не пишет admin_audit и не делает email-fallback) — источник
--     будущих ошибок и путаницы, поэтому убираем совсем.
--  2) Гарантирует, что subscriptions.plan принимает все id из SHOP_PLANS/
--     AQ_PLANS (pro_m1..pro_m12, max_m1..max_m12 + legacy m1/m6/m12) —
--     ТОЛЬКО если ещё не применена ideal-v1-stage1.sql (которая заменяет
--     CHECK на FK subscriptions_plan_fk → plans). Если FK уже стоит —
--     ничего не трогаем (иначе воспроизведём собственный баг
--     ideal-v1-stage1.sql: "повторный прогон v2-improvements.sql вернёт CHECK").
--  3) Обновляет bot_activate_sub (8-арг): возвращает email и user_id профиля,
--     на который реально легла подписка, плюс email_mismatch — если email
--     заказа не совпал с email профиля (H3 — telegram_id уже привязан к
--     другому/старому профилю). Пишет то же самое в admin_audit.
--  4) Переприменяет REVOKE EXECUTE для bot_activate_sub (idempotent,
--     дублирует revoke-bot-rpc-execute.sql на случай гонки миграций).
--
-- Идемпотентно: можно выполнять повторно.
-- Применить через Supabase SQL Editor (проект ocrgpmlhtjghiamhbrhv) ПОСЛЕ
-- payment-schema.sql, telegram-schema.sql, v2-improvements.sql.
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────
-- 1. Убрать устаревшую 5-арг перегрузку bot_activate_sub.
-- ─────────────────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.bot_activate_sub(BIGINT, TEXT, NUMERIC, TEXT, TEXT);

-- ─────────────────────────────────────────────────────────────────────────
-- 2. Constraint на subscriptions.plan — только если FK ещё не применён.
-- ─────────────────────────────────────────────────────────────────────────
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'subscriptions_plan_fk') THEN
    ALTER TABLE public.subscriptions DROP CONSTRAINT IF EXISTS subscriptions_plan_check;
    ALTER TABLE public.subscriptions ADD CONSTRAINT subscriptions_plan_check
      CHECK (plan IN ('m1','m6','m12',
                      'pro_m1','pro_m3','pro_m6','pro_m12',
                      'max_m1','max_m3','max_m6','max_m12'));
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────
-- 3. bot_activate_sub (8-арг): + email/user_id/email_mismatch в ответе и
--    в admin_audit. Логика поиска профиля НЕ меняется (telegram_id → email
--    fallback, линковка только если telegram_id был NULL) — меняется только
--    что мы теперь ВИДИМ результат, а не гадаем по нему постфактум.
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.bot_activate_sub(
  p_telegram_id BIGINT, p_plan TEXT,
  p_amount      NUMERIC  DEFAULT NULL,
  p_promo       TEXT     DEFAULT NULL,
  p_source      TEXT     DEFAULT 'telegram',
  p_actor_tg    BIGINT   DEFAULT NULL,
  p_months      INT      DEFAULT NULL,
  p_email       TEXT     DEFAULT NULL
)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_user_id        UUID;
  v_profile_email  TEXT;
  v_months         INT;
  v_promo          TEXT;
  v_base           TIMESTAMPTZ;
  v_sub            public.subscriptions%ROWTYPE;
  v_email_mismatch BOOLEAN;
BEGIN
  SELECT id, email INTO v_user_id, v_profile_email
    FROM public.profiles WHERE telegram_id = p_telegram_id;

  IF v_user_id IS NULL AND p_email IS NOT NULL AND TRIM(p_email) <> '' THEN
    SELECT id, email INTO v_user_id, v_profile_email
      FROM public.profiles WHERE LOWER(email) = LOWER(TRIM(p_email));
    IF FOUND THEN
      UPDATE public.profiles SET telegram_id = p_telegram_id, updated_at = NOW()
        WHERE id = v_user_id AND telegram_id IS NULL;
    END IF;
  END IF;

  IF v_user_id IS NULL THEN
    RETURN json_build_object('ok', false, 'reason', 'not_registered');
  END IF;
  v_months := COALESCE(p_months, public.plan_months(p_plan));
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

  v_email_mismatch := (p_email IS NOT NULL AND TRIM(p_email) <> ''
                        AND LOWER(TRIM(p_email)) <> LOWER(COALESCE(v_profile_email, '')));

  INSERT INTO public.admin_audit (actor_tg, action, target_id, details)
  VALUES (p_actor_tg, 'grant_sub', p_telegram_id,
          jsonb_build_object('plan', p_plan, 'expires_at', v_sub.expires_at,
                             'amount', p_amount, 'promo', v_promo,
                             'user_id', v_user_id, 'profile_email', v_profile_email,
                             'order_email', p_email, 'email_mismatch', v_email_mismatch));

  RETURN json_build_object(
    'ok', true, 'sub_id', v_sub.id,
    'plan', v_sub.plan, 'expires_at', v_sub.expires_at,
    'user_id', v_user_id, 'email', v_profile_email,
    'email_mismatch', v_email_mismatch
  );
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────
-- 4. REVOKE защита не пострадала после CREATE OR REPLACE (защита на функцию,
--    не на её тело — но переприменяем на случай, если этот файл когда-нибудь
--    выполнится ДО revoke-bot-rpc-execute.sql).
-- ─────────────────────────────────────────────────────────────────────────
DO $$
DECLARE fn_sig TEXT;
BEGIN
  FOR fn_sig IN
    SELECT p.oid::regprocedure::text
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.proname = 'bot_activate_sub'
  LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', fn_sig);
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', fn_sig);
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', fn_sig);
  END LOOP;
END $$;

-- ============================================================================
-- ГОТОВО. Проверка после применения:
--
-- 1) Ровно одна сигнатура bot_activate_sub (8 аргументов):
--    SELECT p.oid::regprocedure FROM pg_proc p JOIN pg_namespace n
--      ON n.oid = p.pronamespace
--    WHERE n.nspname='public' AND p.proname='bot_activate_sub';
--
-- 2) Текущий constraint на plan (CHECK или FK — оба варианта корректны):
--    SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
--    WHERE conrelid = 'public.subscriptions'::regclass
--      AND conname IN ('subscriptions_plan_check','subscriptions_plan_fk');
--
-- 3) email_mismatch реально приходит в ответе — тестовый вызов сервисным
--    ключом (замените значения на реальные из тестового заказа):
--    SELECT public.bot_activate_sub(p_telegram_id := 123, p_plan := 'pro_m1',
--                                    p_months := 1, p_email := 'test@example.com');
-- ============================================================================
