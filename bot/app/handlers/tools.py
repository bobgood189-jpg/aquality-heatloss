"""Standalone engineering calculators reachable straight from the main menu.

Each tool is a tiny flow: a prompt, one or two plain-number inputs, then a
result — no wizard, no paywall. The physics reuses the same engine helpers the
full calculator does, so a bare boiler/radiator/fuel figure here matches a full
run. Pure compute lives in the top helpers (unit-testable); the handlers just
parse input, guard ranges, and render.
"""
import math
import re

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .. import storage
from .. import keyboards as K
from ..i18n import t
from ..states import Tools
from ..config import SB_CONFIGURED
from ..engine import (recommend_boiler, aq_boiler, recommend_pipe, section_watt,
                      cost_estimate, aq_rad_model, LOAD_FACTOR)
from ..presets import CITIES
from .util import get_lang

router = Router()


# ── input helpers ───────────────────────────────────────────────────────────
def _num(s):
    """Parse a positive-ish number, tolerating comma decimals and stray text."""
    m = re.search(r"-?\d+(?:\.\d+)?", (s or "").replace(",", "."))
    return float(m.group()) if m else None


def _fmt_sum(n):
    return f"{int(round(n)):,}".replace(",", " ")


# ── pure compute (mirrors engine.py; safe to unit-test) ─────────────────────
QUICK_WM2 = {"good": 70, "avg": 110, "poor": 160}     # specific heat loss, W/m²


def quick_estimate(area, quality):
    """Rule-of-thumb heat loss from area × a specific-loss norm (W/m²)."""
    wm2 = QUICK_WM2.get(quality, 110)
    kw = area * wm2 / 1000.0
    sw = section_watt(20, "80/60")
    sections = math.ceil(kw * 1000 * 1.15 / sw) if sw > 0 else 0
    gas = cost_estimate(kw)["out"]["gas"]["month"]
    return {"wm2": wm2, "kw": round(kw, 1), "boiler": recommend_boiler(kw * 1.25),
            "sections": sections, "gas": _fmt_sum(gas)}


def boiler_info(kw):
    margin = kw * 1.25
    b = aq_boiler(margin)
    return {"kw": round(kw, 1), "margin": round(margin, 1),
            "size": recommend_boiler(margin), "model": b["model"],
            "type": b["type"], "pipe": recommend_pipe(margin)}


def rad_sections(kw):
    q = kw * 1000

    def s(regime):
        sw = section_watt(20, regime)
        return math.ceil(q * 1.15 / sw) if sw > 0 else 0

    s8060 = s("80/60")
    model = aq_rad_model(s8060)
    return {"kw": round(kw, 2), "s9070": s("90/70"), "s8060": s8060,
            "s7565": s("75/65"), "model": model["model"], "spec": model["spec"]}


def fuel_info(kw):
    est = cost_estimate(kw)
    lines = []
    for k in ("gas", "coal", "elec"):
        c = est["out"][k]
        lines.append(f"• {c['name']}: <b>{_fmt_sum(c['month'])} сум/мес</b> "
                     f"({round(c['units'])} {c['unit']})")
    return {"kwh": _fmt_sum(est["monthlyKwh"]), "lines": "\n".join(lines),
            "load": int(round(LOAD_FACTOR * 100))}


INSUL_TYPES = [("Минвата", 0.045), ("Эковата", 0.042), ("EPS (пенопласт)", 0.038),
               ("XPS (экструзия)", 0.032), ("ППУ (напыление)", 0.028)]
STD_BOARDS = [50, 100, 150, 200, 250, 300]


def insul_lines(cur, tgt):
    dr = tgt - cur
    out = []
    for name, lam in INSUL_TYPES:
        mm = dr * lam * 1000
        board = next((b for b in STD_BOARDS if b >= mm), math.ceil(mm / 50) * 50)
        out.append(f"• {name} (λ{lam}): <b>{math.ceil(mm)} мм</b> → плита {board}")
    return "\n".join(out)


def convert_power(kw):
    return {"kw": round(kw, 2), "kcal": _fmt_sum(kw * 859.845),
            "btu": _fmt_sum(kw * 3412.142), "hp": round(kw * 1.35962, 2),
            "w": _fmt_sum(kw * 1000)}


