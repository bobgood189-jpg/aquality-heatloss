"""Entry point. Long-polling aiogram 3.x bot.

    export BOT_TOKEN='123456:ABC...'   # from @BotFather
    python -m app.bot
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from .config import require_token
from . import storage
from .handlers import menu, admin, wizard, results

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aquality-bot")


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
        BotCommand(command="reset", description="Сбросить расчёт"),
        BotCommand(command="myid", description="Мой Telegram ID"),
    ])


async def main():
    token = require_token()
    storage.init_db()
    bot = _make_bot(token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(menu.router)
    dp.include_router(admin.router)
    dp.include_router(wizard.router)
    dp.include_router(results.router)
    await _set_commands(bot)
    me = await bot.get_me()
    log.info("Starting @%s (id=%s)", me.username, me.id)
    # drop_pending_updates: on (re)start, ignore the backlog so old button taps
    # aren't replayed against stale callback-query ids.
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(),
                           drop_pending_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
