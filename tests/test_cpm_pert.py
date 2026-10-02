"""Tests for CPM and PERT project scheduling."""
from __future__ import annotations

import math

import pytest

import walopy as wl

# Classic 6-activity network
# A(3) → C(2) → E(4)
# A(3) → D(1) → F(3)
# B(4) → D(1) → F(3)
# B(4) → E(4)
# Critical: B→E→F or compute manually
CPM_ACTS = [
    {"name": "A", "duration": 3, "predecessors": []},
    {"name": "B", "duration": 4, "predecessors": []},
    {"name": "C", "duration": 2, "predecessors": ["A"]},
    {"name": "D", "duration": 1, "predecessors": ["A", "B"]},
    {"name": "E", "duration": 4, "predecessors": ["C"]},
    {"name": "F", "duration": 3, "predecessors": ["D", "E"]},
]
# ES/EF: A:0-3, B:0-4, C:3-5, D:4-5, E:5-9, F:9-12
# Critical: B→D→E→F or A→C→E→F? Let's check:
# Path A-C-E-F: 3+2+4+3=12; Path B-D-E-F: 4+1+4+3=12; both critical
# Project duration = 12

PERT_ACTS = [
    {"name": "A", "optimistic": 1, "most_likely": 3, "pessimistic": 5, "predecessors": []},
    {"name": "B", "optimistic": 2, "most_likely": 4, "pessimistic": 6, "predecessors": []},
    {"name": "C", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": ["A"]},
    {"name": "D", "optimistic": 1, "most_likely": 1, "pessimistic": 1, "predecessors": ["B"]},
]
# te: A=(1+12+5)/6=3, B=4, C=2, D=1
# Paths: A-C: 5; B-D: 5 → both critical, duration=5


# ─── CPM ─────────────────────────────────────────────────────────────────────

def test_cpm_returns_result():
    r = wl.cpm(CPM_ACTS)
    assert isinstance(r, wl.ProjectResult)


def test_cpm_method():
    r = wl.cpm(CPM_ACTS)
    assert r.method == "CPM"


def test_cpm_project_duration():
    r = wl.cpm(CPM_ACTS)
    assert r.project_duration == pytest.approx(12.0)


def test_cpm_critical_path_contains_expected():
    r = wl.cpm(CPM_ACTS)
    # Both A-C-E-F and B-D-E-F are critical
    assert "E" in r.critical_path
    assert "F" in r.critical_path


def test_cpm_non_critical_has_float():
    r = wl.cpm(CPM_ACTS)
    # In this network D is critical (float=0), C is critical (float=0)
    # A critical: TF=0; B critical: TF=0
    for a in r.activities:
        if a.is_critical:
            assert a.total_float == pytest.approx(0.0, abs=1e-9)
        else:
            assert a.total_float > 0


def test_cpm_ef_equals_es_plus_duration():
    r = wl.cpm(CPM_ACTS)
    for a in r.activities:
        assert a.ef == pytest.approx(a.es + a.duration, abs=1e-9)


def test_cpm_lf_equals_ls_plus_duration():
    r = wl.cpm(CPM_ACTS)
    for a in r.activities:
        assert a.lf == pytest.approx(a.ls + a.duration, abs=1e-9)


def test_cpm_no_variance():
    r = wl.cpm(CPM_ACTS)
    assert r.project_variance is None
    assert r.project_std is None


def test_cpm_to_frame():
    import pandas as pd
    df = wl.cpm(CPM_ACTS).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "Critical" in df.columns
    assert "TF" in df.columns


def test_cpm_simple_linear():
    acts = [
        {"name": "X", "duration": 5, "predecessors": []},
        {"name": "Y", "duration": 3, "predecessors": ["X"]},
    ]
    r = wl.cpm(acts)
    assert r.project_duration == pytest.approx(8.0)
    assert r.critical_path == ["X", "Y"]


def test_cpm_unknown_predecessor_raises():
    with pytest.raises(ValueError):
        wl.cpm([{"name": "A", "duration": 1, "predecessors": ["Z"]}])


def test_cpm_empty_raises():
    with pytest.raises(ValueError):
        wl.cpm([])


# ─── PERT ─────────────────────────────────────────────────────────────────────

def test_pert_returns_result():
    r = wl.pert(PERT_ACTS)
    assert isinstance(r, wl.ProjectResult)


def test_pert_method():
    r = wl.pert(PERT_ACTS)
    assert r.method == "PERT"


def test_pert_expected_duration():
    r = wl.pert(PERT_ACTS)
    assert r.project_duration == pytest.approx(5.0, abs=1e-9)


def test_pert_has_variance():
    r = wl.pert(PERT_ACTS)
    assert r.project_variance is not None
    assert r.project_variance > 0


def test_pert_std_is_sqrt_variance():
    r = wl.pert(PERT_ACTS)
    assert r.project_std == pytest.approx(math.sqrt(r.project_variance), rel=1e-9)


def test_pert_activity_variance_formula():
    r = wl.pert(PERT_ACTS)
    for a in r.activities:
        if a.variance is not None:
            expected = ((a.pessimistic - a.optimistic) / 6.0) ** 2
            assert a.variance == pytest.approx(expected, rel=1e-9)


def test_pert_probability_below_mean_is_50pct():
    r = wl.pert(PERT_ACTS)
    assert r.probability(r.project_duration) == pytest.approx(0.5, abs=1e-6)


def test_pert_probability_increases_with_target():
    r = wl.pert(PERT_ACTS)
    assert r.probability(r.project_duration + 1) > r.probability(r.project_duration)


def test_pert_invalid_estimates_raises():
    with pytest.raises(ValueError):
        wl.pert([{"name": "A", "optimistic": 5, "most_likely": 3, "pessimistic": 7, "predecessors": []}])
