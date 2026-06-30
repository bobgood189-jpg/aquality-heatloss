"""Start, language, main menu, contact, FAQ, materials reference and demo."""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .. import engine as E
from .. import storage
from .. import supabase_db as sb
from ..config import CONTACT, PAYWALL, SB_CONFIGURED
from ..i18n import t, loc_name, LANG_NAMES
from ..presets import BASE_PRESETS
from .. import keyboards as K
from .util import get_lang, is_owner
from .results import send_results

router = Router()


async def show_menu(message, lang, owner=False):
    await message.answer(t("welcome", lang), reply_markup=K.menu_kb(lang, owner, PAYWALL),
                         disable_web_page_preview=True)


async def _maybe_start_registration(message, state, lang):
    """If SB is configured and user is not registered, start registration flow."""
    if not SB_CONFIGURED:
        return False
    profile = await sb.get_profile(message.from_user.id)
    if profile:
        return False
    from .auth import start_registration
    await start_registration(message, state, lang)
    return True


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    storage.init_db()
    tg_id = message.from_user.id
    lang = storage.get_user_lang(tg_id) or "ru"
    await state.update_data(lang=lang)

    if not storage.get_user_lang(tg_id):
        # First visit: choose language, then register
        await state.update_data(sb_need_reg=True)
        await message.answer(t("choose_lang", "ru"), reply_markup=K.lang_kb())
        return

    if await _maybe_start_registration(message, state, lang):
        return

    await show_menu(message, lang, is_owner(message.from_user))


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    await show_menu(message, lang, is_owner(message.from_user))


