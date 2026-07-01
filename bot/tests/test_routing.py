"""Regression guard for command routing.

A stateless catch-all `@router.message(StateFilter(None))` placed in the FIRST
router silently swallows every command defined in LATER routers (it matches the
update and stops propagation before the real handler runs). This feeds real
updates through a dispatcher assembled exactly like bot.main() and asserts the
late-router commands still reach their handlers. See menu.fallback_router.
"""
import asyncio
import os
import tempfile
from datetime import datetime

os.environ.setdefault("BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402
from aiogram.types import Update  # noqa: E402
from aiogram.methods import SendMessage  # noqa: E402

import sys  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import storage  # noqa: E402

# Isolate the DB in a temp file so tests never touch the real bot database.
storage.DB_PATH = os.path.join(tempfile.gettempdir(), "aq_routing_test.db")
try:
    os.remove(storage.DB_PATH)
except OSError:
    pass
storage.init_db()
storage.seed_promos()

from app.handlers import (menu, admin, wizard, results, payments, auth,  # noqa: E402
                          shop, review, site_payments, account, tools)

_sent = []


async def _fake_call(self, method, request_timeout=None):
    if isinstance(method, SendMessage):
        _sent.append(method.text)
    return None


Bot.__call__ = _fake_call

_bot = Bot(os.environ["BOT_TOKEN"])
_dp = Dispatcher(storage=MemoryStorage())
for _r in (menu.router, auth.router, account.router, tools.router, admin.router,
           payments.router, shop.router, review.router, site_payments.router,
           wizard.router, results.router, menu.fallback_router):
    _dp.include_router(_r)

_uid = [70000]


async def _feed(text, username="ibrokh1movv7"):
    _uid[0] += 1
    _sent.clear()
    upd = Update.model_validate({"update_id": _uid[0], "message": {
        "message_id": 1, "date": int(datetime.now().timestamp()),
        "chat": {"id": _uid[0], "type": "private"},
        "from": {"id": _uid[0], "is_bot": False, "first_name": "T", "username": username},
        "text": text}})
    await _dp.feed_update(_bot, upd)
    return list(_sent)


def _run(text, **kw):
    return asyncio.run(_feed(text, **kw))


def test_late_router_commands_reachable():
    # every one of these lives in a router included AFTER menu.router
    for cmd in ["/status", "/mysub", "/stats", "/buy", "/tools", "/subs", "/promo X"]:
        out = _run(cmd)
        assert out, f"{cmd} produced no reply — swallowed by the fallback again?"


def test_menu_router_commands_still_work():
    for cmd in ["/help", "/reset", "/myid"]:
        assert _run(cmd), f"{cmd} stopped replying"


def test_unknown_text_hits_fallback():
    out = _run("бла бла бла")
    assert out and "Не понял" in out[0]


def test_unknown_command_stays_silent():
    assert _run("/definitelynotacommand") == []


def test_owner_gate_holds():
    # /stats is owner-only — a stranger gets no reply, an owner does
    assert _run("/stats", username="stranger") == []
    assert _run("/stats", username="ibrokh1movv7")
