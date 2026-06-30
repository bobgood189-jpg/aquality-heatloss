"""The calculation wizard: city → object params → materials → rooms → results.

Navigation: every screen is rendered through `_render`, which pushes a frame onto
a per-user `nav` stack (FSM data). A single '◀️ Назад' button (callback nav:back)
pops the stack and re-renders the previous screen — so a mis-tap is always
recoverable. Each frame snapshots the material cursor (mat_idx) and the count of
committed openings, so going back also rewinds those (no duplicate windows/doors).
"""
import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .. import engine as E
from .. import storage
from ..i18n import t, loc_name
from ..presets import CITIES, ROOM_TYPES, BASE_PRESETS
from ..states import Wizard
from .. import keyboards as K
from .util import get_lang, is_owner
from .results import build_object, send_results
from .payments import has_access, show_tariffs

router = Router()

MAT_SEQ = ["walls", "windows", "doors", "floors", "ceilings"]
MAT_KEY = {"walls": "wallId", "windows": "windowId", "doors": "doorId",
           "floors": "floorId", "ceilings": "ceilingId"}


def _f(s):
    """Parse a float, tolerating comma decimals and stray chars."""
    m = re.search(r"-?\d+(?:[.,]\d+)?", (s or "").replace(",", "."))
    return float(m.group()) if m else None


def _dims(s):
    """Parse 'W×H' with ×/x/х/* separators → (w, h)."""
    parts = re.split(r"[×xхX*]", (s or "").replace(",", "."))
    if len(parts) < 2:
        return None
    w, h = _f(parts[0]), _f(parts[1])
    if w is None or h is None:
        return None
    return w, h


# ── navigation stack ───────────────────────────────────────────────────────
async def _render(message, state, lang, step, push=True):
    """Render one wizard screen, set its FSM state, and (optionally) push a nav frame.

    A frame is {s: step, mi: mat_idx, ol: len(openings)} so nav:back can rewind
    the material cursor and any committed openings together with the screen."""
    if push:
        data = await state.get_data()
        draft = data.get("draft") or {}
        nav = list(data.get("nav", []))
        nav.append({"s": step, "mi": data.get("mat_idx", 0),
                    "ol": len(draft.get("openings", []))})
        await state.update_data(nav=nav)

    if step == "city":
        await state.set_state(Wizard.lang)
        await message.answer(t("ask_city", lang), reply_markup=K.with_back(K.cities_kb(lang), lang))
    elif step == "floors":
        await state.set_state(Wizard.floors)
        await message.answer(t("ask_floors", lang), reply_markup=K.with_back(K.floors_kb(lang), lang))
    elif step == "height":
        await state.set_state(Wizard.height)
        await message.answer(t("ask_height", lang), reply_markup=K.back_only_kb(lang))
    elif step == "attic":
        await state.set_state(Wizard.attic)
        await message.answer(t("ask_attic", lang), reply_markup=K.with_back(K.attic_kb(lang), lang))
    elif step == "airtight":
        await state.set_state(Wizard.airtight)
        await message.answer(t("ask_airtight", lang), reply_markup=K.with_back(K.airtight_kb(lang), lang))
    elif step == "regime":
        await state.set_state(Wizard.regime)
        await message.answer(t("ask_regime", lang), reply_markup=K.with_back(K.regime_kb(lang), lang))
    elif step == "lambda":
        await state.set_state(Wizard.lambda_mode)
        await message.answer(t("ask_lambda", lang), reply_markup=K.with_back(K.lambda_kb(lang), lang))
    elif step == "mat":
        data = await state.get_data()
        cat = MAT_SEQ[data["mat_idx"]]
        await state.set_state(Wizard.mat)
        await message.answer(t("ask_mat", lang, cat=t("mat_" + cat, lang)),
                             reply_markup=K.with_back(K.mat_groups_kb(cat, lang), lang))
    elif step == "rooms_menu":
        await _rooms_menu(message, state, lang)
    elif step == "room_type":
        await state.set_state(Wizard.room_type)
        await message.answer(t("ask_room_type", lang), reply_markup=K.with_back(K.room_types_kb(lang), lang))
    elif step == "room_len":
        await state.set_state(Wizard.room_len)
        await message.answer(t("ask_room_len", lang), reply_markup=K.back_only_kb(lang))
    elif step == "room_wid":
        await state.set_state(Wizard.room_wid)
        await message.answer(t("ask_room_wid", lang), reply_markup=K.back_only_kb(lang))
    elif step == "room_walls":
        data = await state.get_data()
        sel = (data.get("draft") or {}).get("ext_dirs", [])
        await state.set_state(Wizard.room_walls)
        await message.answer(t("ask_ext_walls", lang), reply_markup=K.with_back(K.ext_walls_kb(lang, sel), lang))
    elif step == "win_count":
        await state.set_state(Wizard.win_count)
        await message.answer(t("ask_windows", lang), reply_markup=K.with_back(K.count_kb("wincount", lang), lang))
    elif step == "win_size":
        await state.set_state(Wizard.win_size)
        await message.answer(t("ask_win_size", lang), reply_markup=K.back_only_kb(lang))
    elif step == "win_dir":
        data = await state.get_data()
        dirs = (data.get("draft") or {}).get("ext_dirs", [])
        await state.set_state(Wizard.win_dir)
        await message.answer(t("ask_win_dir", lang), reply_markup=K.with_back(K.opening_dir_kb(lang, dirs, "win"), lang))
    elif step == "door_count":
        await state.set_state(Wizard.door_count)
        await message.answer(t("ask_doors", lang), reply_markup=K.with_back(K.count_kb("doorcount", lang), lang))
    elif step == "door_size":
        await state.set_state(Wizard.door_size)
        await message.answer(t("ask_door_size", lang), reply_markup=K.back_only_kb(lang))
    elif step == "door_dir":
        data = await state.get_data()
        dirs = (data.get("draft") or {}).get("ext_dirs", [])
        await state.set_state(Wizard.door_dir)
        await message.answer(t("ask_door_dir", lang), reply_markup=K.with_back(K.opening_dir_kb(lang, dirs, "door"), lang))
    elif step == "door_beta":
        await state.set_state(Wizard.door_beta)
        await message.answer(t("ask_door_beta", lang), reply_markup=K.with_back(K.door_beta_kb(lang), lang))


