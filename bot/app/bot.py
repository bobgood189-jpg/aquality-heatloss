"""Entry point. Long-polling aiogram 3.x bot.

    export BOT_TOKEN='123456:ABC...'   # from @BotFather
    python -m app.bot
"""
import asyncio
import logging
import math
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from .config import require_token, SB_CONFIGURED, ADMIN_CHAT_ID
from . import storage
from . import supabase_db as _sb
from . import keyboards as K
from .handlers import menu, admin, wizard, results, payments, auth, shop, review, site_payments, account
from .i18n import t

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aquality-bot")

_EXPIRY_CHECK_INTERVAL = 86400  # раз в сутки


def _make_bot(token):
    """Construct a Bot with HTML parse mode, across aiogram 3.x variants."""
    try:
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        return Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    except Exception:
        return Bot(token, parse_mode="HTML")


async def _set_commands(bot):
    await bot.set_my_commands([
        BotCommand(command="start",  description="Меню / Menyu / Menu"),
        BotCommand(command="buy",    description="Купить подписку 🛒"),
        BotCommand(command="status", description="Статус текущего заказа 📋"),
        BotCommand(command="mysub",  description="Моя подписка / Mening obuna"),
        BotCommand(command="help",   description="Справка и поддержка"),
        BotCommand(command="link",   description="Привязать аккаунт / Akkaunt bog'lash"),
        BotCommand(command="account", description="Мой аккаунт 👤"),
        BotCommand(command="resetpass", description="Сбросить пароль сайта 🔑"),
        BotCommand(command="reset",  description="Сбросить расчёт"),
        BotCommand(command="myid",   description="Мой Telegram ID"),
        BotCommand(command="stats",  description="Статистика (владелец)"),
    ])


async def _check_expiry_once(bot: Bot):
    """Отправляет предупреждения пользователям с истекающими подписками (SQLite)."""
    import time as _time
    expiring = storage.get_expiring_subs(within_days=3)
    for sub in expiring:
        uid = sub["tg_user_id"]
        lang = sub.get("lang") or "ru"
        date = datetime.fromtimestamp(sub["expires_ts"]).strftime("%d.%m.%Y")
        days = math.ceil((sub["expires_ts"] - _time.time()) / 86400)
        try:
            if days <= 1:
                msg = t("sub_expiry_tomorrow", lang, date=date)
            else:
                msg = t("sub_expiry_warn", lang, n=days, date=date)
            await bot.send_message(uid, msg)
            log.info("Expiry warning sent to %s (%d days)", uid, days)
        except Exception as e:
            log.warning("Could not warn %s: %s", uid, e)

    expired = storage.get_expired_subs_unnotified()
    for sub in expired:
        uid = sub["tg_user_id"]
        lang = sub.get("lang") or "ru"
        try:
            await bot.send_message(uid, t("sub_expired_warn", lang))
            storage.cancel_sub(uid)
            log.info("Expired notice sent to %s", uid)
        except Exception as e:
            log.warning("Could not notify expired %s: %s", uid, e)


async def _expiry_loop(bot: Bot):
    await asyncio.sleep(60)
    while True:
        try:
            await _check_expiry_once(bot)
        except Exception as e:
            log.error("Expiry check failed: %s", e)
        await asyncio.sleep(_EXPIRY_CHECK_INTERVAL)


_REVIEW_CHECK_INTERVAL = 900  # check every 15 minutes

_SITE_PAYMENT_POLL_INTERVAL = 25  # seconds — site payments awaiting owner notification

_RESET_CODE_POLL_INTERVAL = 4  # seconds — user is watching the site live for this code

_SITE_PROVIDER_LABELS = {
    "tg": "Telegram", "humo": "HUMO", "uzcard": "Uzcard", "visa": "Visa",
    "master": "MasterCard", "paypal": "PayPal", "sbp": "СБП", "manual": "Вручную",
}
_SITE_PLAN_LABELS = {
    "max_m1": "Max · 1 мес", "max_m3": "Max · 3 мес",
    "max_m6": "Max · 6 мес", "max_m12": "Max · 12 мес",
    "pro_m1": "Pro · 1 мес", "pro_m3": "Pro · 3 мес",
    "pro_m6": "Pro · 6 мес", "pro_m12": "Pro · 12 мес",
    "m1": "1 мес", "m6": "6 мес", "m12": "12 мес",
}


