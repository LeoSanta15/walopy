"""All plotting functions for walopy.  Import matplotlib lazily."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    from .queuing import QueueResult
    from .operations import OEEResult
    from .bottleneck import BottleneckResult
    from .kpi import KPINode

# Brand-neutral palette
BLUE   = "#1f4e9c"
RED    = "#d62728"
GREEN  = "#2e8b57"
GRAY   = "#8c8c8c"
ORANGE = "#e08a00"
TEAL   = "#009090"
PURPLE = "#7b2d8b"


# ---------------------------------------------------------------------------
# Queue sensitivity — Wq vs ρ
# ---------------------------------------------------------------------------

def plot_queue_sensitivity(
    result: "QueueResult",
    *,
    title: str | None = None,
    figsize: tuple | None = None,
) -> "plt.Figure":
    """Plot Wq and Lq as a function of utilization ρ around the operating point."""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(1, 2, figsize=figsize or (12, 4))

    rho_range = np.linspace(0.05, 0.99, 300)
    mu = result.mu

    if result.model == "M/M/1" or result.model == "M/D/1":
        coeff = 1.0 if result.model == "M/M/1" else 0.5
        Wq_curve = coeff * rho_range / ((1 - rho_range) * mu)
        Lq_curve = rho_range**2 / ((1 - rho_range) * (1 if coeff == 1.0 else 2))
    else:
        Wq_curve = rho_range / ((1 - rho_range) * mu)
        Lq_curve = rho_range**2 / (1 - rho_range)

    for ax, y_curve, y_point, ylabel, label in [
        (axes[0], Wq_curve, result.Wq, "Wq (avg wait time)", "Wq"),
        (axes[1], Lq_curve, result.Lq, "Lq (avg queue length)", "Lq"),
    ]:
        ax.plot(rho_range, y_curve, color=BLUE, lw=2, label=f"{label} curve")
        ax.axvline(result.rho, color=ORANGE, ls="--", lw=1.5, label=f"ρ = {result.rho:.3f}")
        ax.scatter([result.rho], [y_point], color=RED, zorder=5, s=60)
        ax.set_xlabel("Utilization ρ")
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.25)

    fig.suptitle(title or f"{result.model} — Queue Sensitivity", fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Queuing metrics bar chart
# ---------------------------------------------------------------------------

def plot_queue_metrics(
    result: "QueueResult",
    *,
    title: str | None = None,
    figsize: tuple | None = None,
) -> "plt.Figure":
    """Bar chart of the main queuing KPIs."""
    import matplotlib.pyplot as plt

    labels = ["ρ", "L", "Lq", "W", "Wq"]
    values = [result.rho, result.L, result.Lq, result.W, result.Wq]
    colors = [BLUE, GREEN, TEAL, ORANGE, RED]

    fig, ax = plt.subplots(figsize=figsize or (8, 4))
    bars = ax.bar(labels, values, color=colors, alpha=0.85, edgecolor="white")
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.01,
            f"{val:.4g}",
            ha="center", va="bottom", fontsize=9,
        )
    ax.set_ylabel("Value")
    ax.set_title(title or f"{result.model} — KPI Summary", fontweight="bold")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# OEE waterfall
# ---------------------------------------------------------------------------

def plot_oee(
    result: "OEEResult",
    *,
    title: str | None = None,
    figsize: tuple | None = None,
) -> "plt.Figure":
    """Horizontal bar chart showing OEE decomposition."""
    import matplotlib.pyplot as plt
    import numpy as np

    labels = ["Availability", "Performance", "Quality", "OEE"]
    values = [
        result.availability,
        result.performance,
        result.quality,
        result.oee,
    ]
    colors = [BLUE, GREEN, TEAL, ORANGE]

    fig, ax = plt.subplots(figsize=figsize or (7, 4))
    bars = ax.barh(labels, values, color=colors, alpha=0.87, edgecolor="white")
    ax.set_xlim(0, 1.05)
    for bar, val in zip(bars, values):
        ax.text(
            val + 0.005,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1%}",
            va="center", fontsize=10,
        )
    ax.axvline(0.85, color=GRAY, ls="--", lw=1, label="World-class (85%)")
    ax.set_xlabel("Factor value")
    ax.legend(fontsize=8)
    ax.set_title(title or "OEE Decomposition", fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Bottleneck utilization chart
# ---------------------------------------------------------------------------

def plot_bottleneck(
    result: "BottleneckResult",
    *,
    title: str | None = None,
    figsize: tuple | None = None,
) -> "plt.Figure":
    """Bar chart of station utilizations with bottleneck highlighted."""
    import matplotlib.pyplot as plt

    names  = [s.name for s in result.stations]
    utils  = [s.utilization for s in result.stations]
    colors = [RED if s.is_bottleneck else BLUE for s in result.stations]

    fig, ax = plt.subplots(figsize=figsize or (max(6, len(names) * 1.2), 4))
    bars = ax.bar(names, utils, color=colors, alpha=0.85, edgecolor="white")
    for bar, u in zip(bars, utils):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{u:.1%}",
            ha="center", va="bottom", fontsize=9,
        )
    ax.axhline(1.0, color=RED, ls="--", lw=1.2, label="Capacity limit")
    ax.set_ylim(0, max(1.1, max(utils) * 1.1))
    ax.set_ylabel("Utilization")
    ax.legend(fontsize=8)
    ax.set_title(title or f"Bottleneck: {result.bottleneck}", fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# KPI tree — text-based radial / sunburst via nested rectangles
# ---------------------------------------------------------------------------

def plot_kpi_tree(
    root: "KPINode",
    *,
    title: str | None = None,
    figsize: tuple | None = None,
) -> "plt.Figure":
    """Horizontal tree layout for a KPI node hierarchy."""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    rows: list[tuple[int, str, float, str]] = []

    def _collect(node: "KPINode", depth: int) -> None:
        rows.append((depth, node.name, node.value, node.unit))
        for child in node.children:
            _collect(child, depth + 1)

    _collect(root, 0)

    n   = len(rows)
    fig, ax = plt.subplots(figsize=figsize or (10, max(4, n * 0.55)))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, n - 0.5)
    ax.axis("off")

    palette = [BLUE, GREEN, TEAL, ORANGE, PURPLE, RED, GRAY]

    for i, (depth, name, value, unit) in enumerate(rows):
        y     = n - 1 - i
        x     = depth * 0.06
        color = palette[depth % len(palette)]
        unit_str = f" [{unit}]" if unit else ""
        ax.text(
            x + 0.02, y,
            f"● {name}: {value:.4g}{unit_str}",
            va="center", ha="left",
            fontsize=10 - depth,
            color=color,
            fontweight="bold" if depth == 0 else "normal",
        )

    fig.suptitle(title or f"KPI Tree — {root.name}", fontweight="bold")
    fig.tight_layout()
    return fig
