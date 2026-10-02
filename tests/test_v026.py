"""Tests for v0.2.6: Wagner-Whitin, (r,Q)/(R,S) policies, scheduling, reliability."""
from __future__ import annotations

import math

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


# ─── Single-machine scheduling ────────────────────────────────────────────────

def test_spt_minimises_total_completion():
    # SPT is optimal for ΣCj on a single machine
    p = [3, 1, 4, 1, 5]
    r_spt  = wl.schedule_single(p, rule="SPT")
    r_fifo = wl.schedule_single(p, rule="FIFO")
    assert r_spt.total_completion_time <= r_fifo.total_completion_time


def test_edd_minimises_max_lateness():
    p = [3, 2, 4]
    d = [6, 4, 8]
    r_edd  = wl.schedule_single(p, rule="EDD", due_dates=d)
    r_fifo = wl.schedule_single(p, rule="FIFO", due_dates=d)
    assert r_edd.max_lateness <= r_fifo.max_lateness + 1e-9


def test_wspt_minimises_weighted_completion():
    p = [3, 1, 4]
    w = [2, 5, 1]
    r_wspt = wl.schedule_single(p, rule="WSPT", weights=w)
    r_fifo = wl.schedule_single(p, rule="FIFO", weights=w)
    assert r_wspt.total_weighted_completion_time <= r_fifo.total_weighted_completion_time


def test_schedule_makespan_equals_sum_p():
    p = [2, 3, 5, 1]
    r = wl.schedule_single(p, rule="SPT")
    assert r.makespan == pytest.approx(sum(p), rel=1e-9)


def test_schedule_names():
    r = wl.schedule_single([2, 3], rule="FIFO", names=["A", "B"])
    assert set(r.sequence) == {"A", "B"}


def test_schedule_to_frame():
    import pandas as pd
    df = wl.schedule_single([1, 2, 3], rule="SPT").to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "C" in df.columns


def test_schedule_invalid_rule_raises():
    with pytest.raises(ValueError, match="rule"):
        wl.schedule_single([1, 2], rule="INVALID")


# ─── Johnson's flow-shop ──────────────────────────────────────────────────────

def test_johnson_makespan_le_any_other():
    # Classic example: optimal sequence should beat naive order
    m1 = [3, 8, 5, 7, 2]
    m2 = [5, 2, 8, 4, 6]
    r = wl.johnson_flowshop(m1, m2)
    assert r.makespan > 0
    assert len(r.sequence) == 5


def test_johnson_all_jobs_scheduled():
    r = wl.johnson_flowshop([1, 2, 3], [3, 2, 1])
    assert len(r.sequence) == 3


def test_johnson_makespan_exact():
    # Two jobs: a=[2,3], b=[4,1] → Set1: J1(a≤b), Set2: J2(a>b) → seq J1→J2
    r = wl.johnson_flowshop([2, 3], [4, 1])
    assert r.sequence == ["J1", "J2"]
    # J1: M1 0-2, M2 2-6; J2: M1 2-5, M2 6-7 → makespan=7
    assert r.makespan == pytest.approx(7.0, rel=1e-9)


def test_johnson_to_frame():
    import pandas as pd
    df = wl.johnson_flowshop([2, 3], [4, 1]).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "Makespan" not in df.columns   # frame has job rows, not totals
    assert "M1 start" in df.columns


def test_johnson_names():
    r = wl.johnson_flowshop([1, 2], [2, 1], names=["Alpha", "Beta"])
    assert set(r.sequence) == {"Alpha", "Beta"}


# ─── Reliability ──────────────────────────────────────────────────────────────

def test_mtbf_analysis_basic():
    r = wl.mtbf_analysis(failure_rate=0.01)
    assert r.mtbf == pytest.approx(100.0, rel=1e-9)


def test_mtbf_analysis_R_t():
    r = wl.mtbf_analysis(failure_rate=0.01, t=100)
    assert r.R_t == pytest.approx(math.exp(-1), rel=1e-6)


def test_mtbf_availability():
    r = wl.mtbf_analysis(failure_rate=0.01, mttr=5.0)
    expected = 100 / (100 + 5)
    assert r.availability == pytest.approx(expected, rel=1e-9)


def test_series_failure_rate_additive():
    r = wl.series_system([0.01, 0.02, 0.03])
    assert r.mtbf == pytest.approx(1 / 0.06, rel=1e-9)


def test_series_R_t():
    r = wl.series_system([0.01, 0.02], t=10)
    expected = math.exp(-0.03 * 10)
    assert r.R_t == pytest.approx(expected, rel=1e-6)


def test_parallel_R_t_gt_series_R_t():
    lams = [0.01, 0.02]
    r_par = wl.parallel_system(lams, t=50)
    r_ser = wl.series_system(lams, t=50)
    assert r_par.R_t > r_ser.R_t


def test_parallel_mtbf_gt_single():
    r = wl.parallel_system([0.01, 0.01])
    single_mtbf = 1 / 0.01
    assert r.mtbf > single_mtbf


def test_parallel_R_t_formula():
    lams = [0.01, 0.02]
    t = 20
    r = wl.parallel_system(lams, t=t)
    expected = 1 - (1 - math.exp(-0.01 * t)) * (1 - math.exp(-0.02 * t))
    assert r.R_t == pytest.approx(expected, rel=1e-6)


def test_koon_1_of_1_equals_single():
    r = wl.koon_system(1, 1, 0.01, t=50)
    assert r.R_t == pytest.approx(math.exp(-0.01 * 50), rel=1e-6)
    assert r.mtbf == pytest.approx(100.0, rel=1e-9)


def test_koon_1_of_2_parallel_matches():
    # 1-of-2 identical should match parallel_system with same λ
    lam = 0.01
    r_koon = wl.koon_system(2, 1, lam, t=50)
    r_par  = wl.parallel_system([lam, lam], t=50)
    assert r_koon.R_t == pytest.approx(r_par.R_t, rel=1e-5)


def test_koon_n_of_n_series_matches():
    # n-of-n identical should match series_system with same λ
    lam = 0.01
    r_koon = wl.koon_system(3, 3, lam, t=30)
    r_ser  = wl.series_system([lam, lam, lam], t=30)
    assert r_koon.R_t == pytest.approx(r_ser.R_t, rel=1e-6)


def test_koon_invalid_k_raises():
    with pytest.raises(ValueError):
        wl.koon_system(3, 4, 0.01)


def test_reliability_to_frame():
    import pandas as pd
    df = wl.series_system([0.01, 0.02], t=10).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "MTBF" in df.columns
