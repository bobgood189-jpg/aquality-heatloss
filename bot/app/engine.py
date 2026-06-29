"""Heat-loss engine — faithful Python port of the index.html ENGINE block.

Physics (KMK 2.01.04-18 / KMK 2.01.01-94, parameter B):
    enclosure: Q = (ΔT / R) · S · (1 + Σβ) · k_corner
    ground floor: zonal method (Staroverov, 4 zones × 2 m)
    infiltration: Q = 0.28 · 1.005 · V · ρ(t) · ΔT · ACH

The website models rooms as canvas polygons and derives exterior walls /
partitions from geometry. A chat bot can't draw, so a room here carries an
explicit list of exterior walls (direction + length) and openings. For a
standalone rectangle this reproduces computeRoom byte-for-byte — see self_test().
"""
import math
import re
from .presets import BASE_PRESETS, CITIES, ROOM_TYPES

# ── Constants (verbatim from index.html) ──
BETA_ORIENT = {"N": 0.10, "NE": 0.10, "E": 0.10, "SE": 0.05,
               "S": 0.0, "SW": 0.0, "W": 0.05, "NW": 0.10}
R_PARTITION = 0.45
CORNER_SURCHARGE = 0.05
WALL_HOMOG_DEFAULT = 0.85
ALPHA = {"in_wall": 8.7, "in_ceiling": 7.6, "in_floor": 5.8,
         "out_wall": 23, "out_roof": 12, "out_vent": 6}
WALL_ENVELOPE_R = 0.17

BETA_DOOR = {
    "none": {"beta": 0, "name": "Без надбавки"},
    "single": {"beta": 0.22, "name": "1-створ. без тамбура"},
    "double": {"beta": 0.34, "name": "2-створ. без тамбура"},
    "double_tambour": {"beta": 0.27, "name": "2-створ. + тамбур"},
    "triple_tambour": {"beta": 0.20, "name": "3-створ. + 2 тамбура"},
    "tambour": {"beta": 0.05, "name": "Тамбур без тепл. завесы"},
    "gate_tambour": {"beta": 0.10, "name": "Ворота + тамбур"},
}

WET_RATIO = {"clay": 1.157, "silicate": 1.145, "limestone": 1.05, "aac": 1.18,
             "concrete": 1.06, "wood": 1.21, "insul": 1.13, "default": 1.12}

FLOOR_ZONE_R = [2.1, 4.3, 8.6, 14.2]

AIRTIGHT = {
    "new": {"ach": 0.4, "name": "Новый / герметичный", "nameUz": "Yangi / germetik", "nameEn": "New / Airtight"},
    "normal": {"ach": 0.7, "name": "Обычный", "nameUz": "Oddiy", "nameEn": "Standard"},
    "old": {"ach": 1.2, "name": "Старый / с щелями", "nameUz": "Eski / g'ovakli", "nameEn": "Old / Drafty"},
}

HEAT_REGIMES = [
    {"id": "90/70", "name": "90/70 °C", "tm": 80, "desc": "Высокотемпературный", "descUz": "Yuqori haroratli", "descEn": "High-temperature"},
    {"id": "80/60", "name": "80/60 °C", "tm": 70, "desc": "Стандартный", "descUz": "Standart", "descEn": "Standard"},
    {"id": "75/65", "name": "75/65 °C", "tm": 70, "desc": "Низкотемпературный", "descUz": "Past haroratli", "descEn": "Low-temperature"},
    {"id": "70/55", "name": "70/55 °C", "tm": 62.5, "desc": "Конденсационный котёл", "descUz": "Kondensatsion qozon", "descEn": "Condensing boiler"},
    {"id": "55/45", "name": "55/45 °C", "tm": 50, "desc": "Тёплый режим", "descUz": "Iliq rejim", "descEn": "Warm mode"},
]
SECTION_W_NOMINAL = 150
SECTION_DT_NOMINAL = 60

ATTIC = {
    "open": {"n": 1.0, "name": "Открытый (вентилируемый)", "nameUz": "Ochiq (shamollatilgan)", "nameEn": "Open (ventilated)"},
    "closed": {"n": 0.8, "name": "Закрытый", "nameUz": "Yopiq", "nameEn": "Closed"},
    "unvent": {"n": 1.2, "name": "Невентилируемый", "nameUz": "Shamollatilmagan", "nameEn": "Unventilated"},
}

FUEL = {
    "gas": {"name": "Природный газ", "kwh": 9.3, "eff": 0.92, "tariff": 1380, "unit": "м³"},
    "coal": {"name": "Уголь", "kwh": 5.0, "eff": 0.65, "tariff": 1200, "unit": "кг"},
    "elec": {"name": "Электричество", "kwh": 1, "eff": 0.99, "tariff": 450, "unit": "кВт·ч"},
}
SEASON_DAYS = 120
LOAD_FACTOR = 0.45

