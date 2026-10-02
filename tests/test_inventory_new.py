"""Tests for new inventory models: EBQ, multi-item, constrained, dynamic lot-sizing, quantity discount."""
from __future__ import annotations

import math

import pytest

import walopy as wl

# ─── EBQ ──────────────────────────────────────────────────────────────────────

def test_ebq_formula():
    # Q* = sqrt(2*1000*50 / (2*(1-1000/4000))) = sqrt(100000/1.5) ≈ 258.2
    r = wl.ebq(demand_rate=1000, setup_cost=50, holding_cost=2, production_rate=4000)
    expected = math.sqrt(2 * 1000 * 50 / (2 * (1 - 1000 / 4000)))
    assert r.ebq == pytest.approx(expected, rel=1e-6)


def test_ebq_gt_eoq():
    # EBQ ≥ EOQ because it accounts for simultaneous production
    r_ebq = wl.ebq(1000, 50, 2, 4000)
    r_eoq = wl.eoq(1000, 50, 2)
    assert r_ebq.ebq >= r_eoq.eoq


def test_ebq_max_and_avg_inventory():
    r = wl.ebq(1000, 50, 2, 4000)
    assert r.max_inventory == pytest.approx(r.ebq * (1 - 1000 / 4000), rel=1e-9)
    assert r.avg_inventory == pytest.approx(r.max_inventory / 2, rel=1e-9)


def test_ebq_total_cost():
    r = wl.ebq(1000, 50, 2, 4000)
    assert r.total_cost == pytest.approx(r.holding_cost_total + r.setup_cost_total, rel=1e-9)


def test_ebq_demand_ge_production_raises():
    with pytest.raises(ValueError, match="production_rate"):
        wl.ebq(1000, 50, 2, 500)


def test_ebq_to_frame():
    import pandas as pd
    df = wl.ebq(1000, 50, 2, 4000).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "EBQ" in df.columns


# ─── Multi-item EOQ ───────────────────────────────────────────────────────────

def test_eoq_multi_two_items():
    r = wl.eoq_multi([1000, 500], [50, 30], [2, 1])
    assert len(r.items) == 2
    # Each item's cost should match the individual eoq
    r1 = wl.eoq(1000, 50, 2)
    r2 = wl.eoq(500, 30, 1)
    assert r.items[0]["EOQ"] == pytest.approx(r1.eoq, rel=1e-9)
    assert r.items[1]["EOQ"] == pytest.approx(r2.eoq, rel=1e-9)
    assert r.total_cost == pytest.approx(r1.total_cost + r2.total_cost, rel=1e-9)


def test_eoq_multi_names():
    r = wl.eoq_multi([100, 200], [10, 20], [1, 2], names=["A", "B"])
    assert r.items[0]["Name"] == "A"
    assert r.items[1]["Name"] == "B"


def test_eoq_multi_to_frame():
    import pandas as pd
    df = wl.eoq_multi([1000, 500], [50, 30], [2, 1]).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "EOQ" in df.columns


def test_eoq_multi_length_mismatch_raises():
    with pytest.raises(ValueError):
        wl.eoq_multi([1000, 500], [50], [2, 1])


# ─── Multi-item EBQ ───────────────────────────────────────────────────────────

def test_ebq_multi_two_items():
    r = wl.ebq_multi([1000, 500], [50, 30], [2, 1], [4000, 2000])
    assert len(r.items) == 2
    r1 = wl.ebq(1000, 50, 2, 4000)
    r2 = wl.ebq(500, 30, 1, 2000)
    assert r.items[0]["EBQ"] == pytest.approx(r1.ebq, rel=1e-9)
    assert r.total_cost == pytest.approx(r1.total_cost + r2.total_cost, rel=1e-9)


# ─── Constrained multi-item EOQ ───────────────────────────────────────────────

def test_eoq_multi_constrained_no_constraints_equals_unconstrained():
    r_unc = wl.eoq_multi([1000, 500, 800], [50, 30, 40], [2, 1, 1.5])
    r_con = wl.eoq_multi_constrained([1000, 500, 800], [50, 30, 40], [2, 1, 1.5])
    assert r_con.total_cost == pytest.approx(r_unc.total_cost, rel=1e-6)


