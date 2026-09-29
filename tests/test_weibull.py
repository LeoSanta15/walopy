"""Tests for Weibull analysis."""
from __future__ import annotations
import math
import pytest
import walopy as wl

# Weibull(β=2, η=100): F(t) = 1 - exp(-(t/100)^2)
# Generate exact quantiles via inverse CDF: t_p = 100 * (-ln(1-p))^(1/2)
_BETA, _ETA = 2.0, 100.0
_PROBS = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95]
TIMES = [_ETA * (-math.log(1.0 - p)) ** (1.0 / _BETA) for p in _PROBS]


def test_mle_returns_weibull_result():
    r = wl.weibull_analysis(TIMES)
    assert isinstance(r, wl.WeibullResult)


def test_mle_method_label():
    r = wl.weibull_analysis(TIMES)
    assert r.method == "MLE"


def test_mle_shape_close():
    r = wl.weibull_analysis(TIMES)
    assert r.shape == pytest.approx(_BETA, rel=0.05)


def test_mle_scale_close():
    r = wl.weibull_analysis(TIMES)
    assert r.scale == pytest.approx(_ETA, rel=0.05)


def test_rry_method_label():
    r = wl.weibull_analysis(TIMES, method="RRY")
    assert r.method == "RRY"


def test_rry_shape_reasonable():
    r = wl.weibull_analysis(TIMES, method="RRY")
    assert 1.0 < r.shape < 3.5


def test_n_stored():
    r = wl.weibull_analysis(TIMES)
    assert r.n == len(TIMES)


def test_mttf_formula():
    r = wl.weibull_analysis(TIMES)
    expected_mttf = r.scale * math.gamma(1.0 + 1.0 / r.shape)
    assert r.mttf == pytest.approx(expected_mttf, rel=1e-6)


def test_b10_life():
    r = wl.weibull_analysis(TIMES)
    # F(b10) ≈ 0.10
    assert r.F(r.b10) == pytest.approx(0.10, rel=0.05)


def test_b50_life():
    r = wl.weibull_analysis(TIMES)
    assert r.F(r.b50) == pytest.approx(0.50, rel=0.05)


def test_b_life_method():
    r = wl.weibull_analysis(TIMES)
    assert r.b_life(10) == pytest.approx(r.b10, rel=1e-6)
    assert r.b_life(50) == pytest.approx(r.b50, rel=1e-6)


def test_reliability_is_1_at_t0():
    r = wl.weibull_analysis(TIMES)
    assert r.R(0.0) == pytest.approx(1.0, abs=1e-9)


def test_reliability_decreasing():
    r = wl.weibull_analysis(TIMES)
    assert r.R(10) > r.R(50) > r.R(200)


def test_F_plus_R_equals_1():
    r = wl.weibull_analysis(TIMES)
    for t in [10, 50, 100, 200]:
        assert r.F(t) + r.R(t) == pytest.approx(1.0, abs=1e-9)


def test_to_frame():
    import pandas as pd
    df = wl.weibull_analysis(TIMES).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "shape_beta" in df.columns
    assert "MTTF" in df.columns


def test_less_than_2_raises():
    with pytest.raises(ValueError):
        wl.weibull_analysis([50.0])


def test_nonpositive_time_raises():
    with pytest.raises(ValueError):
        wl.weibull_analysis([10, -5, 20])


def test_invalid_method_raises():
    with pytest.raises(ValueError):
        wl.weibull_analysis(TIMES, method="OLS")
