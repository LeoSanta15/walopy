"""Tests for ABC, XYZ, and ABC-XYZ classification."""
from __future__ import annotations
import pytest
import walopy as wl

# 5 items: annual values 500, 300, 100, 70, 30 → total 1000
ITEMS = [
    {"name": "A", "demand": 50,  "unit_value": 10},   # 500  (50%)
    {"name": "B", "demand": 30,  "unit_value": 10},   # 300  (30%)
    {"name": "C", "demand": 100, "unit_value":  1},   # 100  (10%)
    {"name": "D", "demand":  70, "unit_value":  1},   #  70   (7%)
    {"name": "E", "demand":  30, "unit_value":  1},   #  30   (3%)
]
# Cumulative: 50% → A, 80% → A, 90% → B, 97% → C, 100% → C
# prev_pct before item:
#   A: 0%  < 80% → A
#   B: 50% < 80% → A
#   C: 80% >= 80%, < 95% → B
#   D: 90% < 95% → B
#   E: 97% >= 95% → C

XYZ_ITEMS = [
    {"name": "X1", "cv": 0.2},
    {"name": "X2", "demand_std": 5, "demand_mean": 50},    # CV=0.1
    {"name": "Y1", "cv": 0.7},
    {"name": "Y2", "demand_std": 40, "demand_rate": 80},   # CV=0.5
    {"name": "Z1", "cv": 1.5},
]


# ─── ABCResult ───────────────────────────────────────────────────────────────

def test_abc_returns_result():
    r = wl.abc_analysis(ITEMS)
    assert isinstance(r, wl.ABCResult)


def test_abc_class_A_items():
    r = wl.abc_analysis(ITEMS)
    a_items = [e for e in r.items if e["class"] == "A"]
    assert len(a_items) == 2


def test_abc_class_B_items():
    r = wl.abc_analysis(ITEMS)
    b_items = [e for e in r.items if e["class"] == "B"]
    assert len(b_items) == 2


def test_abc_class_C_items():
    r = wl.abc_analysis(ITEMS)
    c_items = [e for e in r.items if e["class"] == "C"]
    assert len(c_items) == 1


def test_abc_total_value():
    r = wl.abc_analysis(ITEMS)
    assert r.total_value == pytest.approx(1000.0)


def test_abc_sorted_descending():
    r = wl.abc_analysis(ITEMS)
    vals = [e["annual_value"] for e in r.items]
    assert vals == sorted(vals, reverse=True)


def test_abc_cumulative_pct_monotone():
    r = wl.abc_analysis(ITEMS)
    cpcts = [e["cumulative_pct"] for e in r.items]
    assert all(cpcts[i] <= cpcts[i + 1] for i in range(len(cpcts) - 1))


def test_abc_cumulative_pct_ends_at_one():
    r = wl.abc_analysis(ITEMS)
    assert r.items[-1]["cumulative_pct"] == pytest.approx(1.0, abs=1e-9)


def test_abc_class_summary_counts():
    r = wl.abc_analysis(ITEMS)
    assert r.class_summary["A"]["count"] == 2
    assert r.class_summary["B"]["count"] == 2
    assert r.class_summary["C"]["count"] == 1


def test_abc_to_frame_columns():
    import pandas as pd
    df = wl.abc_analysis(ITEMS).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "class" in df.columns
    assert "annual_value" in df.columns


def test_abc_empty_raises():
    with pytest.raises(ValueError):
        wl.abc_analysis([])


def test_abc_invalid_thresholds_raises():
    with pytest.raises(ValueError):
        wl.abc_analysis(ITEMS, a_threshold=0.95, b_threshold=0.80)


# ─── XYZResult ───────────────────────────────────────────────────────────────

def test_xyz_returns_result():
    r = wl.xyz_analysis(XYZ_ITEMS)
    assert isinstance(r, wl.XYZResult)


def test_xyz_class_X():
    r = wl.xyz_analysis(XYZ_ITEMS)
    x_items = [e for e in r.items if e["class"] == "X"]
    # X1(cv=0.2), X2(cv=0.1), Y2(cv=0.5 == x_threshold → X): 3 items
    assert len(x_items) == 3


def test_xyz_class_Y():
    r = wl.xyz_analysis(XYZ_ITEMS)
    y_items = [e for e in r.items if e["class"] == "Y"]
    # cv=0.5 <= x_threshold=0.5 → X; only Y1(cv=0.7) → Y
    assert len(y_items) == 1


def test_xyz_cv_from_std_mean():
    items = [{"name": "I1", "demand_std": 10, "demand_mean": 100}]
    r = wl.xyz_analysis(items)
    assert r.items[0]["cv"] == pytest.approx(0.1, rel=1e-6)
    assert r.items[0]["class"] == "X"


def test_xyz_cv_from_demand_rate():
    items = [{"name": "I1", "demand_std": 20, "demand_rate": 40}]
    r = wl.xyz_analysis(items)
    assert r.items[0]["cv"] == pytest.approx(0.5, rel=1e-6)


def test_xyz_to_frame():
    import pandas as pd
    df = wl.xyz_analysis(XYZ_ITEMS).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "cv" in df.columns
    assert "class" in df.columns


def test_xyz_empty_raises():
    with pytest.raises(ValueError):
        wl.xyz_analysis([])


# ─── ABCXYZResult ────────────────────────────────────────────────────────────

COMBO_ITEMS = [
    {"name": "I1", "demand": 100, "unit_value": 10, "cv": 0.2},  # A, X
    {"name": "I2", "demand":  50, "unit_value": 10, "cv": 0.3},  # A, X
    {"name": "I3", "demand":  10, "unit_value":  5, "cv": 0.8},  # B, Y
    {"name": "I4", "demand":   5, "unit_value":  1, "cv": 1.5},  # C, Z
]


def test_abcxyz_returns_result():
    r = wl.abc_xyz(COMBO_ITEMS)
    assert isinstance(r, wl.ABCXYZResult)


def test_abcxyz_combined_class_format():
    r = wl.abc_xyz(COMBO_ITEMS)
    for e in r.items:
        assert e["combined_class"] == e["abc_class"] + e["xyz_class"]


def test_abcxyz_matrix_sums_to_n():
    r = wl.abc_xyz(COMBO_ITEMS)
    assert sum(r.matrix.values()) == len(COMBO_ITEMS)


def test_abcxyz_matrix_frame_shape():
    import pandas as pd
    df = wl.abc_xyz(COMBO_ITEMS).matrix_frame()
    assert df.shape == (3, 3)  # 3 ABC rows × 3 XYZ columns
