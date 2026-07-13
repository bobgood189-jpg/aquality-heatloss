-- ============================================================================
-- Диагностика: «оплата в TG подтверждена, сайт подписку не видит».
-- См. docs/fix-tg-sub-sync-prompt.md для разбора гипотез H1-H5.
--
-- READ-ONLY: ничего не меняет. Выполнить в Supabase SQL Editor (проект
-- ocrgpmlhtjghiamhbrhv) и прислать результат каждого блока.
-- ============================================================================

-- ── 1. Обе ли сигнатуры bot_activate_sub ещё живы? (H2) ─────────────────────
-- Ожидание ПОСЛЕ применения fix-sub-sync.sql: ровно одна строка (8 аргументов).
-- Если сейчас (до фикса) их две — это подтверждает риск из H2, хотя сам бот
-- по факту резолвится в 8-арг версию (см. разбор в docs/fix-tg-sub-sync-prompt.md).
SELECT p.oid::regprocedure AS signature,
       pg_get_function_identity_arguments(p.oid) AS args
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname = 'bot_activate_sub';

-- ── 2. Текущий constraint на subscriptions.plan (H4) ────────────────────────
-- Смотрим: subscriptions_plan_check (со списком id) ИЛИ subscriptions_plan_fk
-- (если применена ideal-v1-stage1.sql). Если это check с ТОЛЬКО ('m1','m6','m12')
-- без pro_m*/max_m* — v2-improvements.sql не применён, и КАЖДАЯ покупка
-- pro_mN/max_mN сейчас падает с ошибкой (админ увидит "ОШИБКА АКТИВАЦИИ",
-- клиент НЕ получит "🎉" — если у вас другой симптом, это не ваш случай).
SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.subscriptions'::regclass
  AND conname IN ('subscriptions_plan_check', 'subscriptions_plan_fk');

-- ── 3. Дублирующиеся email/telegram_id в profiles (H3) ──────────────────────
-- Дубли email: обычно означает несколько auth-аккаунтов на одну почту
-- (не должно быть возможным через обычную регистрацию, но create_auth_user
-- в боте создаёт аккаунт напрямую через Admin API).
SELECT lower(email) AS email_lc, count(*) AS profiles_count,
       array_agg(id) AS profile_ids, array_agg(telegram_id) AS telegram_ids
FROM public.profiles
GROUP BY lower(email)
HAVING count(*) > 1;

-- Дубли telegram_id (не должно быть возможным — UNIQUE — но проверяем на
-- случай гонки/старой схемы без constraint):
SELECT telegram_id, count(*) AS profiles_count, array_agg(id) AS profile_ids,
       array_agg(email) AS emails
FROM public.profiles
WHERE telegram_id IS NOT NULL
GROUP BY telegram_id
HAVING count(*) > 1;

-- ── 4. Последние 20 подписок — на какие profile/email реально легли (H1/H3) ─
SELECT s.id, s.plan, s.status, s.started_at, s.expires_at, s.source,
       s.just_activated, p.id AS profile_id, p.email, p.telegram_id
FROM public.subscriptions s
JOIN public.profiles p ON p.id = s.user_id
ORDER BY s.started_at DESC
LIMIT 20;

-- ── 5. Последние 20 записей admin_audit (grant_sub) ─────────────────────────
-- После применения fix-sub-sync.sql в details появятся user_id/profile_email/
-- order_email/email_mismatch — сразу видно, если бот попал не в тот профиль.
SELECT created_at, actor_tg, action, target_id, details
FROM public.admin_audit
WHERE action = 'grant_sub'
ORDER BY created_at DESC
LIMIT 20;

-- ── 6. Проверка конкретного telegram_id ПЕРЕД покупкой (H3, целевой запрос) ─
-- Замените <TELEGRAM_ID> на id покупателя (бот показывает его в /myid) —
-- покажет, привязан ли этот telegram_id к профилю с ДРУГИМ email, чем тот,
-- который покупатель вводил в боте.
-- SELECT id, email, telegram_id, created_at FROM public.profiles
-- WHERE telegram_id = <TELEGRAM_ID>;

-- ============================================================================
-- Что ещё нужно проверить ВНЕ Supabase (недоступно из этой сессии — H1):
--
--  • Railway → сервис бота → Variables: реально ли задан SUPABASE_SERVICE_KEY
--    (bot/README.md инструкция для Railway его не упоминает вовсе — см. H1).
--  • Railway → Logs: после этого фикса при активации без SUPABASE_SERVICE_KEY
--    бот больше НЕ активирует локально молча — ищите строку
--    "PAYWALL включён, но SUPABASE_SERVICE_KEY не задан — активация отклонена".
--  • Локальный bot/aquality_bot.db (SQLite) → таблица subscriptions: если там
--    появляются строки с недавними датами — это прямое доказательство H1
--    (это тот самый "тихий локальный fallback").
-- ============================================================================
