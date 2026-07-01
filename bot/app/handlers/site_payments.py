"""Подтверждение оплаты, оформленной на САЙТЕ (paywall-модалка, payIHavePaid()),
прямо из Telegram — без входа в админку сайта.

Отдельный путь от bot/app/handlers/review.py (тот обслуживает покупки,
оформленные ВНУТРИ бота через /shop, ключ — telegram_id). Здесь платежи лежат
в Supabase-таблице payments (ключ — user_id сайта), уведомление владельцу шлёт
_site_payment_notify_loop (bot/app/bot.py), подтверждение идёт через RPC
bot_activate_site_payment/bot_reject_site_payment (supabase/site-payments-schema.sql).

Callback data:
  sitepay:ok:<payment_id>   — подтвердить, активировать подписку
  sitepay:rej:<payment_id>  — отклонить
"""
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery

from .. import supabase_db as _sb
from ..config import SITE_URL
from .util import is_owner

router = Router()
log = logging.getLogger("aquality-bot.site_payments")

_PLAN_LABELS = {
    "max_m1": "Max · 1 мес", "max_m3": "Max · 3 мес",
    "max_m6": "Max · 6 мес", "max_m12": "Max · 12 мес",
    "pro_m1": "Pro · 1 мес", "pro_m3": "Pro · 3 мес",
    "pro_m6": "Pro · 6 мес", "pro_m12": "Pro · 12 мес",
    "m1": "1 мес", "m6": "6 мес", "m12": "12 мес",
}


def _plan_label(plan: str) -> str:
    return _PLAN_LABELS.get(plan, plan or "—")


def _fmt_sum(n) -> str:
    try:
        return f"{int(round(n)):,}".replace(",", " ") + " сум"
    except (TypeError, ValueError):
        return "—"


def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%d.%m.%Y")
    except Exception:
        return (iso or "—")[:10]


@router.callback_query(F.data.startswith("sitepay:ok:"))
async def cb_site_payment_ok(cb: CallbackQuery):
    if not is_owner(cb.from_user):
        return await cb.answer("Только для администратора.", show_alert=True)

    payment_id = cb.data.split(":", 2)[2]
    res = await _sb.activate_site_payment(payment_id, actor_tg=cb.from_user.id)

    if not res.get("ok"):
        reason = res.get("reason", "unknown")
        return await cb.answer(f"⚠️ Не удалось активировать: {reason}", show_alert=True)

    expires_str = _fmt_date(res.get("expires_at", ""))
    plan_label = _plan_label(res.get("plan"))
    who = res.get("email") or res.get("full_name") or str(res.get("user_id", ""))[:8]

    suffix = f"\n\n✅ <b>ПОДТВЕРЖДЁН</b> · {plan_label} до {expires_str}"
    try:
        await cb.message.edit_text((cb.message.text or "") + suffix, reply_markup=None)
    except Exception:
        pass

    tg_id = res.get("telegram_id")
    if tg_id:
        try:
            await cb.bot.send_message(
                tg_id,
                f"🎉 <b>Оплата подтверждена!</b> Тариф {plan_label} активирован.\n\n"
                f"📅 Действует до: <b>{expires_str}</b>\n\n"
                f"Заходите на сайт: {SITE_URL}\n\n"
                "Спасибо, что выбрали Aquality! 💙"
            )
        except Exception as e:
            log.warning("Site payment client notify failed for %s: %s", payment_id, e)

    await cb.answer(f"✅ Активировано для {who}, до {expires_str}.")


@router.callback_query(F.data.startswith("sitepay:rej:"))
async def cb_site_payment_reject(cb: CallbackQuery):
    if not is_owner(cb.from_user):
        return await cb.answer("Только для администратора.", show_alert=True)

    payment_id = cb.data.split(":", 2)[2]
    res = await _sb.reject_site_payment(payment_id, actor_tg=cb.from_user.id)

    if not res.get("ok"):
        reason = res.get("reason", "unknown")
        return await cb.answer(f"⚠️ Не удалось отклонить: {reason}", show_alert=True)

    suffix = "\n\n❌ <b>ОТКЛОНЁН</b>"
    try:
        await cb.message.edit_text((cb.message.text or "") + suffix, reply_markup=None)
    except Exception:
        pass

    await cb.answer("❌ Заявка отклонена.")
