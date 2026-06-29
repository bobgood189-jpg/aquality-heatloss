"""Regression tests for the ported heat-loss engine. Mirrors runSelfTest() in index.html."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import engine as E  # noqa: E402


def _ctx(**over):
    ctx = {
        "mat": {"wallId": "brick_380", "windowId": "double_glazing_pvc",
                "doorId": "door_metal_insulated", "floorId": "floor_xps50", "ceilingId": "ceil_i100"},
        "attic": "closed", "airtight": "normal", "heat_regime": "90/70",
        "lambda_mode": "A", "tExt": -14,
    }
    ctx.update(over)
    return ctx


def _room(openings=None, **over):
    r = {
        "type_id": "living_room", "tInt": 20, "length": 4, "width": 5, "height": 3.0,
        "walls": [{"dir": "N", "length": 4}, {"dir": "S", "length": 4},
                  {"dir": "W", "length": 5}, {"dir": "E", "length": 5}],
        "openings": openings or [], "is_ground": True, "is_top": True,
    }
    r.update(over)
    return r


def test_pinned_reference():
    r = E.compute_room(_room(), _ctx())
    assert abs(r["qW"] - E.SELFTEST_PINNED_Q) <= E.SELFTEST_PINNED_Q * 0.015


def test_no_double_minus():
    r = E.compute_room(_room(), _ctx())
    assert r["qW"] > 0


def test_infiltration_formula():
    r = E.compute_room(_room(), _ctx())
    v, rho = 20 * 3, (1.293 * 273) / (273 - 14)
    expected = 0.28 * 1.005 * v * rho * 34 * E.airtight_ach("normal")
    assert abs(r["breakdown"]["infil"] - expected) < 1e-3


def test_window_subtracts_from_wall():
    base = E.compute_room(_room(), _ctx())
    win = E.compute_room(_room([{"kind": "window", "dir": "N", "w": 2, "h": 1.5, "count": 1}]), _ctx())
    assert win["breakdown"]["wall"] < base["breakdown"]["wall"]
    assert win["breakdown"]["window"] > 0


def test_door_beta_increases_loss():
    d_none = E.compute_room(_room([{"kind": "door", "dir": "N", "w": 1, "h": 2.1, "count": 1, "door_type": "none"}]), _ctx())
    d_dbl = E.compute_room(_room([{"kind": "door", "dir": "N", "w": 1, "h": 2.1, "count": 1, "door_type": "double"}]), _ctx())
    assert d_dbl["breakdown"]["door"] > d_none["breakdown"]["door"]


def test_lambda_mode_b_increases():
    a = E.compute_room(_room(), _ctx(lambda_mode="A"))
    b = E.compute_room(_room(), _ctx(lambda_mode="B"))
    assert b["qW"] > a["qW"]


def test_compute_object_boiler_margin():
    obj = {**_ctx(), "floors": [{"name": "1 этаж", "height": 3.0, "rooms": [_room()]}]}
    res = E.compute_object(obj)
    assert abs(res["boilerKw"] - res["totalKw"] * 1.25) < 1e-9
