"""Todas las funciones de gráficas de walopy. Matplotlib y Plotly se importan de forma perezosa."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    import pandas as pd
    import plotly.graph_objects as go

    from .advanced import BreakEvenResult, LineBalanceResult, SimulationResult
    from .bottleneck import BottleneckResult
    from .inventory import EOQResult
    from .kpi import KPINode
    from .operations import OEEResult
    from .queuing import QueueResult
    from .solver import OptimizeResult

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
    result: QueueResult,
    *,
    title: str | None = None,
    figsize: tuple | None = None,
) -> plt.Figure:
    """Grafica Wq y Lq en función de la utilización ρ alrededor del punto de operación."""
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
        (axes[0], Wq_curve, result.Wq, "Wq (espera media en cola)", "Wq"),
        (axes[1], Lq_curve, result.Lq, "Lq (longitud media de cola)", "Lq"),
    ]:
        ax.plot(rho_range, y_curve, color=BLUE, lw=2, label=f"curva de {label}")
        ax.axvline(result.rho, color=ORANGE, ls="--", lw=1.5, label=f"ρ = {result.rho:.3f}")
        ax.scatter([result.rho], [y_point], color=RED, zorder=5, s=60)
        ax.set_xlabel("Utilización ρ")
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.25)

    fig.suptitle(title or f"{result.model} — Sensibilidad de la cola", fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Queuing metrics bar chart
# ---------------------------------------------------------------------------

def plot_queue_metrics(
    result: QueueResult,
    *,
    title: str | None = None,
    figsize: tuple | None = None,
) -> plt.Figure:
    """Gráfico de barras de los principales KPI de colas."""
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
    ax.set_ylabel("Valor")
    ax.set_title(title or f"{result.model} — Resumen de KPI", fontweight="bold")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# OEE waterfall
# ---------------------------------------------------------------------------

def plot_oee(
    result: OEEResult,
    *,
    title: str | None = None,
    figsize: tuple | None = None,
) -> plt.Figure:
    """Gráfico de barras horizontales con la descomposición del OEE."""
    import matplotlib.pyplot as plt

    labels = ["Disponibilidad", "Rendimiento", "Calidad", "OEE"]
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
    ax.axvline(0.85, color=GRAY, ls="--", lw=1, label="Clase mundial (85%)")
    ax.set_xlabel("Valor del factor")
    ax.legend(fontsize=8)
    ax.set_title(title or "Descomposición del OEE", fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Bottleneck utilization chart
# ---------------------------------------------------------------------------

def plot_bottleneck(
    result: BottleneckResult,
    *,
    title: str | None = None,
    figsize: tuple | None = None,
) -> plt.Figure:
    """Gráfico de barras de utilización por estación con el cuello de botella resaltado."""
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
    ax.axhline(1.0, color=RED, ls="--", lw=1.2, label="Límite de capacidad")
    ax.set_ylim(0, max(1.1, max(utils) * 1.1))
    ax.set_ylabel("Utilización")
    ax.legend(fontsize=8)
    ax.set_title(title or f"Cuello de botella: {result.bottleneck}", fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# KPI tree — text-based radial / sunburst via nested rectangles
# ---------------------------------------------------------------------------

def plot_kpi_tree(
    root: KPINode,
    *,
    title: str | None = None,
    kind: str = "treemap",
) -> go.Figure:
    """Árbol de KPI interactivo con Plotly.

    Parameters
    ----------
    root : KPINode
        Raíz de la jerarquía de KPI.
    title : str, optional
        Título de la figura. Por defecto "Árbol de KPI — <root.name>".
    kind : {'treemap', 'sunburst'}
        Tipo de gráfico. 'treemap' (por defecto) codifica el valor con el área;
        'sunburst' usa una disposición radial.

    Returns
    -------
    plotly.graph_objects.Figure
        Llame a ``.show()`` para mostrarla o a ``.write_html()`` para guardarla.
    """
    import plotly.graph_objects as go

    ids: list[str]        = []
    labels: list[str]     = []
    parents: list[str]    = []
    values: list[float]   = []
    hover: list[str]      = []

    def _collect(node: KPINode, parent_id: str = "") -> None:
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

    chart_title = title or f"Árbol de KPI — {root.name}"

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
    df: pd.DataFrame,
    param: str,
    metrics: list[str] | None = None,
    *,
    title: str | None = None,
) -> go.Figure:
    """Gráfico de líneas de KPI al variar un parámetro.

    Parameters
    ----------
    df : pd.DataFrame
        Salida de ``walopy.solver.sensitivity()``.
    param : str
        Nombre del parámetro barrido (eje x).
    metrics : list of str, optional
        Columnas a graficar. Por defecto ``['rho', 'Wq', 'Lq', 'W', 'L']``
        (filtradas a las presentes en *df*).
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
        title=dict(text=title or f"Sensibilidad: {param}", font=dict(size=16)),
        xaxis_title=param,
        yaxis_title="Valor",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        margin=dict(t=80, l=60, r=20, b=60),
    )
    return fig