@router.callback_query(F.data == "nav:back")
async def nav_back(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    data = await state.get_data()
    nav = list(data.get("nav", []))
    if len(nav) < 2:                       # already at the first screen → main menu
        await state.set_state(None)
        from .menu import show_menu
        await show_menu(cb.message, lang, is_owner(cb.from_user))
        return await cb.answer()
    nav.pop()                              # drop the current screen
    prev = nav[-1]
    draft = dict(data.get("draft") or {})
    if "openings" in draft:                # rewind committed windows/doors
        draft["openings"] = draft["openings"][:prev["ol"]]
    await state.update_data(nav=nav, mat_idx=prev["mi"], draft=draft)
    await _render(cb.message, state, lang, prev["s"], push=False)
    await cb.answer()


# ── entry ──
@router.callback_query(F.data == "menu:calc")
async def start_calc(cb: CallbackQuery, state: FSMContext):
    from ..config import SB_CONFIGURED
    from .. import supabase_db as sb_mod
    lang = await get_lang(state, cb.from_user.id)
    # If SB is configured and user is not registered, send to registration first
    if SB_CONFIGURED:
        profile = await sb_mod.get_profile(cb.from_user.id)
        if not profile:
            from .auth import start_registration
            await start_registration(cb.message, state, lang)
            return await cb.answer()
    if not await has_access(cb.from_user):
        await cb.message.answer(t("pay_locked", lang))
        await show_tariffs(cb.message, state, cb.from_user, lang)
        return await cb.answer()
    await state.update_data(floors=[], cur_floor=0, mat={}, mat_idx=0, draft={}, nav=[])
    storage.log_event("calc_start")
    await _render(cb.message, state, lang, "city")
    await cb.answer()


@router.callback_query(F.data.startswith("city:"))
async def pick_city(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    cid = cb.data.split(":", 1)[1]
    city = next((c for c in CITIES if c["id"] == cid), None)
    if not city:
        return await cb.answer()
    await state.update_data(cityName=city["name"], tExt=city["t"])
    await cb.message.edit_text(t("city_set", lang, city=city["name"], t=int(city["t"])))
    await _render(cb.message, state, lang, "floors")
    await cb.answer()


@router.callback_query(Wizard.floors, F.data.startswith("floors:"))
async def pick_floors(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    n = int(cb.data.split(":", 1)[1])
    await state.update_data(n_floors=n)
    await _render(cb.message, state, lang, "height")
    await cb.answer()


@router.message(Wizard.height)
async def set_height(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    h = _f(message.text)
    if h is None or h <= 0 or h > 10:
        return await message.answer(t("invalid_number", lang))
    await state.update_data(height=h)
    await _render(message, state, lang, "attic")


@router.callback_query(Wizard.attic, F.data.startswith("attic:"))
async def set_attic(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(attic=cb.data.split(":", 1)[1])
    await _render(cb.message, state, lang, "airtight")
    await cb.answer()


@router.callback_query(Wizard.airtight, F.data.startswith("air:"))
async def set_air(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(airtight=cb.data.split(":", 1)[1])
    await _render(cb.message, state, lang, "regime")
    await cb.answer()


@router.callback_query(Wizard.regime, F.data.startswith("reg:"))
async def set_regime(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(heat_regime=cb.data.split(":", 1)[1])
    await _render(cb.message, state, lang, "lambda")
    await cb.answer()


@router.callback_query(Wizard.lambda_mode, F.data.startswith("lam:"))
async def set_lambda(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(lambda_mode=cb.data.split(":", 1)[1], mat={}, mat_idx=0)
    await cb.message.answer(t("mat_intro", lang))
    await _render(cb.message, state, lang, "mat")
    await cb.answer()


# ── materials ──
@router.callback_query(Wizard.mat, F.data.startswith("matgrp:"))
async def mat_groups(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    cat = cb.data.split(":", 1)[1]
    await cb.message.edit_text(t("ask_mat", lang, cat=t("mat_" + cat, lang)),
                               reply_markup=K.with_back(K.mat_groups_kb(cat, lang), lang))
    await cb.answer()


@router.callback_query(Wizard.mat, F.data.startswith("matpg:"))
async def mat_page(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    _, cat, gi, page = cb.data.split(":")
    await cb.message.edit_text(t("pick_group", lang, cat=t("mat_" + cat, lang)),
                               reply_markup=K.mat_items_kb(cat, gi, page, lang))
    await cb.answer()


@router.callback_query(Wizard.mat, F.data.startswith("mat:"))
async def mat_pick(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    _, cat, pid = cb.data.split(":")
    p = E.find_preset(cat, pid)
    if not p:
        return await cb.answer()
    data = await state.get_data()
    mat = dict(data.get("mat", {}))
    mat[MAT_KEY[cat]] = pid
    idx = data["mat_idx"] + 1
    await state.update_data(mat=mat, mat_idx=idx)
    await cb.message.edit_text(t("mat_set", lang, cat=t("mat_" + cat, lang),
                                 name=loc_name(p, lang), r=p.get("r")))
    if idx < len(MAT_SEQ):
        await _render(cb.message, state, lang, "mat")
    else:
        await _start_rooms(cb.message, state, lang)
    await cb.answer()


# ── rooms ──
async def _start_rooms(message, state, lang):
    data = await state.get_data()
    floors = data.get("floors") or []
    if not floors:
        floors = [{"name": "1", "rooms": [], "height": data["height"]}]
    await state.update_data(floors=floors, cur_floor=0)
    await _rooms_menu(message, state, lang)


async def _rooms_menu(message, state, lang):
    data = await state.get_data()
    cf = data["cur_floor"]
    floors = data["floors"]
    has_rooms = any(len(f["rooms"]) for f in floors)
    # Reset the nav stack at this hub: each room is built fresh on top of it,
    # and nav:back from here returns to the main menu.
    await state.update_data(nav=[{"s": "rooms_menu", "mi": data.get("mat_idx", 0), "ol": 0}])
    await state.set_state(Wizard.rooms_menu)
    await message.answer(t("rooms_intro", lang, floor=cf + 1),
                         reply_markup=K.with_back(K.rooms_menu_kb(lang, cf, data["n_floors"], has_rooms), lang))


@router.callback_query(Wizard.rooms_menu, F.data == "room:add")
async def room_add(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(draft={"openings": [], "ext_dirs": []})
    await _render(cb.message, state, lang, "room_type")
    await cb.answer()


@router.callback_query(Wizard.rooms_menu, F.data == "room:nextfloor")
async def room_nextfloor(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    data = await state.get_data()
    floors = data["floors"]
    cf = data["cur_floor"] + 1
    while len(floors) <= cf:
        floors.append({"name": str(len(floors) + 1), "rooms": [], "height": data["height"]})
    await state.update_data(floors=floors, cur_floor=cf)
    await _rooms_menu(cb.message, state, lang)
    await cb.answer()


@router.callback_query(Wizard.rooms_menu, F.data == "room:calc")
async def room_calc(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    data = await state.get_data()
    if not any(len(f["rooms"]) for f in data["floors"]):
        await cb.answer(t("no_rooms", lang), show_alert=True)
        return
    obj = build_object(data)
    res = E.compute_object(obj)
    await state.set_state(None)
    await send_results(cb.message, res, lang, state)
    await cb.answer()


@router.callback_query(Wizard.room_type, F.data.startswith("rt:"))
async def room_type(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    rid = cb.data.split(":", 1)[1]
    rt = next((r for r in ROOM_TYPES if r["id"] == rid), None)
    data = await state.get_data()
    draft = dict(data["draft"])
    draft.update(type_id=rid, name=loc_name(rt, lang), tInt=rt["t"])
    await state.update_data(draft=draft)
    await _render(cb.message, state, lang, "room_len")
    await cb.answer()


@router.message(Wizard.room_len)
async def room_len(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    v = _f(message.text)
    if v is None or v <= 0 or v > 100:
        return await message.answer(t("invalid_number", lang))
    data = await state.get_data()
    draft = dict(data["draft"]); draft["length"] = v
    await state.update_data(draft=draft)
    await _render(message, state, lang, "room_wid")


@router.message(Wizard.room_wid)
async def room_wid(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    v = _f(message.text)
    if v is None or v <= 0 or v > 100:
        return await message.answer(t("invalid_number", lang))
    data = await state.get_data()
    draft = dict(data["draft"]); draft["width"] = v
    await state.update_data(draft=draft)
    await _render(message, state, lang, "room_walls")


@router.callback_query(Wizard.room_walls, F.data.startswith("dir:"))
async def toggle_dir(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    d = cb.data.split(":", 1)[1]
    data = await state.get_data()
    draft = dict(data["draft"])
    sel = list(draft.get("ext_dirs", []))
    if d in sel:
        sel.remove(d)
    else:
        sel.append(d)
    draft["ext_dirs"] = sel
    await state.update_data(draft=draft)
    await cb.message.edit_reply_markup(reply_markup=K.with_back(K.ext_walls_kb(lang, sel), lang))
    await cb.answer()


@router.callback_query(Wizard.room_walls, F.data == "extdone")
async def ext_done(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    data = await state.get_data()
    draft = dict(data["draft"])
    sel = draft.get("ext_dirs", [])
    if not sel:
        return await cb.answer(t("need_one_wall", lang), show_alert=True)
    # N/S walls take the length dimension; E/W take the width dimension.
    walls = []
    for d in sel:
        ln = draft["length"] if d in ("N", "S") else draft["width"]
        walls.append({"dir": d, "length": ln})
    draft["walls"] = walls
    await state.update_data(draft=draft)
    await cb.message.edit_text(t("ext_walls_set", lang, dirs=", ".join(sel)))
    await _render(cb.message, state, lang, "win_count")
    await cb.answer()


@router.callback_query(Wizard.win_count, F.data.startswith("wincount:"))
async def win_count(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    n = int(cb.data.split(":", 1)[1])
    data = await state.get_data()
    draft = dict(data["draft"]); draft["_win_n"] = n
    await state.update_data(draft=draft)
    if n == 0:
        await _render(cb.message, state, lang, "door_count")
    else:
        await _render(cb.message, state, lang, "win_size")
    await cb.answer()


@router.message(Wizard.win_size)
async def win_size(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    dims = _dims(message.text)
    if not dims:
        return await message.answer(t("invalid_number", lang))
    data = await state.get_data()
    draft = dict(data["draft"]); draft["_win_w"], draft["_win_h"] = dims
    await state.update_data(draft=draft)
    dirs = draft.get("ext_dirs", [])
    if len(dirs) == 1:
        await _store_windows(message, state, lang, dirs[0])
    else:
        await _render(message, state, lang, "win_dir")


@router.callback_query(Wizard.win_dir, F.data.startswith("windir:"))
async def win_dir(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    d = cb.data.split(":", 1)[1]
    await _store_windows(cb.message, state, lang, d)
    await cb.answer()


async def _store_windows(message, state, lang, d):
    data = await state.get_data()
    draft = dict(data["draft"])
    draft["openings"].append({"kind": "window", "w": draft["_win_w"], "h": draft["_win_h"],
                              "count": draft["_win_n"], "dir": d})
    await state.update_data(draft=draft)
    await _render(message, state, lang, "door_count")


@router.callback_query(Wizard.door_count, F.data.startswith("doorcount:"))
async def door_count(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    n = int(cb.data.split(":", 1)[1])
    data = await state.get_data()
    draft = dict(data["draft"]); draft["_door_n"] = n
    await state.update_data(draft=draft)
    if n == 0:
        await _finish_room(cb.message, state, lang)
    else:
        await _render(cb.message, state, lang, "door_size")
    await cb.answer()


@router.message(Wizard.door_size)
async def door_size(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    dims = _dims(message.text)
    if not dims:
        return await message.answer(t("invalid_number", lang))
    data = await state.get_data()
    draft = dict(data["draft"]); draft["_door_w"], draft["_door_h"] = dims
    await state.update_data(draft=draft)
    dirs = draft.get("ext_dirs", [])
    if len(dirs) == 1:
        draft["_door_dir"] = dirs[0]
        await state.update_data(draft=draft)
        await _render(message, state, lang, "door_beta")
    else:
        await _render(message, state, lang, "door_dir")


@router.callback_query(Wizard.door_dir, F.data.startswith("doordir:"))
async def door_dir(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    d = cb.data.split(":", 1)[1]
    data = await state.get_data()
    draft = dict(data["draft"]); draft["_door_dir"] = d
    await state.update_data(draft=draft)
    await _render(cb.message, state, lang, "door_beta")
    await cb.answer()


@router.callback_query(Wizard.door_beta, F.data.startswith("dbeta:"))
async def door_beta(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    bt = cb.data.split(":", 1)[1]
    data = await state.get_data()
    draft = dict(data["draft"])
    draft["openings"].append({"kind": "door", "w": draft["_door_w"], "h": draft["_door_h"],
                              "count": draft["_door_n"], "dir": draft["_door_dir"], "door_type": bt})
    await state.update_data(draft=draft)
    await _finish_room(cb.message, state, lang)
    await cb.answer()


async def _finish_room(message, state, lang):
    data = await state.get_data()
    draft = dict(data["draft"])
    room = {k: draft[k] for k in ("type_id", "name", "tInt", "length", "width", "walls", "openings")}
    floors = data["floors"]
    floors[data["cur_floor"]]["rooms"].append(room)
    total = sum(len(f["rooms"]) for f in floors)
    await state.update_data(floors=floors, draft={})
    await message.answer(t("room_added", lang, name=room["name"],
                          l=round(room["length"], 1), w=round(room["width"], 1), n=total))
    await _rooms_menu(message, state, lang)
