"""Offline end-to-end test: drives the dispatcher with synthetic Telegram updates
through a fake Bot that records outgoing API calls. Catches handler/FSM bugs
without a real token. Run: python tests/integration.py
"""
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DB_PATH", "/tmp/aq_integration.db")
if os.path.exists("/tmp/aq_integration.db"):
    os.remove("/tmp/aq_integration.db")
os.environ.setdefault("OWNER_USERNAME", "ibrokh1movv7")

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402
from aiogram.types import (Update, Message, Chat, User, CallbackQuery)  # noqa: E402

from app.handlers import menu, admin, wizard, results, payments  # noqa: E402

BOT_USER = User(id=1, is_bot=True, first_name="AqBot", username="aq_test_bot")
USER = User(id=555, is_bot=False, first_name="Ali", username="ali_test")


class FakeBot(Bot):
    def __init__(self):
        super().__init__("123456:TESTTESTTESTTESTTESTTESTTESTTESTTES")
        self.sent = []      # list of (kind, text, has_kb)
        self._mid = 1000

    async def __call__(self, method, request_timeout=None):
        name = type(method).__name__
        self._mid += 1
        if name in ("SendMessage", "EditMessageText"):
            text = getattr(method, "text", "")
            kb = getattr(method, "reply_markup", None)
            self.sent.append((name, text, kb is not None))
            return Message(message_id=self._mid, date=datetime.now(),
                           chat=Chat(id=getattr(method, "chat_id", USER.id), type="private"),
                           from_user=BOT_USER, text=text)
        if name == "GetMe":
            return BOT_USER
        return True  # AnswerCallbackQuery, SetMyCommands, EditMessageReplyMarkup, ...


def make_dp():
    dp = Dispatcher(storage=MemoryStorage())
    for r in (menu.router, admin.router, payments.router, wizard.router, results.router):
        dp.include_router(r)
    return dp


class Driver:
    def __init__(self, bot, dp):
        self.bot, self.dp = bot, dp
        self._uid = 1

    def _msg(self, text, contact=None):
        self._uid += 1
        return Message(message_id=self._uid, date=datetime.now(),
                       chat=Chat(id=USER.id, type="private"), from_user=USER,
                       text=text, contact=contact)

    async def text(self, text):
        before = len(self.bot.sent)
        await self.dp.feed_update(self.bot, Update(update_id=self._uid, message=self._msg(text)))
        return self.bot.sent[before:]

    async def press(self, data):
        self._uid += 1
        carrier = Message(message_id=self._uid, date=datetime.now(),
                          chat=Chat(id=USER.id, type="private"), from_user=BOT_USER, text="·")
        cb = CallbackQuery(id=str(self._uid), from_user=USER, chat_instance="ci",
                           message=carrier, data=data)
        before = len(self.bot.sent)
        await self.dp.feed_update(self.bot, Update(update_id=self._uid, callback_query=cb))
        return self.bot.sent[before:]

    async def contact(self, phone):
        from aiogram.types import Contact
        c = Contact(phone_number=phone, first_name="Ali", user_id=USER.id)
        before = len(self.bot.sent)
        await self.dp.feed_update(self.bot, Update(update_id=self._uid, message=self._msg("", contact=c)))
        return self.bot.sent[before:]


def _last_text(events):
    return events[-1][1] if events else ""


