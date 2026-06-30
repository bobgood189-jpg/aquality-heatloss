"""Registration flow: email → name (optional) → phone (optional) → Supabase.

The flow starts when SB_CONFIGURED=True and the user is not yet in profiles.
On completion the telegram_id is linked to the Supabase profile (new or existing).
Existing website users who enter the same email get their accounts merged automatically.
"""
import re
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .. import storage
from .. import supabase_db as sb
from ..config import SB_CONFIGURED, PAYWALL
from ..states import Register
from ..i18n import t
from .. import keyboards as K
from .util import get_lang, is_owner

router = Router()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_SKIP_TOKENS = {"/skip", "skip"}


def _is_skip(text: str, lang: str) -> bool:
    low = (text or "").strip().lower()
    return low in _SKIP_TOKENS or low == t("skip", lang).lower().strip()


async def start_registration(message: Message, state: FSMContext, lang: str):
    """Entry point: set state and prompt for email."""
    await state.set_state(Register.email)
    await message.answer(t("reg_prompt", lang), reply_markup=K.back_only_kb(lang))


# ── email step ──────────────────────────────────────────────────────────────

@router.message(Register.email)
async def reg_email(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    email = (message.text or "").strip()

    if not EMAIL_RE.match(email):
        return await message.answer(t("reg_invalid_email", lang))

    tg_id = message.from_user.id
    tg_name = message.from_user.full_name or ""

    # Try to link to an existing Supabase account by email
    res = await sb.link_telegram(email, tg_id, name=tg_name)

    if res.get("ok"):
        # Account found (existing site user) and linked
        await state.update_data(sb_email=email, sb_user_id=res.get("user_id"), reg_existed=True)
        await message.answer(t("reg_account_found", lang, email=email))
        await _ask_name(message, state, lang)
        return

    reason = res.get("reason", "")

    if reason == "email_not_found":
        # New user — create auth account
        user_id = await sb.create_auth_user(email, tg_id, name=tg_name)
        if user_id:
            await state.update_data(sb_email=email, sb_user_id=user_id, reg_existed=False)
            await message.answer(t("reg_created", lang, email=email))
            await _ask_name(message, state, lang)
            return
        # Email might exist in auth.users but not in profiles (edge case)
        user_id = await sb.find_auth_user_by_email(email)
        if user_id:
            ok = await sb.upsert_profile(user_id, tg_id, email, tg_name)
            if ok:
                await state.update_data(sb_email=email, sb_user_id=user_id, reg_existed=True)
                await message.answer(t("reg_account_found", lang, email=email))
                await _ask_name(message, state, lang)
                return
        # Could not create or find account — prompt for another email
        await state.set_state(Register.email)
        return await message.answer(t("reg_email_error", lang))

    await message.answer(t("reg_error", lang))


async def _ask_name(message: Message, state: FSMContext, lang: str):
    tg_name = message.from_user.full_name or ""
    hint = f" ({tg_name})" if tg_name else ""
    await state.set_state(Register.name)
    await message.answer(t("reg_ask_name", lang, hint=hint), reply_markup=K.reg_skip_kb(lang))


# ── name step ───────────────────────────────────────────────────────────────

@router.message(Register.name)
async def reg_name(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    text = (message.text or "").strip()
    if _is_skip(text, lang):
        name = message.from_user.full_name or ""
    else:
        name = text
    await state.update_data(reg_name=name)
    await state.set_state(Register.phone)
    await message.answer(t("reg_ask_phone", lang), reply_markup=K.reg_skip_kb(lang))


@router.callback_query(Register.name, F.data == "reg:skip")
async def reg_name_skip(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(reg_name=cb.from_user.full_name or "")
    await state.set_state(Register.phone)
    await cb.message.answer(t("reg_ask_phone", lang), reply_markup=K.reg_skip_kb(lang))
    await cb.answer()


# ── phone step ──────────────────────────────────────────────────────────────

@router.message(Register.phone)
async def reg_phone(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    data = await state.get_data()

    if message.contact:
        phone = message.contact.phone_number
    elif _is_skip((message.text or ""), lang):
        phone = ""
    else:
        phone = (message.text or "").strip()

    await _finish_registration(message, state, lang, data, phone)


@router.callback_query(Register.phone, F.data == "reg:skip")
async def reg_phone_skip(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    data = await state.get_data()
    await _finish_registration(cb.message, state, lang, data, phone="",
                               tg_user=cb.from_user)
    await cb.answer()


async def _finish_registration(message: Message, state: FSMContext,
                               lang: str, data: dict, phone: str,
                               tg_user=None):
    tg_id = (tg_user or message.from_user).id
    name = data.get("reg_name", "")

    # Update profile with name + phone
    if name or phone:
        await sb.update_profile(tg_id, name=name, phone=phone)

    # Persist lang preference in SQLite
    storage.set_user_lang(tg_id, lang)

    await state.set_state(None)
    await message.answer(
        t("reg_done", lang),
        reply_markup=K.menu_kb(lang, is_owner(tg_user or message.from_user), PAYWALL),
    )