BOILER_SIZES = [7, 9, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48, 60, 80, 100]
AQ_BOILERS = [
    {"maxKw": 12, "model": "Navien ACE-13K", "type": "Настенный газовый двухконтурный"},
    {"maxKw": 18, "model": "Navien Deluxe-18K", "type": "Настенный газовый двухконтурный"},
    {"maxKw": 24, "model": "Navien Deluxe-24K", "type": "Настенный газовый двухконтурный"},
    {"maxKw": 30, "model": "BAXI LUNA-3 1.310 Fi", "type": "Настенный газовый"},
    {"maxKw": 40, "model": "BAXI Slim 1.400 iN", "type": "Напольный/настенный газовый"},
    {"maxKw": 60, "model": "Ferroli PEGASUS F2N 56", "type": "Напольный газовый"},
    {"maxKw": 1e9, "model": "Buderus GB125 / каскад", "type": "Напольный или каскадная установка"},
]
AQ_RADIATORS = [
    {"model": "GLOBAL Style Plus 500", "spec": "Биметалл, высота 500 мм, ~171 Вт/секц."},
    {"model": "GLOBAL Style Plus 500 + RIFAR Monolit 500", "spec": "Биметалл+монолит"},
]

POPULAR_UZ = {
    "walls": ["brick_380", "gazo_300", "rakush_300", "kzb_250", "brick_380_i100"],
    "windows": ["imzo_70", "imzo_benkam", "double_glazing_pvc", "rehau_blitz_60"],
    "doors": ["door_metal_insulated", "door_metal_ppu60", "door_steel_30"],
    "floors": ["floor_ground_xps50", "floor_ground", "floor_xps_ufh"],
    "ceilings": ["ceil_i100", "ceil_i150", "ceil_panel_i100"],
}


def find_preset(cat, pid):
    for p in BASE_PRESETS.get(cat, []):
        if p["id"] == pid:
            return p
    return None


def disp_lambda(p):
    """λ [Вт/(м·°C)] to show next to R. For homogeneous walls it's the stored
    material λ; for composite walls it's the effective λ derived from thickness
    and R (δ/(R−R_конв)). None when not applicable — windows/doors/floors/
    ceilings carry no thickness, so they keep R only."""
    lam = p.get("lambda")
    if lam:
        return lam
    th, r = p.get("thickness"), p.get("r")
    if th and r and r > WALL_ENVELOPE_R:
        return round((th / 1000.0) / (r - WALL_ENVELOPE_R), 3)
    return None


def cls_of(s):
    s = (s or "").lower()
    if re.search(r"(вата|минват|базальт|эковат|\beps\b|\bxps\b|пенопол|ппу|пеноплекс|перлит|керамзит\b|каркас|пенофол|сип|\bsip\b|пир|\bpir\b)", s):
        return "insul"
    if re.search(r"силикат", s):
        return "silicate"
    if re.search(r"(газоблок|газобетон|пеноблок|пенобетон|пеносиликат|aac|ячеист)", s):
        return "aac"
    if re.search(r"(ракушеч|известн)", s):
        return "limestone"
    if re.search(r"(монолит|панель|ж/б|жб |бетон|керамзитоблок|керамзитобетон)", s):
        return "concrete"
    if re.search(r"(дерев|сосна|ель|дуб|осб|\bosb\b|фанер|гкл|гвл|вагонк)", s):
        return "wood"
    if re.search(r"(кирпич|пахса|саман|шлакоблок|керамоблок)", s):
        return "clay"
    return "default"


def preset_class(p):
    return cls_of(((p or {}).get("name", "") or "") + " " +
                  ((p or {}).get("group", "") or "") + " " +
                  ((p or {}).get("desc", "") or ""))


def wet_ratio(cls, mode):
    return WET_RATIO.get(cls, WET_RATIO["default"]) if mode == "B" else 1.0


def regime_r(r_total, envelope, cls, mode):
    k = wet_ratio(cls, mode)
    if k == 1:
        return r_total
    return envelope + max(0, (r_total - envelope)) / k


def door_beta(door_type):
    return BETA_DOOR.get(door_type, BETA_DOOR["none"])["beta"]


def attic_n(attic):
    return ATTIC.get(attic, ATTIC["closed"])["n"]


def airtight_ach(airtight):
    return AIRTIGHT.get(airtight, AIRTIGHT["normal"])["ach"]


def heat_regime(rid):
    for r in HEAT_REGIMES:
        if r["id"] == rid:
            return r
    return HEAT_REGIMES[0]


def _lmtd(tin, tout, tr):
    a, b = tin - tr, tout - tr
    if a <= 0 or b <= 0:
        return max(a, b, 1)
    if abs(a - b) < 0.5:
        return (a + b) / 2
    return (a - b) / math.log(a / b)


