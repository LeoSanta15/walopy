"""Tests for M/G/1 (P-K) and CV² distribution helpers."""
from __future__ import annotations

import pytest

import walopy as wl

# ─── M/G/1 correctness ───────────────────────────────────────────────────────

def test_mg1_reduces_to_mm1_when_cs2_is_1():
    """With cs²=1 (exponential service), M/G/1 P-K must equal M/M/1."""
    r_mg1 = wl.mg1(lam=3.0, mu=5.0, cs2=1.0)
    r_mm1 = wl.mm1(lam=3.0, mu=5.0)
    assert r_mg1.Lq == pytest.approx(r_mm1.Lq, rel=1e-9)
    assert r_mg1.Wq == pytest.approx(r_mm1.Wq, rel=1e-9)
    assert r_mg1.L  == pytest.approx(r_mm1.L,  rel=1e-9)
    assert r_mg1.W  == pytest.approx(r_mm1.W,  rel=1e-9)


def test_mg1_reduces_to_md1_when_cs2_is_0():
    """With cs²=0 (deterministic service), M/G/1 P-K must equal M/D/1."""
    r_mg1 = wl.mg1(lam=3.0, mu=5.0, cs2=0.0)
    r_md1 = wl.md1(lam=3.0, mu=5.0)
    assert r_mg1.Lq == pytest.approx(r_md1.Lq, rel=1e-9)
    assert r_mg1.Wq == pytest.approx(r_md1.Wq, rel=1e-9)


def test_mg1_lq_increases_with_cs2():
    """Higher service variability → longer queue."""
    r_low  = wl.mg1(3.0, 5.0, cs2=0.5)
    r_high = wl.mg1(3.0, 5.0, cs2=2.0)
    assert r_high.Lq > r_low.Lq


def test_mg1_littles_law():
    r = wl.mg1(lam=2.0, mu=4.0, cs2=0.8)
    assert r.L  == pytest.approx(r.lam * r.W,  rel=1e-9)
    assert r.Lq == pytest.approx(r.lam * r.Wq, rel=1e-9)


def test_mg1_wq_formula():
    lam, mu, cs2 = 2.0, 5.0, 1.5
    rho = lam / mu
    ES2 = (1 + cs2) / mu**2
    expected_Wq = lam * ES2 / (2 * (1 - rho))
    r = wl.mg1(lam, mu, cs2)
    assert r.Wq == pytest.approx(expected_Wq, rel=1e-9)


def test_mg1_unstable_raises():
    with pytest.raises(ValueError, match="inestable"):
        wl.mg1(lam=5.0, mu=3.0, cs2=1.0)


def test_mg1_model_label():
    assert wl.mg1(1.0, 2.0, 0.5).model == "M/G/1 (P-K)"


def test_mg1_to_frame():
    import pandas as pd
    df = wl.mg1(2.0, 5.0, 1.0).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "Lq (en cola)" in df.columns


# ─── CV² helpers ─────────────────────────────────────────────────────────────

def test_cv2_normal_formula():
    assert wl.cv2_normal(10.0, 2.0) == pytest.approx(0.04, rel=1e-9)


def test_cv2_normal_zero_std():
    assert wl.cv2_normal(5.0, 0.0) == pytest.approx(0.0)


def test_cv2_erlang_k1_is_1():
    assert wl.cv2_erlang(1) == pytest.approx(1.0)


def test_cv2_erlang_k4():
    assert wl.cv2_erlang(4) == pytest.approx(0.25, rel=1e-9)


def test_cv2_gamma_equals_erlang_for_integer():
    assert wl.cv2_gamma(3.0) == pytest.approx(wl.cv2_erlang(3), rel=1e-9)


def test_cv2_uniform_symmetric():
    # Uniform(0, 2): mean=1, var=1/3 → cv²=1/3
    assert wl.cv2_uniform(0, 2) == pytest.approx(1/3, rel=1e-9)


def test_cv2_uniform_bad_order_raises():
    with pytest.raises(ValueError):
        wl.cv2_uniform(5, 3)


def test_cv2_triangular_symmetric():
    # Triangular(0, 1, 2): mean=1, var=(0+1+4-0-0-2)/18=3/18=1/6 → cv²=1/6
    assert wl.cv2_triangular(0, 1, 2) == pytest.approx(1/6, rel=1e-9)


def test_cv2_triangular_bad_order_raises():
    with pytest.raises(ValueError):
        wl.cv2_triangular(0, 5, 2)


def test_cv2_lognormal_same_as_normal_formula():
    assert wl.cv2_lognormal(8.0, 2.0) == pytest.approx(wl.cv2_normal(8.0, 2.0))


def test_cv2_weibull_shape1_is_1():
    # Weibull(1) = Exponential → cv²=1
    assert wl.cv2_weibull(1.0) == pytest.approx(1.0, rel=1e-6)


def test_cv2_weibull_large_shape_approaches_0():
    # Very large shape → near-deterministic → cv²→0
    assert wl.cv2_weibull(100.0) < 0.05


# ─── Integration: cv2 helpers feed mg1 ───────────────────────────────────────

def test_mg1_with_triangular_service():
    cs2 = wl.cv2_triangular(1, 5, 9)   # mean=5, var=8/3
    r   = wl.mg1(lam=0.15, mu=1/5, cs2=cs2)
    assert r.Wq > 0


def test_mg1_with_uniform_service():
    cs2 = wl.cv2_uniform(2, 8)          # mean=5
    r   = wl.mg1(lam=0.15, mu=1/5, cs2=cs2)
    assert r.L  == pytest.approx(r.lam * r.W, rel=1e-9)


def test_mg1_with_weibull_service():
    cs2 = wl.cv2_weibull(2.0)
    r   = wl.mg1(lam=1.0, mu=2.0, cs2=cs2)
    assert 0 < r.rho < 1
