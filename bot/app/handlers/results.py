"""Result rendering, equipment recommendation, fuel cost and lead capture."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .. import engine as E
from ..config import CONTACT, OWNER_ID, OWNER_USERNAME
from .. import storage
from ..i18n import t
from ..states import Wizard
from ..keyboards import results_kb, share_phone_kb, remove_kb, back_menu_kb
from .util import get_lang

router = Router()

_COMP_KEYS = ["wall", "window", "door", "floor", "ceiling", "infil"]


def build_object(data):
    """Convert accumulated FSM data into the engine object dict."""
    return {
        "tExt": data["tExt"],
        "mat": data["mat"],
        "attic": data.get("attic", "closed"),
        "airtight": data.get("airtight", "normal"),
        "lambda_mode": data.get("lambda_mode", "A"),
        "heat_regime": data.get("heat_regime", "90/70"),
        "floors": data["floors"],
    }


def _bar(frac):
    filled = max(0, min(10, round(frac * 10)))
    return "█" * filled + "░" * (10 - filled)


def format_results(res, lang):
    total_w = res["totalW"]
    lines = [t("result_title", lang), ""]
    lines.append(t("res_totalkw", lang, kw=round(res["totalKw"], 2)))
    lines.append(t("res_area", lang, area=round(res["totalArea"], 1),
                   rooms=res["roomCount"], floors=len(res["floors"])))
    if res["totalArea"] > 0:
        lines.append(t("res_persqm", lang, v=round(total_w / res["totalArea"])))
    lines.append("")
    lines.append(t("res_breakdown", lang))
    for k in _COMP_KEYS:
        val = res["byType"].get(k, 0)
        if val <= 0:
            continue
        frac = val / total_w if total_w else 0
        lines.append(f"  {t('comp_' + k, lang)}: {_bar(frac)} {round(val / 1000, 2)} кВт ({round(frac * 100)}%)")
    # Equipment recommendations (boiler / radiators / pipe) intentionally omitted —
    # see commit "remove equipment recommendations". Re-add res_boiler/res_sections/
    # res_pipe/res_boiler_model lines here to restore.
    lines.append("")
    lines.append(t("res_fuel", lang))
    cost = E.cost_estimate(res["totalKw"])
    for k in ("gas", "coal", "elec"):
        c = cost["out"][k]
        lines.append(f"  • {c['name']}: ≈ {c['month']:,} сум ({round(c['units'])} {c['unit']})".replace(",", " "))
    lines.append("")
    lines.append(t("res_disclaimer", lang))
    return "\n".join(lines)


async def send_results(message, res, lang, state):
    await state.update_data(last_kw=round(res["totalKw"], 2))
    storage.log_event("calc_complete")
    await message.answer(format_results(res, lang), reply_markup=results_kb(lang),
                         disable_web_page_preview=True)


# ── Lead capture ──
@router.callback_query(F.data == "menu:lead")
async def lead_start(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(state, cb.from_user.id)
    await state.set_state(Wizard.lead_name)
    await cb.message.answer(t("lead_start", lang))
    await cb.answer()


@router.message(Wizard.lead_name)
async def lead_name(message: Message, state: FSMContext):
    lang = await get_lang(state, message.from_user.id)
    name = (message.text or "").strip()[:80]
    await state.update_data(lead_name=name)
    await state.set_state(Wizard.lead_phone)
    await message.answer(t("lead_phone", lang), reply_markup=share_phone_kb(lang))


@router.message(Wizard.lead_phone, F.contact)
async def lead_phone_contact(message: Message, state: FSMContext):
    await _finish_lead(message, state, message.contact.phone_number)


@router.message(Wizard.lead_phone)
async def lead_phone_text(message: Message, state: FSMContext):
    await _finish_lead(message, state, (message.text or "").strip()[:40])


async def _finish_lead(message: Message, state: FSMContext, phone):
    lang = await get_lang(state, message.from_user.id)
    data = await state.get_data()
    name = data.get("lead_name", "—")
    city = data.get("cityName", "")
    kw = data.get("last_kw")
    user = message.from_user
    payload = {"floors": data.get("floors"), "mat": data.get("mat"),
               "tExt": data.get("tExt"), "attic": data.get("attic"),
               "airtight": data.get("airtight"), "lambda_mode": data.get("lambda_mode")}
    storage.save_lead(user.id, user.username, name, phone, city, kw, payload)
    storage.log_event("lead_sent")
    await message.answer(t("lead_sent", lang, name=name, phone=phone), reply_markup=remove_kb())
    await message.answer(t("menu", lang), reply_markup=back_menu_kb(lang))
    await _notify_owner(message.bot, name, phone, city, kw, user)
    await state.set_state(None)


async def _notify_owner(bot, name, phone, city, kw, user):
    uname = f"@{user.username}" if user.username else f"id{user.id}"
    txt = (f"🔔 <b>Новая заявка</b>\n\n"
           f"👤 {name}\n📱 {phone}\n🏙 {city or '—'}\n"
           f"🔥 Расчёт: {kw if kw is not None else '—'} кВт\n"
           f"💬 Telegram: {uname}")
    targets = []
    if OWNER_ID:
        targets.append(OWNER_ID)
    for tgt in targets:
        try:
            await bot.send_message(tgt, txt)
        except Exception:
            pass
