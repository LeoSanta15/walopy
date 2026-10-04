"""Modelos de colas avanzados, simulación, balance de línea y análisis de punto de equilibrio."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ._i18n import t as _t
from ._utils import (
    MAX_CLIENTES,
    MAX_ESTADOS,
    MAX_SERVIDORES,
    as_float_list,
    as_fraction,
    as_int_positive,
    as_nonempty,
    as_nonneg,
    as_positive,
)
from .queuing import QueueResult

if TYPE_CHECKING:
    import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Erlang B — M/M/c/c (loss system, no queue)
# ---------------------------------------------------------------------------

def erlang_b(lam: float, mu: float, c: int) -> float:
    """Fórmula Erlang B: probabilidad de bloqueo de un sistema de pérdida M/M/c/c.

    En un sistema de pérdida no hay sala de espera: los clientes que llegan y encuentran
    los *c* servidores ocupados se pierden (se bloquean).

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ por servidor.
    c : int
        Número de servidores (= capacidad del sistema).

    Returns
    -------
    float
        Probabilidad de bloqueo B(c, a) ∈ [0, 1].

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``c`` supera 10⁶.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = erlang_b(lam=2.0, mu=3.0, c=2)
    >>> round(r, 4)
    0.1176
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    c   = as_int_positive(c, "c", max=MAX_SERVIDORES)
    a = lam / mu  # offered traffic

    # Recursive formula (numerically stable for large c)
    B = 1.0
    for k in range(1, c + 1):
        B = (a * B) / (k + a * B)
    return B


# ---------------------------------------------------------------------------
# M/M/1/K — finite capacity queue
# ---------------------------------------------------------------------------

