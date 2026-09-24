"""Tests for fitting module."""
from __future__ import annotations

import numpy as np
import pytest

from walopy import fit_from_data, FitResult


def test_fit_exponential_ia():
    rng = np.random.default_rng(0)
    ia  = rng.exponential(scale=0.2, size=5000)   # true λ = 5
    r   = fit_from_data(ia)
    assert r.lam == pytest.approx(5.0, rel=0.05)
    assert r.ca2 == pytest.approx(1.0, rel=0.1)   # exponential → CV² ≈ 1
    assert r.mu is None
    assert r.n_arrivals == 5000


def test_fit_service_only():
    rng = np.random.default_rng(1)
    svc = rng.exponential(scale=0.1, size=3000)   # true μ = 10
    r   = fit_from_data(service_times=svc)
    assert r.mu == pytest.approx(10.0, rel=0.05)
    assert r.cs2 == pytest.approx(1.0, rel=0.1)
    assert r.lam is None
    assert r.n_services == 3000


def test_fit_both():
    rng = np.random.default_rng(2)
    ia  = rng.exponential(scale=0.2, size=2000)
    svc = rng.exponential(scale=0.1, size=2000)
    r   = fit_from_data(ia, svc)
    assert r.lam is not None and r.mu is not None
    assert r.ca2 is not None and r.cs2 is not None


def test_fit_from_timestamps():
    rng = np.random.default_rng(3)
    ia  = rng.exponential(scale=0.5, size=1000)
    ts  = np.cumsum(ia)
    r_ia = fit_from_data(ia)
    r_ts = fit_from_data(arrival_timestamps=ts)
    # timestamps → n-1 inter-arrivals vs n; estimates differ slightly
    assert r_ts.lam == pytest.approx(r_ia.lam, rel=0.01)
    assert r_ts.ca2 == pytest.approx(r_ia.ca2, rel=0.01)


def test_fit_deterministic_cv2_zero():
    times = np.full(100, 0.5)   # deterministic → CV² = 0
    r = fit_from_data(times)
    assert r.ca2 == pytest.approx(0.0, abs=1e-10)


def test_fit_to_model_kwargs():
    rng = np.random.default_rng(4)
    ia  = rng.exponential(scale=0.2, size=500)
    svc = rng.exponential(scale=0.1, size=500)
    r   = fit_from_data(ia, svc)
    kw  = r.to_model_kwargs()
    assert "lam" in kw and "mu" in kw and "ca2" in kw and "cs2" in kw


def test_fit_to_frame():
    import pandas as pd
    r  = fit_from_data(np.ones(10) * 0.1)
    df = r.to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "λ" in df.columns


def test_fit_both_errors_both_given():
    with pytest.raises(ValueError, match="not both"):
        fit_from_data(np.array([0.1, 0.2]), arrival_timestamps=np.array([0.1, 0.3]))


def test_fit_neither_raises():
    with pytest.raises(ValueError):
        fit_from_data()


def test_fit_non_positive_raises():
    with pytest.raises(ValueError):
        fit_from_data(np.array([0.5, -0.1, 0.3]))


def test_fit_too_few_raises():
    with pytest.raises(ValueError):
        fit_from_data(np.array([0.5]))
