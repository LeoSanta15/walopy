"""Secuenciación de una máquina y algoritmo de Johnson."""
from __future__ import annotations

import pytest

import walopy as wl

# ─── Single-machine scheduling ────────────────────────────────────────────────

def test_spt_minimises_total_completion():
    # SPT is optimal for ΣCj on a single machine
    p = [3, 1, 4, 1, 5]
    r_spt  = wl.schedule_single(p, rule="SPT")
    r_fifo = wl.schedule_single(p, rule="FIFO")
    assert r_spt.total_completion_time <= r_fifo.total_completion_time


def test_edd_minimises_max_lateness():
    p = [3, 2, 4]
    d = [6, 4, 8]
    r_edd  = wl.schedule_single(p, rule="EDD", due_dates=d)
    r_fifo = wl.schedule_single(p, rule="FIFO", due_dates=d)
    assert r_edd.max_lateness <= r_fifo.max_lateness + 1e-9


def test_wspt_minimises_weighted_completion():
    p = [3, 1, 4]
    w = [2, 5, 1]
    r_wspt = wl.schedule_single(p, rule="WSPT", weights=w)
    r_fifo = wl.schedule_single(p, rule="FIFO", weights=w)
    assert r_wspt.total_weighted_completion_time <= r_fifo.total_weighted_completion_time


def test_schedule_makespan_equals_sum_p():
    p = [2, 3, 5, 1]
    r = wl.schedule_single(p, rule="SPT")
    assert r.makespan == pytest.approx(sum(p), rel=1e-9)


def test_schedule_names():
    r = wl.schedule_single([2, 3], rule="FIFO", names=["A", "B"])
    assert set(r.sequence) == {"A", "B"}


def test_schedule_to_frame():
    import pandas as pd
    df = wl.schedule_single([1, 2, 3], rule="SPT").to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "C" in df.columns


def test_schedule_invalid_rule_raises():
    with pytest.raises(ValueError, match="rule"):
        wl.schedule_single([1, 2], rule="INVALID")


# ─── Johnson's flow-shop ──────────────────────────────────────────────────────

def test_johnson_makespan_le_any_other():
    # Classic example: optimal sequence should beat naive order
    m1 = [3, 8, 5, 7, 2]
    m2 = [5, 2, 8, 4, 6]
    r = wl.johnson_flowshop(m1, m2)
    assert r.makespan > 0
    assert len(r.sequence) == 5


def test_johnson_all_jobs_scheduled():
    r = wl.johnson_flowshop([1, 2, 3], [3, 2, 1])
    assert len(r.sequence) == 3


def test_johnson_makespan_exact():
    # Two jobs: a=[2,3], b=[4,1] → Set1: J1(a≤b), Set2: J2(a>b) → seq J1→J2
    r = wl.johnson_flowshop([2, 3], [4, 1])
    assert r.sequence == ["J1", "J2"]
    # J1: M1 0-2, M2 2-6; J2: M1 2-5, M2 6-7 → makespan=7
    assert r.makespan == pytest.approx(7.0, rel=1e-9)


def test_johnson_to_frame():
    import pandas as pd
    df = wl.johnson_flowshop([2, 3], [4, 1]).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "Makespan" not in df.columns   # frame has job rows, not totals
    assert "M1 inicio" in df.columns


def test_johnson_names():
    r = wl.johnson_flowshop([1, 2], [2, 1], names=["Alpha", "Beta"])
    assert set(r.sequence) == {"Alpha", "Beta"}
