"""«Мой аккаунт» — профиль, подписка и управление привязкой Telegram прямо
в боте (смена пароля, отвязка), без захода на сайт."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ..config import SB_CONFIGURED, SITE_URL, PAYWALL
from ..i18n import t
from .. import keyboards as K
from .util import get_lang, is_owner

if SB_CONFIGURED:
    from .. import supabase_db as _sb
    from .auth import start_password_reset as _start_password_reset

router = Router()


async def _send_account(target, tg_id: int, lang: str, owner: bool):
    if not SB_CONFIGURED:
        return await target.answer(t("reg_no_sb", lang))

    profile = await _sb.get_profile(tg_id)
    if not profile:
        text = t("account_not_linked", lang, site=SITE_URL)
        return await target.answer(text, reply_markup=K.account_kb(lang, linked=False, site_url=SITE_URL))

    sub_text = ""
    if PAYWALL and not owner:
        sub = await _sb.get_active_sub(tg_id)
        if sub:
            date = (sub.get("expires_at") or "")[:10]
            sub_text = t("account_sub_active", lang, plan=sub.get("plan", "—"), date=date)
        else:
            sub_text = t("account_sub_none", lang)

    text = t("account_info", lang,
             email=profile.get("email") or "—",
             name=profile.get("full_name") or "—",
             phone=profile.get("phone") or "—",
             sub=sub_text)
    await target.answer(text, reply_markup=K.account_kb(lang, linked=True, site_url=SITE_URL))


@router.message(Command("account"))
async def cmd_account(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    await _send_account(message, message.from_user.id, lang, is_owner(message.from_user))


@router.callback_query(F.data == "menu:account")
async def cb_account(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await cb.answer()
    await _send_account(cb.message, cb.from_user.id, lang, is_owner(cb.from_user))


@router.callback_query(F.data == "account:resetpass")
async def cb_account_resetpass(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await cb.answer()
    await _start_password_reset(cb.message, state, lang, tg_id=cb.from_user.id)


@router.callback_query(F.data == "account:unlink")
async def cb_account_unlink_confirm(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await cb.answer()
    await cb.message.answer(t("account_unlink_confirm", lang), reply_markup=K.account_unlink_confirm_kb(lang))


@router.callback_query(F.data == "account:unlink_no")
async def cb_account_unlink_no(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await cb.message.delete()


@router.callback_query(F.data == "account:unlink_yes")
async def cb_account_unlink_yes(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await cb.answer()
    result = await _sb.unlink_by_telegram(cb.from_user.id)
    if result.get("ok"):
        await cb.message.edit_text(t("account_unlinked", lang))
    else:
        await cb.message.edit_text(t("account_unlink_error", lang))