def section_watt(t_int, regime_id):
    r = heat_regime(regime_id)
    parts = r["id"].split("/")
    tin = float(parts[0]) if parts[0] else 80
    tout = float(parts[1]) if len(parts) > 1 and parts[1] else 60
    dt = _lmtd(tin, tout, t_int)
    return SECTION_W_NOMINAL * (max(dt, 1) / SECTION_DT_NOMINAL) ** 1.3


def zonal_floor_areas(area, perimeter):
    if perimeter <= 0.01:
        return [{"r": FLOOR_ZONE_R[3], "a": area}]
    areas = [0, 0, 0, 0]
    rem = area
    for z in range(3):
        if rem <= 0:
            break
        strip = min(rem, perimeter * 2)
        areas[z] = strip
        rem -= strip
    areas[3] = max(0, rem)
    return [{"r": FLOOR_ZONE_R[i], "a": a} for i, a in enumerate(areas) if a > 0.01]


def recommend_boiler(kw):
    for s in BOILER_SIZES:
        if s >= kw:
            return s
    return math.ceil(kw / 10) * 10


def recommend_pipe(kw):
    if kw <= 7:
        return '20 (¾")'
    if kw <= 15:
        return '25 (1")'
    if kw <= 25:
        return '32 (1¼")'
    if kw <= 40:
        return '40 (1½")'
    return '50 (2")'


def aq_boiler(boiler_kw):
    for b in AQ_BOILERS:
        if b["maxKw"] >= boiler_kw:
            return b
    return AQ_BOILERS[-1]


def aq_rad_model(sections):
    return AQ_RADIATORS[1] if sections > 150 else AQ_RADIATORS[0]


def compute_room(room, ctx):
    """room: dict with type_id, tInt, length, width, height, walls[], openings[],
    is_ground, is_top.  ctx: object-level settings (mat, attic, airtight,
    lambda_mode, heat_regime, tExt)."""
    t_int = room["tInt"]
    t_ext = ctx["tExt"]
    d_tout = t_int - t_ext
    mode = ctx.get("lambda_mode", "A")
    mat = ctx["mat"]
    breakdown = {"wall": 0.0, "window": 0.0, "door": 0.0, "floor": 0.0, "ceiling": 0.0, "infil": 0.0}
    height = room["height"]
    area = room["length"] * room["width"]
    if d_tout <= 0:
        return {"area": area, "qW": 0.0, "breakdown": breakdown, "sections": 0}

    wp = find_preset("walls", mat["wallId"])
    wall_r = (regime_r(wp["r"], WALL_ENVELOPE_R, preset_class(wp), mode) * WALL_HOMOG_DEFAULT) if wp else 0

    walls = room.get("walls", [])
    ext_dirs = set(w["dir"] for w in walls)
    corner_k = (1 + CORNER_SURCHARGE) if len(ext_dirs) >= 2 else 1.0

    openings = room.get("openings", [])
    for w in walls:
        d = w["dir"]
        beta = BETA_ORIENT.get(d, 0)
        # per-wall preset override (optional)
        edge_r = wall_r
        if w.get("preset"):
            ep = find_preset("walls", w["preset"])
            if ep:
                edge_r = regime_r(ep["r"], WALL_ENVELOPE_R, preset_class(ep), mode) * WALL_HOMOG_DEFAULT
        gross = w["length"] * height
        op_area = 0.0
        for op in openings:
            if op.get("dir") != d:
                continue
            a = (op.get("w", 0)) * (op.get("h", 0)) * (op.get("count", 1))
            op_area += a
            pl = "windows" if op["kind"] == "window" else "doors"
            pp = find_preset(pl, op.get("preset")) or find_preset(
                pl, mat["windowId"] if op["kind"] == "window" else mat["doorId"])
            op_r = (1 / op["customU"]) if op.get("customU", 0) > 0 else (pp["r"] if pp else 0)
            d_beta = door_beta(op.get("door_type")) if op["kind"] == "door" else 0
            k = (1 + beta + d_beta) * corner_k
            if op_r > 0:
                breakdown[op["kind"]] += (d_tout / op_r) * a * k
        net = max(0, gross - op_area)
        if edge_r > 0 and net > 0:
            breakdown["wall"] += (d_tout / edge_r) * net * (1 + beta) * corner_k

    perimeter = sum(w["length"] for w in walls)
    if room.get("is_ground"):
        fp = find_preset("floors", mat["floorId"])
        if fp:
            if fp.get("ground"):
                add_r = fp.get("addR", 0)
                n = fp.get("n", 1)
                for z in zonal_floor_areas(area, perimeter):
                    breakdown["floor"] += (d_tout / (z["r"] + add_r)) * z["a"] * n
            else:
                breakdown["floor"] += (d_tout / regime_r(fp["r"], 0.17, preset_class(fp), mode)) * area * fp.get("n", 1)

    if room.get("is_top"):
        cp = find_preset("ceilings", mat["ceilingId"])
        if cp:
            breakdown["ceiling"] += (d_tout / regime_r(cp["r"], 0.17, preset_class(cp), mode)) * area * attic_n(ctx.get("attic", "closed"))

    v = area * height
    rho = (1.293 * 273) / (273 + t_ext)
    breakdown["infil"] = 0.28 * 1.005 * v * rho * d_tout * airtight_ach(ctx.get("airtight", "normal"))

    q_w = sum(breakdown.values())
    sections = math.ceil((q_w * 1.15) / section_watt(t_int, ctx.get("heat_regime", "90/70")))
    return {"area": area, "qW": q_w, "breakdown": breakdown, "sections": sections}