# ---------------------------------------------------------------------------
# Optimize servers — cost vs c
# ---------------------------------------------------------------------------

def plot_optimize_servers(
    result: OptimizeResult,
    *,
    title: str | None = None,
) -> go.Figure:
    """Gráfico de barras y línea con el desglose de costos por número de servidores."""
    import plotly.graph_objects as go

    df  = result.cost_breakdown
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["c"], y=df["server_cost"],
        name="Costo de servidores", marker_color=BLUE, opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        x=df["c"], y=df["wait_cost"],
        name="Costo de espera", marker_color=ORANGE, opacity=0.8,
    ))
    fig.add_trace(go.Scatter(
        x=df["c"], y=df["total_cost"],
        mode="lines+markers", name="Costo total",
        line=dict(color=RED, width=2.5),
        marker=dict(size=7),
    ))
    fig.add_vline(
        x=result.optimal_servers,
        line=dict(color=GREEN, width=2, dash="dash"),
        annotation_text=f"c óptimo = {result.optimal_servers}",
        annotation_position="top right",
    )

    fig.update_layout(
        barmode="stack",
        title=dict(text=title or "Optimización del costo de servidores", font=dict(size=16)),
        xaxis_title="Número de servidores (c)",
        yaxis_title="Costo por unidad de tiempo",
        hovermode="x unified",
        margin=dict(t=80, l=60, r=20, b=60),
    )
    return fig


# ---------------------------------------------------------------------------
# Monte-Carlo simulation — Wq histogram + percentiles
# ---------------------------------------------------------------------------

