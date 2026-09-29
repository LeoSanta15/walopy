"""Tests for exchange_curve."""
from __future__ import annotations

import math
import pytest
import walopy as wl


ITEMS = [
    {"name": "A", "demand": 1000, "ordering_cost": 50,  "holding_cost": 2,  "unit_value": 10},
    {"name": "B", "demand":  500, "ordering_cost": 30,  "holding_cost": 1,  "unit_value":  5},
    {"name": "C", "demand": 2000, "ordering_cost": 100, "holding_cost": 4,  "unit_value":  8},
]


def _eoq(D, K, h):
    return math.sqrt(2 * D * K / h)


# ─── EOQ point (no target) ────────────────────────────────────────────────────

def test_no_target_multiplier_is_one():
    r = wl.exchange_curve(ITEMS)
    assert r.multiplier == pytest.approx(1.0, rel=1e-9)


def test_no_target_n_matches_individual_eoq():
    N_expected = sum(_eoq(it["demand"], it["ordering_cost"], it["holding_cost"])
                     and it["demand"] / _eoq(it["demand"], it["ordering_cost"], it["holding_cost"])
                     for it in ITEMS)
    r = wl.exchange_curve(ITEMS)
    assert r.n_orders_eoq == pytest.approx(N_expected, rel=1e-6)


def test_no_target_investment_matches_individual_eoq():
    I_expected = sum(
        _eoq(it["demand"], it["ordering_cost"], it["holding_cost"])
        * it["unit_value"] / 2
        for it in ITEMS
    )
    r = wl.exchange_curve(ITEMS)
    assert r.investment_eoq == pytest.approx(I_expected, rel=1e-6)


def test_no_target_optimal_equals_eoq_point():
    r = wl.exchange_curve(ITEMS)
    assert r.n_orders_optimal == pytest.approx(r.n_orders_eoq, rel=1e-9)
    assert r.investment_optimal == pytest.approx(r.investment_eoq, rel=1e-9)


# ─── Hyperbola property ───────────────────────────────────────────────────────

def test_hyperbola_product_constant():
    r = wl.exchange_curve(ITEMS)
    product = r.n_orders_eoq * r.investment_eoq
    for pt in r.curve_points:
        assert pt["N"] * pt["I"] == pytest.approx(product, rel=1e-4)


# ─── target_orders ────────────────────────────────────────────────────────────

def test_target_orders_n_matches():
    target = 20.0
    r = wl.exchange_curve(ITEMS, target_orders=target)
    assert r.n_orders_optimal == pytest.approx(target, rel=1e-9)


def test_target_orders_investment_increases_when_n_decreases():
    r_eoq = wl.exchange_curve(ITEMS)
    r_few = wl.exchange_curve(ITEMS, target_orders=r_eoq.n_orders_eoq / 2)
    assert r_few.investment_optimal > r_eoq.investment_eoq


def test_target_orders_multiplier_correct():
    r_eoq = wl.exchange_curve(ITEMS)
    target = r_eoq.n_orders_eoq / 2
    r = wl.exchange_curve(ITEMS, target_orders=target)
    assert r.multiplier == pytest.approx(2.0, rel=1e-9)


def test_target_orders_sum_of_item_n_matches():
    target = 15.0
    r = wl.exchange_curve(ITEMS, target_orders=target)
    n_sum = sum(q["n_orders"] for q in r.optimal_quantities)
    assert n_sum == pytest.approx(target, rel=1e-6)


# ─── target_investment ────────────────────────────────────────────────────────

def test_target_investment_matches():
    r_eoq = wl.exchange_curve(ITEMS)
    target = r_eoq.investment_eoq * 2
    r = wl.exchange_curve(ITEMS, target_investment=target)
    assert r.investment_optimal == pytest.approx(target, rel=1e-9)


def test_target_investment_sum_of_items():
    r_eoq = wl.exchange_curve(ITEMS)
    target = r_eoq.investment_eoq * 1.5
    r = wl.exchange_curve(ITEMS, target_investment=target)
    inv_sum = sum(q["investment"] for q in r.optimal_quantities)
    assert inv_sum == pytest.approx(target, rel=1e-6)


def test_target_investment_n_decreases_when_i_increases():
    r_eoq = wl.exchange_curve(ITEMS)
    r_more = wl.exchange_curve(ITEMS, target_investment=r_eoq.investment_eoq * 2)
    assert r_more.n_orders_optimal < r_eoq.n_orders_eoq


# ─── Mutual exclusion ─────────────────────────────────────────────────────────

def test_both_targets_raises():
    with pytest.raises(ValueError):
        wl.exchange_curve(ITEMS, target_orders=10, target_investment=1000)


# ─── Output helpers ───────────────────────────────────────────────────────────

def test_to_frame_columns():
    import pandas as pd
    df = wl.exchange_curve(ITEMS, target_orders=20).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "Q_eoq" in df.columns
    assert "Q_optimal" in df.columns
    assert "n_orders" in df.columns
    assert "investment" in df.columns


def test_to_frame_row_count():
    df = wl.exchange_curve(ITEMS).to_frame()
    assert len(df) == len(ITEMS)


def test_curve_points_count():
    r = wl.exchange_curve(ITEMS, n_curve_points=30)
    assert len(r.curve_points) == 30


# ─── No unit_value defaults to 1 ─────────────────────────────────────────────

def test_no_unit_value_defaults():
    items_no_v = [{"demand": d["demand"], "ordering_cost": d["ordering_cost"],
                   "holding_cost": d["holding_cost"]} for d in ITEMS]
    r = wl.exchange_curve(items_no_v)
    assert r.n_orders_eoq > 0
    assert r.investment_eoq > 0
