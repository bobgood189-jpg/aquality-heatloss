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

from .config import require_token
from . import storage
from .handlers import menu, admin, wizard, results, payments, auth
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
        BotCommand(command="start", description="Меню / Menyu / Menu"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="mysub", description="Моя подписка / Mening obuna"),
        BotCommand(command="link", description="Привязать аккаунт / Akkaunt bog'lash"),
        BotCommand(command="reset", description="Сбросить расчёт"),
        BotCommand(command="myid",  description="Мой Telegram ID"),
        BotCommand(command="stats", description="Статистика (владелец)"),
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


async def main():
    token = require_token()
    storage.init_db()
    bot = _make_bot(token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(menu.router)
    dp.include_router(auth.router)      # registration — before wizard
    dp.include_router(admin.router)
    dp.include_router(payments.router)
    dp.include_router(wizard.router)
    dp.include_router(results.router)
    await _set_commands(bot)
    me = await bot.get_me()
    log.info("Starting @%s (id=%s)", me.username, me.id)
    asyncio.create_task(_expiry_loop(bot))
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(),
                           drop_pending_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
