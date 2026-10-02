"""Wagner-Whitin y políticas de inventario (r,Q) y (R,S)."""
from __future__ import annotations

import pytest

import walopy as wl

# ─── Wagner-Whitin ────────────────────────────────────────────────────────────

def test_ww_optimal_le_silver_meal():
    demands = [100, 80, 120, 60, 90, 50]
    r_ww = wl.wagner_whitin(demands, setup_cost=200, holding_cost=1)
    r_sm = wl.silver_meal(demands, setup_cost=200, holding_cost=1)
    assert r_ww.total_cost <= r_sm.total_cost + 1e-6


def test_ww_covers_all_demand():
    demands = [100, 80, 120, 60]
    r = wl.wagner_whitin(demands, 200, 1)
    total_ordered = sum(o["order_qty"] for o in r.orders)
    assert total_ordered == pytest.approx(sum(demands), rel=1e-9)


def test_ww_single_period():
    r = wl.wagner_whitin([200], 100, 1)
    assert r.n_orders == 1
    assert r.total_cost == pytest.approx(100.0, rel=1e-9)


def test_ww_method_label():
    assert wl.wagner_whitin([50, 50], 100, 1).method == "Wagner-Whitin"


def test_ww_to_frame():
    import pandas as pd
    df = wl.wagner_whitin([100, 80, 120], 200, 1).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "order_qty" in df.columns


def test_ww_total_cost_components():
    r = wl.wagner_whitin([100, 80, 120, 60], 200, 1)
    assert r.total_cost == pytest.approx(r.total_setup_cost + r.total_holding_cost, rel=1e-9)


# ─── (r, Q) policy ────────────────────────────────────────────────────────────

def test_rq_order_qty_equals_eoq():
    r_rq  = wl.rq_policy(demand_rate=100, ordering_cost=50, holding_cost=2,
                          lead_time=1)
    r_eoq = wl.eoq(100, 50, 2)
    assert r_rq.order_qty == pytest.approx(r_eoq.eoq, rel=1e-9)


def test_rq_deterministic_rop_equals_mean_demand():
    # No variability → safety stock = 0, r = D*L
    r = wl.rq_policy(100, 50, 2, 2, demand_std=0, lead_time_std=0, service_level=0.95)
    assert r.safety_stock == pytest.approx(0.0, abs=1e-9)
    assert r.reorder_point == pytest.approx(200.0, rel=1e-9)


def test_rq_safety_stock_positive_with_variability():
    r = wl.rq_policy(100, 50, 2, 2, demand_std=10, service_level=0.95)
    assert r.safety_stock > 0


def test_rq_service_level_stored():
    r = wl.rq_policy(100, 50, 2, 2, service_level=0.99)
    assert r.service_level == pytest.approx(0.99, rel=1e-9)


def test_rq_to_frame():
    import pandas as pd
    df = wl.rq_policy(100, 50, 2, 2).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "Q*" in df.columns


# ─── (R, S) policy ────────────────────────────────────────────────────────────

def test_rs_order_up_to_gt_mean_demand():
    r = wl.rs_policy(100, 50, 2, lead_time=1, review_period=1,
                     demand_std=10, service_level=0.95)
    assert r.order_up_to > 100 * (1 + 1)   # > D*(R+L) for zero safety stock


def test_rs_deterministic_no_safety_stock():
    r = wl.rs_policy(100, 50, 2, lead_time=1, review_period=2,
                     demand_std=0, service_level=0.95)
    assert r.safety_stock == pytest.approx(0.0, abs=1e-9)
    assert r.order_up_to == pytest.approx(100 * (2 + 1), rel=1e-9)


def test_rs_higher_service_level_higher_ss():
    r90 = wl.rs_policy(100, 50, 2, 1, 1, demand_std=10, service_level=0.90)
    r99 = wl.rs_policy(100, 50, 2, 1, 1, demand_std=10, service_level=0.99)
    assert r99.safety_stock > r90.safety_stock


def test_rs_to_frame():
    import pandas as pd
    df = wl.rs_policy(100, 50, 2, 1, 1).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "S" in df.columns
