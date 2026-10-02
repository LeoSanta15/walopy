"""Tests for NEH flow-shop heuristic."""
from __future__ import annotations

import pytest

import walopy as wl

# 3-job / 3-machine classic example
TIMES_3x3 = [
    [3, 2, 2],
    [4, 1, 3],
    [2, 3, 1],
]

# 4-job / 2-machine (Johnson's algorithm gives optimal: J3,J1,J4,J2 or similar)
TIMES_4x2 = [
    [5, 2],
    [1, 6],
    [3, 7],
    [4, 3],
]


def test_basic_returns_neh_result():
    r = wl.neh_flowshop(TIMES_3x3)
    assert isinstance(r, wl.NEHResult)


def test_makespan_positive():
    r = wl.neh_flowshop(TIMES_3x3)
    assert r.makespan > 0


def test_sequence_contains_all_jobs():
    r = wl.neh_flowshop(TIMES_3x3)
    assert sorted(r.sequence) == ["J1", "J2", "J3"]


def test_n_machines_correct():
    r = wl.neh_flowshop(TIMES_3x3)
    assert r.n_machines == 3


def test_machine_schedules_length():
    r = wl.neh_flowshop(TIMES_3x3)
    assert len(r.machine_schedules) == 3
    for m_sched in r.machine_schedules:
        assert len(m_sched) == 3  # one entry per job


def test_machine_schedule_start_end_consistent():
    r = wl.neh_flowshop(TIMES_3x3)
    for mi, m_sched in enumerate(r.machine_schedules):
        for si, slot in enumerate(m_sched):
            job_name = r.sequence[si]
            job_idx  = int(job_name[1]) - 1
            assert pytest.approx(slot["end"] - slot["start"], abs=1e-9) == TIMES_3x3[job_idx][mi]


def test_makespan_equals_last_machine_last_job():
    r = wl.neh_flowshop(TIMES_3x3)
    assert r.makespan == pytest.approx(r.machine_schedules[-1][-1]["end"], abs=1e-9)


def test_custom_names():
    names = ["Alpha", "Beta", "Gamma"]
    r = wl.neh_flowshop(TIMES_3x3, names=names)
    assert set(r.sequence) == set(names)


def test_single_job():
    r = wl.neh_flowshop([[5, 3, 2]])
    assert r.makespan == pytest.approx(10.0)
    assert r.sequence == ["J1"]


def test_single_machine():
    r = wl.neh_flowshop([[3], [1], [4]])
    # Optimal order by SPT: J2, J1, J3 → makespan = 1+3+4 = 8
    assert r.makespan == pytest.approx(1 + 3 + 4)


def test_to_frame_columns():
    import pandas as pd
    df = wl.neh_flowshop(TIMES_4x2).to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "M1_start" in df.columns
    assert "M2_start" in df.columns
    assert "M1_end"   in df.columns


def test_no_negative_start_times():
    r = wl.neh_flowshop(TIMES_4x2)
    for m_sched in r.machine_schedules:
        for slot in m_sched:
            assert slot["start"] >= -1e-9


def test_empty_raises():
    with pytest.raises(ValueError):
        wl.neh_flowshop([])


def test_mismatched_row_raises():
    with pytest.raises(ValueError):
        wl.neh_flowshop([[1, 2], [3]])


def test_summary_contains_makespan():
    r = wl.neh_flowshop(TIMES_3x3)
    s = str(r)
    assert "Makespan" in s
    assert "NEH" in s
