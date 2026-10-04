"""Todas las funciones de gráficas de walopy. Matplotlib y Plotly se importan de forma perezosa."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ._i18n import columna
from ._i18n import t as _t

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
        (axes[0], Wq_curve, result.Wq, _t("plotting.grafica.plot_queue_sensitivity.wq_espera_media_cola"), "Wq"),
        (axes[1], Lq_curve, result.Lq, _t("plotting.grafica.plot_queue_sensitivity.lq_longitud_media_cola"), "Lq"),
    ]:
        ax.plot(rho_range, y_curve, color=BLUE, lw=2, label=_t("plotting.grafica.plot_queue_sensitivity.curva", label=label))
        ax.axvline(result.rho, color=ORANGE, ls="--", lw=1.5, label=f"ρ = {result.rho:.3f}")
        ax.scatter([result.rho], [y_point], color=RED, zorder=5, s=60)
        ax.set_xlabel(_t("plotting.grafica.plot_queue_sensitivity.utilizacion"))
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.25)

    fig.suptitle(title or _t("plotting.grafica.plot_queue_sensitivity.sensibilidad_cola", model=result.model), fontweight="bold")
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
    ax.set_ylabel(_t("plotting.grafica.plot_queue_metrics.valor"))
    ax.set_title(title or _t("plotting.grafica.plot_queue_metrics.resumen_kpi", model=result.model), fontweight="bold")
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

    labels = [_t("plotting.grafica.plot_oee.disponibilidad"), _t("plotting.grafica.plot_oee.rendimiento"), _t("plotting.grafica.plot_oee.calidad"), "OEE"]
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
    ax.axvline(0.85, color=GRAY, ls="--", lw=1, label=_t("plotting.grafica.plot_oee.clase_mundial_85"))
    ax.set_xlabel(_t("plotting.grafica.plot_oee.valor_factor"))
    ax.legend(fontsize=8)
    ax.set_title(title or _t("plotting.grafica.plot_oee.descomposicion_oee"), fontweight="bold")
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
    ax.axhline(1.0, color=RED, ls="--", lw=1.2, label=_t("plotting.grafica.plot_bottleneck.limite_capacidad"))
    ax.set_ylim(0, max(1.1, max(utils) * 1.1))
    ax.set_ylabel(_t("plotting.grafica.plot_bottleneck.utilizacion"))
    ax.legend(fontsize=8)
    ax.set_title(title or _t("plotting.grafica.plot_bottleneck.cuello_botella", bottleneck=result.bottleneck), fontweight="bold")
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
        formula_str = _t("plotting.grafica.collect.br_2", formula=node.formula) if node.formula else ""
        hover.append(_t("plotting.grafica.collect.br", name=node.name, value=node.value, unit_str=unit_str, formula_str=formula_str))
        for child in node.children:
            _collect(child, node_id)

    _collect(root)

    chart_title = title or _t("plotting.grafica.plot_kpi_tree.arbol_kpi", name=root.name)

    if kind == "sunburst":
        trace = go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            customdata=hover,
            hovertemplate=_t("plotting.grafica.plot_kpi_tree.customdata_extra_extra"),
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
            hovertemplate=_t("plotting.grafica.plot_kpi_tree.customdata_extra_extra"),
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
        title=dict(text=title or _t("plotting.grafica.plot_sensitivity.sensibilidad", param=param), font=dict(size=16)),
        xaxis_title=param,
        yaxis_title=_t("plotting.grafica.plot_queue_metrics.valor"),
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
        name=_t("plotting.grafica.plot_optimize_servers.costo_servidores"), marker_color=BLUE, opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        x=df["c"], y=df["wait_cost"],
        name=_t("plotting.grafica.plot_optimize_servers.costo_espera"), marker_color=ORANGE, opacity=0.8,
    ))
    fig.add_trace(go.Scatter(
        x=df["c"], y=df["total_cost"],
        mode="lines+markers", name=_t("plotting.grafica.plot_optimize_servers.costo_total"),
        line=dict(color=RED, width=2.5),
        marker=dict(size=7),
    ))
    fig.add_vline(
        x=result.optimal_servers,
        line=dict(color=GREEN, width=2, dash="dash"),
        annotation_text=_t("plotting.grafica.plot_optimize_servers.optimo", optimal_servers=result.optimal_servers),
        annotation_position="top right",
    )

    fig.update_layout(
        barmode="stack",
        title=dict(text=title or _t("plotting.grafica.plot_optimize_servers.optimizacion_costo_servidores"), font=dict(size=16)),
        xaxis_title=_t("plotting.grafica.plot_optimize_servers.numero_servidores"),
        yaxis_title=_t("plotting.grafica.plot_optimize_servers.costo_unidad_tiempo"),
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
    fig  = make_subplots(rows=1, cols=2, subplot_titles=[_t("plotting.grafica.plot_simulation.distribucion_wq"), _t("plotting.grafica.plot_simulation.fda_wq")])

    # Histogram
    counts, edges = __import__("numpy").histogram(Wq, bins=n_bins)
    midpoints = 0.5 * (edges[:-1] + edges[1:])
    fig.add_trace(go.Bar(x=midpoints, y=counts, name=_t("plotting.grafica.plot_simulation.wq"),
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
                              name=_t("plotting.grafica.plot_simulation.fda_empirica"),
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
    fig.update_xaxes(title_text=_t("plotting.grafica.plot_simulation.wq_tiempo_espera"), row=1, col=1)
    fig.update_xaxes(title_text=_t("plotting.grafica.plot_simulation.wq_tiempo_espera"), row=1, col=2)
    fig.update_yaxes(title_text=_t("plotting.grafica.plot_simulation.frecuencia"), row=1, col=1)
    fig.update_yaxes(title_text=_t("plotting.grafica.plot_simulation.probabilidad_acumulada"), row=1, col=2)
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
    colors = [RED if ov else BLUE for ov in df[columna(df, "columnas.columna_df.global.sobrecargada")]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[columna(df, "columnas.columna_df.global.estacion")], y=df[columna(df, "columnas.columna_df.global.tiempo_ciclo")],
        name=_t("plotting.grafica.plot_line_balance.tiempo_ciclo"),
        marker_color=colors,
        text=[f"{ct:.3g}" for ct in df[columna(df, "columnas.columna_df.global.tiempo_ciclo")]],
        textposition="outside",
    ))
    fig.add_hline(
        y=result.takt,
        line=dict(color=GREEN, width=2.5, dash="dash"),
        annotation_text=_t("plotting.grafica.plot_line_balance.takt", takt=result.takt),
        annotation_position="top right",
    )
    fig.add_trace(go.Bar(
        x=df[columna(df, "columnas.columna_df.global.estacion")], y=df[columna(df, "columnas.columna_df.global.tiempo_ocioso")],
        name=_t("plotting.grafica.plot_line_balance.tiempo_ocioso"),
        marker_color=GRAY, opacity=0.45,
    ))

    fig.update_layout(
        barmode="stack",
        title=dict(
            text=title or _t("plotting.grafica.plot_line_balance.balance_linea_efic", balance_efficiency=result.balance_efficiency),
            font=dict(size=16),
        ),
        xaxis_title=_t("plotting.grafica.plot_line_balance.estacion"),
        yaxis_title=_t("plotting.grafica.plot_line_balance.tiempo"),
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
    fig.add_trace(go.Scatter(x=units, y=rev,  mode="lines", name=_t("plotting.grafica.plot_break_even.ingresos"),
                              line=dict(color=GREEN, width=2.5)))
    fig.add_trace(go.Scatter(x=units, y=cost, mode="lines", name=_t("plotting.grafica.plot_optimize_servers.costo_total"),
                              line=dict(color=RED, width=2.5)))
    fig.add_trace(go.Scatter(
        x=[bep], y=[result.bep_revenue],
        mode="markers+text",
        text=[_t("plotting.grafica.plot_break_even.pe", bep=bep, expr=_t('plotting.texto_en_expresion.plot_break_even.ventas') if en_ventas else _t('plotting.texto_en_expresion.plot_break_even.unidades'))],
        textposition="top right",
        marker=dict(color=ORANGE, size=12, symbol="star"),
        name=_t("plotting.grafica.plot_break_even.punto_equilibrio"),
    ))

    # Shade profit / loss regions
    fig.add_trace(go.Scatter(
        x=np.concatenate([units, units[::-1]]),
        y=np.concatenate([np.where(rev > cost, rev, cost),
                          np.where(rev > cost, cost, cost)[::-1]]),
        fill="toself", fillcolor="rgba(46,139,87,0.12)",
        line=dict(color="rgba(0,0,0,0)"), name=_t("plotting.grafica.plot_break_even.zona_utilidad"),
    ))

    if actual is not None:
        fig.add_vline(x=actual, line=dict(color=BLUE, width=1.5, dash="dot"),
                      annotation_text=_t("plotting.grafica.plot_break_even.real", actual=actual), annotation_position="top left")

    fig.update_layout(
        title=dict(text=title or _t("plotting.grafica.plot_break_even.analisis_punto_equilibrio"), font=dict(size=16)),
        xaxis_title=_t("plotting.grafica.plot_break_even.ventas") if en_ventas else _t("plotting.grafica.plot_break_even.unidades"),
        yaxis_title=_t("plotting.grafica.plot_break_even.monto"),
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
    ax.plot(Q_range, holding,  color=BLUE,   lw=2, label=_t("plotting.grafica.plot_eoq.costo_mantener_hq"))
    ax.plot(Q_range, ordering, color=ORANGE, lw=2, label=_t("plotting.grafica.plot_eoq.costo_ordenar_kd"))
    ax.plot(Q_range, total,    color=RED,    lw=2.5, label=_t("plotting.grafica.plot_optimize_servers.costo_total"))
    ax.axvline(Q_star, color=GREEN, ls="--", lw=1.5,
               label=_t("plotting.grafica.plot_eoq.eoq", Q_star=Q_star))
    ax.scatter([Q_star], [result.total_cost], color=GREEN, zorder=5, s=70)
    ax.set_xlabel(_t("plotting.grafica.plot_eoq.cantidad_pedido"))
    ax.set_ylabel(_t("plotting.grafica.plot_optimize_servers.costo_unidad_tiempo"))
    ax.set_title(title or _t("plotting.grafica.plot_eoq.eoq_curvas_costo"), fontweight="bold")
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
                        subplot_titles=[_t("plotting.grafica.plot_queue_distribution.longitud_cola"), _t("plotting.grafica.plot_queue_distribution.fda_tiempo_permanencia")])

    fig.add_trace(go.Bar(x=pmf_df["n"], y=pmf_df[columna(pmf_df, "columnas.columna_df.global.texto_2")],
                          name=_t("plotting.grafica.plot_queue_distribution.texto_3"), marker_color=BLUE, opacity=0.8), row=1, col=1)
    fig.add_trace(go.Scatter(x=pmf_df["n"], y=pmf_df[columna(pmf_df, "columnas.columna_df.global.texto")],
                              mode="lines+markers", name=_t("plotting.grafica.plot_queue_distribution.nn"),
                              line=dict(color=ORANGE, width=2)), row=1, col=1)

    fig.add_trace(go.Scatter(x=cdf_df["t"], y=cdf_df[columna(cdf_df, "columnas.columna_df.global.texto_3")],
                              mode="lines", name=_t("plotting.grafica.plot_queue_distribution.texto"),
                              line=dict(color=GREEN, width=2.5)), row=1, col=2)
    fig.add_trace(go.Scatter(x=cdf_df["t"], y=cdf_df[columna(cdf_df, "columnas.columna_df.global.texto_4")],
                              mode="lines", name=_t("plotting.grafica.plot_queue_distribution.texto_4"),
                              line=dict(color=TEAL, width=1.5, dash="dot"),
                              yaxis="y3"), row=1, col=2)

    fig.update_layout(
        title=dict(text=title or _t("plotting.grafica.plot_queue_distribution.distribuciones"), font=dict(size=16)),
        margin=dict(t=80, l=60, r=20, b=60),
    )
    fig.update_xaxes(title_text=_t("plotting.grafica.plot_queue_distribution.clientes"), row=1, col=1)
    fig.update_xaxes(title_text=_t("plotting.grafica.plot_queue_distribution.tiempo"), row=1, col=2)
    fig.update_yaxes(title_text=_t("plotting.grafica.plot_queue_distribution.probabilidad"), row=1, col=1)
    fig.update_yaxes(title_text=_t("plotting.grafica.plot_queue_distribution.texto_2"), row=1, col=2)
    return fig
