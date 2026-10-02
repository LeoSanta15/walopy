"""Confiabilidad: MTBF, sistemas serie/paralelo/k-de-n."""
from __future__ import annotations

import math

import pytest

import walopy as wl

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