def mm1k(lam: float, mu: float, K: int) -> QueueResult:
    """Cola M/M/1/K: un servidor con sala de espera finita.

    La capacidad del sistema es *K* (servidor + cola). Los clientes que llegan cuando
    el sistema está lleno se pierden.

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ.
    K : int
        Capacidad del sistema (máximo de clientes en el sistema, ≥ 1).

    Returns
    -------
    QueueResult
        Nota: aquí ``rho`` es la intensidad de tráfico λ/μ (puede ser ≥ 1);
        el sistema siempre es estable por su capacidad finita.

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``K`` supera 10⁶.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = mm1k(lam=2.0, mu=3.0, K=5)
    >>> round(r.L, 4)
    1.4226
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    K   = as_int_positive(K, "K", max=MAX_ESTADOS)

    rho = lam / mu

    if abs(rho - 1.0) < 1e-12:
        # ρ = 1 special case
        P0 = 1.0 / (K + 1)
        Pn = [P0] * (K + 1)
    else:
        P0 = (1 - rho) / (1 - rho ** (K + 1))
        Pn = [P0 * rho**n for n in range(K + 1)]

    PK          = Pn[K]
    lam_eff     = lam * (1 - PK)               # effective arrival rate (non-blocked)
    L           = sum(n * Pn[n] for n in range(K + 1))
    Lq          = sum((n - 1) * Pn[n] for n in range(1, K + 1))
    W           = L / lam_eff  if lam_eff > 0 else float("inf")
    Wq          = Lq / lam_eff if lam_eff > 0 else float("inf")
    util        = 1 - Pn[0]    # fraction of time server is busy

    return QueueResult(
        model=_t("advanced.modelo.mm1k.texto", K=K),
        lam=lam,
        mu=mu,
        servers=1,
        rho=util,
        L=L,
        Lq=Lq,
        W=W,
        Wq=Wq,
        params={
            "K (capacidad)": K,
            "P0 (vacío)": Pn[0],
            "PK (prob. de bloqueo)": PK,
            "λ_eff (tasa efectiva)": lam_eff,
        },
    )


# ---------------------------------------------------------------------------
# Monte-Carlo simulation of a G/G/1 queue
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """Resultado de una simulación Monte Carlo G/G/1.

    Attributes
    ----------
    model : str
    lam, mu : float
    rho : float
    Wq_mean : float  Tiempo de espera promedio en cola.
    W_mean  : float  Tiempo de permanencia promedio.
    Lq : float  Longitud promedio de la cola (por la ley de Little).
    L  : float  Longitud promedio del sistema.
    Wq_p50, Wq_p90, Wq_p95, Wq_p99 : float  Percentiles de Wq.
    n_customers : int
    params : dict
    """

    model: str
    lam: float
    mu: float
    rho: float
    Wq_mean: float
    W_mean: float
    Lq: float
    L: float
    Wq_p50: float
    Wq_p90: float
    Wq_p95: float
    Wq_p99: float
    n_customers: int
    _Wq_array: np.ndarray = field(repr=False)
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "model": self.model,
            "λ": self.lam,
            "μ": self.mu,
            "ρ": self.rho,
            _t("advanced.cabecera.to_frame.wq_medio"): self.Wq_mean,
            _t("advanced.cabecera.to_frame.medio"): self.W_mean,
            "Lq": self.Lq,
            "L": self.L,
            _t("advanced.cabecera.to_frame.wq_p50"): self.Wq_p50,
            _t("advanced.cabecera.to_frame.wq_p90"): self.Wq_p90,
            _t("advanced.cabecera.to_frame.wq_p95"): self.Wq_p95,
            _t("advanced.cabecera.to_frame.wq_p99"): self.Wq_p99,
            _t("advanced.cabecera.to_frame.clientes"): self.n_customers,
        }])

    def summary(self) -> str:
        return (
            _t("advanced.etiqueta.summary.modelo_wq_medio_p50_p90", model=self.model, n_customers=self.n_customers, rho=self.rho, Wq_mean=self.Wq_mean, Wq_p50=self.Wq_p50, Wq_p90=self.Wq_p90, Wq_p95=self.Wq_p95, Wq_p99=self.Wq_p99, W_mean=self.W_mean, Lq=self.Lq, L=self.L)
        )

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> go.Figure:
        from .plotting import plot_simulation
        return plot_simulation(self, **kwargs)


def monte_carlo_gg1(
    lam: float,
    mu: float,
    ca2: float,
    cs2: float,
    *,
    n_customers: int = 20_000,
    seed: int | None = None,
) -> SimulationResult:
    """Simulación Monte Carlo de una cola G/G/1 de un servidor.

    Los tiempos entre llegadas y de servicio se extraen de distribuciones Gamma ajustadas
    a la media y al coeficiente de variación al cuadrado dados. Con CV² = 0 los tiempos son
    determinísticos; con CV² = 1 son exponenciales (se recupera el caso M/M/1).

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ (= 1 / tiempo medio de servicio).
    ca2 : float
        Coeficiente de variación al cuadrado de los tiempos entre llegadas (≥ 0).
    cs2 : float
        Coeficiente de variación al cuadrado de los tiempos de servicio (≥ 0).
    n_customers : int
        Número de clientes a simular (por defecto 20 000).
    seed : int, optional
        Semilla aleatoria para reproducibilidad.

    Returns
    -------
    SimulationResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el sistema es inestable (ρ ≥ 1).
        Si ``n_customers`` supera 10⁷.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = monte_carlo_gg1(lam=2.0, mu=3.0, ca2=1.0, cs2=1.0, n_customers=500, seed=1)
    >>> round(r.L, 4)
    2.0427
    """
    lam         = as_positive(lam, "lam")
    mu          = as_positive(mu, "mu")
    ca2         = as_nonneg(ca2, "ca2")
    cs2         = as_nonneg(cs2, "cs2")
    n_customers = as_int_positive(n_customers, "n_customers", max=MAX_CLIENTES)
    rho         = lam / mu
    if rho >= 1.0:
        raise ValueError(_t("advanced.error.monte_carlo_gg1.sistema_inestable", rho=rho))

    rng          = np.random.default_rng(seed)
    mean_ia      = 1.0 / lam
    mean_svc     = 1.0 / mu

    # Gamma(k, θ): mean = k·θ, CV² = 1/k  →  k = 1/cv², θ = mean·cv²
    def _gamma_sample(mean: float, cv2: float, size: int) -> np.ndarray:
        if cv2 < 1e-12:
            return np.full(size, mean)
        k = 1.0 / cv2
        return rng.gamma(shape=k, scale=mean * cv2, size=size)

    ia_times  = _gamma_sample(mean_ia, ca2, n_customers)
    svc_times = _gamma_sample(mean_svc, cs2, n_customers)

    arrival    = np.cumsum(ia_times)
    depart     = np.zeros(n_customers)
    wait       = np.zeros(n_customers)

    depart[0] = arrival[0] + svc_times[0]
    for i in range(1, n_customers):
        start      = max(arrival[i], depart[i - 1])
        wait[i]    = start - arrival[i]
        depart[i]  = start + svc_times[i]

    sojourn    = depart - arrival
    pct        = np.percentile(wait, [50, 90, 95, 99])

    return SimulationResult(
        model=_t("advanced.modelo.monte_carlo_gg1.simulacion_ca2_cs2", ca2=ca2, cs2=cs2),
        lam=lam,
        mu=mu,
        rho=rho,
        Wq_mean=float(wait.mean()),
        W_mean=float(sojourn.mean()),
        Lq=float(lam * wait.mean()),
        L=float(lam * sojourn.mean()),
        Wq_p50=float(pct[0]),
        Wq_p90=float(pct[1]),
        Wq_p95=float(pct[2]),
        Wq_p99=float(pct[3]),
        n_customers=n_customers,
        _Wq_array=wait,
        params={"ca2": ca2, "cs2": cs2, "seed": seed},
    )


# ---------------------------------------------------------------------------
# Takt time
# ---------------------------------------------------------------------------

def takt_time(available_time: float, demand: float) -> float:
    """Calcula el tiempo takt = tiempo de producción disponible / demanda del cliente.

    Parameters
    ----------
    available_time : float
        Tiempo neto de producción disponible en el periodo (mismas unidades que el
        resultado, p. ej. segundos o minutos).
    demand : float
        Número de unidades (o clientes) demandadas en el mismo periodo.

    Returns
    -------
    float
        Tiempo takt (tiempo por unidad).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = takt_time(available_time=480.0, demand=60.0)
    >>> round(r, 4)
    8.0
    """
    return as_positive(available_time, "available_time") / as_positive(demand, "demand")


# ---------------------------------------------------------------------------
# Line balance analysis
# ---------------------------------------------------------------------------

@dataclass
class LineBalanceResult:
    """Resultado del análisis de balance de una línea de producción.

    Attributes
    ----------
    takt : float
        Tiempo takt.
    n_stations : int
        Número de estaciones analizadas.
    balance_efficiency : float
        Suma de tiempos de ciclo / (n_stations × takt).
    theoretical_min_stations : int
        ceil(suma(tiempos de ciclo) / takt).
    stations : pd.DataFrame
        Métricas por estación: Estación, Tiempo_ciclo, Tiempo_ocioso, Utilización, Sobrecargada.
    bottleneck : str
        Estación con el mayor tiempo de ciclo.
    """

    takt: float
    n_stations: int
    balance_efficiency: float
    theoretical_min_stations: int
    stations: pd.DataFrame
    bottleneck: str
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            _t("advanced.etiqueta.summary.tiempo_takt_estaciones_minimo_teorico", takt=self.takt, n_stations=self.n_stations, theoretical_min_stations=self.theoretical_min_stations, balance_efficiency=self.balance_efficiency, bottleneck=self.bottleneck)
        )

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> go.Figure:
        from .plotting import plot_line_balance
        return plot_line_balance(self, **kwargs)


def line_balance(
    station_names: Sequence[str],
    cycle_times: Sequence[float],
    takt: float,
) -> LineBalanceResult:
    """Analiza el balance de una línea de producción o de servicio.

    Parameters
    ----------
    station_names : sequence of str
        Nombres de las estaciones.
    cycle_times : sequence of float
        Tiempo de ciclo real por estación.
    takt : float
        Tiempo takt (tiempo disponible / demanda).

    Returns
    -------
    LineBalanceResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = line_balance(station_names=['A', 'B'], cycle_times=[5.0, 9.0], takt=10.0)
    >>> round(r.balance_efficiency, 4)
    0.7
    """
    names  = list(station_names)
    as_nonempty(names, "station_names")
    cts    = [as_positive(ct, f"cycle_times[{i}]") for i, ct in enumerate(cycle_times)]
    takt   = as_positive(takt, "takt")
    n      = len(names)

    if len(cts) != n:
        raise ValueError(_t("advanced.error.line_balance.station_names_cycle_times_deben"))

    idle        = [max(takt - ct, 0.0) for ct in cts]
    utils       = [ct / takt for ct in cts]
    overloaded  = [ct > takt for ct in cts]
    sum_ct      = sum(cts)
    bn_idx      = int(np.argmax(cts))
    eff         = sum_ct / (n * takt)
    min_stat    = math.ceil(sum_ct / takt)

    df = pd.DataFrame({
        _t("columnas.columna_df.global.estacion"):    names,
        _t("columnas.columna_df.global.tiempo_ciclo"):  cts,
        _t("columnas.columna_df.global.tiempo_ocioso"):   idle,
        _t("columnas.columna_df.global.utilizacion"): utils,
        _t("columnas.columna_df.global.sobrecargada"): overloaded,
    })

    return LineBalanceResult(
        takt=takt,
        n_stations=n,
        balance_efficiency=eff,
        theoretical_min_stations=min_stat,
        stations=df,
        bottleneck=names[bn_idx],
    )


# ---------------------------------------------------------------------------
# Break-even analysis
# ---------------------------------------------------------------------------

@dataclass
class BreakEvenResult:
    """Resultado del análisis de punto de equilibrio.

    Attributes
    ----------
    bep_units : float
        Volumen de equilibrio en unidades.
    bep_revenue : float
        Ingresos en el punto de equilibrio.
    contribution_margin : float
        Precio − costo variable por unidad.
    contribution_margin_ratio : float
        Margen de contribución / precio.
    margin_of_safety_units : float
        Unidades reales − unidades de equilibrio (si se indica actual_units).
    margin_of_safety_pct : float
        Margen de seguridad como fracción de las unidades reales.
    params : dict
    """

    bep_units: float
    bep_revenue: float
    contribution_margin: float
    contribution_margin_ratio: float
    margin_of_safety_units: float = 0.0
    margin_of_safety_pct: float = 0.0
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{
            _t("advanced.cabecera.to_frame.pe_unidades"): self.bep_units,
            _t("advanced.cabecera.to_frame.pe_ingresos"): self.bep_revenue,
            _t("advanced.cabecera.to_frame.margen_contribucion"): self.contribution_margin,
            _t("advanced.cabecera.to_frame.razon_mc"): self.contribution_margin_ratio,
            _t("advanced.cabecera.to_frame.margen_seguridad_unidades"): self.margin_of_safety_units,
            _t("advanced.cabecera.to_frame.margen_seguridad"): self.margin_of_safety_pct,
        }])

    def summary(self) -> str:
        lines = [
            _t("advanced.etiqueta.summary.punto_equilibrio_unidades", bep_units=self.bep_units),
            _t("advanced.etiqueta.summary.punto_equilibrio_ingresos", bep_revenue=self.bep_revenue),
            _t("advanced.etiqueta.summary.margen_contribucion", contribution_margin=self.contribution_margin),
            _t("advanced.etiqueta.summary.razon_contribucion", contribution_margin_ratio=self.contribution_margin_ratio),
        ]
        if self.margin_of_safety_units:
            lines.append(_t("advanced.etiqueta.summary.margen_seguridad_unidades", margin_of_safety_units=self.margin_of_safety_units, margin_of_safety_pct=self.margin_of_safety_pct))
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> go.Figure:
        from .plotting import plot_break_even
        return plot_break_even(self, **kwargs)


def break_even(
    fixed_cost: float,
    price_per_unit: float,
    variable_cost_per_unit: float,
    *,
    actual_units: float | None = None,
) -> BreakEvenResult:
    """Calcula el punto de equilibrio y el margen de contribución.

    Parameters
    ----------
    fixed_cost : float
        Costo fijo total del periodo.
    price_per_unit : float
        Precio de venta por unidad.
    variable_cost_per_unit : float
        Costo variable por unidad.
    actual_units : float, optional
        Volumen real de producción o ventas (para calcular el margen de seguridad).

    Returns
    -------
    BreakEvenResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el precio no supera al costo variable unitario.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = break_even(fixed_cost=1000.0, price_per_unit=10.0, variable_cost_per_unit=4.0)
    >>> round(r.bep_units, 4)
    166.6667
    """
    fixed_cost             = as_positive(fixed_cost, "fixed_cost")
    price_per_unit         = as_positive(price_per_unit, "price_per_unit")
    variable_cost_per_unit = as_nonneg(variable_cost_per_unit, "variable_cost_per_unit")

    cm  = price_per_unit - variable_cost_per_unit
    if cm <= 0:
        raise ValueError(_t("advanced.error.break_even.price_per_unit_debe_superar"))

    cmr       = cm / price_per_unit
    bep_units = fixed_cost / cm
    bep_rev   = bep_units * price_per_unit

    mos_units = 0.0
    mos_pct   = 0.0
    params: dict = {
        "fixed_cost": fixed_cost,
        "price_per_unit": price_per_unit,
        "variable_cost_per_unit": variable_cost_per_unit,
    }
    if actual_units is not None:
        actual_units = as_positive(actual_units, "actual_units")
        mos_units = actual_units - bep_units
        mos_pct   = mos_units / actual_units
        params["actual_units"] = actual_units

    return BreakEvenResult(
        bep_units=bep_units,
        bep_revenue=bep_rev,
        contribution_margin=cm,
        contribution_margin_ratio=cmr,
        margin_of_safety_units=mos_units,
        margin_of_safety_pct=mos_pct,
        params=params,
    )


# ---------------------------------------------------------------------------
# Multi-product break-even
# ---------------------------------------------------------------------------

@dataclass
class BreakEvenMultiResult:
    """Resultado del punto de equilibrio con varios productos.

    Attributes
    ----------
    bep_units_total : float
        Volumen de equilibrio total (todos los productos combinados).
    bep_revenue_total : float
        Ingresos de equilibrio totales.
    weighted_avg_cm : float
        Margen de contribución promedio ponderado por unidad.
    cm_ratio_weighted : float
        Razón de MC ponderada = MCP / precio promedio ponderado.
    items : list[dict]
        Por producto: Producto, Precio, Costo variable, MC, Mezcla,
        PE unidades, PE ingresos.
    params : dict
    """

    bep_units_total: float
    bep_revenue_total: float
    weighted_avg_cm: float
    cm_ratio_weighted: float
    items: list
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.items)

    def summary(self) -> str:
        lines = [
            _t("advanced.etiqueta.summary.punto_equilibrio_unidades_totales", bep_units_total=self.bep_units_total),
            _t("advanced.etiqueta.summary.punto_equilibrio_ingresos_totales", bep_revenue_total=self.bep_revenue_total),
            _t("advanced.etiqueta.summary.mc_ponderado_promedio", weighted_avg_cm=self.weighted_avg_cm),
            _t("advanced.etiqueta.summary.razon_mc_ponderada", cm_ratio_weighted=self.cm_ratio_weighted),
            "",
            f"{_t('advanced.texto_en_expresion.summary.producto'):<18} {_t('advanced.texto_en_expresion.summary.precio'):>8} {_t('advanced.texto_en_expresion.summary.cv'):>8} {_t('advanced.texto_en_expresion.summary.mc'):>8} {_t('advanced.texto_en_expresion.summary.mezcla'):>6} {_t('advanced.texto_en_expresion.summary.pe_unid'):>10} {_t('advanced.texto_en_expresion.summary.pe_ingr'):>10}",
            "-" * 72,
        ]
        for row in self.items:
            lines.append(
                f"{row[_t('columnas.columna_df.global.producto')]:<18} {row[_t('columnas.columna_df.global.precio')]:>8.4g} {row[_t('columnas.columna_df.global.costo_variable')]:>8.4g} {row['MC']:>8.4g} {row[_t('columnas.columna_df.global.mezcla')]:>6.2%} {row[_t('columnas.columna_df.global.pe_unidades')]:>10.4g} {row[_t('columnas.columna_df.global.pe_ingresos')]:>10.4g}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def break_even_multi(
    fixed_cost: float,
    prices: Sequence[float],
    variable_costs: Sequence[float],
    sales_mix: Sequence[float],
    *,
    names: Sequence[str] | None = None,
) -> BreakEvenMultiResult:
    """Punto de equilibrio con varios productos y mezcla de ventas.

    Usa el margen de contribución promedio ponderado (MCP) para hallar el volumen de
    equilibrio total y luego lo reparte según la mezcla de ventas.

    PE_total = CF / MCP
    PE_i     = PE_total × mezcla_i

    Parameters
    ----------
    fixed_cost : float
        Costo fijo total del periodo.
    prices : sequence of float
        Precio de venta por unidad de cada producto.
    variable_costs : sequence of float
        Costo variable por unidad de cada producto.
    sales_mix : sequence of float
        Proporciones relativas de venta (no necesitan sumar 1; se normalizan internamente).
    names : sequence of str, optional
        Nombres de los productos.

    Returns
    -------
    BreakEvenMultiResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si algún producto tiene margen de contribución no positivo o una secuencia está vacía o las secuencias tienen longitudes distintas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = break_even_multi(
    ...     fixed_cost=120_000,
    ...     prices=[50, 80, 120],
    ...     variable_costs=[30, 50, 70],
    ...     sales_mix=[3, 2, 1],
    ... )
    >>> r.bep_units_total > 0
    True
    """
    prices         = as_float_list(prices, "prices")
    variable_costs = as_float_list(variable_costs, "variable_costs", kind="nonneg")
    sales_mix      = as_float_list(sales_mix, "sales_mix", kind="nonneg")
    n = len(prices)
    if len(variable_costs) != n or len(sales_mix) != n:
        raise ValueError(_t("advanced.error.break_even_multi.prices_variable_costs_sales_mix"))
    if names is None:
        names = [_t("advanced.valor_por_defecto.break_even_multi.producto", expr=i + 1) for i in range(n)]
    elif len(list(names)) != n:
        raise ValueError(_t("advanced.error.break_even_multi.names_debe_tener_misma_longitud"))
    fixed_cost = as_positive(fixed_cost, "fixed_cost")

    total_mix = sum(sales_mix)
    if total_mix <= 0:
        raise ValueError(_t("advanced.error.break_even_multi.suma_sales_mix_debe_ser"))
    mix_frac = [m / total_mix for m in sales_mix]

    cms = [p - v for p, v in zip(prices, variable_costs)]
    if any(cm <= 0 for cm in cms):
        raise ValueError(_t("advanced.error.break_even_multi.todos_productos_deben_tener_margen"))

    wacm     = sum(cm * mf for cm, mf in zip(cms, mix_frac))
    avg_price = sum(p * mf for p, mf in zip(prices, mix_frac))
    bep_total = fixed_cost / wacm
    bep_rev_total = sum(bep_total * mix_frac[i] * prices[i] for i in range(n))

    items = []
    for i in range(n):
        bep_i = bep_total * mix_frac[i]
        items.append({
            _t("columnas.columna_df.global.producto"): names[i],
            _t("columnas.columna_df.global.precio"): prices[i],
            _t("columnas.columna_df.global.costo_variable"): variable_costs[i],
            "MC": cms[i],
            _t("columnas.columna_df.global.mezcla"): mix_frac[i],
            _t("columnas.columna_df.global.pe_unidades"): bep_i,
            _t("columnas.columna_df.global.pe_ingresos"): bep_i * prices[i],
        })

    return BreakEvenMultiResult(
        bep_units_total=bep_total,
        bep_revenue_total=bep_rev_total,
        weighted_avg_cm=wacm,
        cm_ratio_weighted=wacm / avg_price,
        items=items,
        params={"fixed_cost": fixed_cost, "n_products": n},
    )


def break_even_sales(
    fixed_cost: float,
    variable_cost_ratio: float,
    *,
    actual_revenue: float | None = None,
) -> BreakEvenResult:
    """Punto de equilibrio expresado como ingresos por ventas.

    Usa la razón de margen de contribución (RMC) cuando los costos se dan como fracción
    de los ingresos y no por unidad.

    PE_ventas = CF / RMC = CF / (1 − variable_cost_ratio)

    Parameters
    ----------
    fixed_cost : float
        Costo fijo total del periodo.
    variable_cost_ratio : float
        Costos variables como fracción de los ingresos ∈ (0, 1)  (p. ej. 0.60 significa
        que los costos variables son el 60 % de cada peso vendido).
    actual_revenue : float, optional
        Ingresos reales para calcular el margen de seguridad.

    Returns
    -------
    BreakEvenResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``variable_cost_ratio`` no está estrictamente entre 0 y 1.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = break_even_sales(fixed_cost=50_000, variable_cost_ratio=0.60)
    >>> r.bep_revenue
    125000.0
    """
    fc  = as_positive(fixed_cost, "fixed_cost")
    vcr = as_fraction(variable_cost_ratio, "variable_cost_ratio")
    if vcr == 0.0 or vcr == 1.0:
        raise ValueError(_t("advanced.error.break_even_sales.variable_cost_ratio_debe_estar"))

    cmr       = 1.0 - vcr
    bep_sales = fc / cmr

    mos_units = 0.0
    mos_pct   = 0.0
    params: dict = {"fixed_cost": fc, "variable_cost_ratio": vcr}
    if actual_revenue is not None:
        actual_revenue = as_positive(actual_revenue, "actual_revenue")
        mos_units = actual_revenue - bep_sales
        mos_pct   = mos_units / actual_revenue
        params["actual_revenue"] = actual_revenue

    return BreakEvenResult(
        bep_units=math.nan,          # not meaningful in revenue-based form
        bep_revenue=bep_sales,
        contribution_margin=math.nan,
        contribution_margin_ratio=cmr,
        margin_of_safety_units=mos_units,
        margin_of_safety_pct=mos_pct,
        params=params,
    )


# ---------------------------------------------------------------------------
# Queue length PMF and sojourn CDF for M/M/1
# ---------------------------------------------------------------------------

def queue_length_pmf(lam: float, mu: float, n_max: int = 30) -> pd.DataFrame:
    """Función de masa de probabilidad del número de clientes en un sistema M/M/1.

    P(N = n) = (1 − ρ) · ρ^n

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ.
    n_max : int
        Longitud máxima de cola a calcular (por defecto 30).

    Returns
    -------
    pd.DataFrame
        Columnas: ``n``, ``P(N=n)``, ``P(N<=n)``.

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el sistema es inestable (ρ ≥ 1).
        Si ``n_max`` no es un entero entre 0 y 10⁶.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = queue_length_pmf(lam=2.0, mu=3.0, n_max=10)
    >>> r.shape
    (11, 3)
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    rho = lam / mu
    if rho >= 1.0:
        raise ValueError(_t("advanced.error.monte_carlo_gg1.sistema_inestable", rho=rho))
    if isinstance(n_max, bool) or not isinstance(n_max, (int, np.integer)):
        raise TypeError(_t("advanced.error.queue_length_pmf.max_debe_ser_entero_recibio", __name__=type(n_max).__name__))
    if not 0 <= n_max <= MAX_ESTADOS:
        raise ValueError(_t("advanced.error.queue_length_pmf.max_debe_estar_entre_recibio", MAX_ESTADOS=MAX_ESTADOS, n_max=n_max))
    ns    = np.arange(0, n_max + 1)
    pmf   = (1 - rho) * rho**ns
    return pd.DataFrame({"n": ns, _t("columnas.columna_df.global.texto_2"): pmf, _t("columnas.columna_df.global.texto"): np.cumsum(pmf)})