def plot_simulation(
    result: SimulationResult,
    *,
    title: str | None = None,
    n_bins: int = 60,
) -> go.Figure:
    """Histograma de tiempos de espera simulados con anotaciones de percentiles."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    Wq   = result._Wq_array
    fig  = make_subplots(rows=1, cols=2, subplot_titles=["Distribución de Wq", "FDA de Wq"])

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
                              name="FDA empírica",
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
    fig.update_xaxes(title_text="Wq (tiempo de espera)", row=1, col=1)
    fig.update_xaxes(title_text="Wq (tiempo de espera)", row=1, col=2)
    fig.update_yaxes(title_text="Frecuencia", row=1, col=1)
    fig.update_yaxes(title_text="Probabilidad acumulada", row=1, col=2)
    return fig


# ---------------------------------------------------------------------------
# Line balance — cycle time vs takt
# ---------------------------------------------------------------------------

def plot_line_balance(
    result: LineBalanceResult,
    *,
    title: str | None = None,
) -> go.Figure:
    """Gráfico de barras de tiempos de ciclo por estación con la línea de referencia del takt."""
    import plotly.graph_objects as go

    df     = result.stations
    colors = [RED if ov else BLUE for ov in df["Sobrecargada"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Estación"], y=df["Tiempo_ciclo"],
        name="Tiempo de ciclo",
        marker_color=colors,
        text=[f"{ct:.3g}" for ct in df["Tiempo_ciclo"]],
        textposition="outside",
    ))
    fig.add_hline(
        y=result.takt,
        line=dict(color=GREEN, width=2.5, dash="dash"),
        annotation_text=f"Takt = {result.takt:.4g}",
        annotation_position="top right",
    )
    fig.add_trace(go.Bar(
        x=df["Estación"], y=df["Tiempo_ocioso"],
        name="Tiempo ocioso",
        marker_color=GRAY, opacity=0.45,
    ))

    fig.update_layout(
        barmode="stack",
        title=dict(
            text=title or f"Balance de línea — efic. {result.balance_efficiency:.1%}",
            font=dict(size=16),
        ),
        xaxis_title="Estación",
        yaxis_title="Tiempo",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=80, l=60, r=20, b=60),
    )
    return fig


# ---------------------------------------------------------------------------
# Break-even — revenue / cost lines
# ---------------------------------------------------------------------------

def plot_break_even(
    result: BreakEvenResult,
    *,
    title: str | None = None,
    unit_range_factor: float = 2.0,
) -> go.Figure:
    """Líneas de ingresos y costo total con el punto de equilibrio resaltado."""
    import numpy as np
    import plotly.graph_objects as go

    p   = result.params
    fc  = p["fixed_cost"]
    # break_even_sales() trabaja en ventas (no en unidades): precio 1 y costo variable = razón de costo variable.
    en_ventas = "price_per_unit" not in p
    if en_ventas:
        ppu, vcu, bep = 1.0, p["variable_cost_ratio"], result.bep_revenue
        actual = p.get("actual_revenue")
    else:
        ppu, vcu, bep = p["price_per_unit"], p["variable_cost_per_unit"], result.bep_units
        actual = p.get("actual_units")

    units = np.linspace(0, bep * unit_range_factor, 300)
    rev   = ppu * units
    cost  = fc + vcu * units

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=units, y=rev,  mode="lines", name="Ingresos",
                              line=dict(color=GREEN, width=2.5)))
    fig.add_trace(go.Scatter(x=units, y=cost, mode="lines", name="Costo total",
                              line=dict(color=RED, width=2.5)))
    fig.add_trace(go.Scatter(
        x=[bep], y=[result.bep_revenue],
        mode="markers+text",
        text=[f"PE ({bep:.0f} {'ventas' if en_ventas else 'unidades'})"],
        textposition="top right",
        marker=dict(color=ORANGE, size=12, symbol="star"),
        name="Punto de equilibrio",
    ))

    # Shade profit / loss regions
    fig.add_trace(go.Scatter(
        x=np.concatenate([units, units[::-1]]),
        y=np.concatenate([np.where(rev > cost, rev, cost),
                          np.where(rev > cost, cost, cost)[::-1]]),
        fill="toself", fillcolor="rgba(46,139,87,0.12)",
        line=dict(color="rgba(0,0,0,0)"), name="Zona de utilidad",
    ))

    if actual is not None:
        fig.add_vline(x=actual, line=dict(color=BLUE, width=1.5, dash="dot"),
                      annotation_text=f"Real ({actual:.0f})", annotation_position="top left")

    fig.update_layout(
        title=dict(text=title or "Análisis de punto de equilibrio", font=dict(size=16)),
        xaxis_title="Ventas" if en_ventas else "Unidades",
        yaxis_title="Monto",
        hovermode="x unified",
        margin=dict(t=80, l=60, r=20, b=60),
    )
    return fig


# ---------------------------------------------------------------------------
# EOQ — cost curves
# ---------------------------------------------------------------------------

def plot_eoq(
    result: EOQResult,
    *,
    title: str | None = None,
    figsize: tuple | None = None,
) -> plt.Figure:
    """Curvas de costo total, de mantener y de ordenar alrededor del EOQ."""
    import matplotlib.pyplot as plt
    import numpy as np

    p   = result.params
    D   = p["demand_rate"]
    K   = p["ordering_cost"]
    h   = p["holding_cost"]
    Q_star = result.eoq

    Q_range = np.linspace(Q_star * 0.1, Q_star * 3.0, 400)
    holding  = h * Q_range / 2.0
    ordering = K * D / Q_range
    total    = holding + ordering

    fig, ax = plt.subplots(figsize=figsize or (8, 5))
    ax.plot(Q_range, holding,  color=BLUE,   lw=2, label="Costo de mantener (hQ/2)")
    ax.plot(Q_range, ordering, color=ORANGE, lw=2, label="Costo de ordenar (KD/Q)")
    ax.plot(Q_range, total,    color=RED,    lw=2.5, label="Costo total")
    ax.axvline(Q_star, color=GREEN, ls="--", lw=1.5,
               label=f"EOQ = {Q_star:.4g}")
    ax.scatter([Q_star], [result.total_cost], color=GREEN, zorder=5, s=70)
    ax.set_xlabel("Cantidad de pedido Q")
    ax.set_ylabel("Costo por unidad de tiempo")
    ax.set_title(title or "EOQ — Curvas de costo", fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Queue-length PMF and sojourn CDF (MM1)
# ---------------------------------------------------------------------------

def plot_queue_distribution(
    pmf_df: pd.DataFrame,
    cdf_df: pd.DataFrame,
    *,
    title: str | None = None,
) -> go.Figure:
    """Gráfico de dos paneles: PMF de la longitud de la cola (barras) y FDA del tiempo de permanencia (línea)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=["P(N = n) — Longitud de la cola", "F(t) — FDA del tiempo de permanencia"])

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
        title=dict(text=title or "Distribuciones M/M/1", font=dict(size=16)),
        margin=dict(t=80, l=60, r=20, b=60),
    )
    fig.update_xaxes(title_text="n (clientes)", row=1, col=1)
    fig.update_xaxes(title_text="t (tiempo)", row=1, col=2)
    fig.update_yaxes(title_text="Probabilidad", row=1, col=1)
    fig.update_yaxes(title_text="F(t) / f(t)", row=1, col=2)
    return fig