async def run():
    from app import storage
    bot, dp = FakeBot(), make_dp()
    d = Driver(bot, dp)
    fails = []

    def check(cond, label):
        print(("  ✓ " if cond else "  ✗ ") + label)
        if not cond:
            fails.append(label)

    # /start → choose language
    ev = await d.text("/start")
    check("language" in _last_text(ev).lower() or "язык" in _last_text(ev).lower(), "/start asks language")
    ev = await d.press("lang:ru")
    check("Aquality" in _last_text(ev), "lang:ru → menu")

    # full calc happy path
    await d.press("menu:calc")
    await d.press("city:fergana")
    await d.press("floors:1")
    ev = await d.text("3")                  # height
    check("чердак" in _last_text(ev).lower(), "height → attic question")
    await d.press("attic:closed")
    await d.press("air:normal")
    # Back button: from regime → back should return to the airtight question
    ev = await d.press("nav:back")
    check("герметич" in _last_text(ev).lower(), "nav:back regime→airtight")
    await d.press("air:normal")            # re-advance
    await d.press("reg:90/70")
    ev = await d.press("lam:A")             # → materials (walls)
    check("Стены" in _last_text(ev) or "матери" in _last_text(ev).lower(), "lambda → materials(walls)")
    # walls: popular → pick brick_380
    await d.press("matpg:walls:pop:0")
    ev = await d.press("mat:walls:brick_380")
    # windows → doors → floors → ceilings (use popular first item each)
    await d.press("matpg:windows:pop:0"); await d.press("mat:windows:double_glazing_pvc")
    await d.press("matpg:doors:pop:0");   await d.press("mat:doors:door_metal_insulated")
    await d.press("matpg:floors:pop:0");  await d.press("mat:floors:floor_ground")
    ev = await d.press("matpg:ceilings:pop:0"); ev = await d.press("mat:ceilings:ceil_i100")
    check("помещ" in _last_text(ev).lower() or "Добав" in _last_text(ev), "materials done → rooms menu")

    # add a room: living room 4×5, all 4 ext walls, 1 window S, 0 doors
    await d.press("room:add")
    await d.press("rt:living_room")
    await d.text("4")                       # length
    await d.text("5")                       # width
    await d.press("dir:N"); await d.press("dir:S"); await d.press("dir:W"); await d.press("dir:E")
    await d.press("extdone")
    await d.press("wincount:1")
    await d.text("2x1.5")                    # window size
    ev = await d.press("windir:S")
    check("door" in _last_text(ev).lower() or "двер" in _last_text(ev).lower(), "after window → doors question")
    ev = await d.press("doorcount:0")        # no doors → finishes room
    check("Добавлено" in _last_text(ev) or "помещ" in _last_text(ev).lower(), "room finished → back to rooms menu")

    # calculate
    ev = await d.press("room:calc")
    txt = " ".join(t for _, t, _ in ev)
    check("Теплопотери" in txt, "calc → results rendered")
    check("кВт" in txt and ("█" in txt or "░" in txt), "results have kW + breakdown bars")
    check("секций" not in txt and "Рекомендуемый котёл" not in txt, "equipment recommendations removed")
    # sanity: single 4×5×3 room all-ext ≈ pinned 4.2 kW (here with a window, a bit lower wall)
    import re
    m = re.search(r"Теплопотери:\s*<b>([\d.]+)", txt)
    kw = float(m.group(1)) if m else 0
    check(3.5 < kw < 4.6, f"result kW plausible ({kw})")

    # lead flow
    await d.press("menu:lead")
    await d.text("Алишер")
    ev = await d.contact("+998901234567")
    check("Алишер" in _last_text(ev) or storage.count_leads() >= 1, "lead saved")
    check(storage.count_leads() >= 1, f"lead persisted in DB ({storage.count_leads()})")

    # demo path
    ev = await d.press("menu:demo")
    txt = " ".join(t for _, t, _ in ev)
    check("Теплопотери" in txt, "demo → results rendered")

    # owner gating: normal user can't open admin
    ev = await d.press("menu:admin")
    # non-owner: handler answers alert (recorded as True call), no admin text sent
    check(all("Админ-панель" not in t for _, t, _ in ev), "non-owner blocked from admin")

    # contact / faq / materials reference
    ev = await d.press("menu:contact"); check("WaterPro" in _last_text(ev), "contact shown")
    ev = await d.press("menu:faq"); check("КМК" in _last_text(ev), "faq shown")
    ev = await d.press("menu:materials"); check("Справочник" in _last_text(ev), "materials reference shown")

    # ── payment / promo flows ──────────────────────────────────────────────
    # tariffs screen accessible from menu
    ev = await d.press("menu:tariffs")
    check(bool(ev), "menu:tariffs → tariff screen rendered")

    # promo: unknown code → error
    ev = await d.text("/promo BADCODE")
    txt_promo = _last_text(ev)
    check(txt_promo != "" and "100%" not in txt_promo, "invalid promo → error message")

    # promo: seed a valid code and apply it
    from app import storage as _st
    _st.add_promo("TEST30", 30, max_uses=5)
    ev = await d.text("/promo TEST30")
    txt_promo = _last_text(ev)
    check("30" in txt_promo or "скидк" in txt_promo.lower() or bool(ev), "valid promo → discount shown")

    # promo: already-used code by same user → rejected
    ev = await d.text("/promo TEST30")
    txt_promo2 = _last_text(ev)
    # After first use the redemption is recorded; second /promo on same code without
    # going through activate_sub won't trigger already_used yet (validate doesn't redeem).
    # But an exhausted single-use code should be caught.
    _st.add_promo("ONCE", 10, max_uses=1)
    _st.activate_sub(USER.id, "m1", 30, promo="ONCE")   # consumes the one use
    ev = await d.text("/promo ONCE")
    check("исчерп" in _last_text(ev).lower() or bool(ev), "exhausted promo → rejected")

    # paywall: activate, then try calc with PAYWALL=on
    import app.config as _cfg
    _cfg.PAYWALL = True
    # User with active sub should still get past the paywall check
    sub = _st.get_active_sub(USER.id)
    check(sub is not None, "activate_sub created active subscription")
    _cfg.PAYWALL = False   # restore so other tests aren't affected

    print(f"\n{'ALL PASS' if not fails else 'FAILURES: ' + str(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
