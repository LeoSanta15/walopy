"""walopy — Queuing theory, operations analysis and KPI trees for Python."""
from __future__ import annotations

# Queuing
from .queuing import (
    QueueResult,
    littles_law,
    mm1,
    mmc,
    md1,
    kingman,
)

# Operations
from .operations import (
    OEEResult,
    UtilizationResult,
    UnitCostResult,
    oee,
    utilization_efficiency,
    unit_cost,
)

# Bottleneck
from .bottleneck import (
    BottleneckResult,
    StationResult,
    bottleneck_analysis,
)

# KPI trees
from .kpi import (
    KPINode,
    oee_kpi_tree,
    throughput_kpi_tree,
    roi_kpi_tree,
)

# Solvers
from .solver import (
    SolverResult,
    OptimizeResult,
    solve_lam,
    solve_mu,
    solve_servers,
    optimize_servers,
    sensitivity,
    batch_model,
)

# Advanced models
from .advanced import (
    SimulationResult,
    LineBalanceResult,
    BreakEvenResult,
    erlang_b,
    mm1k,
    monte_carlo_gg1,
    takt_time,
    line_balance,
    break_even,
    queue_length_pmf,
    sojourn_cdf,
)

__version__ = "0.1.0"

__all__ = [
    # queuing
    "QueueResult",
    "littles_law",
    "mm1",
    "mmc",
    "md1",
    "kingman",
    # operations
    "OEEResult",
    "UtilizationResult",
    "UnitCostResult",
    "oee",
    "utilization_efficiency",
    "unit_cost",
    # bottleneck
    "BottleneckResult",
    "StationResult",
    "bottleneck_analysis",
    # kpi
    "KPINode",
    "oee_kpi_tree",
    "throughput_kpi_tree",
    "roi_kpi_tree",
    # solver
    "SolverResult",
    "OptimizeResult",
    "solve_lam",
    "solve_mu",
    "solve_servers",
    "optimize_servers",
    "sensitivity",
    "batch_model",
    # advanced
    "SimulationResult",
    "LineBalanceResult",
    "BreakEvenResult",
    "erlang_b",
    "mm1k",
    "monte_carlo_gg1",
    "takt_time",
    "line_balance",
    "break_even",
    "queue_length_pmf",
    "sojourn_cdf",
]
