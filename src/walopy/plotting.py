"""All plotting functions for walopy.  Matplotlib and Plotly are imported lazily."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    from .queuing import QueueResult
    from .operations import OEEResult
    from .bottleneck import BottleneckResult
    from .kpi import KPINode
    from .solver import OptimizeResult
    from .advanced import SimulationResult, LineBalanceResult, BreakEvenResult

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
    kind: str = "treemap",
) -> "go.Figure":
    """Interactive KPI tree using Plotly.

    Parameters
    ----------
    root : KPINode
        Root of the KPI hierarchy.
    title : str, optional
        Figure title.  Defaults to "KPI Tree — <root.name>".
    kind : {'treemap', 'sunburst'}
        Chart type.  'treemap' (default) uses area to encode value;
        'sunburst' uses a radial layout.

    Returns
    -------
    plotly.graph_objects.Figure
        Call ``.show()`` to display or ``.write_html()`` to save.
    """
    import plotly.graph_objects as go

    ids: list[str]        = []
    labels: list[str]     = []
    parents: list[str]    = []
    values: list[float]   = []
    hover: list[str]      = []

    def _collect(node: "KPINode", parent_id: str = "") -> None:
        node_id = f"{parent_id}/{node.name}" if parent_id else node.name
        ids.append(node_id)
        labels.append(node.name)
        parents.append(parent_id)
        # Use absolute value for area sizing; zero would collapse the tile
        values.append(max(abs(node.value), 1e-9))
        unit_str    = f" {node.unit}" if node.unit else ""
        formula_str = f"<br><i>{node.formula}</i>" if node.formula else ""
        hover.append(f"<b>{node.name}</b><br>{node.value:.6g}{unit_str}{formula_str}")
        for child in node.children:
            _collect(child, node_id)

    _collect(root)

    chart_title = title or f"KPI Tree — {root.name}"

    if kind == "sunburst":
        trace = go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            customdata=hover,
            hovertemplate="%{customdata}<extra></extra>",
            branchvalues="total",
            textinfo="label+value",
            insidetextorientation="radial",
            marker=dict(colorscale="Blues"),
        )
        layout = go.Layout(
            title=dict(text=chart_title, font=dict(size=16)),
            margin=dict(t=60, l=10, r=10, b=10),
        )
    else:
        trace = go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            customdata=hover,
            hovertemplate="%{customdata}<extra></extra>",
            branchvalues="total",
            texttemplate="<b>%{label}</b><br>%{value:.4g}",
            textfont=dict(size=13),
            marker=dict(
                colorscale="Blues",
                showscale=False,
                line=dict(width=2, color="white"),
            ),
            pathbar=dict(visible=True),
        )
        layout = go.Layout(
            title=dict(text=chart_title, font=dict(size=16)),
            margin=dict(t=60, l=10, r=10, b=10),
        )

    return go.Figure(data=[trace], layout=layout)


# ---------------------------------------------------------------------------
# Sensitivity — line chart for one swept parameter
# ---------------------------------------------------------------------------

def plot_sensitivity(
    df: "pd.DataFrame",
    param: str,
    metrics: list[str] | None = None,
    *,
    title: str | None = None,
) -> "go.Figure":
    """Line chart of KPI metrics swept over one parameter.

    Parameters
    ----------
    df : pd.DataFrame
        Output of ``walopy.solver.sensitivity()``.
    param : str
        Name of the swept parameter (x-axis).
    metrics : list of str, optional
        Columns to plot.  Defaults to ``['rho', 'Wq', 'Lq', 'W', 'L']``
        (filtered to those present in *df*).
    title : str, optional
    """
    import plotly.graph_objects as go

    default_metrics = ["rho", "Wq", "Lq", "W", "L"]
    cols = metrics or [m for m in default_metrics if m in df.columns]
    if not cols:
        cols = [c for c in df.columns if c != param]

    colors = [BLUE, RED, GREEN, ORANGE, TEAL, PURPLE, GRAY]
    fig = go.Figure()
    for i, col in enumerate(cols):
        sub = df[[param, col]].dropna()
        fig.add_trace(go.Scatter(
            x=sub[param], y=sub[col],
            mode="lines", name=col,
            line=dict(color=colors[i % len(colors)], width=2),
        ))

    fig.update_layout(
        title=dict(text=title or f"Sensitivity: {param}", font=dict(size=16)),
        xaxis_title=param,
        yaxis_title="Value",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        margin=dict(t=80, l=60, r=20, b=60),
    )
    return fig


# ---------------------------------------------------------------------------
# Optimize servers — cost vs c
# ---------------------------------------------------------------------------

def plot_optimize_servers(
    result: "OptimizeResult",
    *,
    title: str | None = None,
) -> "go.Figure":
    """Bar + line chart showing cost breakdown per number of servers."""
    import plotly.graph_objects as go

    df  = result.cost_breakdown
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["c"], y=df["server_cost"],
        name="Server cost", marker_color=BLUE, opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        x=df["c"], y=df["wait_cost"],
        name="Waiting cost", marker_color=ORANGE, opacity=0.8,
    ))
    fig.add_trace(go.Scatter(
        x=df["c"], y=df["total_cost"],
        mode="lines+markers", name="Total cost",
        line=dict(color=RED, width=2.5),
        marker=dict(size=7),
    ))
    fig.add_vline(
        x=result.optimal_servers,
        line=dict(color=GREEN, width=2, dash="dash"),
        annotation_text=f"Optimal c = {result.optimal_servers}",
        annotation_position="top right",
    )

    fig.update_layout(
        barmode="stack",
        title=dict(text=title or "Server Cost Optimization", font=dict(size=16)),
        xaxis_title="Number of servers (c)",
        yaxis_title="Cost per unit time",
        hovermode="x unified",
        margin=dict(t=80, l=60, r=20, b=60),
    )
    return fig


# ---------------------------------------------------------------------------
# Monte-Carlo simulation — Wq histogram + percentiles
# ---------------------------------------------------------------------------

def plot_simulation(
    result: "SimulationResult",
    *,
    title: str | None = None,
    n_bins: int = 60,
) -> "go.Figure":
    """Histogram of simulated waiting times with percentile annotations."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    Wq   = result._Wq_array
    fig  = make_subplots(rows=1, cols=2, subplot_titles=["Wq Distribution", "Wq CDF"])

    # Histogram
    counts, edges = __import__("numpy").histogram(Wq, bins=n_bins)
    midpoints = 0.5 * (edges[:-1] + edges[1:])
    fig.add_trace(go.Bar(x=midpoints, y=counts, name="Wq",
                         marker_color=BLUE, opacity=0.75), row=1, col=1)

    for pct_val, pct_label, color in [
        (result.Wq_p50, "p50", GREEN),
        (result.Wq_p90, "p90", ORANGE),
        (result.Wq_p95, "p95", RED),
    ]:
        fig.add_vline(x=pct_val, line=dict(color=color, width=1.5, dash="dot"),
                      annotation_text=pct_label, row=1, col=1)

    # Empirical CDF
    sorted_Wq = __import__("numpy").sort(Wq)
    cdf        = __import__("numpy").arange(1, len(sorted_Wq) + 1) / len(sorted_Wq)
    fig.add_trace(go.Scatter(x=sorted_Wq, y=cdf, mode="lines",
                              name="Empirical CDF",
                              line=dict(color=BLUE, width=2)), row=1, col=2)
    for pct_val, pct_label, color in [
        (result.Wq_p90, "p90=90%", ORANGE),
        (result.Wq_p95, "p95=95%", RED),
    ]:
        fig.add_hline(y=pct_val / max(Wq) if max(Wq) > 0 else 0,
                      line=dict(color=color, width=1, dash="dot"), row=1, col=2)
        fig.add_trace(go.Scatter(x=[pct_val], y=[0.9 if "90" in pct_label else 0.95],
                                  mode="markers+text",
                                  text=[pct_label], textposition="top right",
                                  marker=dict(color=color, size=8),
                                  showlegend=False), row=1, col=2)

    fig.update_layout(
        title=dict(text=title or result.model, font=dict(size=15)),
        showlegend=False,
        margin=dict(t=80, l=60, r=20, b=60),
    )
    fig.update_xaxes(title_text="Wq (wait time)", row=1, col=1)
    fig.update_xaxes(title_text="Wq (wait time)", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative probability", row=1, col=2)
    return fig


# ---------------------------------------------------------------------------
# Line balance — cycle time vs takt
# ---------------------------------------------------------------------------

def plot_line_balance(
    result: "LineBalanceResult",
    *,
    title: str | None = None,
) -> "go.Figure":
    """Bar chart of cycle times per station with takt time reference line."""
    import plotly.graph_objects as go

    df     = result.stations
    colors = [RED if ov else BLUE for ov in df["Overloaded"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Station"], y=df["CycleTime"],
        name="Cycle time",
        marker_color=colors,
        text=[f"{ct:.3g}" for ct in df["CycleTime"]],
        textposition="outside",
    ))
    fig.add_hline(
        y=result.takt,
        line=dict(color=GREEN, width=2.5, dash="dash"),
        annotation_text=f"Takt = {result.takt:.4g}",
        annotation_position="top right",
    )
    fig.add_trace(go.Bar(
        x=df["Station"], y=df["IdleTime"],
        name="Idle time",
        marker_color=GRAY, opacity=0.45,
    ))

    fig.update_layout(
        barmode="stack",
        title=dict(
            text=title or f"Line Balance — eff. {result.balance_efficiency:.1%}",
            font=dict(size=16),
        ),
        xaxis_title="Station",
        yaxis_title="Time",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=80, l=60, r=20, b=60),
    )
    return fig


