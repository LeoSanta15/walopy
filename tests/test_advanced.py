"""Tests for advanced module."""
from __future__ import annotations

import numpy as np
import pytest

from walopy import (
    erlang_b,
    mm1k,
    monte_carlo_gg1,
    takt_time,
    line_balance,
    break_even,
    queue_length_pmf,
    sojourn_cdf,
)


# --- Erlang B ---

def test_erlang_b_zero_traffic():
    assert erlang_b(lam=0.001, mu=1.0, c=5) == pytest.approx(0.0, abs=1e-6)


def test_erlang_b_high_traffic():
    # Very high load → blocking ≈ 1
    b = erlang_b(lam=100.0, mu=1.0, c=3)
    assert b > 0.9


def test_erlang_b_one_server():
    # M/M/1/1: B = rho / (1 + rho)
    rho = 2.0
    b   = erlang_b(lam=rho, mu=1.0, c=1)
    assert b == pytest.approx(rho / (1 + rho), rel=1e-6)


# --- M/M/1/K ---

def test_mm1k_finite_capacity():
    r = mm1k(lam=5.0, mu=3.0, K=10)  # ρ > 1 but finite K → stable
    assert 0 < r.L < 10
    assert 0 < r.params["PK (blocking prob)"] < 1


def test_mm1k_large_k_approaches_mm1():
    # With very large K and ρ < 1, M/M/1/K ≈ M/M/1
    from walopy import mm1
    r1 = mm1(lam=2.0, mu=5.0)
    rK = mm1k(lam=2.0, mu=5.0, K=500)
    assert rK.L  == pytest.approx(r1.L,  rel=0.01)
    assert rK.Lq == pytest.approx(r1.Lq, rel=0.01)


def test_mm1k_blocking_prob_zero_for_small_load():
    r = mm1k(lam=0.1, mu=10.0, K=5)
    assert r.params["PK (blocking prob)"] < 0.001


# --- Monte Carlo ---

def test_monte_carlo_gg1_mm1_case():
    # ca2 = cs2 = 1 recovers M/M/1 approximately
    from walopy import mm1
    r_analytic = mm1(lam=3.0, mu=5.0)
    r_sim      = monte_carlo_gg1(lam=3.0, mu=5.0, ca2=1.0, cs2=1.0,
                                  n_customers=50_000, seed=42)
    assert r_sim.Wq_mean == pytest.approx(r_analytic.Wq, rel=0.05)


def test_monte_carlo_gg1_deterministic_service():
    # cs2=0 → deterministic service → Wq ≈ M/D/1
    from walopy import md1
    r_analytic = md1(lam=3.0, mu=5.0)
    r_sim      = monte_carlo_gg1(lam=3.0, mu=5.0, ca2=1.0, cs2=0.0,
                                  n_customers=50_000, seed=0)
    assert r_sim.Wq_mean == pytest.approx(r_analytic.Wq, rel=0.05)


def test_monte_carlo_percentiles_ordered():
    r = monte_carlo_gg1(lam=3.0, mu=5.0, ca2=1.0, cs2=1.0,
                         n_customers=10_000, seed=7)
    assert r.Wq_p50 <= r.Wq_p90 <= r.Wq_p95 <= r.Wq_p99


def test_monte_carlo_unstable_raises():
    with pytest.raises(ValueError, match="unstable"):
        monte_carlo_gg1(lam=6.0, mu=5.0, ca2=1.0, cs2=1.0)


# --- Takt time ---

def test_takt_time_basic():
    assert takt_time(available_time=480, demand=60) == pytest.approx(8.0)


# --- Line balance ---

def test_line_balance_basic():
    r = line_balance(
        station_names=["A", "B", "C"],
        cycle_times=[5.0, 9.0, 4.0],
        takt=10.0,
    )
    assert r.bottleneck == "B"
    assert r.balance_efficiency == pytest.approx((5 + 9 + 4) / (3 * 10))
    assert r.theoretical_min_stations == 2  # ceil(18/10)


def test_line_balance_overloaded_station():
    r = line_balance(["X", "Y"], [12.0, 8.0], takt=10.0)
    df = r.stations.set_index("Station")
    assert df.loc["X", "Overloaded"]
    assert not df.loc["Y", "Overloaded"]


# --- Break-even ---

def test_break_even_basic():
    r = break_even(fixed_cost=10_000, price_per_unit=25, variable_cost_per_unit=15)
    assert r.bep_units == pytest.approx(1000.0)
    assert r.contribution_margin == pytest.approx(10.0)
    assert r.contribution_margin_ratio == pytest.approx(0.4)


def test_break_even_margin_of_safety():
    r = break_even(fixed_cost=10_000, price_per_unit=25,
                   variable_cost_per_unit=15, actual_units=1500)
    assert r.margin_of_safety_units == pytest.approx(500.0)
    assert r.margin_of_safety_pct   == pytest.approx(500 / 1500)


def test_break_even_negative_cm_raises():
    with pytest.raises(ValueError, match="contribution margin"):
        break_even(fixed_cost=1000, price_per_unit=5, variable_cost_per_unit=10)


# --- PMF / CDF ---

def test_queue_length_pmf_sums_to_one():
    df = queue_length_pmf(lam=3.0, mu=5.0, n_max=200)
    assert df["P(N=n)"].sum() == pytest.approx(1.0, rel=1e-4)


def test_queue_length_pmf_cdf_ends_at_one():
    df = queue_length_pmf(lam=3.0, mu=5.0, n_max=200)
    assert df["P(N<=n)"].iloc[-1] == pytest.approx(1.0, rel=1e-4)


def test_sojourn_cdf_bounds():
    df = sojourn_cdf(lam=3.0, mu=5.0)
    assert df["F(t)"].iloc[0] == pytest.approx(0.0, abs=1e-9)
    assert df["F(t)"].iloc[-1] > 0.98  # approaches 1


# --- Robustness ---

def test_erlang_b_numpy_int():
    import numpy as np
    b = erlang_b(lam=2.0, mu=1.0, c=np.int64(3))
    assert 0.0 < b < 1.0


def test_mm1k_numpy_int():
    import numpy as np
    r = mm1k(lam=5.0, mu=3.0, K=np.int64(10))
    assert 0 < r.L < 10


def test_monte_carlo_zero_customers_raises():
    with pytest.raises((ValueError, TypeError)):
        monte_carlo_gg1(lam=3.0, mu=5.0, ca2=1.0, cs2=1.0, n_customers=0)


def test_line_balance_empty_raises():
    with pytest.raises(ValueError, match="station_names"):
        line_balance([], [], takt=10.0)