def compute_object(obj):
    """obj: dict with tExt, mat, attic, airtight, lambda_mode, heat_regime, floors[]."""
    floors = obj["floors"]
    last = len(floors) - 1
    total_w = total_area = total_sections = room_count = 0.0
    by_type = {"wall": 0.0, "window": 0.0, "door": 0.0, "floor": 0.0, "ceiling": 0.0, "infil": 0.0}
    fres = []
    ctx_base = {k: obj.get(k) for k in ("mat", "attic", "airtight", "lambda_mode", "heat_regime", "tExt")}
    for fi, fl in enumerate(floors):
        f_w = f_area = f_sec = 0.0
        rres = []
        for room in fl["rooms"]:
            ctx = dict(ctx_base)
            r = compute_room({**room, "height": room.get("height", fl.get("height", 3.0)),
                              "is_ground": fi == 0, "is_top": fi == last}, ctx)
            f_w += r["qW"]
            f_area += r["area"]
            f_sec += r["sections"]
            room_count += 1
            for k in by_type:
                by_type[k] += r["breakdown"][k]
            rres.append({**room, "qW": r["qW"], "qKw": r["qW"] / 1000,
                         "area": r["area"], "sections": r["sections"], "breakdown": r["breakdown"]})
        total_w += f_w
        total_area += f_area
        total_sections += f_sec
        fres.append({"name": fl.get("name"), "height": fl.get("height", 3.0),
                     "qW": f_w, "qKw": f_w / 1000, "area": f_area, "sections": f_sec, "rooms": rres})
    return {
        "floors": fres, "byType": by_type,
        "totalW": total_w, "totalKw": total_w / 1000, "boilerKw": (total_w / 1000) * 1.25,
        "totalArea": total_area, "totalSections": int(total_sections), "roomCount": int(room_count),
    }


def cost_estimate(total_kw):
    monthly_kwh = total_kw * 24 * 30 * LOAD_FACTOR
    out = {}
    for k, f in FUEL.items():
        units = monthly_kwh / (f["kwh"] * f["eff"])
        out[k] = {"month": round(units * f["tariff"]), "units": units,
                  "name": f["name"], "unit": f["unit"]}
    return {"monthlyKwh": monthly_kwh, "out": out}


SELFTEST_PINNED_Q = 4198.1


def self_test():
    """Reproduce the website's pinned reference: room 4×5×3, brick_380 / closed
    attic / normal airtightness, t20/t-14 → qW ≈ 4198.1 W."""
    room = {
        "type_id": "living_room", "tInt": 20, "length": 4, "width": 5, "height": 3.0,
        "walls": [{"dir": "N", "length": 4}, {"dir": "S", "length": 4},
                  {"dir": "W", "length": 5}, {"dir": "E", "length": 5}],
        "openings": [], "is_ground": True, "is_top": True,
    }
    ctx = {
        "mat": {"wallId": "brick_380", "windowId": "double_glazing_pvc",
                "doorId": "door_metal_insulated", "floorId": "floor_xps50", "ceilingId": "ceil_i100"},
        "attic": "closed", "airtight": "normal", "heat_regime": "90/70",
        "lambda_mode": "A", "tExt": -14,
    }
    r = compute_room(room, ctx)
    return r


if __name__ == "__main__":
    r = self_test()
    b = r["breakdown"]
    print("walls   ", round(b["wall"], 1))
    print("ceiling ", round(b["ceiling"], 1))
    print("floor   ", round(b["floor"], 1))
    print("infil   ", round(b["infil"], 1))
    print("qW      ", round(r["qW"], 1), "(pinned", SELFTEST_PINNED_Q, ")")
    ok = abs(r["qW"] - SELFTEST_PINNED_Q) <= SELFTEST_PINNED_Q * 0.015
    print("PASS" if ok else "FAIL")