def sojourn_cdf(lam: float, mu: float, t_max: float | None = None, n_points: int = 200) -> pd.DataFrame:
    """FDA del tiempo de permanencia (tiempo en el sistema) de una cola M/M/1.

    F(t) = 1 − exp(−(μ − λ)·t)

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ.
    t_max : float, optional
        Cota superior del eje de tiempo (por defecto 5 × tiempo medio de permanencia).
    n_points : int
        Número de puntos de evaluación.

    Returns
    -------
    pd.DataFrame
        Columnas: ``t``, ``F(t)`` (FDA), ``f(t)`` (densidad).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el sistema es inestable (ρ ≥ 1).
        Si ``n_points`` supera 10⁶ o ``t_max`` no es positivo.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = sojourn_cdf(lam=2.0, mu=3.0, n_points=20)
    >>> r.shape
    (20, 3)
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    rho = lam / mu
    if rho >= 1.0:
        raise ValueError(_t("advanced.error.monte_carlo_gg1.sistema_inestable", rho=rho))
    n_points = as_int_positive(n_points, "n_points", max=MAX_ESTADOS)
    W_mean = 1.0 / (mu - lam)
    t_upper = as_positive(t_max, "t_max") if t_max is not None else 5.0 * W_mean
    t       = np.linspace(0, t_upper, n_points)
    rate    = mu - lam
    cdf     = 1.0 - np.exp(-rate * t)
    pdf     = rate * np.exp(-rate * t)
    return pd.DataFrame({"t": t, _t("columnas.columna_df.global.texto_3"): cdf, _t("columnas.columna_df.global.texto_4"): pdf})


# ---------------------------------------------------------------------------
# M/M/c/K — multi-server finite capacity queue
# ---------------------------------------------------------------------------

def mmck(lam: float, mu: float, c: int, K: int) -> QueueResult:
    """Cola M/M/c/K: *c* servidores y capacidad del sistema *K* (incluidos los servidores).

    Los clientes que llegan cuando el sistema está lleno se bloquean (se pierden).
    El sistema siempre es estable, sea cual sea ρ, por su capacidad finita.

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ por servidor.
    c : int
        Número de servidores (≥ 1).
    K : int
        Capacidad del sistema (máximo de clientes en el sistema, ≥ c).

    Returns
    -------
    QueueResult
        ``rho`` es la utilización del servidor λ_eff / (c · μ).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``K < c`` o ``c``/``K`` superan 10⁶.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = mmck(lam=2.0, mu=3.0, c=2, K=5)
    >>> round(r.L, 4)
    0.7381
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    c   = as_int_positive(c, "c", max=MAX_SERVIDORES)
    K   = as_int_positive(K, "K", max=MAX_ESTADOS)
    if K < c:
        raise ValueError(_t("advanced.error.mmck.capacidad_sistema_debe_ser_servidores", K=K, c=c))

    a   = lam / mu           # offered load

    # Unnormalised state probabilities:
    #   p_n = a^n / n!          for n = 0 … c
    #   p_n = a^n / (c! c^(n-c)) for n = c+1 … K
    log_fact_c = sum(math.log(k) for k in range(1, c + 1))  # log(c!)

    def _log_p(n: int) -> float:
        if n <= c:
            return n * math.log(a) - sum(math.log(k) for k in range(1, n + 1))
        return n * math.log(a) - log_fact_c - (n - c) * math.log(c)

    # Normalise in log-space for numerical stability
    log_ps = [_log_p(n) for n in range(K + 1)]
    max_lp = max(log_ps)
    ps     = [math.exp(lp - max_lp) for lp in log_ps]
    Z      = sum(ps)
    Pn     = [p / Z for p in ps]

    PK      = Pn[K]
    lam_eff = lam * (1 - PK)
    L       = sum(n * Pn[n] for n in range(K + 1))
    Lq      = sum((n - c) * Pn[n] for n in range(c, K + 1))
    W       = L / lam_eff  if lam_eff > 0 else float("inf")
    Wq      = Lq / lam_eff if lam_eff > 0 else float("inf")
    util    = lam_eff / (c * mu)  # effective server utilization

    return QueueResult(
        model=_t("advanced.modelo.mmck.texto", c=c, K=K),
        lam=lam, mu=mu, servers=c,
        rho=util, L=L, Lq=Lq, W=W, Wq=Wq,
        params={
            "K (capacidad)": K,
            "P0 (vacío)": Pn[0],
            "PK (prob. de bloqueo)": PK,
            "λ_eff (tasa efectiva)": lam_eff,
        },
    )


