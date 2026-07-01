"""Inline keyboard builders. Callback data stays ASCII and short (<64 bytes):
materials reference groups/items by index/id, never by localized name."""
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                           ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)

from .presets import BASE_PRESETS, CITIES, ROOM_TYPES
from .engine import (ATTIC, AIRTIGHT, HEAT_REGIMES, BETA_DOOR, POPULAR_UZ)
from . import i18n
from .i18n import t, loc_name

PAGE = 8
DIRS = ["N", "E", "S", "W"]


def _rows(buttons, per_row=2):
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def btn(text, data):
    return InlineKeyboardButton(text=text, callback_data=data)


def with_back(markup, lang):
    """Append a '◀️ Назад' row (callback nav:back) to an existing inline keyboard."""
    rows = list(markup.inline_keyboard) + [[btn(t("back", lang), "nav:back")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_only_kb(lang):
    """A lone '◀️ Назад' button — for text-input steps that have no other buttons."""
    return kb([[btn(t("back", lang), "nav:back")]])


# ── language ──
def lang_kb():
    rows = [[btn(i18n.LANG_NAMES[l], f"lang:{l}")] for l in i18n.LANGS]
    return kb(rows)


# ── main menu ──
def menu_kb(lang, is_owner=False, paywall=False):
    rows = [
        [btn("🛒 Купить подписку", "menu:buy")],
        [btn(t("menu_materials", lang), "menu:materials"), btn(t("menu_faq", lang), "menu:faq")],
        [btn(t("menu_contact", lang), "menu:contact"), btn(t("menu_lang", lang), "menu:lang")],
    ]
    if is_owner:
        rows.append([btn("👑 Админ-панель", "menu:admin")])
    return kb(rows)


# ── tariffs / paywall ──
def tariffs_kb(lang, pay_tg):
    rows = [[InlineKeyboardButton(text=t("tariffs_pay", lang), url=f"https://t.me/{pay_tg}")]]
    rows.append([btn(t("menu", lang), "menu:home")])
    return kb(rows)


def back_menu_kb(lang):
    return kb([[btn(t("menu", lang), "menu:home")]])


# ── cities ──
def cities_kb(lang):
    buttons = [btn(f"{c['name']} ({int(c['t'])}°)", f"city:{c['id']}") for c in CITIES]
    return kb(_rows(buttons, 2))


# ── object params ──
def floors_kb(lang):
    buttons = [btn(str(n), f"floors:{n}") for n in range(1, 6)]
    return kb([buttons])


def attic_kb(lang):
    rows = [[btn(f"{a['name'] if lang == 'ru' else a.get('name' + lang.capitalize(), a['name'])}", f"attic:{k}")]
            for k, a in ATTIC.items()]
    return kb(rows)


def airtight_kb(lang):
    rows = []
    for k, a in AIRTIGHT.items():
        label = a["name"] if lang == "ru" else a.get("name" + lang.capitalize(), a["name"])
        rows.append([btn(f"{label} (ACH {a['ach']})", f"air:{k}")])
    return kb(rows)


def regime_kb(lang):
    rows = []
    for r in HEAT_REGIMES:
        desc = r["desc"] if lang == "ru" else r.get("desc" + lang.capitalize(), r["desc"])
        rows.append([btn(f"{r['name']} — {desc}", f"reg:{r['id']}")])
    return kb(rows)


def lambda_kb(lang):
    return kb([[btn(t("lambda_a", lang), "lam:A")], [btn(t("lambda_b", lang), "lam:B")]])


# ── materials ──
def _groups(cat):
    seen, out = set(), []
    for p in BASE_PRESETS[cat]:
        g = p.get("group", "")
        if g not in seen:
            seen.add(g)
            out.append(g)
    return out


def mat_groups_kb(cat, lang):
    rows = [[btn(t("popular", lang), f"matpg:{cat}:pop:0")]]
    for gi, g in enumerate(_groups(cat)):
        rows.append([btn(g, f"matpg:{cat}:{gi}:0")])
    return kb(rows)


def mat_items_kb(cat, group_idx, page, lang):
    if group_idx == "pop":
        ids = POPULAR_UZ.get(cat, [])
        items = [p for pid in ids for p in BASE_PRESETS[cat] if p["id"] == pid]
    else:
        g = _groups(cat)[int(group_idx)]
        items = [p for p in BASE_PRESETS[cat] if p.get("group") == g]
    page = int(page)
    total = len(items)
    chunk = items[page * PAGE:(page + 1) * PAGE]
    rows = []
    from .engine import disp_lambda
    for p in chunk:
        r = p.get("r")
        lam = disp_lambda(p)
        tail = f" · R{r}" + (f" · λ{lam}" if lam else "")
        # keep the name readable: trim the name, not the R/λ figures
        name = loc_name(p, lang)
        label = (name[:60 - len(tail)] + tail) if len(name) + len(tail) > 60 else name + tail
        rows.append([btn(label, f"mat:{cat}:{p['id']}")])
    nav = []
    if page > 0:
        nav.append(btn("◀️", f"matpg:{cat}:{group_idx}:{page - 1}"))
    if (page + 1) * PAGE < total:
        nav.append(btn("▶️", f"matpg:{cat}:{group_idx}:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([btn(t("all_groups", lang), f"matgrp:{cat}")])
    return kb(rows)


# ── rooms ──
def rooms_menu_kb(lang, cur_floor, n_floors, has_rooms):
    rows = [[btn(t("add_room", lang), "room:add")]]
    if has_rooms:
        if cur_floor < n_floors - 1:
            rows.append([btn(t("next_floor", lang), "room:nextfloor")])
        rows.append([btn(t("calc_now", lang), "room:calc")])
    return kb(rows)


def room_types_kb(lang):
    buttons = [btn(f"{loc_name(rt, lang)} +{int(rt['t'])}°", f"rt:{rt['id']}") for rt in ROOM_TYPES]
    return kb(_rows(buttons, 2))


def ext_walls_kb(lang, selected):
    rows = []
    pair = []
    for d in DIRS:
        mark = "✅ " if d in selected else ""
        pair.append(btn(f"{mark}{t('dir_' + d, lang)}", f"dir:{d}"))
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([btn(t("done", lang), "extdone")])
    return kb(rows)


def opening_dir_kb(lang, dirs, kind):
    """kind: 'win' or 'door' — choose which external wall the opening sits on."""
    buttons = [btn(t("dir_" + d, lang), f"{kind}dir:{d}") for d in dirs]
    return kb(_rows(buttons, 2))


def door_beta_kb(lang):
    rows = []
    for k, d in BETA_DOOR.items():
        suffix = f" (+{d['beta']})" if d["beta"] else ""
        rows.append([btn(f"{d['name']}{suffix}", f"dbeta:{k}")])
    return kb(rows)


def count_kb(prefix, lang, maximum=6):
    buttons = [btn(str(n), f"{prefix}:{n}") for n in range(0, maximum + 1)]
    return kb(_rows(buttons, 4))


# ── results ──
def results_kb(lang):
    return kb([
        [btn(t("menu_lead", lang), "menu:lead")],
        [btn(t("menu_calc", lang), "menu:calc"), btn(t("menu", lang), "menu:home")],
    ])


def share_phone_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("lead_share_phone", lang), request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True)


def remove_kb():
    return ReplyKeyboardRemove()


# ── Shop (subscription purchase) ──────────────────────────────────────────────

def shop_plans_kb():
    return kb([
        [btn("🔹 PRO", "buy:plan:pro")],
        [btn("🔸 MAX",  "buy:plan:max")],
        [btn("❌ Отмена", "buy:cancel")],
    ])


def shop_duration_kb():
    return kb([
        [btn("1 месяц", "buy:dur:1"),      btn("3 месяца", "buy:dur:3")],
        [btn("6 месяцев", "buy:dur:6"),    btn("12 месяцев 🔥", "buy:dur:12")],
        [btn("◀️ Назад", "buy:back"),       btn("❌ Отмена", "buy:cancel")],
    ])


def shop_promo_kb():
    return kb([
        [btn("✅ Да, ввести", "buy:promo:yes"), btn("➡️ Пропустить", "buy:promo:no")],
        [btn("◀️ Назад", "buy:back"),           btn("❌ Отмена", "buy:cancel")],
    ])


def shop_promo_retry_kb():
    return kb([
        [btn("🔁 Ввести другой", "buy:promo:yes"), btn("➡️ Пропустить", "buy:promo:no")],
        [btn("◀️ Назад", "buy:back"),              btn("❌ Отмена", "buy:cancel")],
    ])


def shop_back_cancel_kb():
    return kb([[btn("◀️ Назад", "buy:back"), btn("❌ Отмена", "buy:cancel")]])


def shop_confirm_kb():
    return kb([
        [btn("✅ Подтвердить и оплатить", "buy:confirm")],
        [btn("✏️ Изменить", "buy:edit"), btn("❌ Отмена", "buy:cancel")],
    ])


def shop_cancel_kb():
    return kb([[btn("❌ Отменить заказ", "buy:cancel")]])


def shop_resume_kb(oid_str: str, order_id: int):
    return kb([
        [btn(f"▶️ Продолжить {oid_str}", f"buy:resume:{order_id}")],
        [btn("🆕 Новый заказ", "buy:new")],
    ])


def admin_review_kb(order_id: int):
    return kb([
        [btn("✅ Подтвердить", f"review:ok:{order_id}"),
         btn("❌ Отклонить",   f"review:nok:{order_id}")],
    ])


def admin_reject_reasons_kb(order_id: int):
    return kb([
        [btn("💰 Сумма не совпадает",   f"review:rej:{order_id}:sum")],
        [btn("⏳ Платёж не поступил",   f"review:rej:{order_id}:norecv")],
        [btn("🖼 Плохой скриншот",      f"review:rej:{order_id}:bad")],
        [btn("📝 Другая причина",       f"review:rej:{order_id}:other")],
    ])
