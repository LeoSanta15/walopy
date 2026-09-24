"""Tests for KPI trees."""
from __future__ import annotations

import pytest

from walopy import KPINode, oee_kpi_tree, throughput_kpi_tree, roi_kpi_tree


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


def test_roi_kpi_tree():
    tree = roi_kpi_tree(
        revenue=50_000,
        fixed_cost=10_000,
        variable_cost_per_unit=8,
        units_sold=2_000,
        investment=20_000,
    )
    # Net Profit = 50000 - (10000 + 8*2000) = 50000 - 26000 = 24000
    # ROI = 24000 / 20000 = 1.2
    assert tree.value == pytest.approx(1.2)
    net_profit_node = tree.find("Net Profit")
    assert net_profit_node is not None
    assert net_profit_node.value == pytest.approx(24_000)


def test_roi_kpi_tree_structure():
    tree = roi_kpi_tree(
        revenue=10_000,
        fixed_cost=2_000,
        variable_cost_per_unit=5,
        units_sold=1_000,
        investment=5_000,
    )
    assert tree.find("Revenue") is not None
    assert tree.find("Total Cost") is not None
    assert tree.find("Fixed Cost") is not None
    assert tree.find("Variable Cost") is not None
    assert tree.find("Investment") is not None