# ---------------------------------------------------------------------------
# M/M/1 non-preemptive Head-of-Line priority queue
# ---------------------------------------------------------------------------

@dataclass
class PriorityQueueResult:
    """Resultado del análisis de una cola con prioridades HOL no expropiativas.

    Cada entrada de *classes* es un diccionario con las claves:
    ``class_id``, ``lam``, ``rho``, ``Wq``, ``W``, ``Lq``, ``L``.

    Attributes
    ----------
    classes : list[dict]
        Métricas por clase en orden de prioridad (clase 0 = mayor prioridad).
    rho_total : float
        Utilización total del servidor = suma(λ_k) / μ.
    mu : float
        Tasa de servicio.
    """

    classes: list[dict]
    rho_total: float
    mu: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.classes).rename(
            columns={"class_id": _t("advanced.cabecera.to_frame.id_clase"), "lam": "λ", "rho": "ρ"}
        )

    def summary(self) -> str:
        lines = [
            _t("advanced.etiqueta.summary.prioridad_hol_expropiativa", mu=self.mu, rho_total=self.rho_total),
            f"{_t('advanced.texto_en_expresion.summary.clase'):>6}  {'λ':>10}  {'ρ':>8}  {_t('advanced.texto_en_expresion.summary.wq'):>12}  {_t('advanced.texto_en_expresion.summary.texto_2'):>12}  {_t('advanced.texto_en_expresion.summary.lq'):>10}  {_t('advanced.texto_en_expresion.summary.texto'):>10}",
            "-" * 72,
        ]
        for cl in self.classes:
            lines.append(
                f"{cl['class_id']:>6}  {cl['lam']:>10.4g}  {cl['rho']:>8.4f}  "
                f"{cl['Wq']:>12.6g}  {cl['W']:>12.6g}  {cl['Lq']:>10.4g}  {cl['L']:>10.4g}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def mm1_priority(
    lam_list: Sequence[float],
    mu: float,
    *,
    class_names: Sequence[str] | None = None,
) -> PriorityQueueResult:
    """Cola M/M/1 con prioridades Head-of-Line (HOL) no expropiativas.

    La clase 0 tiene la mayor prioridad; la clase N−1 la menor. El servicio es FCFS dentro de
    cada clase y no expropiativo (un cliente de menor prioridad en servicio no se interrumpe).

    La fórmula (Kleinrock, 1975):

    .. code-block:: text

        Wq_k = R / ((1 − σ_{k−1}) · (1 − σ_k))
        donde R = ρ / μ,  σ_k = Σ_{i=0}^{k} λ_i / μ,  σ_{−1} = 0.

    Parameters
    ----------
    lam_list : sequence of float
        Tasas de llegada λ_k de cada clase en orden *descendente* de prioridad
        (índice 0 = mayor prioridad).
    mu : float
        Tasa de servicio μ (el mismo servidor exponencial para todas las clases).
    class_names : sequence of str, optional
        Etiquetas de las clases de prioridad. Por defecto '0', '1', …

    Returns
    -------
    PriorityQueueResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el sistema es inestable (ρ ≥ 1).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = mm1_priority([2.0, 1.0], mu=5.0)
    >>> r.classes[0]['Wq'] < r.classes[1]['Wq']   # high priority waits less
    True
    """
    lams = [as_positive(l, f"lam_list[{i}]") for i, l in enumerate(lam_list)]
    mu   = as_positive(mu, "mu")
    N    = len(lams)
    if N == 0:
        raise ValueError(_t("advanced.error.mm1_priority.lam_list_debe_contener_menos"))

    rho_total = sum(lams) / mu
    if rho_total >= 1.0:
        raise ValueError(_t("advanced.error.mm1_priority.sistema_inestable_total", rho_total=rho_total))

    names = list(class_names) if class_names else [str(i) for i in range(N)]
    if len(names) != N:
        raise ValueError(_t("advanced.error.mm1_priority.class_names_debe_tener_misma"))

    # Residual service time for M/M/1 (exponential, cv²=1): R = ρ/μ
    R = rho_total / mu

    # Partial utilizations: sigma[k] = sum_{i=0}^{k} rho_i
    rhos   = [l / mu for l in lams]
    sigmas = [sum(rhos[:k + 1]) for k in range(N)]  # sigma[k]

    classes = []
    for k in range(N):
        s_prev = sigmas[k - 1] if k > 0 else 0.0
        s_k    = sigmas[k]
        Wq_k   = R / ((1 - s_prev) * (1 - s_k))
        W_k    = Wq_k + 1.0 / mu
        Lq_k   = lams[k] * Wq_k
        L_k    = lams[k] * W_k
        classes.append({
            "class_id": names[k],
            "lam": lams[k],
            "rho": rhos[k],
            "Wq": Wq_k,
            "W": W_k,
            "Lq": Lq_k,
            "L": L_k,
        })

    return PriorityQueueResult(
        classes=classes,
        rho_total=rho_total,
        mu=mu,
        params={"N_clases": N, "R (residual)": R},
    )
