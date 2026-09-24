"""Tests for KPI trees."""
from __future__ import annotations

import pytest

from walopy import KPINode, oee_kpi_tree, throughput_kpi_tree, cost_kpi_tree


def test_oee_kpi_tree_root_value():
    tree = oee_kpi_tree(0.9, 0.8, 0.95)
    assert tree.value == pytest.approx(0.9 * 0.8 * 0.95)
    assert len(tree.children) == 3


def test_kpi_node_find():
    tree = oee_kpi_tree(0.9, 0.8, 0.95)
    node = tree.find("Performance")
    assert node is not None
    assert node.value == pytest.approx(0.8)


def test_kpi_node_leaves():
    tree = oee_kpi_tree(0.9, 0.8, 0.95)
    leaves = tree.leaves()
    assert len(leaves) == 3  # A, P, Q all have no children


def test_kpi_to_frame():
    import pandas as pd

    tree = oee_kpi_tree(0.9, 0.8, 0.95)
    df = tree.to_frame()
    assert isinstance(df, pd.DataFrame)
    assert "name" in df.columns
    assert len(df) == 4  # root + 3 children


def test_throughput_kpi_tree():
    tree = throughput_kpi_tree(actual_throughput=80, capacity=100, defect_rate=0.05)
    assert tree.value == pytest.approx(80 * 0.95)


def test_cost_kpi_tree():
    tree = cost_kpi_tree(fixed_cost=1000, variable_cost_per_unit=5, units_produced=200)
    assert tree.value == pytest.approx(5 + 5)   # 1000/200 + 5
