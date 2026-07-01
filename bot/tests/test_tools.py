"""Regression tests for the standalone menu calculators (app/handlers/tools.py).
Pure compute only — no Telegram I/O. Guards that each tool stays consistent with
the engine it borrows from."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.handlers import tools as T  # noqa: E402
from app import engine as E  # noqa: E402


def test_quick_estimate_scales_with_quality():
    good = T.quick_estimate(120, "good")
    poor = T.quick_estimate(120, "poor")
    assert good["wm2"] == 70 and poor["wm2"] == 160
    assert poor["kw"] > good["kw"]                 # worse insulation → more loss
    assert good["kw"] == round(120 * 70 / 1000, 1)  # area × norm
    assert good["boiler"] >= good["kw"]            # boiler sized above load


def test_boiler_matches_engine():
    r = T.boiler_info(12.5)
    assert r["margin"] == round(12.5 * 1.25, 1)
    assert r["size"] == E.recommend_boiler(12.5 * 1.25)
    assert r["pipe"] == E.recommend_pipe(12.5 * 1.25)


def test_radiator_regimes_ordered():
    r = T.rad_sections(1.6)
    # a hotter regime needs fewer sections than a cooler one
    assert r["s9070"] <= r["s8060"] <= r["s7565"]
    assert r["s8060"] == math.ceil(1600 * 1.15 / E.section_watt(20, "80/60"))


def test_fuel_gas_cheapest():
    r = T.fuel_info(12.5)
    assert r["load"] == 45
    assert "Природный газ" in r["lines"] and "сум/мес" in r["lines"]


def test_insulation_thickness_formula():
    lines = T.insul_lines(0.75, 2.8)
    # XPS λ0.032: ΔR 2.05 → 65.6 mm → ceil 66
    assert "66 мм" in lines
    assert T.insul_lines(1.0, 1.0) == T.insul_lines(1.0, 1.0)  # deterministic


def test_power_converter():
    r = T.convert_power(10)
    assert r["w"] == "10 000"
    assert r["kcal"] == "8 598"          # 10 × 859.845 ≈ 8598
