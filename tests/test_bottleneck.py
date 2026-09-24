"""Tests for bottleneck analysis."""
from __future__ import annotations

import pytest

from walopy import bottleneck_analysis


def test_bottleneck_identified():
    r = bottleneck_analysis(
        station_names=["A", "B", "C"],
        capacities=[10.0, 6.0, 9.0],
        demand_rate=5.0,
    )
    assert r.bottleneck == "B"
    assert r.system_throughput == pytest.approx(6.0)


def test_all_utilizations_computed():
    r = bottleneck_analysis(
        station_names=["X", "Y"],
        capacities=[20.0, 10.0],
        demand_rate=8.0,
    )
    stations = {s.name: s for s in r.stations}
    assert stations["X"].utilization == pytest.approx(0.4)
    assert stations["Y"].utilization == pytest.approx(0.8)
    assert r.bottleneck == "Y"


def test_routing_fractions():
    r = bottleneck_analysis(
        station_names=["Shared", "Exclusive"],
        capacities=[10.0, 4.0],
        demand_rate=8.0,
        routing_fractions=[1.0, 0.5],
    )
    # Exclusive station: demand = 4.0, capacity = 4.0 → utilization = 1.0
    assert r.bottleneck == "Exclusive"


def test_mismatched_lengths_raises():
    with pytest.raises(ValueError):
        bottleneck_analysis(["A", "B"], [5.0], demand_rate=3.0)


def test_empty_station_names_raises():
    with pytest.raises(ValueError, match="station_names"):
        bottleneck_analysis([], [], demand_rate=5.0)