@router.message(Command("reset", "cancel"))
async def cmd_reset(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    await state.clear()
    await state.update_data(lang=lang)
    await message.answer(t("restart_hint", lang))


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    u = message.from_user
    await message.answer(
        f"🆔 Your Telegram id: <code>{u.id}</code>\n"
        f"username: @{u.username or '—'}\n\n"
        f"Set <code>OWNER_ID={u.id}</code> in the bot env to receive leads here.")


@router.message(Command("link"))
async def cmd_link(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    token = message.text.partition(" ")[2].strip().upper()
    if not token:
        return await message.answer(t("link_usage", lang))
    from ..supabase_sync import link_account
    u = message.from_user
    result = link_account(u.id, u.username or "", token)
    if result.get("ok"):
        await message.answer(t("link_success", lang))
    else:
        reason = result.get("reason", "error")
        key = {
            "invalid_token": "link_bad_token",
            "already_linked": "link_already",
            "not_configured": "link_error",
        }.get(reason, "link_error")
        await message.answer(t(key, lang))


@router.callback_query(F.data.startswith("lang:"))
async def set_lang(cb: CallbackQuery, state: FSMContext):
    lang = cb.data.split(":", 1)[1]
    if lang not in LANG_NAMES:
        return await cb.answer()
    storage.set_user_lang(cb.from_user.id, lang)
    await state.update_data(lang=lang)

    # After language selection, check if registration is needed
    data = await state.get_data()
    if data.get("sb_need_reg") and SB_CONFIGURED:
        await state.update_data(sb_need_reg=False)
        from .auth import start_registration
        await start_registration(cb.message, state, lang)
        await cb.answer()
        return
    # Also check on any lang switch
    if await _maybe_start_registration(cb.message, state, lang):
        await cb.answer()
        return

    await cb.message.answer(t("welcome", lang), reply_markup=K.menu_kb(lang, is_owner(cb.from_user), PAYWALL),
                            disable_web_page_preview=True)
    await cb.answer()


@router.callback_query(F.data == "menu:home")
async def menu_home(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.set_state(None)
    await show_menu(cb.message, lang, is_owner(cb.from_user))
    await cb.answer()


@router.callback_query(F.data == "menu:lang")
async def menu_lang(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer(t("choose_lang", "ru"), reply_markup=K.lang_kb())
    await cb.answer()


@router.callback_query(F.data == "menu:contact")
async def menu_contact(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    txt = t("contact_text", lang, phone=CONTACT["phone"], phone2=CONTACT["phone2"],
            wa=CONTACT["whatsapp"], addr=CONTACT["address"])
    await cb.message.answer(txt, reply_markup=K.back_menu_kb(lang), disable_web_page_preview=True)
    await cb.answer()


@router.callback_query(F.data == "menu:faq")
async def menu_faq(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await cb.message.answer(t("faq_text", lang), reply_markup=K.back_menu_kb(lang))
    await cb.answer()


@router.callback_query(F.data == "menu:materials")
async def menu_materials(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    cats = [("mat_walls", "walls"), ("mat_windows", "windows"), ("mat_doors", "doors"),
            ("mat_floors", "floors"), ("mat_ceilings", "ceilings")]
    lines = ["📚 <b>Справочник материалов</b>\n"]
    total = 0
    for key, cat in cats:
        items = BASE_PRESETS[cat]
        total += len(items)
        rng = [p.get("r") for p in items if p.get("r") is not None]
        line = f"• <b>{t(key, lang)}</b>: {len(items)} шт., R = {min(rng)}…{max(rng)} м²·°C/Вт"
        lams = [E.disp_lambda(p) for p in items]
        lams = [x for x in lams if x]
        if lams:
            line += f", λ = {min(lams)}…{max(lams)} Вт/(м·°C)"
        lines.append(line)
    lines.append(f"\nВсего {total} готовых конструкций (KMK 2.01.04-18). "
                 f"Выбор материалов — внутри расчёта.")
    await cb.message.answer("\n".join(lines), reply_markup=K.back_menu_kb(lang))
    await cb.answer()


@router.callback_query(F.data == "menu:demo")
async def menu_demo(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    mat = {"wallId": "brick_380", "windowId": "double_glazing_pvc",
           "doorId": "door_metal_insulated", "floorId": "floor_ground", "ceilingId": "ceil_i100"}
    rooms = [
        {"type_id": "living_room", "name": "Гостиная", "tInt": 20, "length": 5, "width": 4,
         "walls": [{"dir": "S", "length": 5}, {"dir": "E", "length": 4}],
         "openings": [{"kind": "window", "w": 1.5, "h": 1.4, "count": 2, "dir": "S"}]},
        {"type_id": "kitchen", "name": "Кухня", "tInt": 18, "length": 3, "width": 4,
         "walls": [{"dir": "E", "length": 4}],
         "openings": [{"kind": "window", "w": 1.2, "h": 1.4, "count": 1, "dir": "E"}]},
        {"type_id": "bedroom", "name": "Спальня", "tInt": 20, "length": 4, "width": 3.5,
         "walls": [{"dir": "N", "length": 4}, {"dir": "W", "length": 3.5}],
         "openings": [{"kind": "window", "w": 1.2, "h": 1.4, "count": 1, "dir": "W"}]},
        {"type_id": "bathroom", "name": "Санузел", "tInt": 25, "length": 2, "width": 3.5,
         "walls": [{"dir": "N", "length": 2}], "openings": []},
        {"type_id": "corridor", "name": "Прихожая", "tInt": 16, "length": 2, "width": 3.5,
         "walls": [{"dir": "W", "length": 3.5}],
         "openings": [{"kind": "door", "w": 0.9, "h": 2.1, "count": 1, "dir": "W", "door_type": "single"}]},
    ]
    obj = {"tExt": -14, "mat": mat, "attic": "closed", "airtight": "normal",
           "lambda_mode": "A", "heat_regime": "90/70",
           "floors": [{"name": "1", "height": 3.0, "rooms": rooms}]}
    res = E.compute_object(obj)
    await state.update_data(cityName="Фергана", tExt=-14, mat=mat,
                            floors=obj["floors"], attic="closed", airtight="normal",
                            lambda_mode="A", heat_regime="90/70")
    storage.log_event("demo_run")
    await cb.message.answer("🏡 <b>Демо: типовой дом ~60 м² (Фергана)</b>")
    await send_results(cb.message, res, lang, state)
    await cb.answer()