# ---------------------------------------------------------------------------
# Break-even — revenue / cost lines
# ---------------------------------------------------------------------------

def plot_break_even(
    result: "BreakEvenResult",
    *,
    title: str | None = None,
    unit_range_factor: float = 2.0,
) -> "go.Figure":
    """Revenue and total cost lines with break-even point highlighted."""
    import plotly.graph_objects as go
    import numpy as np

    p   = result.params
    fc  = p["fixed_cost"]
    ppu = p["price_per_unit"]
    vcu = p["variable_cost_per_unit"]
    bep = result.bep_units

    units = np.linspace(0, bep * unit_range_factor, 300)
    rev   = ppu * units
    cost  = fc + vcu * units

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=units, y=rev,  mode="lines", name="Revenue",
                              line=dict(color=GREEN, width=2.5)))
    fig.add_trace(go.Scatter(x=units, y=cost, mode="lines", name="Total Cost",
                              line=dict(color=RED, width=2.5)))
    fig.add_trace(go.Scatter(
        x=[bep], y=[result.bep_revenue],
        mode="markers+text",
        text=[f"BEP ({bep:.0f} units)"],
        textposition="top right",
        marker=dict(color=ORANGE, size=12, symbol="star"),
        name="Break-even",
    ))

    # Shade profit / loss regions
    fig.add_trace(go.Scatter(
        x=np.concatenate([units, units[::-1]]),
        y=np.concatenate([np.where(rev > cost, rev, cost),
                          np.where(rev > cost, cost, cost)[::-1]]),
        fill="toself", fillcolor="rgba(46,139,87,0.12)",
        line=dict(color="rgba(0,0,0,0)"), name="Profit zone",
    ))

    if "actual_units" in p:
        au  = p["actual_units"]
        fig.add_vline(x=au, line=dict(color=BLUE, width=1.5, dash="dot"),
                      annotation_text=f"Actual ({au:.0f})", annotation_position="top left")

    fig.update_layout(
        title=dict(text=title or "Break-Even Analysis", font=dict(size=16)),
        xaxis_title="Units",
        yaxis_title="Amount",
        hovermode="x unified",
        margin=dict(t=80, l=60, r=20, b=60),
    )
    return fig