# ── result keyboards ────────────────────────────────────────────────────────
def _quick_result_kb(lang):
    return K.kb([
        [K.btn(t("menu_calc", lang), "menu:calc")],
        [K.btn(t("menu_lead", lang), "menu:lead"), K.btn(t("menu", lang), "menu:home")],
    ])


# ── tools submenu ───────────────────────────────────────────────────────────
@router.callback_query(F.data == "menu:tools")
async def open_tools(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.set_state(None)
    await cb.message.answer(t("tools_title", lang), reply_markup=K.tools_menu_kb(lang))
    await cb.answer()


@router.message(Command("tools"))
async def cmd_tools(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    await state.set_state(None)
    await message.answer(t("tools_title", lang), reply_markup=K.tools_menu_kb(lang))


# ── 1) quick estimate ───────────────────────────────────────────────────────
@router.callback_query(F.data == "menu:quick")
async def quick_start(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.set_state(Tools.quick_area)
    await cb.message.answer(t("quick_ask_area", lang), reply_markup=K.back_menu_kb(lang))
    await cb.answer()


@router.message(Tools.quick_area)
async def quick_area(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    v = _num(message.text)
    if v is None or v <= 0 or v > 100000:
        return await message.answer(t("invalid_number", lang))
    await state.update_data(quick_area=v)
    await state.set_state(None)
    await message.answer(t("quick_ask_quality", lang, area=round(v)),
                         reply_markup=K.quick_quality_kb(lang))


@router.callback_query(F.data.startswith("quick:"))
async def quick_quality(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    quality = cb.data.split(":", 1)[1]
    data = await state.get_data()
    area = data.get("quick_area")
    if area is None:                       # session lost the area — restart the tool
        await state.set_state(Tools.quick_area)
        await cb.message.answer(t("quick_ask_area", lang), reply_markup=K.back_menu_kb(lang))
        return await cb.answer()
    r = quick_estimate(area, quality)
    qlabel = {"good": t("quick_q_good", lang), "avg": t("quick_q_avg", lang),
              "poor": t("quick_q_poor", lang)}[quality]
    storage.log_event("tool_quick")
    await cb.message.answer(
        t("quick_result", lang, area=round(area), qlabel=qlabel, kw=r["kw"],
          wm2=r["wm2"], boiler=r["boiler"], sections=r["sections"], gas=r["gas"]),
        reply_markup=_quick_result_kb(lang))
    await cb.answer()


# ── 2) boiler selector ──────────────────────────────────────────────────────
@router.callback_query(F.data == "tool:boiler")
async def boiler_start(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.set_state(Tools.boiler_kw)
    await cb.message.answer(t("boiler_ask_kw", lang), reply_markup=K.back_tools_kb(lang))
    await cb.answer()


@router.message(Tools.boiler_kw)
async def boiler_calc(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    v = _num(message.text)
    if v is None or v <= 0 or v > 100000:
        return await message.answer(t("invalid_number", lang))
    await state.set_state(None)
    r = boiler_info(v)
    storage.log_event("tool_boiler")
    await message.answer(
        t("boiler_result", lang, kw=r["kw"], margin=r["margin"], size=r["size"],
          model=r["model"], type=r["type"], pipe=r["pipe"]),
        reply_markup=K.tools_menu_kb(lang))


# ── 3) radiator sizing ──────────────────────────────────────────────────────
@router.callback_query(F.data == "tool:rad")
async def rad_start(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.set_state(Tools.rad_kw)
    await cb.message.answer(t("rad_ask_kw", lang), reply_markup=K.back_tools_kb(lang))
    await cb.answer()


@router.message(Tools.rad_kw)
async def rad_calc(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    v = _num(message.text)
    if v is None or v <= 0 or v > 1000:
        return await message.answer(t("invalid_number", lang))
    await state.set_state(None)
    r = rad_sections(v)
    storage.log_event("tool_rad")
    await message.answer(
        t("rad_result", lang, kw=r["kw"], s9070=r["s9070"], s8060=r["s8060"],
          s7565=r["s7565"], model=r["model"], spec=r["spec"]),
        reply_markup=K.tools_menu_kb(lang))


# ── 4) heating cost ─────────────────────────────────────────────────────────
@router.callback_query(F.data == "tool:fuel")
async def fuel_start(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.set_state(Tools.fuel_kw)
    await cb.message.answer(t("fuel_ask_kw", lang), reply_markup=K.back_tools_kb(lang))
    await cb.answer()


@router.message(Tools.fuel_kw)
async def fuel_calc(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    v = _num(message.text)
    if v is None or v <= 0 or v > 100000:
        return await message.answer(t("invalid_number", lang))
    await state.set_state(None)
    r = fuel_info(v)
    storage.log_event("tool_fuel")
    await message.answer(
        t("fuel_result", lang, kw=round(v, 1), kwh=r["kwh"], lines=r["lines"], load=r["load"]),
        reply_markup=K.tools_menu_kb(lang))


# ── 5) insulation thickness (two-step) ──────────────────────────────────────
@router.callback_query(F.data == "tool:insul")
async def insul_start(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.set_state(Tools.insul_current)
    await cb.message.answer(t("insul_ask_current", lang), reply_markup=K.back_tools_kb(lang))
    await cb.answer()


@router.message(Tools.insul_current)
async def insul_current(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    v = _num(message.text)
    if v is None or v <= 0 or v > 20:
        return await message.answer(t("invalid_number", lang))
    await state.update_data(insul_cur=v)
    await state.set_state(Tools.insul_target)
    await message.answer(t("insul_ask_target", lang), reply_markup=K.back_tools_kb(lang))


@router.message(Tools.insul_target)
async def insul_target(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    v = _num(message.text)
    if v is None or v <= 0 or v > 20:
        return await message.answer(t("invalid_number", lang))
    data = await state.get_data()
    cur = data.get("insul_cur", 0)
    await state.set_state(None)
    if v <= cur:
        return await message.answer(t("insul_already", lang), reply_markup=K.tools_menu_kb(lang))
    storage.log_event("tool_insul")
    await message.answer(
        t("insul_result", lang, cur=round(cur, 2), tgt=round(v, 2),
          dr=round(v - cur, 2), lines=insul_lines(cur, v)),
        reply_markup=K.tools_menu_kb(lang))


# ── 6) power converter ──────────────────────────────────────────────────────
@router.callback_query(F.data == "tool:conv")
async def conv_start(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.set_state(Tools.conv_value)
    await cb.message.answer(t("conv_ask_kw", lang), reply_markup=K.back_tools_kb(lang))
    await cb.answer()


@router.message(Tools.conv_value)
async def conv_calc(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    v = _num(message.text)
    if v is None or v <= 0 or v > 1000000:
        return await message.answer(t("invalid_number", lang))
    await state.set_state(None)
    r = convert_power(v)
    await message.answer(
        t("conv_result", lang, kw=r["kw"], kcal=r["kcal"], btu=r["btu"], hp=r["hp"], w=r["w"]),
        reply_markup=K.tools_menu_kb(lang))


# ── 7) cities & design temps (static) ───────────────────────────────────────
@router.callback_query(F.data == "tool:cities")
async def cities_list(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    lines = [t("cities_title", lang)]
    for c in sorted(CITIES, key=lambda x: x["t"]):
        lines.append(f"• <b>{c['name']}</b> ({c['region']}): <b>{int(c['t'])}°C</b>")
    await cb.message.answer("\n".join(lines), reply_markup=K.tools_menu_kb(lang))
    await cb.answer()


# ── 8) promo checker ────────────────────────────────────────────────────────
@router.callback_query(F.data == "menu:promo")
async def promo_start(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.set_state(Tools.promo_code)
    await cb.message.answer(t("promo_ask", lang), reply_markup=K.back_menu_kb(lang))
    await cb.answer()


@router.message(Tools.promo_code)
async def promo_check(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    code = (message.text or "").strip().upper()
    await state.set_state(None)
    if not code:
        return await message.answer(t("promo_ask", lang), reply_markup=K.back_menu_kb(lang))
    if SB_CONFIGURED:
        from .. import supabase_db as _sb
        res = await _sb.validate_promo(message.from_user.id, code)
    else:
        res = storage.validate_promo(code, message.from_user.id)
    if res.get("ok"):
        await message.answer(t("promo_ok", lang, code=code, disc=res["discount"]),
                             reply_markup=K.back_menu_kb(lang))
    else:
        reason = res.get("reason")
        key = {"exhausted": "promo_exhausted", "already_used": "promo_used"}.get(reason, "promo_bad")
        await message.answer(t(key, lang), reply_markup=K.back_menu_kb(lang))
