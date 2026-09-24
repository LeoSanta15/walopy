"""Tests for inventory module."""
from __future__ import annotations

import pytest

from walopy import eoq, reorder_point, newsvendor


# --- EOQ ---

def test_eoq_formula():
    # Q* = sqrt(2*1000*50/2) = sqrt(50000) ≈ 223.6
    r = eoq(demand_rate=1000, ordering_cost=50, holding_cost=2)
    assert r.eoq == pytest.approx(223.6, rel=1e-3)


def test_eoq_equal_costs_at_optimum():
    r = eoq(demand_rate=500, ordering_cost=100, holding_cost=5)
    assert r.holding_cost_total == pytest.approx(r.ordering_cost_total, rel=1e-6)


def test_eoq_total_cost():
    r = eoq(demand_rate=1000, ordering_cost=50, holding_cost=2)
    assert r.total_cost == pytest.approx(r.holding_cost_total + r.ordering_cost_total, rel=1e-10)


def test_eoq_cycle_time_inverse_of_frequency():
    r = eoq(demand_rate=200, ordering_cost=20, holding_cost=1)
    assert r.cycle_time == pytest.approx(1.0 / r.order_frequency, rel=1e-10)


def test_eoq_to_frame():
    import pandas as pd
    df = eoq(1000, 50, 2).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "EOQ" in df.columns


# --- Reorder point ---

def test_rop_deterministic():
    # No variability → safety stock = 0 → ROP = D * LT
    r = reorder_point(demand_rate=50, lead_time=2,
                      demand_std=0, lead_time_std=0,
                      service_level=0.95)
    assert r.reorder_point == pytest.approx(100.0)
    assert r.safety_stock  == pytest.approx(0.0, abs=1e-9)


def test_rop_positive_safety_stock():
    r = reorder_point(demand_rate=50, lead_time=2,
                      demand_std=10, service_level=0.95)
    assert r.safety_stock > 0
    assert r.reorder_point > r.mean_demand_lt


def test_rop_higher_service_higher_ss():
    r90 = reorder_point(demand_rate=50, lead_time=2, demand_std=10, service_level=0.90)
    r99 = reorder_point(demand_rate=50, lead_time=2, demand_std=10, service_level=0.99)
    assert r99.safety_stock > r90.safety_stock


def test_rop_to_frame():
    import pandas as pd
    df = reorder_point(50, 2, demand_std=5, service_level=0.95).to_frame()
    assert "Reorder point" in df.columns


def test_rop_service_level_1_raises():
    with pytest.raises(ValueError):
        reorder_point(50, 2, service_level=1.0)


# --- Newsvendor ---

def test_newsvendor_critical_ratio():
    # Cu = 10-6 = 4, Co = 6-2 = 4 → CR = 0.5 → Q* ≈ mean
    r = newsvendor(demand_mean=100, demand_std=20, price=10, cost=6, salvage=2)
    assert r.critical_ratio == pytest.approx(0.5, rel=1e-6)
    assert r.optimal_qty == pytest.approx(100.0, rel=1e-3)


def test_newsvendor_high_margin():
    # Cu >> Co → Q* >> mean
    r = newsvendor(demand_mean=100, demand_std=20, price=50, cost=6, salvage=0)
    assert r.optimal_qty > 100.0


def test_newsvendor_low_margin():
    # Cu << Co → Q* < mean
    r = newsvendor(demand_mean=100, demand_std=20, price=7, cost=6, salvage=2)
    assert r.optimal_qty < 100.0


def test_newsvendor_deterministic():
    # sigma=0 → Q* = demand_mean
    r = newsvendor(demand_mean=100, demand_std=0, price=10, cost=6, salvage=2)
    assert r.optimal_qty == pytest.approx(100.0)
    assert r.expected_leftover == pytest.approx(0.0, abs=1e-9)


def test_newsvendor_profit_positive():
    r = newsvendor(demand_mean=200, demand_std=30, price=15, cost=8, salvage=2)
    assert r.expected_profit > 0


def test_newsvendor_cost_ge_price_raises():
    with pytest.raises(ValueError, match="price"):
        newsvendor(demand_mean=100, demand_std=10, price=5, cost=6)


def test_newsvendor_salvage_ge_cost_raises():
    with pytest.raises(ValueError, match="salvage"):
        newsvendor(demand_mean=100, demand_std=10, price=10, cost=6, salvage=7)