# ---------------------------------------------------------------------------
# Queue-length PMF and sojourn CDF (MM1)
# ---------------------------------------------------------------------------

def plot_queue_distribution(
    pmf_df: "pd.DataFrame",
    cdf_df: "pd.DataFrame",
    *,
    title: str | None = None,
) -> "go.Figure":
    """Two-panel chart: queue-length PMF (bar) and sojourn-time CDF (line)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=["P(N = n) — Queue length", "F(t) — Sojourn time CDF"])

    fig.add_trace(go.Bar(x=pmf_df["n"], y=pmf_df["P(N=n)"],
                          name="P(N=n)", marker_color=BLUE, opacity=0.8), row=1, col=1)
    fig.add_trace(go.Scatter(x=pmf_df["n"], y=pmf_df["P(N<=n)"],
                              mode="lines+markers", name="P(N≤n)",
                              line=dict(color=ORANGE, width=2)), row=1, col=1)

    fig.add_trace(go.Scatter(x=cdf_df["t"], y=cdf_df["F(t)"],
                              mode="lines", name="F(t)",
                              line=dict(color=GREEN, width=2.5)), row=1, col=2)
    fig.add_trace(go.Scatter(x=cdf_df["t"], y=cdf_df["f(t)"],
                              mode="lines", name="f(t)",
                              line=dict(color=TEAL, width=1.5, dash="dot"),
                              yaxis="y3"), row=1, col=2)

    fig.update_layout(
        title=dict(text=title or "M/M/1 Distributions", font=dict(size=16)),
        margin=dict(t=80, l=60, r=20, b=60),
    )
    fig.update_xaxes(title_text="n (customers)", row=1, col=1)
    fig.update_xaxes(title_text="t (time)", row=1, col=2)
    fig.update_yaxes(title_text="Probability", row=1, col=1)
    fig.update_yaxes(title_text="F(t) / f(t)", row=1, col=2)
    return fig