async def _notify_site_payment(bot: Bot, pay: dict):
    raw = pay.get("raw") or {}
    plan = _SITE_PLAN_LABELS.get(raw.get("plan"), raw.get("plan") or "—")
    provider = _SITE_PROVIDER_LABELS.get(pay.get("provider"), pay.get("provider") or "—")
    who = pay.get("email") or pay.get("full_name") or str(pay.get("user_id", ""))[:8]
    try:
        amount = f"{int(round(pay.get('amount') or 0)):,}".replace(",", " ") + " сум"
    except (TypeError, ValueError):
        amount = "—"
    created = pay.get("created_at", "")[:16].replace("T", " ")

    text = (
        "💳 <b>Новая заявка на оплату (сайт)</b>\n\n"
        f"👤 {who}\n"
        f"📦 Тариф: <b>{plan}</b>\n"
        f"💰 Сумма: <b>{amount}</b>\n"
        f"🏦 Способ: {provider}\n"
        f"🕐 {created}"
    )
    await bot.send_message(ADMIN_CHAT_ID, text, reply_markup=K.site_payment_review_kb(pay["id"]))


async def _site_payment_notify_loop(bot: Bot):
    if not SB_CONFIGURED:
        return
    await asyncio.sleep(30)
    while True:
        try:
            for pay in await _sb.list_pending_site_payments():
                try:
                    await _notify_site_payment(bot, pay)
                    await _sb.mark_site_payment_notified(pay["id"])
                    log.info("Notified owner about site payment %s", pay["id"])
                except Exception as e:
                    log.warning("Could not notify owner about site payment %s: %s", pay.get("id"), e)
        except Exception as e:
            log.error("Site payment poll failed: %s", e)
        await asyncio.sleep(_SITE_PAYMENT_POLL_INTERVAL)


async def _reset_code_notify_loop(bot: Bot):
    """Delivers site-requested password-reset codes to the user's Telegram chat.
    Short interval — the user is watching the site's forgot-password screen live."""
    if not SB_CONFIGURED:
        return
    while True:
        try:
            for rec in await _sb.list_pending_reset_codes():
                try:
                    lang = storage.get_user_lang(rec["telegram_id"]) or "ru"
                    await bot.send_message(rec["telegram_id"], t("reset_code_message", lang, code=rec["code"]))
                    await _sb.mark_reset_code_notified(rec["id"])
                except Exception as e:
                    log.warning("Could not deliver reset code %s: %s", rec.get("id"), e)
        except Exception as e:
            log.error("Reset code poll failed: %s", e)
        await asyncio.sleep(_RESET_CODE_POLL_INTERVAL)


async def _review_reminder_loop(bot: Bot):
    await asyncio.sleep(300)
    while True:
        try:
            for order in storage.get_stale_review_orders():
                uid = order["tg_user_id"]
                oid_str = storage.order_id_str(order["id"])
                try:
                    await bot.send_message(
                        uid,
                        f"⏳ Извините за ожидание по заказу <b>{oid_str}</b>.\n"
                        "Администратор скоро проверит оплату. Спасибо за терпение! 🙏"
                    )
                    storage.mark_delay_notified(order["id"])
                    log.info("Delay notice sent to %s for order %s", uid, order["id"])
                except Exception as e:
                    log.warning("Could not send delay notice to %s: %s", uid, e)
        except Exception as e:
            log.error("Review reminder check failed: %s", e)
        await asyncio.sleep(_REVIEW_CHECK_INTERVAL)


async def main():
    token = require_token()
    storage.init_db()
    storage.seed_promos()
    bot = _make_bot(token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(menu.router)
    dp.include_router(auth.router)      # registration — before wizard
    dp.include_router(account.router)   # "Мой аккаунт" screen
    dp.include_router(admin.router)
    dp.include_router(payments.router)
    dp.include_router(shop.router)      # purchase wizard
    dp.include_router(review.router)    # admin order review
    dp.include_router(site_payments.router)  # site paywall payment review
    dp.include_router(wizard.router)
    dp.include_router(results.router)
    await _set_commands(bot)
    me = await bot.get_me()
    log.info("Starting @%s (id=%s)", me.username, me.id)
    asyncio.create_task(_expiry_loop(bot))
    asyncio.create_task(_review_reminder_loop(bot))
    asyncio.create_task(_site_payment_notify_loop(bot))
    asyncio.create_task(_reset_code_notify_loop(bot))
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(),
                           drop_pending_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
