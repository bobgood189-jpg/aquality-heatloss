#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Деплой SMS-OTP интеграции (Eskiz.uz) в Supabase, проект ocrgpmlhtjghiamhbrhv.
#
# Что делает:
#   1) проверяет, что CLI залогинен и проект слинкован;
#   2) безопасно спрашивает пароль Eskiz (не попадает в историю shell);
#   3) выставляет секреты ESKIZ_EMAIL / ESKIZ_PASSWORD / ESKIZ_FROM;
#   4) деплоит функции send-sms-otp/verify-sms-otp (подтверждение телефона
#      при регистрации) и send-sms-reset/verify-sms-reset (сброс пароля по
#      SMS) — общий модуль _shared/eskiz.ts подтягивается автоматически;
#   5) напоминает про SQL (его применяют вручную в SQL Editor).
#
# Запуск:   bash scripts/deploy-sms.sh
# Требует:  залогиненный CLI  →  npx supabase@latest login
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SB="npx --yes supabase@latest"
PROJECT_REF="ocrgpmlhtjghiamhbrhv"
ESKIZ_EMAIL_DEFAULT="bobgood189@gmail.com"
ESKIZ_FROM_DEFAULT="4546"

cd "$(dirname "$0")/.."

echo "→ Проверяю авторизацию CLI…"
if ! $SB projects list >/dev/null 2>&1; then
  echo "✗ CLI не залогинен. Выполните: npx supabase@latest login" >&2
  exit 1
fi

# Секреты. Пароль читаем скрыто — он не попадёт ни в argv, ни в историю.
read -rp "ESKIZ_EMAIL [${ESKIZ_EMAIL_DEFAULT}]: " ESKIZ_EMAIL
ESKIZ_EMAIL="${ESKIZ_EMAIL:-$ESKIZ_EMAIL_DEFAULT}"
read -rp "ESKIZ_FROM (ник отправителя) [${ESKIZ_FROM_DEFAULT}]: " ESKIZ_FROM
ESKIZ_FROM="${ESKIZ_FROM:-$ESKIZ_FROM_DEFAULT}"
read -rsp "ESKIZ_PASSWORD (ввод скрыт): " ESKIZ_PASSWORD; echo
if [ -z "$ESKIZ_PASSWORD" ]; then echo "✗ Пароль пустой — прерываю." >&2; exit 1; fi

echo "→ Выставляю секреты…"
$SB secrets set \
  "ESKIZ_EMAIL=${ESKIZ_EMAIL}" \
  "ESKIZ_FROM=${ESKIZ_FROM}" \
  "ESKIZ_PASSWORD=${ESKIZ_PASSWORD}" \
  --project-ref "$PROJECT_REF"

echo "→ Деплою функции…"
$SB functions deploy send-sms-otp     --project-ref "$PROJECT_REF"
$SB functions deploy verify-sms-otp   --project-ref "$PROJECT_REF"
$SB functions deploy send-sms-reset   --project-ref "$PROJECT_REF"
$SB functions deploy verify-sms-reset --project-ref "$PROJECT_REF"

cat <<'EOF'

✓ Функции задеплоены и секреты установлены.

Осталось два ручных шага:
  1. SQL: Supabase Dashboard → SQL Editor → выполнить supabase/otp-sms-schema.sql
     и supabase/sms-reset-codes-schema.sql
  2. Тест: см. команду curl ниже (подставьте свой номер 998XXXXXXXXX).

⚠ Пока Eskiz не одобрил ник отправителя, аккаунт шлёт только текст
  "Bu Eskiz dan test". До модерации временно замените текст в
  supabase/functions/send-sms-otp/index.ts на "Bu Eskiz dan test",
  задеплойте, проверьте, затем верните обратно.
EOF
