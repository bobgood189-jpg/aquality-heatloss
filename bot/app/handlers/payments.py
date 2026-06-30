"""Платный доступ (Фаза 1): подписка, промокоды, ручная активация владельцем.

Демо (menu:demo) бесплатно. Полный расчёт (menu:calc) — по активной подписке.
Оплата идёт вручную через Telegram владельца; владелец активирует подписку
командой /grant. Промокоды (10/30/50/100 %) проверяются командой /promo.
"""
import time
import math
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .. import storage
from ..config import PAYWALL, PLANS, PAY_TG, PAY_REQUISITES
from ..i18n import t
from .. import keyboards as K
from .util import get_lang, is_owner

router = Router()

PLAN_NAME_KEY = {"m1": "plan_m1", "m6": "plan_m6", "m12": "plan_m12"}


def _fmt_sum(n):
    return f"{int(round(n)):,}".replace(",", " ") + " сум"


def _plan_name(plan_id, lang):
    return t(PLAN_NAME_KEY.get(plan_id, plan_id), lang)


def has_access(user):
    """Доступ к полному расчёту: paywall выключен, владелец, либо активная подписка."""
    if not PAYWALL:
        return True
    if is_owner(user):
        return True
    return storage.get_active_sub(user.id) is not None


def _days_left(expires_ts):
    return math.ceil((expires_ts - time.time()) / 86400)


def _status_line(user, lang):
    sub = storage.get_active_sub(user.id)
    if not sub:
        return ""
    date = datetime.fromtimestamp(sub["expires_ts"]).strftime("%d.%m.%Y")
    days = _days_left(sub["expires_ts"])
    base = t("sub_active", lang, date=date)
    if days <= 1:
        return f"⚠️ {base} — {t('sub_expires_tomorrow', lang)}"
    if days <= 3:
        return f"⚠️ {base} — {t('sub_expires_in', lang, n=days)}"
    return f"✅ {base} ({t('sub_days_left', lang, n=days)})"


def _plans_block(lang, disc=0):
    lines = []
    for pid, p in PLANS.items():
        name = _plan_name(pid, lang)
        if disc:
            new = p["price"] * (1 - disc / 100)
            lines.append(f"\n• {name} — <s>{_fmt_sum(p['price'])}</s> <b>{_fmt_sum(new)}</b>")
        else:
            lines.append(f"\n• {name} — <b>{_fmt_sum(p['price'])}</b>")
    return "".join(lines)


async def _tariffs_text(state, user, lang):
    data = await state.get_data()
    code = data.get("pay_promo")
    disc = data.get("pay_disc", 0) or 0
    total = ""
    if code and disc:
        # суммарная строка по выбранному «выгодному» тарифу (6 мес) как ориентир
        plan = "m6"
        price = PLANS[plan]["price"] * (1 - disc / 100)
        total = "\n\n" + t("promo_applied", lang, code=code, disc=disc,
                           plan=_plan_name(plan, lang), price=_fmt_sum(price))
    return t("tariffs_title", lang, status=_status_line(user, lang),
             plans=_plans_block(lang, disc), total=total)


async def show_tariffs(message, state, user, lang):
    txt = await _tariffs_text(state, user, lang)
    if PAY_REQUISITES:
        txt += "\n\n" + PAY_REQUISITES
    await message.answer(txt, reply_markup=K.tariffs_kb(lang, PAY_TG),
                         disable_web_page_preview=True)


