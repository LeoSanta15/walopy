"""Tests for Jackson network module."""
from __future__ import annotations

import pytest

from walopy import jackson_network, mm1, mmc


def test_single_station_equals_mm1():
    # Single station with no routing → pure M/M/1
    r = jackson_network(["A"], mu=[5.0], gamma=[3.0], routing=[[0.0]])
    assert r.stations[0].lam_total == pytest.approx(3.0)
    mm1_r = mm1(3.0, 5.0)
    assert r.stations[0].Wq == pytest.approx(mm1_r.Wq, rel=1e-6)
    assert r.stations[0].L  == pytest.approx(mm1_r.L,  rel=1e-6)


def test_tandem_network():
    # Two stations in tandem: all customers go A → B → exit
    r = jackson_network(
        ["A", "B"],
        mu=[10.0, 8.0],
        gamma=[5.0, 0.0],
        routing=[[0.0, 1.0], [0.0, 0.0]],
    )
    assert r.stations[0].lam_total == pytest.approx(5.0)
    assert r.stations[1].lam_total == pytest.approx(5.0)
    assert r.L_system == pytest.approx(
        r.stations[0].L + r.stations[1].L, rel=1e-6
    )


def test_l_system_littles_law():
    r = jackson_network(
        ["A", "B"],
        mu=[10.0, 8.0],
        gamma=[5.0, 0.0],
        routing=[[0.0, 1.0], [0.0, 0.0]],
    )
    # L_system = λ_ext_total × W_system
    assert r.L_system == pytest.approx(5.0 * r.W_system, rel=1e-6)


def test_multi_server_station():
    r = jackson_network(
        ["A"],
        mu=[3.0],
        gamma=[4.0],
        routing=[[0.0]],
        servers=[2],
    )
    mmc_r = mmc(4.0, 3.0, 2)
    assert r.stations[0].Wq == pytest.approx(mmc_r.Wq, rel=1e-6)


def test_unstable_raises():
    with pytest.raises(ValueError, match="unstable"):
        jackson_network(["A"], mu=[2.0], gamma=[5.0], routing=[[0.0]])


def test_to_frame():
    import pandas as pd
    r  = jackson_network(["A", "B"], mu=[5.0, 4.0], gamma=[2.0, 0.0],
                         routing=[[0.0, 1.0], [0.0, 0.0]])
    df = r.to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "Station" in df.columns
    assert len(df) == 2


def test_routing_row_sums_gt_1_raises():
    with pytest.raises(ValueError, match="sum"):
        jackson_network(["A"], mu=[5.0], gamma=[2.0], routing=[[1.5]])


def test_empty_stations_raises():
    with pytest.raises(ValueError, match="station_names"):
        jackson_network([], mu=[], gamma=[], routing=[])
