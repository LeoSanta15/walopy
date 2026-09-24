"""Tests for OEE, utilization and unit cost."""
from __future__ import annotations

import pytest

from walopy import oee, utilization_efficiency, unit_cost


def test_oee_direct():
    r = oee(availability=0.9, performance=0.8, quality=0.95)
    assert r.oee == pytest.approx(0.9 * 0.8 * 0.95)


def test_oee_from_raw_availability():
    r = oee(availability=0.0, performance=0.8, quality=0.95,
            planned_time=480, downtime=48)
    assert r.availability == pytest.approx(0.9)


def test_oee_from_raw_performance():
    r = oee(availability=0.9, performance=0.0, quality=0.95,
            ideal_cycle_time=1.0, actual_cycle_time=1.25)
    assert r.performance == pytest.approx(0.8)


def test_oee_from_raw_quality():
    r = oee(availability=0.9, performance=0.8, quality=0.0,
            total_units=100, defective_units=5)
    assert r.quality == pytest.approx(0.95)


def test_utilization_efficiency_basic():
    r = utilization_efficiency(actual_output=80, capacity=100)
    assert r.utilization == pytest.approx(0.8)
    assert r.efficiency  == pytest.approx(0.8)


def test_utilization_with_standard():
    r = utilization_efficiency(actual_output=80, capacity=100, standard_output=90)
    assert r.utilization == pytest.approx(0.8)
    assert r.efficiency  == pytest.approx(80 / 90)


def test_unit_cost_basic():
    r = unit_cost(fixed_cost=1000, variable_cost_per_unit=5, units_produced=200)
    assert r.fixed_cost_per_unit      == pytest.approx(5.0)
    assert r.variable_cost_per_unit   == pytest.approx(5.0)
    assert r.unit_cost                == pytest.approx(10.0)
    assert r.total_cost               == pytest.approx(2000.0)


def test_unit_cost_with_overhead():
    r = unit_cost(fixed_cost=1000, variable_cost_per_unit=10,
                  units_produced=100, overhead_rate=0.1)
    assert r.variable_cost_per_unit == pytest.approx(11.0)
    assert r.unit_cost              == pytest.approx(10 + 11.0)
