"""walopy — Herramientas de investigación de operaciones para Python: colas, inventarios, scheduling, proyectos, confiabilidad, OEE y árboles de KPI."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

# Advanced models
from .advanced import (
    BreakEvenMultiResult,
    BreakEvenResult,
    LineBalanceResult,
    PriorityQueueResult,
    SimulationResult,
    break_even,
    break_even_multi,
    break_even_sales,
    erlang_b,
    line_balance,
    mm1_priority,
    mm1k,
    mmck,
    monte_carlo_gg1,
    queue_length_pmf,
    sojourn_cdf,
    takt_time,
)

# Bottleneck
from .bottleneck import (
    BottleneckResult,
    StationResult,
    bottleneck_analysis,
)

# Fitting
from .fitting import (
    FitResult,
    fit_from_data,
)

# Inventory
# Inventory additions
from .inventory import (
    ABCResult,
    ABCXYZResult,
    ConstrainedMultiEOQResult,
    EBQResult,
    EOQResult,
    ExchangeCurveResult,
    LotSizingResult,
    MRPResult,
    MultiItemResult,
    NewsvendorResult,
    QuantityDiscountResult,
    ReorderResult,
    RQPolicyResult,
    RSPolicyResult,
    SafetyStockCurveResult,
    XYZResult,
    abc_analysis,
    abc_xyz,
    ebq,
    ebq_multi,
    eoq,
    eoq_multi,
    eoq_multi_constrained,
    eoq_quantity_discount,
    exchange_curve,
    lot_for_lot,
    mrp,
    newsvendor,
    reorder_point,
    rq_policy,
    rs_policy,
    safety_stock_curve,
    silver_meal,
    wagner_whitin,
    xyz_analysis,
)

# KPI trees
from .kpi import (
    KPINode,
    oee_kpi_tree,
    roi_kpi_tree,
    throughput_kpi_tree,
)

# Network
from .network import (
    JacksonResult,
    StationMetrics,
    jackson_network,
)

# Operations
from .operations import (
    OEEResult,
    UnitCostResult,
    UtilizationResult,
    oee,
    unit_cost,
    utilization_efficiency,
)

# Project scheduling
from .project import (
    ActivityResult,
    ProjectResult,
    cpm,
    pert,
)

# Queuing
from .queuing import (
    QueueResult,
    cv2_erlang,
    cv2_gamma,
    cv2_lognormal,
    cv2_normal,
    cv2_triangular,
    cv2_uniform,
    cv2_weibull,
    kingman,
    littles_law,
    md1,
    mg1,
    mm1,
    mmc,
)

# Reliability
from .reliability import (
    ReliabilityResult,
    WeibullResult,
    koon_system,
    mtbf_analysis,
    parallel_system,
    series_system,
    weibull_analysis,
)

# Scheduling
from .scheduling import (
    FlowShopResult,
    JobSchedule,
    NEHResult,
    ScheduleResult,
    johnson_flowshop,
    neh_flowshop,
    schedule_single,
)

# Solvers
from .solver import (
    OptimizeResult,
    SolverResult,
    batch_model,
    compare,
    optimize_servers,
    sensitivity,
    solve_lam,
    solve_mu,
    solve_servers,
)

try:
    __version__: str = version("walopy")
except PackageNotFoundError:
    __version__ = "0+unknown"  # sin instalar: la versión vive solo en pyproject.toml

__all__ = [
    # queuing
    "QueueResult",
    "littles_law",
    "mm1",
    "mmc",
    "md1",
    "kingman",
    "mg1",
    "cv2_triangular",
    "cv2_uniform",
    "cv2_normal",
    "cv2_erlang",
    "cv2_gamma",
    "cv2_lognormal",
    "cv2_weibull",
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
    "compare",
    # advanced
    "SimulationResult",
    "LineBalanceResult",
    "BreakEvenResult",
    "BreakEvenMultiResult",
    "PriorityQueueResult",
    "erlang_b",
    "mm1k",
    "mmck",
    "mm1_priority",
    "monte_carlo_gg1",
    "takt_time",
    "line_balance",
    "break_even",
    "break_even_multi",
    "break_even_sales",
    "queue_length_pmf",
    "sojourn_cdf",
    # fitting
    "FitResult",
    "fit_from_data",
    # inventory
    "EOQResult",
    "EBQResult",
    "MultiItemResult",
    "ConstrainedMultiEOQResult",
    "LotSizingResult",
    "QuantityDiscountResult",
    "ReorderResult",
    "NewsvendorResult",
    "eoq",
    "ebq",
    "eoq_multi",
    "ebq_multi",
    "eoq_multi_constrained",
    "lot_for_lot",
    "silver_meal",
    "eoq_quantity_discount",
    "reorder_point",
    "newsvendor",
    # network
    "StationMetrics",
    "JacksonResult",
    "jackson_network",
    # inventory additions
    "RQPolicyResult",
    "RSPolicyResult",
    "ExchangeCurveResult",
    "SafetyStockCurveResult",
    "ABCResult",
    "XYZResult",
    "ABCXYZResult",
    "MRPResult",
    "rq_policy",
    "rs_policy",
    "wagner_whitin",
    "exchange_curve",
    "safety_stock_curve",
    "abc_analysis",
    "xyz_analysis",
    "abc_xyz",
    "mrp",
    # scheduling
    "JobSchedule",
    "ScheduleResult",
    "FlowShopResult",
    "NEHResult",
    "schedule_single",
    "johnson_flowshop",
    "neh_flowshop",
    # reliability
    "ReliabilityResult",
    "WeibullResult",
    "mtbf_analysis",
    "series_system",
    "parallel_system",
    "koon_system",
    "weibull_analysis",
    # project
    "ActivityResult",
    "ProjectResult",
    "cpm",
    "pert",
]
