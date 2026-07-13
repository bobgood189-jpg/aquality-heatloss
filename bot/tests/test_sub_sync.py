"""Regression guard for the "оплата подтверждена, сайт подписку не видит" bug.
See docs/fix-tg-sub-sync-prompt.md.

1) When PAYWALL is on but Supabase isn't configured, admin-approval must NOT
   silently fall back to the local SQLite subscription (the customer would be
   told they have access the website can never see) — it must refuse loudly.
2) The bot's plan ids (SHOP_PLANS) and the site's plan ids (AQ_PLANS in
   assets/app.js) must match 1:1, or a valid purchase can produce a plan id
   the site's tier logic doesn't recognize.

Run: python tests/test_sub_sync.py (also wired into tests/run.py)
"""
import asyncio
import os
import re
import sys
import tempfile
from datetime import datetime

os.environ.setdefault("BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
os.environ.setdefault("OWNER_USERNAME", "ibrokh1movv7")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher, Router, F  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402
from aiogram.types import Update, Message, Chat, User, CallbackQuery  # noqa: E402

from app import storage  # noqa: E402
from app.handlers import review  # noqa: E402
from app.config import SHOP_PLANS  # noqa: E402


class _IsolatedDb:
    """storage.DB_PATH is a shared module global (see test_routing.py, which sets
    it once at import time) — mutating it for the whole process would make test
    order matter (whichever module imports last "wins" for every test that runs
    after). Scope the override to just this test's execution instead."""
    def __enter__(self):
        self._prev = storage.DB_PATH
        storage.DB_PATH = os.path.join(tempfile.gettempdir(), "aq_sub_sync_test.db")
        try:
            os.remove(storage.DB_PATH)
        except OSError:
            pass
        storage.init_db()
        return self

    def __exit__(self, *exc):
        storage.DB_PATH = self._prev

OWNER = User(id=999001, is_bot=False, first_name="Owner", username="ibrokh1movv7")
BUYER = User(id=999002, is_bot=False, first_name="Buyer", username="buyer_test")
BOT_USER = User(id=1, is_bot=True, first_name="AqBot", username="aq_test_bot")


class FakeBot(Bot):
    def __init__(self):
        super().__init__("123456:TESTTESTTESTTESTTESTTESTTESTTESTTES")
        self.sent = []  # list of (chat_id, text)

    async def __call__(self, method, request_timeout=None):
        name = type(method).__name__
        if name in ("SendMessage", "EditMessageText"):
            self.sent.append((getattr(method, "chat_id", None), getattr(method, "text", "")))
            return Message(message_id=1, date=datetime.now(),
                           chat=Chat(id=getattr(method, "chat_id", 0), type="private"),
                           from_user=BOT_USER, text=getattr(method, "text", ""))
        if name == "GetMe":
            return BOT_USER
        return True


async def _press_review_ok(order_id):
    """Bot/Dispatcher must be built while a loop is already running (aiogram
    reaches for the running loop internally) — see integration.py's Driver.

    Registers cb_review_ok onto a FRESH router rather than reusing the shared
    review.router singleton — that one is already attached to test_routing.py's
    module-level Dispatcher within this same test process, and aiogram routers
    can only be attached to one parent at a time."""
    bot = FakeBot()
    dp = Dispatcher(storage=MemoryStorage())
    test_router = Router()
    test_router.callback_query(F.data.startswith("review:ok:"))(review.cb_review_ok)
    dp.include_router(test_router)
    carrier = Message(message_id=1, date=datetime.now(),
                      chat=Chat(id=OWNER.id, type="private"), from_user=BOT_USER, text="·")
    cb = CallbackQuery(id="1", from_user=OWNER, chat_instance="ci",
                       message=carrier, data=f"review:ok:{order_id}")
    await dp.feed_update(bot, Update(update_id=1, callback_query=cb))
    return bot


def test_no_silent_local_activation_when_paywall_and_no_supabase():
    """The exact bug: PAYWALL on + Supabase not configured must refuse the
    approval, not congratulate the customer while writing only to SQLite."""
    prev_sb, prev_paywall = review.SB_CONFIGURED, review.PAYWALL
    with _IsolatedDb():
        order_id = storage.create_order(
            BUYER.id, BUYER.username, "pro", 1,
            base_price=99000, promo_code=None, promo_disc=0,
            final_price=99000, email="buyer@example.com")

        review.SB_CONFIGURED = False
        review.PAYWALL = True
        try:
            bot = asyncio.run(_press_review_ok(order_id))
        finally:
            review.SB_CONFIGURED, review.PAYWALL = prev_sb, prev_paywall

        order = storage.get_order(order_id)
        assert order["status"] != "completed", (
            f"order was marked completed with no Supabase configured (status={order['status']!r})")
        congrats_sent = any("Оплата подтверждена" in text for _chat, text in bot.sent if text)
        assert not congrats_sent, "customer was congratulated despite no Supabase sync happening"


def test_plan_id_parity_bot_vs_site():
    """SHOP_PLANS (bot) and AQ_PLANS (site) must define the exact same plan ids,
    or a real purchase can activate a plan the site's aqTier()/paywall never
    recognizes as active."""
    bot_ids = {f"{plan}_m{months}"
              for plan, info in SHOP_PLANS.items()
              for months in info["durations"]}

    app_js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "app.js")
    with open(app_js, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"const AQ_PLANS\s*=\s*\[(.*?)\];", src, re.S)
    assert m, "could not find AQ_PLANS array in assets/app.js"
    site_ids = set(re.findall(r"id:\s*'([^']+)'", m.group(1)))

    assert bot_ids, "SHOP_PLANS produced no plan ids — test itself is broken"
    assert site_ids, "AQ_PLANS produced no plan ids — regex/test itself is broken"
    assert bot_ids == site_ids, (
        f"bot/site plan id mismatch — bot only: {bot_ids - site_ids}, "
        f"site only: {site_ids - bot_ids}")


if __name__ == "__main__":
    fails = []
    for name in [n for n in dir() if n.startswith("test_")]:
        try:
            globals()[name]()
            print("  ✓", name)
        except Exception as e:
            fails.append(name)
            print("  ✗", name, "—", e)
    print(f"{'ALL PASS' if not fails else 'FAILURES: ' + str(fails)}")
    sys.exit(1 if fails else 0)