@router.callback_query(F.data == "menu:tariffs")
async def cb_tariffs(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await show_tariffs(cb.message, state, cb.from_user, lang)
    await cb.answer()


@router.message(Command("promo"))
async def cmd_promo(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    code = message.text.partition(" ")[2].strip()
    if not code:
        return await message.answer(t("promo_usage", lang))
    res = storage.validate_promo(code, message.from_user.id)
    if not res["ok"]:
        reason = res.get("reason")
        key = {"exhausted": "promo_exhausted", "already_used": "promo_used"}.get(reason, "promo_bad")
        await state.update_data(pay_promo=None, pay_disc=0)
        return await message.answer(t(key, lang))
    await state.update_data(pay_promo=code.strip().upper(), pay_disc=res["discount"])
    await show_tariffs(message, state, message.from_user, lang)


# ── админ-команды (только владелец) ────────────────────────────────────────
@router.message(Command("mysub"))
async def cmd_mysub(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    sub = storage.get_active_sub(message.from_user.id)
    if not sub:
        await message.answer(t("sub_none_user", lang))
        return
    date = datetime.fromtimestamp(sub["expires_ts"]).strftime("%d.%m.%Y")
    days = _days_left(sub["expires_ts"])
    plan_str = t(PLAN_NAME_KEY.get(sub["plan"], sub["plan"]), lang)
    if days <= 1:
        status = f"⚠️ {t('sub_expiry_tomorrow', lang, date=date)}"
    elif days <= 3:
        status = f"⚠️ {t('sub_expiry_warn', lang, n=days, date=date)}"
    else:
        status = f"✅ {t('sub_active', lang, date=date).strip()} ({t('sub_days_left', lang, n=days)})"
    await message.answer(f"<b>{plan_str}</b>\n\n{status}")


@router.message(Command("grant"))
async def cmd_grant(message: Message):
    if not is_owner(message.from_user):
        return
    parts = message.text.split()
    if len(parts) < 3 or parts[2] not in PLANS:
        return await message.answer("Использование: /grant <user_id> <m1|m6|m12> [ПРОМО]")
    uid = int(parts[1]) if parts[1].lstrip("-").isdigit() else None
    if uid is None:
        return await message.answer("user_id должен быть числом (узнать: пользователь шлёт /myid).")
    plan = parts[2]
    promo = parts[3] if len(parts) > 3 else None
    p = PLANS[plan]
    v = storage.validate_promo(promo, uid) if promo else {"ok": False, "discount": 0}
    price = p["price"] * (1 - v["discount"] / 100) if v["ok"] else p["price"]
    expires = storage.activate_sub(uid, plan, p["days"], amount=price, promo=promo, source="manual")
    date = datetime.fromtimestamp(expires).strftime("%d.%m.%Y")
    await message.answer(f"✅ Подписка {plan} активирована для id{uid} до {date}.")
    try:
        await message.bot.send_message(uid, f"✅ Ваша подписка Aquality активна до <b>{date}</b>. Спасибо!")
    except Exception:
        pass
    # Sync to Supabase if the user has a linked website profile
    try:
        from ..supabase_sync import activate_sub as _sb_activate
        sb_result = _sb_activate(uid, plan, p["days"], amount=price, promo=promo)
        if sb_result.get("ok"):
            await message.answer(f"🔗 Синхронизировано с сайтом (expires_at: {sb_result.get('expires_at','?')[:10]}).")
    except Exception:
        pass


@router.message(Command("revoke"))
async def cmd_revoke(message: Message):
    if not is_owner(message.from_user):
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        return await message.answer("Использование: /revoke <user_id>")
    storage.cancel_sub(int(parts[1]))
    await message.answer(f"Подписка id{parts[1]} отменена.")


@router.message(Command("subs"))
async def cmd_subs(message: Message):
    if not is_owner(message.from_user):
        return
    subs = storage.list_active_subs()
    if not subs:
        return await message.answer("Активных подписок нет.")
    lines = [f"<b>Активные подписки:</b> {len(subs)}"]
    for s in subs:
        date = datetime.fromtimestamp(s["expires_ts"]).strftime("%d.%m.%Y")
        promo = f" · промо {s['promo_code']}" if s["promo_code"] else ""
        lines.append(f"• id{s['tg_user_id']} · {s['plan']} · до {date}{promo}")
    await message.answer("\n".join(lines))


@router.message(Command("promo_add"))
async def cmd_promo_add(message: Message):
    if not is_owner(message.from_user):
        return
    parts = message.text.split()
    if len(parts) < 3 or not parts[2].isdigit() or int(parts[2]) not in (10, 30, 50, 100):
        return await message.answer("Использование: /promo_add <КОД> <10|30|50|100> [лимит] [дней]")
    code = parts[1]
    disc = int(parts[2])
    max_uses = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
    expires_ts = (int(time.time()) + int(parts[4]) * 86400) if len(parts) > 4 and parts[4].isdigit() else None
    storage.add_promo(code, disc, max_uses, expires_ts)
    await message.answer(f"✅ Промокод {code.upper()} (−{disc}%) создан.")


@router.message(Command("promo_del"))
async def cmd_promo_del(message: Message):
    if not is_owner(message.from_user):
        return
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("Использование: /promo_del <КОД>")
    storage.del_promo(parts[1])
    await message.answer(f"Промокод {parts[1].upper()} удалён.")


@router.message(Command("promo_list"))
async def cmd_promo_list(message: Message):
    if not is_owner(message.from_user):
        return
    promos = storage.list_promos()
    if not promos:
        return await message.answer("Промокодов нет.")
    lines = ["<b>Промокоды:</b>"]
    for p in promos:
        lim = f"{p['used_count']}/{p['max_uses']}" if p["max_uses"] is not None else f"{p['used_count']}/∞"
        exp = datetime.fromtimestamp(p["expires_ts"]).strftime("%d.%m.%Y") if p["expires_ts"] else "∞"
        off = "" if p["active"] else " (выкл)"
        lines.append(f"• {p['code']} −{p['discount']}% · {lim} · до {exp}{off}")
    await message.answer("\n".join(lines))
