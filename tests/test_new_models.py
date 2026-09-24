"""Tests for mmck, mm1_priority, and compare."""
from __future__ import annotations

import pytest
import pandas as pd

from walopy import mmck, mm1_priority, compare, mm1, mmc


# --- M/M/c/K ---

def test_mmck_basic_stability():
    # rho > 1 but finite K keeps system stable
    r = mmck(lam=5.0, mu=3.0, c=1, K=10)
    assert 0 < r.L < 10
    assert 0 < r.params["PK (blocking prob)"] < 1


def test_mmck_large_k_approaches_mmc():
    r_inf = mmc(lam=3.0, mu=5.0, c=2)
    r_fin = mmck(lam=3.0, mu=5.0, c=2, K=500)
    assert r_fin.L  == pytest.approx(r_inf.L,  rel=0.01)
    assert r_fin.Lq == pytest.approx(r_inf.Lq, rel=0.01)


def test_mmck_k_less_than_c_raises():
    with pytest.raises(ValueError):
        mmck(lam=2.0, mu=5.0, c=3, K=2)


def test_mmck_blocking_prob_near_zero_light_load():
    r = mmck(lam=0.1, mu=10.0, c=2, K=20)
    assert r.params["PK (blocking prob)"] < 0.001


def test_mmck_numpy_int():
    import numpy as np
    r = mmck(lam=2.0, mu=5.0, c=np.int64(1), K=np.int64(10))
    assert r.L > 0


# --- M/M/1 priority ---

def test_mm1_priority_high_before_low():
    r = mm1_priority([2.0, 1.0], mu=5.0)
    assert r.classes[0]["Wq"] < r.classes[1]["Wq"]


def test_mm1_priority_single_class_equals_mm1():
    r1    = mm1(3.0, 5.0)
    r_pri = mm1_priority([3.0], mu=5.0)
    assert r_pri.classes[0]["Wq"] == pytest.approx(r1.Wq, rel=1e-6)


def test_mm1_priority_unstable_raises():
    with pytest.raises(ValueError, match="unstable"):
        mm1_priority([3.0, 4.0], mu=5.0)


def test_mm1_priority_to_frame():
    r = mm1_priority([1.0, 2.0, 0.5], mu=5.0)
    df = r.to_frame()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "Wq" in df.columns


def test_mm1_priority_class_names():
    r = mm1_priority([2.0, 1.0], mu=5.0, class_names=["premium", "standard"])
    assert r.classes[0]["class_id"] == "premium"
    assert r.classes[1]["class_id"] == "standard"


def test_mm1_priority_weighted_avg_wq():
    # Weighted average Wq should equal M/M/1 Wq
    lams = [1.0, 2.0]
    mu   = 5.0
    r    = mm1_priority(lams, mu=mu)
    r1   = mm1(sum(lams), mu)
    total_lam = sum(lams)
    avg_wq = sum(c["lam"] * c["Wq"] for c in r.classes) / total_lam
    assert avg_wq == pytest.approx(r1.Wq, rel=1e-4)


# --- compare ---

def test_compare_basic():
    df = compare(mm1(2, 5), mmc(2, 5, 2), labels=["M/M/1", "M/M/2"])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df["label"]) == ["M/M/1", "M/M/2"]


def test_compare_default_labels():
    df = compare(mm1(1, 5), mm1(2, 5))
    assert "scenario_1" in df["label"].values
    assert "scenario_2" in df["label"].values


def test_compare_has_kpi_columns():
    df = compare(mm1(2, 5), mm1(3, 5))
    cols = " ".join(df.columns)
    assert "Wq" in cols or "W" in cols


def test_compare_cli_version():
    """Smoke test: CLI --version exits cleanly."""
    from walopy.__main__ import main
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0


def test_cli_mm1():
    from io import StringIO
    import sys
    from walopy.__main__ import main

    captured = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    main(["mm1", "--lam", "3", "--mu", "5"])
    sys.stdout = old_stdout
    output = captured.getvalue()
    assert "M/M/1" in output
    assert "ρ" in output
