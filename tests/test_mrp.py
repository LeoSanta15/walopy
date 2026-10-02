"""Tests for MRP (single-level Material Requirements Planning)."""
from __future__ import annotations

import pytest

import walopy as wl

# Muchos casos usan el lead_time por defecto sobre horizontes cortos: el aviso es esperado.
pytestmark = pytest.mark.filterwarnings("ignore:.*antes del periodo 1:UserWarning")

GR = [0, 50, 0, 30, 60, 20]  # 6 periods


def test_mrp_returns_result():
    r = wl.mrp(GR)
    assert isinstance(r, wl.MRPResult)


def test_mrp_periods_length():
    r = wl.mrp(GR)
    assert len(r.periods) == len(GR)


def test_mrp_default_periods_are_1_indexed():
    r = wl.mrp(GR)
    assert r.periods[0] == 1
    assert r.periods[-1] == len(GR)


def test_mrp_no_demand_no_orders():
    r = wl.mrp([0, 0, 0])
    assert all(pr == 0 for pr in r.planned_receipts)


def test_mrp_lfl_no_initial_oh():
    # With no initial stock, GR=NR each period; planned receipts match GR (non-zero)
    r = wl.mrp([100, 0, 50])
    assert r.planned_receipts[0] == pytest.approx(100.0)
    assert r.planned_receipts[1] == pytest.approx(0.0)
    assert r.planned_receipts[2] == pytest.approx(50.0)


def test_mrp_initial_oh_reduces_requirements():
    r = wl.mrp([100], initial_on_hand=60)
    assert r.net_requirements[0] == pytest.approx(40.0)
    assert r.planned_receipts[0] == pytest.approx(40.0)


def test_mrp_scheduled_receipts_offset():
    # SR covers the requirement
    r = wl.mrp([100], scheduled_receipts=[120])
    assert r.net_requirements[0] == pytest.approx(0.0)
    assert r.planned_receipts[0] == pytest.approx(0.0)


def test_mrp_projected_oh_non_negative():
    r = wl.mrp(GR, initial_on_hand=10)
    assert all(oh >= -1e-9 for oh in r.projected_on_hand)


def test_mrp_fixed_lot_size_rounds_up():
    r = wl.mrp([70], lot_size=50.0)
    assert r.planned_receipts[0] == pytest.approx(100.0)  # ceil(70/50)*50


def test_mrp_planned_release_lead_time_1():
    # receipt in period 2 (idx=1) → release in period 1 (idx=0)
    r = wl.mrp([0, 50, 0], lead_time=1)
    assert r.planned_releases[0] == pytest.approx(50.0)
    assert r.planned_releases[1] == pytest.approx(0.0)


def test_mrp_safety_stock_maintained():
    ss = 10.0
    r  = wl.mrp([30], initial_on_hand=5, safety_stock=ss)
    assert r.projected_on_hand[0] >= ss - 1e-9


def test_mrp_to_frame_columns():
    import pandas as pd
    df = wl.mrp(GR).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "Req_bruto" in df.columns
    assert "Lib_plan" in df.columns


def test_mrp_custom_periods():
    pds = ["Jan", "Feb", "Mar"]
    r   = wl.mrp([10, 20, 30], periods=pds)
    assert r.periods == pds


def test_mrp_empty_raises():
    with pytest.raises(ValueError):
        wl.mrp([])
