"""Registration flow: email → name (optional) → phone (optional).

Triggered when SB_CONFIGURED and the user has no linked Supabase profile.
On success the profile is linked and the menu is shown.
"""
import re
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from aiogram.filters import Command

from .. import storage
from ..config import SB_CONFIGURED
from .. import supabase_db as sb
from ..states import Register
from ..i18n import t
from .. import keyboards as K

log = logging.getLogger("aquality-bot.auth")
router = Router()

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9.\-]+$")


async def start_registration(message: Message, state: FSMContext, lang: str):
    """Entry point — call from menu.cmd_start / wizard.start_calc."""
    await state.set_state(Register.email)
    await state.update_data(reg_lang=lang)
    await message.answer(t("reg_prompt", lang))


# ── email step ──────────────────────────────────────────────────────────────

@router.message(Register.email)
async def reg_email(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang") or data.get("lang") or "ru"
    email = (message.text or "").strip()

    if not EMAIL_RE.match(email):
        return await message.answer(t("reg_invalid_email", lang))

    tg_id = message.from_user.id

    # Atomic upsert — single round-trip instead of 4
    res = await sb.upsert_user(
        email=email, tg_id=tg_id,
        name=message.from_user.full_name or "",
        username=message.from_user.username or "",
    )

    if res.get("ok"):
        await message.answer(t("reg_account_found", lang))
        await state.update_data(reg_email=email, reg_user_id=res.get("user_id"))
        await state.set_state(Register.name)
        return await message.answer(t("reg_ask_name", lang), reply_markup=K.reg_skip_kb(lang))

    reason = res.get("reason", "")

    if reason == "email_not_found":
        # New user — create via Admin API, then create profile row
        uid = await sb.create_auth_user(email, tg_id,
                                        name=message.from_user.full_name or "")
        if uid is None:
            uid = await sb.find_auth_user_by_email(email)
        if uid:
            ok = await sb.create_profile(uid, tg_id, email,
                                         name=message.from_user.full_name or "",
                                         username=message.from_user.username or "")
            if ok:
                await sb.log_event(tg_id, "reg_start", {"email": email})
                await state.update_data(reg_email=email, reg_user_id=uid)
                await state.set_state(Register.name)
                await message.answer(t("reg_created", lang))
                return await message.answer(t("reg_ask_name", lang),
                                            reply_markup=K.reg_skip_kb(lang))
        await message.answer(t("reg_email_error", lang))
        return

    log.error("upsert_user unexpected reason=%s tg_id=%s", reason, tg_id)
    await message.answer(t("reg_error", lang))


# ── name step ────────────────────────────────────────────────────────────────

@router.callback_query(Register.name, F.data == "reg:skip")
async def reg_name_skip(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang") or data.get("lang") or "ru"
    await cb.answer()
    await state.set_state(Register.phone)
    await cb.message.answer(t("reg_ask_phone", lang), reply_markup=K.reg_skip_kb(lang))


@router.message(Register.name)
async def reg_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang") or data.get("lang") or "ru"
    name = (message.text or "").strip()
    if name.lower() in ("/skip", "skip"):
        name = ""
    await state.update_data(reg_name=name)
    await state.set_state(Register.phone)
    await message.answer(t("reg_ask_phone", lang), reply_markup=K.reg_skip_kb(lang))


# ── phone step ────────────────────────────────────────────────────────────────

@router.callback_query(Register.phone, F.data == "reg:skip")
async def reg_phone_skip(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang") or data.get("lang") or "ru"
    await cb.answer()
    await _finish_registration(cb.message, state, lang,
                                name=data.get("reg_name", ""), phone="")


@router.message(Register.phone)
async def reg_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang") or data.get("lang") or "ru"
    phone = ""
    if message.contact:
        phone = message.contact.phone_number or ""
    else:
        phone = (message.text or "").strip()
        if phone.lower() in ("/skip", "skip"):
            phone = ""
    await _finish_registration(message, state, lang,
                                name=data.get("reg_name", ""), phone=phone)


# ── /link command (alias for registration / re-link) ─────────────────────────

@router.message(Command("link"))
async def cmd_link(message: Message, state: FSMContext):
    from .util import get_lang
    lang = await get_lang(state, message.from_user.id)
    if not SB_CONFIGURED:
        return await message.answer(t("reg_no_sb", lang))
    profile = await sb.get_profile(message.from_user.id)
    if profile:
        email = profile.get("email", "")
        return await message.answer(
            f"✅ Аккаунт уже привязан: <b>{email}</b>\n\nЧтобы сменить привязку — напишите /start.")
    await start_registration(message, state, lang)


# ── finish ────────────────────────────────────────────────────────────────────

async def _finish_registration(message: Message, state: FSMContext,
                                lang: str, name: str, phone: str):
    data = await state.get_data()
    tg_id = message.from_user.id
    if name or phone:
        await sb.update_profile(tg_id, name=name, phone=phone)

    storage.set_user_lang(tg_id, lang)
    await state.clear()
    await state.update_data(lang=lang)

    await message.answer(t("reg_done", lang), reply_markup=K.remove_kb())

    from .. import keyboards as _K
    from .util import is_owner
    from ..config import PAYWALL
    await message.answer(t("welcome", lang),
                         reply_markup=_K.menu_kb(lang, is_owner(message.from_user), PAYWALL),
                         disable_web_page_preview=True)
