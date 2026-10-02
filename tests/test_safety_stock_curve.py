"""Tests for safety_stock_curve (Type-2 exchange curve)."""
from __future__ import annotations

import math
from statistics import NormalDist

import pytest

import walopy as wl

_norm = NormalDist()

ITEMS = [
    {"name": "A", "demand_rate": 100, "demand_std": 10, "lead_time": 2,  "unit_value": 10},
    {"name": "B", "demand_rate":  50, "demand_std":  5, "lead_time": 1,  "unit_value":  5},
    {"name": "C", "demand_rate": 200, "demand_std": 20, "lead_time": 3,  "unit_value":  8},
]


# ─── Baseline (no target) ────────────────────────────────────────────────────

def test_no_target_z_is_zero():
    r = wl.safety_stock_curve(ITEMS)
    assert r.z == pytest.approx(0.0, abs=1e-9)


def test_no_target_service_level_is_50pct():
    r = wl.safety_stock_curve(ITEMS)
    assert r.service_level == pytest.approx(0.5, abs=1e-6)


def test_no_target_ss_investment_is_zero():
    r = wl.safety_stock_curve(ITEMS)
    assert r.ss_investment == pytest.approx(0.0, abs=1e-9)


# ─── target_service_level ────────────────────────────────────────────────────

def test_target_sl_z_matches_normal_quantile():
    sl = 0.95
    r = wl.safety_stock_curve(ITEMS, target_service_level=sl)
    assert r.z == pytest.approx(_norm.inv_cdf(sl), rel=1e-6)


def test_target_sl_service_level_matches():
    r = wl.safety_stock_curve(ITEMS, target_service_level=0.95)
    assert r.service_level == pytest.approx(0.95, rel=1e-6)


def test_target_sl_higher_means_more_ss():
    r90 = wl.safety_stock_curve(ITEMS, target_service_level=0.90)
    r99 = wl.safety_stock_curve(ITEMS, target_service_level=0.99)
    assert r99.ss_investment > r90.ss_investment


def test_target_sl_ss_investment_correct():
    sl = 0.95
    z  = _norm.inv_cdf(sl)
    r  = wl.safety_stock_curve(ITEMS, target_service_level=sl)
    expected = z * sum(
        it["demand_std"] * math.sqrt(it["lead_time"]) * it["unit_value"]
        for it in ITEMS
    )
    assert r.ss_investment == pytest.approx(expected, rel=1e-6)


# ─── target_ss_investment ────────────────────────────────────────────────────

def test_target_inv_ss_investment_matches():
    target = 500.0
    r = wl.safety_stock_curve(ITEMS, target_ss_investment=target)
    assert r.ss_investment == pytest.approx(target, rel=1e-6)


def test_target_inv_sum_of_items_matches():
    target = 500.0
    r = wl.safety_stock_curve(ITEMS, target_ss_investment=target)
    total = sum(q["investment"] for q in r.optimal_quantities)
    assert total == pytest.approx(target, rel=1e-6)


def test_target_inv_z_correct():
    target = 500.0
    total_sigma_v = sum(
        it["demand_std"] * math.sqrt(it["lead_time"]) * it["unit_value"]
        for it in ITEMS
    )
    r = wl.safety_stock_curve(ITEMS, target_ss_investment=target)
    assert r.z == pytest.approx(target / total_sigma_v, rel=1e-6)


# ─── reorder_point ────────────────────────────────────────────────────────────

def test_reorder_point_present_when_demand_rate_given():
    r = wl.safety_stock_curve(ITEMS, target_service_level=0.95)
    for q in r.optimal_quantities:
        assert "reorder_point" in q


def test_reorder_point_absent_when_no_demand_rate():
    items_no_d = [{"demand_std": 10, "lead_time": 2, "unit_value": 5}]
    r = wl.safety_stock_curve(items_no_d, target_service_level=0.95)
    assert "reorder_point" not in r.optimal_quantities[0]


def test_reorder_point_formula():
    sl = 0.95
    z  = _norm.inv_cdf(sl)
    r  = wl.safety_stock_curve(ITEMS, target_service_level=sl)
    for q, it in zip(r.optimal_quantities, ITEMS):
        expected_rop = it["demand_rate"] * it["lead_time"] + z * it["demand_std"] * math.sqrt(it["lead_time"])
        assert q["reorder_point"] == pytest.approx(expected_rop, rel=1e-5)


# ─── lead_time_std ───────────────────────────────────────────────────────────

def test_lead_time_std_increases_sigma_dlt():
    items_no_lt = [{"demand_rate": 100, "demand_std": 10, "lead_time": 2, "unit_value": 1}]
    items_lt    = [{"demand_rate": 100, "demand_std": 10, "lead_time": 2,
                    "lead_time_std": 0.5, "unit_value": 1}]
    r_no = wl.safety_stock_curve(items_no_lt, target_service_level=0.95)
    r_lt = wl.safety_stock_curve(items_lt,    target_service_level=0.95)
    assert r_lt.ss_investment > r_no.ss_investment


# ─── Mutual exclusion & validation ───────────────────────────────────────────

def test_both_targets_raises():
    with pytest.raises(ValueError):
        wl.safety_stock_curve(ITEMS, target_service_level=0.95, target_ss_investment=500)


def test_empty_items_raises():
    with pytest.raises(ValueError):
        wl.safety_stock_curve([])


def test_invalid_service_level_raises():
    with pytest.raises(ValueError):
        wl.safety_stock_curve(ITEMS, target_service_level=1.0)

    with pytest.raises(ValueError):
        wl.safety_stock_curve(ITEMS, target_service_level=0.0)


# ─── Output helpers ──────────────────────────────────────────────────────────

def test_to_frame_columns():
    import pandas as pd
    df = wl.safety_stock_curve(ITEMS, target_service_level=0.95).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "safety_stock"  in df.columns
    assert "investment"    in df.columns
    assert "reorder_point" in df.columns


def test_curve_to_frame_columns():
    import pandas as pd
    df = wl.safety_stock_curve(ITEMS).curve_to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "z"             in df.columns
    assert "service_level" in df.columns
    assert "ss_investment" in df.columns


def test_curve_points_count():
    r = wl.safety_stock_curve(ITEMS, n_curve_points=40)
    assert len(r.curve_points) == 40


def test_curve_service_level_monotone():
    r = wl.safety_stock_curve(ITEMS)
    sls = [pt["service_level"] for pt in r.curve_points]
    assert all(sls[i] <= sls[i + 1] for i in range(len(sls) - 1))
