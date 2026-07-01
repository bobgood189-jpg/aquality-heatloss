-- ============================================================================
-- Закрыть публичный доступ к bot-only SECURITY DEFINER RPC.
--
-- Проблема: CREATE FUNCTION в Postgres по умолчанию выдаёт EXECUTE роли PUBLIC,
-- если это явно не отозвано. PostgREST (Supabase REST API) открывает любую
-- функцию схемы public как /rest/v1/rpc/<name> для ролей anon/authenticated,
-- если у этих ролей есть EXECUTE — а он у них есть по умолчанию, раз никто
-- его не отзывал. Ниже перечисленные функции — SECURITY DEFINER и НЕ проверяют
-- auth.uid()/is_admin(): их единственная защита задумывалась как «вызывает
-- только бот через SUPABASE_SERVICE_KEY». Без REVOKE любой посетитель сайта
-- мог вызвать их анонимным ключом (он публично лежит в index.html как
-- AQ_CFG.SUPABASE_ANON_KEY) — например bot_activate_sub(p_telegram_id, 'max_m12')
-- выдаёт себе бесплатную подписку, а bot_get_profile/bot_get_stats читают
-- чужие данные.
--
-- Найдено при аудите (2026-07-01): ни одна из функций ниже не имела REVOKE.
-- Идемпотентно: можно выполнять повторно.
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────
-- Отзываем EXECUTE у PUBLIC/anon/authenticated для ВСЕХ overload'ов каждой
-- bot-only функции (bot_activate_sub существует в двух сигнатурах — 5 и 8
-- аргументов, из telegram-schema.sql и v2-improvements.sql соответственно —
-- поэтому перебираем по имени через pg_proc, а не хардкодим сигнатуры).
-- ─────────────────────────────────────────────────────────────────────────
DO $$
DECLARE
  fn_name TEXT;
  fn_sig  TEXT;
BEGIN
  FOREACH fn_name IN ARRAY ARRAY[
    'bot_get_profile',        -- telegram-schema.sql, v2-improvements.sql
    'bot_link_telegram',      -- telegram-schema.sql
    'bot_get_active_sub',     -- telegram-schema.sql
    'bot_activate_sub',       -- telegram-schema.sql (5 args) + v2-improvements.sql (8 args)
    'bot_validate_promo',     -- telegram-schema.sql, v2-improvements.sql
    'bot_upsert_user',        -- v2-improvements.sql
    'bot_create_profile',     -- v2-improvements.sql
    'bot_log_event',          -- v2-improvements.sql
    'bot_get_stats',          -- v2-improvements.sql
    'link_tg_account',        -- telegram-schema.sql — не bot_*, но явно "вызывается ботом" (комментарий), без GRANT
    'cleanup_expired_tokens'  -- v2-improvements.sql — внутренний cron, не должен быть публичным RPC
  ]
  LOOP
    FOR fn_sig IN
      SELECT p.oid::regprocedure::text
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'public' AND p.proname = fn_name
    LOOP
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', fn_sig);
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM anon', fn_sig);
      EXECUTE format('REVOKE ALL ON FUNCTION %s FROM authenticated', fn_sig);
    END LOOP;
  END LOOP;
END $$;

-- ─────────────────────────────────────────────────────────────────────────
-- НЕ трогаем (осознанно оставляем публично вызываемыми):
--   public.is_admin(uuid)               — вызывается ИЗНУТРИ RLS-политик
--                                          (profiles/subscriptions/leads/...)
--                                          от имени anon/authenticated; без
--                                          EXECUTE эти политики сломаются.
--                                          Сама функция безопасна: с чужим uid
--                                          просто вернёт false.
--   create_tg_link_token/unlink_tg_account/validate_promo/admin_activate_sub/
--   plan_months/user_claim_free_promo   — уже есть явный
--                                          GRANT EXECUTE ... TO authenticated,
--                                          вызываются с сайта залогиненным
--                                          пользователем, это ожидаемо.
--   bot_list_pending_site_payments/bot_mark_site_payment_notified/
--   bot_activate_site_payment/bot_reject_site_payment
--                                        — уже содержат REVOKE ALL FROM PUBLIC
--                                          в самом site-payments-schema.sql.
-- ─────────────────────────────────────────────────────────────────────────

-- ─────────────────────────────────────────────────────────────────────────
-- Долгосрочный фикс: по умолчанию Postgres выдаёт PUBLIC EXECUTE любой НОВОЙ
-- функции в public. Без этой строки следующая bot_*-функция, которую кто-то
-- добавит, снова окажется публично вызываемой, пока её явно не отзовут.
-- Существующих GRANT (validate_promo и т.п.) эта команда не трогает — только
-- назначает privileges по умолчанию для функций, которые будут созданы позже
-- той же ролью (владельцем схемы, из-под которой выполняется этот файл).
-- ─────────────────────────────────────────────────────────────────────────
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- ============================================================================
-- ГОТОВО. Применить через Supabase SQL Editor (проект ocrgpmlhtjghiamhbrhv)
-- или Supabase MCP apply_migration, если он подключён в сессии.
--
-- Проверка после применения — этот запрос должен вернуть anon_can_exec=false
-- и auth_can_exec=false для КАЖДОЙ строки:
--
-- SELECT p.proname,
--        pg_catalog.pg_get_function_identity_arguments(p.oid) AS args,
--        has_function_privilege('anon', p.oid, 'EXECUTE')          AS anon_can_exec,
--        has_function_privilege('authenticated', p.oid, 'EXECUTE') AS auth_can_exec
-- FROM pg_proc p
-- JOIN pg_namespace n ON n.oid = p.pronamespace
-- WHERE n.nspname = 'public'
--   AND p.proname = ANY(ARRAY['bot_get_profile','bot_link_telegram','bot_get_active_sub',
--                             'bot_activate_sub','bot_validate_promo','bot_upsert_user',
--                             'bot_create_profile','bot_log_event','bot_get_stats',
--                             'link_tg_account','cleanup_expired_tokens'])
-- ORDER BY p.proname;
--
-- Живая проверка через REST (должна перестать отдавать 200+JSON, а не просто
-- "уйти в ошибку валидации" — PostgREST для функций без EXECUTE обычно отдаёт
-- 404 "Could not find function", т.к. скрывает её из схемы для этой роли, а
-- не 403 — это ожидаемо и означает, что доступ закрыт):
--
--   curl -s -o /dev/null -w '%{http_code}\n' \
--     -X POST 'https://ocrgpmlhtjghiamhbrhv.supabase.co/rest/v1/rpc/bot_get_stats' \
--     -H "apikey: <SUPABASE_ANON_KEY из index.html>" \
--     -H "Authorization: Bearer <тот же ключ>" \
--     -H "Content-Type: application/json" -d '{}'
--
-- До фикса — 200 с JSON статистикой. После — 404/401, тело без данных.
-- ============================================================================