def test_eoq_multi_constrained_budget_reduces_qty():
    # Very tight budget forces smaller orders
    r_unc = wl.eoq_multi_constrained([1000, 500, 800], [50, 30, 40], [2, 1, 1.5])
    tight_budget = 500.0  # very small
    r_con = wl.eoq_multi_constrained(
        [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
        budget=tight_budget, budget_unit_costs=[10, 8, 12],
    )
    # Constrained Q* should be smaller on average
    q_unc_sum = sum(item["Q*"] for item in r_unc.items)
    q_con_sum = sum(item["Q*"] for item in r_con.items)
    assert q_con_sum <= q_unc_sum + 1e-6


def test_eoq_multi_constrained_budget_satisfied():
    budget = 3000.0
    unit_costs = [10.0, 8.0, 12.0]
    r = wl.eoq_multi_constrained(
        [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
        budget=budget, budget_unit_costs=unit_costs,
    )
    avg_inv_value = sum(unit_costs[i] * r.items[i]["Q*"] / 2 for i in range(3))
    assert avg_inv_value <= budget + 1e-4


def test_eoq_multi_constrained_space_satisfied():
    space = 200.0
    space_w = [0.5, 0.3, 0.4]
    r = wl.eoq_multi_constrained(
        [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
        space=space, space_per_unit=space_w,
    )
    avg_space = sum(space_w[i] * r.items[i]["Q*"] / 2 for i in range(3))
    assert avg_space <= space + 1e-4


def test_eoq_multi_constrained_generic_constraint():
    constraints = [{"name": "custom", "weights": [1.0, 1.0, 1.0], "bound": 400.0}]
    r = wl.eoq_multi_constrained(
        [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
        constraints=constraints,
    )
    total_q = sum(item["Q*"] for item in r.items)
    assert total_q <= 400.0 + 1e-4


def test_eoq_multi_constrained_non_binding_no_multiplier():
    r = wl.eoq_multi_constrained(
        [1000, 500], [50, 30], [2, 1],
        budget=1_000_000, budget_unit_costs=[1.0, 1.0],  # enormous budget
    )
    assert r.lagrange_multipliers.get("budget", 0.0) < 1e-6
    assert "budget" not in r.binding_constraints


def test_eoq_multi_constrained_to_frame():
    import pandas as pd
    r = wl.eoq_multi_constrained([1000, 500], [50, 30], [2, 1])
    df = r.to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "Q*" in df.columns


# ─── Lot-for-Lot ─────────────────────────────────────────────────────────────

def test_lot_for_lot_zero_holding():
    r = wl.lot_for_lot([100, 80, 120, 60], setup_cost=200, holding_cost=1)
    assert r.total_holding_cost == 0.0


def test_lot_for_lot_n_orders_equals_nonzero_periods():
    demands = [100, 0, 120, 60, 0, 80]
    r = wl.lot_for_lot(demands, setup_cost=100, holding_cost=1)
    nonzero = sum(1 for d in demands if d > 0)
    assert r.n_orders == nonzero


def test_lot_for_lot_total_cost():
    demands = [100, 80, 120, 60]
    r = wl.lot_for_lot(demands, setup_cost=200, holding_cost=1)
    assert r.total_cost == pytest.approx(4 * 200, rel=1e-9)


def test_lot_for_lot_to_frame():
    r = wl.lot_for_lot([100, 80, 120], 200, 1)
    df = r.to_frame()
    assert "order_qty" in df.columns


# ─── Silver-Meal ─────────────────────────────────────────────────────────────

def test_silver_meal_cost_le_l4l():
    demands = [100, 80, 120, 60]
    r_sm = wl.silver_meal(demands, setup_cost=200, holding_cost=1)
    r_l4 = wl.lot_for_lot(demands, setup_cost=200, holding_cost=1)
    assert r_sm.total_cost <= r_l4.total_cost + 1e-9


def test_silver_meal_covers_all_demand():
    demands = [100, 80, 120, 60]
    r = wl.silver_meal(demands, setup_cost=200, holding_cost=1)
    total_ordered = sum(o["order_qty"] for o in r.orders)
    assert total_ordered == pytest.approx(sum(demands), rel=1e-9)


def test_silver_meal_single_period():
    r = wl.silver_meal([200], setup_cost=100, holding_cost=2)
    assert r.n_orders == 1
    assert r.total_cost == pytest.approx(100.0, rel=1e-9)


def test_silver_meal_method_label():
    r = wl.silver_meal([100, 50, 80], 150, 2)
    assert r.method == "Silver-Meal"


# ─── EOQ with quantity discount ───────────────────────────────────────────────

def test_eoq_quantity_discount_selects_min_cost():
    r = wl.eoq_quantity_discount(
        demand_rate=1000, ordering_cost=50, holding_cost_rate=0.2,
        price_breaks=[(0, 10.0), (500, 9.5), (1000, 9.0)],
    )
    assert r.total_cost > 0
    # Must be minimum among all candidates
    assert r.total_cost == min(c["Total cost"] for c in r.candidates)


def test_eoq_quantity_discount_to_frame():
    r = wl.eoq_quantity_discount(1000, 50, 0.2, [(0, 10.0), (500, 9.5)])
    df = r.to_frame()
    assert "Total cost" in df.columns


def test_eoq_quantity_discount_valid_price():
    r = wl.eoq_quantity_discount(1000, 50, 0.2, [(0, 10.0), (500, 9.5), (1000, 9.0)])
    assert r.unit_price in [10.0, 9.5, 9.0]


# ─── Break-even multi-product ─────────────────────────────────────────────────

def test_break_even_multi_basic():
    r = wl.break_even_multi(
        fixed_cost=120_000,
        prices=[50, 80, 120],
        variable_costs=[30, 50, 70],
        sales_mix=[3, 2, 1],
    )
    assert r.bep_units_total > 0
    assert r.bep_revenue_total > 0


def test_break_even_multi_sum_equals_total():
    r = wl.break_even_multi(120_000, [50, 80], [30, 50], [1, 1])
    total_from_items = sum(item["BEP units"] for item in r.items)
    assert total_from_items == pytest.approx(r.bep_units_total, rel=1e-9)


def test_break_even_multi_wacm():
    # 3:2:1 mix, CMs = 20, 30, 50 → WACM = (20*3 + 30*2 + 50*1)/6 = 220/6 ≈ 36.67
    r = wl.break_even_multi(120_000, [50, 80, 120], [30, 50, 70], [3, 2, 1])
    expected_wacm = (20 * 3 + 30 * 2 + 50 * 1) / 6
    assert r.weighted_avg_cm == pytest.approx(expected_wacm, rel=1e-9)


def test_break_even_multi_to_frame():
    r = wl.break_even_multi(100_000, [50, 80], [30, 50], [1, 1])
    df = r.to_frame()
    assert "BEP units" in df.columns


def test_break_even_multi_negative_cm_raises():
    with pytest.raises(ValueError, match="contribution margin"):
        wl.break_even_multi(100_000, [20, 80], [25, 50], [1, 1])


# ─── Break-even sales (revenue-based) ────────────────────────────────────────

def test_break_even_sales_formula():
    # BEP = 50_000 / (1 - 0.60) = 125_000
    r = wl.break_even_sales(fixed_cost=50_000, variable_cost_ratio=0.60)
    assert r.bep_revenue == pytest.approx(125_000.0, rel=1e-9)


def test_break_even_sales_cm_ratio():
    r = wl.break_even_sales(50_000, 0.60)
    assert r.contribution_margin_ratio == pytest.approx(0.40, rel=1e-9)


def test_break_even_sales_margin_of_safety():
    r = wl.break_even_sales(50_000, 0.60, actual_revenue=200_000)
    assert r.margin_of_safety_units == pytest.approx(200_000 - 125_000, rel=1e-9)
    assert r.margin_of_safety_pct == pytest.approx((200_000 - 125_000) / 200_000, rel=1e-9)


def test_break_even_sales_ratio_1_raises():
    with pytest.raises(ValueError):
        wl.break_even_sales(50_000, 1.0)


def test_break_even_sales_ratio_0_raises():
    with pytest.raises(ValueError):
        wl.break_even_sales(50_000, 0.0)
