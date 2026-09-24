"""Tests for solver module."""
from __future__ import annotations

import numpy as np
import pytest

from walopy import mm1, mmc, kingman
from walopy import solve_lam, solve_mu, solve_servers, optimize_servers, sensitivity


def test_solve_lam_wq():
    target_Wq = 0.5
    r = solve_lam("Wq", target_Wq, mu=5.0, model="mm1")
    assert r.achieved_value == pytest.approx(target_Wq, rel=1e-5)
    assert r.value > 0
    assert r.converged


def test_solve_mu_wq():
    target_Wq = 0.3
    r = solve_mu("Wq", target_Wq, lam=3.0, model="mm1")
    assert r.achieved_value == pytest.approx(target_Wq, rel=1e-5)
    assert r.value > 3.0  # mu must be > lam


def test_solve_lam_rho():
    r = solve_lam("rho", 0.7, mu=5.0, model="mm1")
    assert r.achieved_value == pytest.approx(0.7, rel=1e-5)
    assert r.value == pytest.approx(3.5, rel=1e-4)


def test_solve_servers_wq():
    r = solve_servers("Wq", 0.1, lam=8.0, mu=5.0)
    assert r.value >= 2       # need at least 2 servers
    assert r.achieved_value <= 0.1


def test_solve_servers_low_load():
    # With lam << mu the minimum stable c (=1) should achieve the target easily
    r = solve_servers("Wq", 10.0, lam=1.0, mu=5.0)
    assert r.achieved_value <= 10.0


def test_optimize_servers_basic():
    r = optimize_servers(lam=4.0, mu=5.0, cost_per_server=10.0, cost_per_wait=5.0)
    assert r.optimal_servers >= 1
    assert r.min_cost > 0
    assert "total_cost" in r.cost_breakdown.columns


def test_optimize_servers_cost_convex():
    r = optimize_servers(lam=6.0, mu=5.0, cost_per_server=8.0, cost_per_wait=20.0)
    df = r.cost_breakdown.set_index("c")
    opt_c = r.optimal_servers
    # total cost at optimal_c should be <= neighbors
    costs = df["total_cost"]
    if opt_c + 1 in costs.index:
        assert costs[opt_c] <= costs[opt_c + 1]


def test_sensitivity_returns_dataframe():
    import pandas as pd

    df = sensitivity(mm1, "lam", np.linspace(0.5, 4.5, 10), mu=5.0)
    assert isinstance(df, pd.DataFrame)
    assert "lam" in df.columns
    assert "Wq" in df.columns
    assert len(df) == 10


def test_sensitivity_skips_infeasible():
    df = sensitivity(mm1, "lam", [1.0, 6.0, 2.0], mu=5.0)
    # lam=6 > mu=5 is infeasible; row should exist but Wq will be NaN
    assert len(df) == 3
    assert df[df["lam"] == 1.0]["Wq"].notna().all()


def test_sensitivity_gg1():
    df = sensitivity(kingman, "ca2", np.linspace(0.2, 2.0, 8),
                     lam=3.0, mu=5.0, cs2=1.0)
    assert "Wq" in df.columns
    # Higher ca2 → higher Wq
    assert df["Wq"].is_monotonic_increasing
