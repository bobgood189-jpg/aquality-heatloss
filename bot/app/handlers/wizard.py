"""The calculation wizard: city → object params → materials → rooms → results."""
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
from .util import get_lang
from .results import build_object, send_results

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


# ── entry ──
@router.callback_query(F.data == "menu:calc")
async def start_calc(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(floors=[], cur_floor=0, mat={}, mat_idx=0, draft={})
    storage.log_event("calc_start")
    await state.set_state(Wizard.lang)  # transient; city next
    await cb.message.answer(t("ask_city", lang), reply_markup=K.cities_kb(lang))
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
    await state.set_state(Wizard.floors)
    await cb.message.answer(t("ask_floors", lang), reply_markup=K.floors_kb(lang))
    await cb.answer()


@router.callback_query(Wizard.floors, F.data.startswith("floors:"))
async def pick_floors(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    n = int(cb.data.split(":", 1)[1])
    await state.update_data(n_floors=n)
    await state.set_state(Wizard.height)
    await cb.message.answer(t("ask_height", lang))
    await cb.answer()


@router.message(Wizard.height)
async def set_height(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    h = _f(message.text)
    if h is None or h <= 0 or h > 10:
        return await message.answer(t("invalid_number", lang))
    await state.update_data(height=h)
    await state.set_state(Wizard.attic)
    await message.answer(t("ask_attic", lang), reply_markup=K.attic_kb(lang))


@router.callback_query(Wizard.attic, F.data.startswith("attic:"))
async def set_attic(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(attic=cb.data.split(":", 1)[1])
    await state.set_state(Wizard.airtight)
    await cb.message.answer(t("ask_airtight", lang), reply_markup=K.airtight_kb(lang))
    await cb.answer()


@router.callback_query(Wizard.airtight, F.data.startswith("air:"))
async def set_air(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(airtight=cb.data.split(":", 1)[1])
    await state.set_state(Wizard.regime)
    await cb.message.answer(t("ask_regime", lang), reply_markup=K.regime_kb(lang))
    await cb.answer()


@router.callback_query(Wizard.regime, F.data.startswith("reg:"))
async def set_regime(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(heat_regime=cb.data.split(":", 1)[1])
    await state.set_state(Wizard.lambda_mode)
    await cb.message.answer(t("ask_lambda", lang), reply_markup=K.lambda_kb(lang))
    await cb.answer()


@router.callback_query(Wizard.lambda_mode, F.data.startswith("lam:"))
async def set_lambda(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(lambda_mode=cb.data.split(":", 1)[1], mat={}, mat_idx=0)
    await state.set_state(Wizard.mat)
    await cb.message.answer(t("mat_intro", lang))
    await _ask_material(cb.message, state, lang)
    await cb.answer()


# ── materials ──
async def _ask_material(message, state, lang):
    data = await state.get_data()
    cat = MAT_SEQ[data["mat_idx"]]
    await message.answer(t("ask_mat", lang, cat=t("mat_" + cat, lang)),
                         reply_markup=K.mat_groups_kb(cat, lang))


@router.callback_query(Wizard.mat, F.data.startswith("matgrp:"))
async def mat_groups(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    cat = cb.data.split(":", 1)[1]
    await cb.message.edit_text(t("ask_mat", lang, cat=t("mat_" + cat, lang)),
                               reply_markup=K.mat_groups_kb(cat, lang))
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
        await _ask_material(cb.message, state, lang)
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
    await state.set_state(Wizard.rooms_menu)
    await _rooms_menu(message, state, lang)


async def _rooms_menu(message, state, lang):
    data = await state.get_data()
    cf = data["cur_floor"]
    floors = data["floors"]
    has_rooms = any(len(f["rooms"]) for f in floors)
    await message.answer(t("rooms_intro", lang, floor=cf + 1),
                         reply_markup=K.rooms_menu_kb(lang, cf, data["n_floors"], has_rooms))


@router.callback_query(Wizard.rooms_menu, F.data == "room:add")
async def room_add(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.update_data(draft={"openings": [], "ext_dirs": []})
    await state.set_state(Wizard.room_type)
    await cb.message.answer(t("ask_room_type", lang), reply_markup=K.room_types_kb(lang))
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
    await state.set_state(Wizard.room_len)
    await cb.message.answer(t("ask_room_len", lang))
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
    await state.set_state(Wizard.room_wid)
    await message.answer(t("ask_room_wid", lang))


@router.message(Wizard.room_wid)
async def room_wid(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    v = _f(message.text)
    if v is None or v <= 0 or v > 100:
        return await message.answer(t("invalid_number", lang))
    data = await state.get_data()
    draft = dict(data["draft"]); draft["width"] = v
    await state.update_data(draft=draft)
    await state.set_state(Wizard.room_walls)
    await message.answer(t("ask_ext_walls", lang), reply_markup=K.ext_walls_kb(lang, []))


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
    await cb.message.edit_reply_markup(reply_markup=K.ext_walls_kb(lang, sel))
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
    await state.set_state(Wizard.win_count)
    await cb.message.answer(t("ask_windows", lang), reply_markup=K.count_kb("wincount", lang))
    await cb.answer()


@router.callback_query(Wizard.win_count, F.data.startswith("wincount:"))
async def win_count(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    n = int(cb.data.split(":", 1)[1])
    data = await state.get_data()
    draft = dict(data["draft"]); draft["_win_n"] = n
    await state.update_data(draft=draft)
    if n == 0:
        await _ask_doors(cb.message, state, lang)
    else:
        await state.set_state(Wizard.win_size)
        await cb.message.answer(t("ask_win_size", lang))
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
        await state.set_state(Wizard.win_dir)
        await message.answer(t("ask_win_dir", lang), reply_markup=K.opening_dir_kb(lang, dirs, "win"))


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
    await _ask_doors(message, state, lang)


async def _ask_doors(message, state, lang):
    await state.set_state(Wizard.door_count)
    await message.answer(t("ask_doors", lang), reply_markup=K.count_kb("doorcount", lang))


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
        await state.set_state(Wizard.door_size)
        await cb.message.answer(t("ask_door_size", lang))
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
        await state.set_state(Wizard.door_beta)
        await message.answer(t("ask_door_beta", lang), reply_markup=K.door_beta_kb(lang))
    else:
        await state.set_state(Wizard.door_dir)
        await message.answer(t("ask_door_dir", lang), reply_markup=K.opening_dir_kb(lang, dirs, "door"))


@router.callback_query(Wizard.door_dir, F.data.startswith("doordir:"))
async def door_dir(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    d = cb.data.split(":", 1)[1]
    data = await state.get_data()
    draft = dict(data["draft"]); draft["_door_dir"] = d
    await state.update_data(draft=draft)
    await state.set_state(Wizard.door_beta)
    await cb.message.answer(t("ask_door_beta", lang), reply_markup=K.door_beta_kb(lang))
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
    await state.set_state(Wizard.rooms_menu)
    await _rooms_menu(message, state, lang)
