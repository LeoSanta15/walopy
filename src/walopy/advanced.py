"""Modelos de colas avanzados, simulación, balance de línea y análisis de punto de equilibrio."""
from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ._i18n import columna
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
    t_cuantil_975,
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
    n_replications: int = 1
    warmup: int = 0
    Wq_halfwidth: float | None = None

    @property
    def Wq_ci(self) -> tuple[float, float] | None:
        """Intervalo de confianza al 95 % de Wq (``Wq_mean`` ± semiancho), o ``None`` si no hay datos suficientes."""
        if self.Wq_halfwidth is None:
            return None
        return (self.Wq_mean - self.Wq_halfwidth, self.Wq_mean + self.Wq_halfwidth)

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
            _t("advanced.cabecera.to_frame.replicas"): self.n_replications,
            _t("advanced.cabecera.to_frame.calentamiento"): self.warmup,
            _t("advanced.cabecera.to_frame.semiancho_wq"): self.Wq_halfwidth,
        }])

    def summary(self) -> str:
        texto = _t("advanced.etiqueta.summary.modelo_wq_medio_p50_p90", model=self.model, n_customers=self.n_customers, rho=self.rho, Wq_mean=self.Wq_mean, Wq_p50=self.Wq_p50, Wq_p90=self.Wq_p90, Wq_p95=self.Wq_p95, Wq_p99=self.Wq_p99, W_mean=self.W_mean, Lq=self.Lq, L=self.L)
        if self.Wq_halfwidth is not None:
            texto += "\n" + _t("advanced.etiqueta.summary.ic_wq", semiancho=self.Wq_halfwidth, replicas=self.n_replications, calentamiento=self.warmup)
        return texto

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> go.Figure:
        from .plotting import plot_simulation
        return plot_simulation(self, **kwargs)


LOTES_MC = 20             # lotes para el intervalo de confianza de Wq cuando hay una sola réplica (medias de lotes)
PRECISION_RELATIVA_MC = 0.10  # avisar si el semiancho al 95 % supera el 10 % de Wq
MAX_REPLICAS = 10_000


def monte_carlo_gg1(
    lam: float,
    mu: float,
    ca2: float,
    cs2: float,
    *,
    n_customers: int = 20_000,
    seed: int | None = None,
    n_replications: int = 1,
    warmup: int = 0,
) -> SimulationResult:
    """Simulación Monte Carlo de una cola G/G/1 de un servidor.

    Los tiempos entre llegadas y de servicio se extraen de distribuciones Gamma ajustadas
    a la media y al coeficiente de variación al cuadrado dados. Con CV² = 0 los tiempos son
    determinísticos; con CV² = 1 son exponenciales (se recupera el caso M/M/1).

    El sistema empieza vacío, así que Wq se subestima al principio (sesgo de arranque, notable con ρ alto). Una sola réplica,
    además, puede alejarse mucho del valor esperado. Para resultados fiables use varias réplicas independientes
    (``n_replications``) y descarte el periodo de calentamiento (``warmup``); el resultado trae el semiancho del intervalo de
    confianza al 95 % de Wq (``Wq_halfwidth``, ``Wq_ci``).

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
        Número de clientes a simular por réplica (por defecto 20 000).
    seed : int, optional
        Semilla aleatoria para reproducibilidad. Con varias réplicas se derivan flujos independientes de ella.
    n_replications : int
        Réplicas independientes (por defecto 1). Con 2 o más, el intervalo de confianza de Wq usa la t de Student sobre las
        medias de las réplicas; con 1 se estima por medias de 20 lotes.
    warmup : int
        Clientes iniciales de cada réplica que se descartan de las estadísticas (por defecto 0). Con ρ cercano a 1 el
        arranque en vacío sesga Wq a la baja durante del orden de 1/(1 − ρ)² clientes; descarte varias veces esa cantidad
        y mantenga ``n_customers`` mucho mayor.

    Returns
    -------
    SimulationResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el sistema es inestable (ρ ≥ 1).
        Si ``n_customers`` o ``n_customers × n_replications`` superan 10⁷, si ``n_replications`` supera 10 000 o si
        ``warmup`` no es un entero entre 0 y ``n_customers`` − 1.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = monte_carlo_gg1(lam=2.0, mu=3.0, ca2=1.0, cs2=1.0, n_customers=50_000, seed=1)
    >>> round(r.L, 4)
    2.0169
    >>> r = monte_carlo_gg1(lam=2.0, mu=3.0, ca2=1.0, cs2=1.0, n_customers=5_000, seed=1, n_replications=10, warmup=500)
    >>> r.n_replications, r.Wq_halfwidth < 0.2
    (10, True)
    """
    lam         = as_positive(lam, "lam")
    mu          = as_positive(mu, "mu")
    ca2         = as_nonneg(ca2, "ca2")
    cs2         = as_nonneg(cs2, "cs2")
    n_customers = as_int_positive(n_customers, "n_customers", max=MAX_CLIENTES)
    n_rep       = as_int_positive(n_replications, "n_replications", max=MAX_REPLICAS)
    if n_customers * n_rep > MAX_CLIENTES:
        raise ValueError(_t("advanced.error.monte_carlo_gg1.demasiados_clientes_total", total=n_customers * n_rep, max=MAX_CLIENTES))
    if isinstance(warmup, str):
        raise ValueError(_t("advanced.error.monte_carlo_gg1.warmup_invalido", n=n_customers))
    valor = as_nonneg(warmup, "warmup")
    if valor != int(valor) or valor >= n_customers:
        raise ValueError(_t("advanced.error.monte_carlo_gg1.warmup_invalido", n=n_customers))
    calentamiento = int(valor)
    rho         = lam / mu
    if rho >= 1.0:
        raise ValueError(_t("advanced.error.monte_carlo_gg1.sistema_inestable", rho=rho))

    mean_ia      = 1.0 / lam
    mean_svc     = 1.0 / mu
    # Una réplica con ``seed`` reproduce exactamente el flujo de siempre; con varias, flujos independientes derivados de la semilla
    rngs = [np.random.default_rng(seed)] if n_rep == 1 else [np.random.default_rng(c) for c in np.random.SeedSequence(seed).spawn(n_rep)]

    def _replica(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
        # Gamma(k, θ): mean = k·θ, CV² = 1/k  →  k = 1/cv², θ = mean·cv²
        def _gamma_sample(mean: float, cv2: float, size: int) -> np.ndarray:
            if cv2 < 1e-12:
                return np.full(size, mean)
            k = 1.0 / cv2
            return rng.gamma(shape=k, scale=mean * cv2, size=size)

        ia_times  = _gamma_sample(mean_ia, ca2, n_customers)
        svc_times = _gamma_sample(mean_svc, cs2, n_customers)
        arrival   = np.cumsum(ia_times)
        depart    = np.zeros(n_customers)
        wait      = np.zeros(n_customers)
        depart[0] = arrival[0] + svc_times[0]
        for i in range(1, n_customers):
            start      = max(arrival[i], depart[i - 1])
            wait[i]    = start - arrival[i]
            depart[i]  = start + svc_times[i]
        return wait, depart - arrival

    esperas: list[np.ndarray] = []
    permanencias: list[np.ndarray] = []
    for rng in rngs:
        wait_r, sojourn_r = _replica(rng)
        esperas.append(wait_r[calentamiento:])
        permanencias.append(sojourn_r[calentamiento:])

    wait    = np.concatenate(esperas)
    medias_wq = np.array([float(w.mean()) for w in esperas])
    wq_mean = float(medias_wq.mean())
    w_mean  = float(np.mean([float(x.mean()) for x in permanencias]))
    pct     = np.percentile(wait, [50, 90, 95, 99])

    # Intervalo de confianza al 95 % de Wq: t de Student sobre las medias de las réplicas o, con una sola, sobre medias de lotes
    semiancho: float | None = None
    if n_rep >= 2:
        semiancho = t_cuantil_975(n_rep - 1) * float(medias_wq.std(ddof=1)) / math.sqrt(n_rep)
    elif len(esperas[0]) >= LOTES_MC:
        lotes = esperas[0][: len(esperas[0]) - len(esperas[0]) % LOTES_MC].reshape(LOTES_MC, -1).mean(axis=1)
        semiancho = t_cuantil_975(LOTES_MC - 1) * float(lotes.std(ddof=1)) / math.sqrt(LOTES_MC)
    if semiancho is not None and wq_mean > 0 and semiancho > PRECISION_RELATIVA_MC * wq_mean:
        warnings.warn(
            _t("advanced.aviso.monte_carlo_gg1.estimacion_imprecisa", wq=wq_mean, semiancho=semiancho,
               relativo=semiancho / wq_mean, n=n_customers, replicas=n_rep),
            UserWarning, stacklevel=2,
        )

    return SimulationResult(
        model=_t("advanced.modelo.monte_carlo_gg1.simulacion_ca2_cs2", ca2=ca2, cs2=cs2),
        lam=lam,
        mu=mu,
        rho=rho,
        Wq_mean=wq_mean,
        W_mean=w_mean,
        Lq=float(lam * wq_mean),
        L=float(lam * w_mean),
        Wq_p50=float(pct[0]),
        Wq_p90=float(pct[1]),
        Wq_p95=float(pct[2]),
        Wq_p99=float(pct[3]),
        n_customers=n_customers,
        _Wq_array=wait,
        params={"ca2": ca2, "cs2": cs2, "seed": seed},
        n_replications=n_rep,
        warmup=calentamiento,
        Wq_halfwidth=semiancho,
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
                f"{row[columna(row, 'columnas.columna_df.global.producto')]:<18} {row[columna(row, 'columnas.columna_df.global.precio')]:>8.4g} {row[columna(row, 'columnas.columna_df.global.costo_variable')]:>8.4g} {row['MC']:>8.4g} {row[columna(row, 'columnas.columna_df.global.mezcla')]:>6.2%} {row[columna(row, 'columnas.columna_df.global.pe_unidades')]:>10.4g} {row[columna(row, 'columnas.columna_df.global.pe_ingresos')]:>10.4g}"
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
# Erlang A — M/M/c+M (abandono de clientes impacientes)
# ---------------------------------------------------------------------------

def _distribucion_erlang_a(lam: float, mu: float, theta: float, c: int) -> np.ndarray:
    """Probabilidades estacionarias p_n (n = 0, 1, …) de M/M/c+M, normalizadas y truncadas donde la cola ya no pesa.

    Es un proceso de nacimiento y muerte: llegadas λ; muertes nμ para n ≤ c y cμ + (n − c)θ para n > c. Se calcula en logaritmos
    (los pesos pueden ser enormes o minúsculos) y se amplía por tramos hasta que la cola es despreciable.
    """
    n = np.arange(1, c + 1)
    lw = np.concatenate(([0.0], np.cumsum(np.log(lam) - np.log(n * mu))))
    tramos = [lw]
    ultimo, k_ini, max_lw = lw[-1], 0, float(lw.max())
    largo = max(64, c)
    while True:
        k = np.arange(k_ini + 1, k_ini + largo + 1, dtype=float)
        log_r = math.log(lam) - np.log(c * mu + k * theta)
        tramo = ultimo + np.cumsum(log_r)
        tramos.append(tramo)
        max_lw = max(max_lw, float(tramo.max()))
        ultimo, k_ini = float(tramo[-1]), k_ini + largo
        if log_r[-1] < 0.0 and ultimo < max_lw - 50.0:
            break
        if k_ini >= MAX_ESTADOS:
            raise ValueError(_t("advanced.error.erlang_a.demasiados_estados", max=MAX_ESTADOS))
        largo *= 2
    lw_todo = np.concatenate(tramos)
    pesos = np.exp(lw_todo - lw_todo.max())
    return pesos / pesos.sum()


def _indicadores_erlang_a(lam: float, mu: float, theta: float, c: int) -> dict[str, float]:
    """Indicadores exactos de M/M/c+M a partir de la distribución estacionaria (PASTA: quien llega ve el estado estacionario).

    Un cliente que llega y encuentra k clientes en cola ocupa la posición j = k + 1: avanza a tasa cμ + (j − 1)θ (alguien delante
    se atiende o abandona) y abandona a tasa θ. Con R_j = cμ + jθ salen en forma recursiva, todas con términos positivos,
    la probabilidad de atenderse S_j = cμ/R_j, la espera acumulada de los atendidos U_j y la de los que abandonan V_j.
    """
    p = _distribucion_erlang_a(lam, mu, theta, c)
    q = p[c:]                                    # q[k] = P(el sistema tiene c + k clientes)
    cmu = c * mu
    j = np.arange(1, len(q) + 1, dtype=float)
    R = cmu + j * theta                          # tasa total de salida de la posición j
    adv = cmu + (j - 1.0) * theta                # tasa de avance de la posición j
    S_prev = np.concatenate(([1.0], cmu / R[:-1]))          # S_{j-1}
    aband = j * theta / R                         # 1 − S_j (sin cancelación)
    U = np.zeros_like(R)
    V = np.zeros_like(R)
    u_prev = v_prev = 0.0
    for i in range(len(R)):
        r, a = R[i], adv[i]
        u_prev = (a / r) * (S_prev[i] / r + u_prev)
        v_prev = theta / (r * r) + (a / r) * ((1.0 - S_prev[i]) / r + v_prev)
        U[i], V[i] = u_prev, v_prev
    k = np.arange(len(q), dtype=float)
    Lq = float((k * q).sum())
    p_espera = float(q.sum())
    p_aband = float((q * aband).sum())
    wq_atendidos = float((q * U).sum()) / (1.0 - p_aband)
    wq_abandonos = float((q * V).sum()) / p_aband if p_aband > 0.0 else 0.0
    return {"Lq": Lq, "p_espera": p_espera, "p_aband": p_aband, "wq_atendidos": wq_atendidos, "wq_abandonos": wq_abandonos}


def erlang_a(lam: float, mu: float, theta: float, c: int) -> QueueResult:
    """Cola M/M/c+M (Erlang A): *c* servidores y clientes impacientes que abandonan la fila.

    Cada cliente en espera abandona a tasa θ (paciencia exponencial de media 1/θ); quien ya está en servicio no abandona. A diferencia de
    ``mmc``, el sistema es estable aunque λ ≥ c·μ, porque las salidas por abandono compensan: es el modelo habitual de centros de contacto. Es
    exacto (nacimiento y muerte), no una aproximación. Con θ → 0 tiende a ``mmc`` (si ρ < 1) y con θ grande, a ``erlang_b``.

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ por servidor.
    theta : float
        Tasa de abandono θ de cada cliente en espera (1/θ = paciencia media).
    c : int
        Número de servidores (≥ 1).

    Returns
    -------
    QueueResult
        ``rho`` es la utilización λ_eff/(c·μ). ``Lq``/``Wq`` cuentan a todos los que llegan (también a los que abandonan) y ``L``/``W``
        cumplen la ley de Little con λ. En ``params`` están P(esperar), P(abandono), la tasa de clientes atendidos y la espera media de
        quienes se atienden y de quienes abandonan.

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``c`` supera 10⁶ o la cola esperada necesita más de 10⁶ estados (λ/θ demasiado grande).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = erlang_a(lam=10.0, mu=1.0, theta=0.5, c=8)
    >>> round(r.params["P(abandono)"], 4)
    0.2272
    >>> round(r.rho, 4)
    0.966
    """
    lam   = as_positive(lam, "lam")
    mu    = as_positive(mu, "mu")
    theta = as_positive(theta, "theta")
    c     = as_int_positive(c, "c", max=MAX_SERVIDORES)
    ind   = _indicadores_erlang_a(lam, mu, theta, c)
    lam_eff = lam * (1.0 - ind["p_aband"])
    Lq    = ind["Lq"]
    Wq    = Lq / lam
    L     = Lq + lam_eff / mu
    return QueueResult(
        model=_t("advanced.modelo.erlang_a.texto", c=c),
        lam=lam, mu=mu, servers=c,
        rho=lam_eff / (c * mu), L=L, Lq=Lq, W=L / lam, Wq=Wq,
        params={
            "θ (tasa de abandono)": theta,
            "P(esperar)": ind["p_espera"],
            "P(abandono)": ind["p_aband"],
            "λ_eff (tasa atendida)": lam_eff,
            "Wq atendidos": ind["wq_atendidos"],
            "Wq abandonos": ind["wq_abandonos"],
        },
    )


def _nivel_servicio_cola(q: np.ndarray, libre: float, cmu: float, theta: float, t: float) -> float:
    """Fracción atendida esperando como máximo *t* (t > 0) para una clase con paciencia θ, dado q[k] = P(llega y hay k de su clase en cola).

    Quien llega a la posición j = k + 1 espera θ·T = −ln B con B ~ Beta(cμ/θ, j); con *j* entero la beta incompleta es una suma finita de
    términos positivos. ``libre`` es la probabilidad de encontrar un servidor libre (espera nula).
    """
    J = len(q)
    j = np.arange(1, J + 1, dtype=float)
    a1 = cmu / theta                             # a' = cμ/θ
    k = np.arange(1, J, dtype=float)
    # I_x(a'+1, j) = x^(a'+1) Σ_{k<j} (a'+1)_k/k! (1−x)^k, con x = e^(−θt); acumulada en logaritmos
    log_uno_menos_x = math.log(-math.expm1(-theta * t))
    log_term = -(a1 + 1.0) * theta * t + np.concatenate(([0.0], np.cumsum(np.log((a1 + k) / k)))) + np.arange(J) * log_uno_menos_x
    I = np.minimum(np.cumsum(np.exp(log_term)), 1.0)
    g = (a1 / (a1 + j)) * (1.0 - I)              # P(atenderse esperando ≤ t | posición j)
    return float(min(libre + float((q * g).sum()), 1.0))


def erlang_a_service_level(lam: float, mu: float, theta: float, c: int, t: float) -> float:
    """Nivel de servicio de M/M/c+M: fracción de las llegadas que se atienden esperando como máximo *t*.

    Es la medida habitual de un centro de contacto (p. ej. «80 % atendidas en 20 segundos»). Los clientes que abandonan antes de *t*
    **no** cuentan como atendidos. El cálculo es exacto: la espera de un cliente en la posición *j* es la de una cola con salidas a tasa
    cμ + iθ, y θ·T = −ln B con B ~ Beta(cμ/θ, j); con *j* entero la distribución beta incompleta es una suma finita de términos positivos.

    Parameters
    ----------
    lam, mu, theta, c
        Igual que en ``erlang_a``.
    t : float
        Tiempo máximo de espera (≥ 0, en las mismas unidades de tiempo que 1/λ).

    Returns
    -------
    float
        Fracción en [0, 1 − P(abandono)]. Con ``t = 0`` es la fracción que no espera; al crecer *t* tiende a 1 − P(abandono).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo, o ``t`` negativo).
        Si ``c`` supera 10⁶ o la cola esperada necesita más de 10⁶ estados.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> round(erlang_a_service_level(lam=10.0, mu=1.0, theta=0.5, c=8, t=0.0), 4)
    0.1302
    >>> round(erlang_a_service_level(lam=10.0, mu=1.0, theta=0.5, c=8, t=2.0), 4)
    0.7715
    """
    lam   = as_positive(lam, "lam")
    mu    = as_positive(mu, "mu")
    theta = as_positive(theta, "theta")
    c     = as_int_positive(c, "c", max=MAX_SERVIDORES)
    t     = as_nonneg(t, "t")
    p     = _distribucion_erlang_a(lam, mu, theta, c)
    libre = float(p[:c].sum())                   # llegan y encuentran un servidor libre
    if t == 0.0:
        return libre
    return _nivel_servicio_cola(p[c:], libre, c * mu, theta, t)


def erlang_a_servers(
    lam: float,
    mu: float,
    theta: float,
    *,
    max_abandon: float | None = None,
    max_wait_prob: float | None = None,
    min_service_level: float | None = None,
    t: float | None = None,
    c_max: int = 10_000,
) -> QueueResult:
    """Mínimo número de servidores de M/M/c+M que cumple los objetivos pedidos (todos a la vez).

    Parameters
    ----------
    lam, mu, theta
        Igual que en ``erlang_a``.
    max_abandon : float, optional
        Máxima probabilidad de abandono permitida, en (0, 1).
    max_wait_prob : float, optional
        Máxima probabilidad de tener que esperar, en (0, 1).
    min_service_level : float, optional
        Mínimo nivel de servicio (fracción atendida esperando ≤ *t*), en (0, 1). Requiere ``t``.
    t : float, optional
        Tiempo de espera del nivel de servicio (≥ 0); solo se usa con ``min_service_level``.
    c_max : int
        Cota superior de servidores a considerar (por defecto 10 000).

    Returns
    -------
    QueueResult
        El resultado de ``erlang_a`` con el menor *c* que cumple todos los objetivos.

    Raises
    ------
    ValueError
        Si no se indica ningún objetivo, si ``min_service_level`` se da sin ``t``, si un objetivo está fuera de (0, 1) o
        si ni con ``c_max`` servidores se cumplen. También los de ``erlang_a``.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = erlang_a_servers(lam=10.0, mu=1.0, theta=0.5, max_abandon=0.02)
    >>> r.servers, round(r.params["P(abandono)"], 4)
    (14, 0.0125)
    """
    lam   = as_positive(lam, "lam")
    mu    = as_positive(mu, "mu")
    theta = as_positive(theta, "theta")
    c_max = as_int_positive(c_max, "c_max", max=MAX_SERVIDORES)
    objetivos = {"max_abandon": max_abandon, "max_wait_prob": max_wait_prob, "min_service_level": min_service_level}
    for nombre, valor in objetivos.items():
        if valor is not None:
            v = as_fraction(valor, nombre)
            if v <= 0.0 or v >= 1.0:
                raise ValueError(_t("advanced.error.erlang_a_servers.objetivo_entre_0_1", nombre=nombre))
    if all(v is None for v in objetivos.values()):
        raise ValueError(_t("advanced.error.erlang_a_servers.sin_objetivo"))
    if min_service_level is not None:
        if t is None:
            raise ValueError(_t("advanced.error.erlang_a_servers.nivel_servicio_requiere_t"))
        t = as_nonneg(t, "t")

    def cumple(c: int) -> bool:
        ind = _indicadores_erlang_a(lam, mu, theta, c)
        if max_abandon is not None and ind["p_aband"] > max_abandon:
            return False
        if max_wait_prob is not None and ind["p_espera"] > max_wait_prob:
            return False
        if min_service_level is not None and erlang_a_service_level(lam, mu, theta, c, t or 0.0) < min_service_level:
            return False
        return True

    # Los tres indicadores mejoran al añadir servidores: se busca por duplicación y bisección.
    hi = 1
    while not cumple(hi):
        if hi >= c_max:
            raise ValueError(_t("advanced.error.erlang_a_servers.inalcanzable", c_max=c_max))
        hi = min(2 * hi, c_max)
    lo = hi // 2 if hi > 1 else 0
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cumple(mid):
            hi = mid
        else:
            lo = mid
    return erlang_a(lam, mu, theta, hi)


# ---------------------------------------------------------------------------
# Erlang A con dos clases y prioridad — M/M/c+M, prioridad no expropiativa
# ---------------------------------------------------------------------------

MAX_ELEMENTOS_PRIORIDAD = 3 * 10**7      # ≈ 2√Q·m² elementos de matrices guardadas (m = fases): ≈ 8 bytes por elemento
MAX_COSTE_CLASES = 10**11                # Q·m³: operaciones de la reducción por niveles (≈ 15 s en el peor caso)
TOL_FRONTERA = 1e-10                     # masa máxima tolerada en la frontera del truncamiento (error relativo de los indicadores ≲ 1e-8)
MAX_PASOS_UNIFORMIZACION = 400_000       # iteraciones del nivel de servicio de las clases de menor prioridad
MAX_CELDAS_PASOS = 6 * 10**9             # estados de la cadena de espera × iteraciones
MAX_CLASES = 6
INICIO_ALTAS, INICIO_BAJA = 6, 12        # truncamiento inicial: suma de las colas altas y cola de la clase de menor prioridad


def _gth(tasas: np.ndarray) -> np.ndarray:
    """Distribución estacionaria de una cadena continua a partir de sus tasas fuera de la diagonal (algoritmo GTH: solo sumas de positivos)."""
    A = np.maximum(tasas, 0.0)                    # las inversas pueden traer −1e-20 de redondeo: son tasas, no negativas
    n = A.shape[0]
    s = np.zeros(n)
    for k in range(n - 1, 0, -1):
        s[k] = A[k, :k].sum()
        A[:k, :k] += np.outer(A[:k, k], A[k, :k]) / s[k]
    # sustitución hacia atrás en logaritmos: los pesos pueden crecer como (λ/θ)^k/k! y desbordarían
    log_pi = np.zeros(n)
    with np.errstate(divide="ignore"):
        log_A = np.log(A)
    for k in range(1, n):
        terminos = log_pi[:k] + log_A[:k, k]
        mx = float(terminos.max())
        log_pi[k] = mx + math.log(float(np.exp(terminos - mx).sum())) - math.log(s[k])
    pi = np.exp(log_pi - log_pi.max())
    return pi / pi.sum()


def _siguiente_tamano(q: int, q_previo: int | None, f: float, f_previo: float | None, factor: float, cota: int) -> int:
    """Siguiente tamaño de una dimensión del truncamiento, dada la masa *f* en su frontera con el tamaño *q*.

    Por defecto multiplica por ``factor``. Si hay un tamaño anterior con más masa en la frontera, extrapola el decaimiento geométrico de esa masa hasta
    ``TOL_FRONTERA`` (con un 30 % de margen) y toma el menor de los dos: evita pasarse por poco de la tolerancia y resolver una malla mucho mayor.
    """
    nuevo = max(q + 1, int(math.ceil(factor * q)))
    if q_previo is not None and f_previo is not None and q > q_previo and 0.0 < f < f_previo:
        tasa = math.log(f_previo / f) / (q - q_previo)
        extrapolado = q + int(math.ceil(1.3 * math.log(f / TOL_FRONTERA) / tasa)) + 1
        nuevo = min(nuevo, max(q + 1, extrapolado))
    return min(nuevo, cota)


def _fases_simplex(n_altas: int, s_max: int) -> list[tuple[int, ...]]:
    """Todas las tuplas (q₀, …, q_{n−1}) de enteros ≥ 0 con q₀ + … + q_{n−1} ≤ s_max, en orden lexicográfico."""
    if n_altas == 0:
        return [()]
    return [(v,) + resto for v in range(s_max + 1) for resto in _fases_simplex(n_altas - 1, s_max - v)]


def _estacionaria_clases_truncada(lams: Sequence[float], ths: Sequence[float], mu: float, c: int, s_max: int, q_bajo: int) -> tuple[np.ndarray, np.ndarray]:
    """Distribución estacionaria de M/M/c+M con K clases y prioridad (0 = la mayor), μ común, con las colas de las K − 1 clases altas sumando a lo más
    ``s_max`` y la de la clase de menor prioridad a lo más ``q_bajo``.

    Estado: *b* < c servidores ocupados sin cola, o b = c con (q₀, …, q_{K−1}) en cola; como μ es común, qué clase hay en servicio no importa. Se resuelve
    por niveles de la cola de la clase de menor prioridad, con las colas de las clases altas como fases (un símplex de C(s_max + K − 1, K − 1) fases; la
    masa conjunta de las colas altas se concentra ahí, y una caja por clase desperdicia casi todo): hacia arriba λ_K·I y hacia abajo la diagonal
    θ_K·k + cμ·[fase vacía] (si no hay cola de las clases altas, el servicio libre atiende a la de menor prioridad), de modo que la reducción por bloques
    solo invierte matrices del tamaño del símplex. Los estados b < c salen de un corte de flujo (λ·π_{c−1} = cμ·π(c; 0, …, 0)) y de un nacimiento y muerte
    (Erlang B), sin matrices de tamaño c. Devuelve (p_b, p[q₀, …, q_{K−1}]), con p = 0 fuera del símplex.
    """
    n_altas = len(lams) - 1
    cmu = c * mu
    fases = _fases_simplex(n_altas, s_max)
    ind = {q: i for i, q in enumerate(fases)}
    m = len(fases)
    lam_bajo, th_bajo = lams[-1], ths[-1]
    T = np.zeros((m, m))
    for q, p in ind.items():
        primera = -1
        for i in range(n_altas):
            if sum(q) < s_max:
                T[p, ind[q[:i] + (q[i] + 1,) + q[i + 1:]]] += lams[i]          # llega uno de la clase i
            if q[i] > 0:
                T[p, ind[q[:i] + (q[i] - 1,) + q[i + 1:]]] += ths[i] * q[i]    # abandona uno de la clase i
                if primera < 0:
                    primera = i
        if primera >= 0:
            T[p, ind[q[:primera] + (q[primera] - 1,) + q[primera + 1:]]] += cmu   # el servicio libre atiende a la primera clase con cola
    cero = ind[(0,) * n_altas]                                                    # = 0: la primera fase del orden lexicográfico
    idx = np.arange(m)

    def bajada(k: int) -> np.ndarray:
        d = np.full(m, th_bajo * k)
        d[cero] += cmu                                                  # fase vacía: el servicio libre atiende a la clase baja
        return d

    def retroceder(n_arriba: np.ndarray, k: int) -> np.ndarray:
        """N_k = (−G_k)⁻¹ a partir de N_{k+1}, con G_k = T + λ_K·N_{k+1}·D_{k+1} (D diagonal) y la diagonal por filas, sin restas."""
        G = T + lam_bajo * n_arriba * bajada(k + 1)[None, :]
        G[idx, idx] = 0.0
        G[idx, idx] = -(bajada(k) + G.sum(axis=1))
        return np.linalg.inv(-G)

    G = T.copy()                                                        # techo: sin subida de nivel
    G[idx, idx] = -(bajada(q_bajo) + T.sum(axis=1))
    # Solo se guardan las N de unos puntos de control (cada ≈ √Q niveles): el recorrido hacia arriba recalcula las demás por tramos. Así la memoria es
    # ≈ 2√Q matrices en vez de Q (con Q·m² grande, la diferencia entre caber o no), a cambio de ≈ el doble de tiempo.
    tramo = max(1, math.isqrt(q_bajo))
    N_act = np.linalg.inv(-G)
    puntos = {q_bajo: N_act}
    for k in range(q_bajo - 1, 0, -1):
        N_act = retroceder(N_act, k)
        if k % tramo == 0:
            puntos[k] = N_act
    # nivel 0 censurado (los estados b < c se resuelven aparte): el paso (0, …, 0) → b < c vuelve a (0, …, 0) con probabilidad 1
    A = T.copy()
    if q_bajo >= 1:
        A += lam_bajo * N_act * bajada(1)[None, :]                      # N_act = N_1
    x0 = _gth(A)
    # recorrido hacia arriba: los niveles altos pueden pesar órdenes de magnitud más que el 0 (colas largas), así que cada nivel se reescala
    niveles = np.zeros((q_bajo + 1, m))
    log_escala = np.zeros(q_bajo + 1)
    niveles[0] = x0
    k = 1
    for fin in sorted(puntos):
        seg = {fin: puntos[fin]}
        for j in range(fin - 1, k - 1, -1):
            seg[j] = retroceder(seg[j + 1], j)
        for j in range(k, fin + 1):
            v = lam_bajo * niveles[j - 1] @ seg[j]
            suma = float(v.sum())
            niveles[j] = v / suma
            log_escala[j] = log_escala[j - 1] + math.log(suma)
        k = fin + 1
    peso = np.exp(log_escala - log_escala.max())
    niveles = np.maximum(niveles * peso[:, None], 0.0)                  # escala común; x(0, …, 0) = niveles[0, 0]
    # estados b < c: π_{c−1} = cμ·x(0, …, 0)/λ y π_{b−1} = (b·μ/λ)·π_b, en logaritmos (con λ ≪ c·μ los pesos son diminutos)
    lam = float(sum(lams))
    paso = np.log(np.arange(c - 1, 0, -1) * mu / lam) if c > 1 else np.zeros(0)
    log_r = np.concatenate(([0.0], np.cumsum(paso)))                    # log(π_{c−1−i}/π_{c−1}), i = 0 … c−1
    log_pb = math.log(max(float(niveles[0, cero]), 1e-300)) + math.log(cmu / lam) + log_r
    mx = max(float(log_pb.max()), math.log(float(niveles.sum())))
    pb_rel = np.exp(log_pb - mx)[::-1]                                  # índice b = 0 … c − 1
    niv_rel = niveles * math.exp(-mx)
    total = float(pb_rel.sum() + niv_rel.sum())
    niv = np.zeros((s_max + 1,) * n_altas + (q_bajo + 1,))
    for q, p in ind.items():
        niv[q] = niv_rel[:, p] / total
    return pb_rel / total, niv


def _estacionaria_clases(lams: Sequence[float], ths: Sequence[float], mu: float, c: int) -> tuple[np.ndarray, np.ndarray]:
    """Distribución estacionaria de M/M/c+M con K clases y prioridad, ampliando el truncamiento hasta que la masa en el borde es despreciable.

    La cola total es estocásticamente menor que la de Erlang A con Σλ y la menor de las pacientes θ, y eso acota las colas de todas las clases. Se amplían
    por separado la suma de las colas altas (×1,25) y la cola de la clase baja (×2) mientras la masa en su frontera supere ``TOL_FRONTERA``.
    """
    n_altas = len(lams) - 1
    q = _distribucion_erlang_a(float(sum(lams)), mu, min(ths), c)[c:]
    cola = np.cumsum(q[::-1])[::-1]                  # P(cola ≥ k)
    cota = max(int(np.argmax(cola < 1e-13)) if (cola < 1e-13).any() else len(cola), 4)
    s_max, q_bajo = min(INICIO_ALTAS, cota), min(INICIO_BAJA, cota)
    previo_s = previo_q = None                       # (tamaño, masa en la frontera) de la solución anterior, para extrapolar
    while True:
        fases = math.comb(s_max + n_altas, n_altas)
        matrices = q_bajo // max(1, math.isqrt(q_bajo)) + 1 + math.isqrt(q_bajo)      # puntos de control + el tramo que se recalcula
        if matrices * fases**2 > MAX_ELEMENTOS_PRIORIDAD or q_bajo * fases**3 > MAX_COSTE_CLASES:
            raise ValueError(_t("advanced.error.erlang_a_prioridad.demasiados_estados"))
        pb, niv = _estacionaria_clases_truncada(lams, ths, mu, c, s_max, q_bajo)
        suma_altas = np.indices(niv.shape[:-1]).sum(axis=0) if n_altas else np.zeros(())
        frontera = float(niv[suma_altas == s_max].sum())
        techo = float(niv[..., q_bajo].sum())
        crece_s, crece_q = s_max < cota and frontera > TOL_FRONTERA, q_bajo < cota and techo > TOL_FRONTERA
        if not (crece_s or crece_q):
            return pb, niv
        nuevo_s = _siguiente_tamano(s_max, previo_s[0] if previo_s else None, frontera, previo_s[1] if previo_s else None, 1.25, cota) if crece_s else s_max
        nuevo_q = _siguiente_tamano(q_bajo, previo_q[0] if previo_q else None, techo, previo_q[1] if previo_q else None, 2.0, cota) if crece_q else q_bajo
        previo_s, previo_q = (s_max, frontera) if crece_s else previo_s, (q_bajo, techo) if crece_q else previo_q
        s_max, q_bajo = nuevo_s, nuevo_q


def _estacionaria_prioridad_truncada(lam1: float, lam2: float, mu: float, th1: float, th2: float, c: int, q1_max: int, q2_max: int) -> tuple[np.ndarray, np.ndarray]:
    """Dos clases: ``_estacionaria_clases_truncada`` con K = 2. Devuelve (p_b, p[q₁, q₂])."""
    return _estacionaria_clases_truncada([lam1, lam2], [th1, th2], mu, c, q1_max, q2_max)


def _estacionaria_prioridad(lam1: float, lam2: float, mu: float, th1: float, th2: float, c: int) -> tuple[np.ndarray, np.ndarray]:
    """Dos clases: ``_estacionaria_clases`` con K = 2."""
    return _estacionaria_clases([lam1, lam2], [th1, th2], mu, c)


def _nivel_servicio_clase(niv: np.ndarray, pb: np.ndarray, lams: Sequence[float], ths: Sequence[float], mu: float, c: int, k: int, t: float) -> float:
    """Nivel de servicio (atendido esperando ≤ t, con t > 0) de la clase *k* de M/M/c+M con prioridad.

    La clase 0 solo ve a las de su clase en la fila: fórmula cerrada. Las demás son pasadas por las llegadas de las clases altas mientras esperan: se usa
    la cadena de su espera —colas a₀ … a_{k−1} de las clases altas y posición propia m— por uniformización. Los estados de esa cadena son los de las
    colas de las clases 0 … k (las de menor prioridad no intervienen), y a = 0 hace que el servicio libre atienda a la clase *k*.
    """
    n_clases = niv.ndim
    cmu = c * mu
    libre = float(pb.sum())
    marg = niv.sum(axis=tuple(range(k + 1, n_clases))) if k + 1 < n_clases else niv     # P(q₀, …, q_k)
    if k == 0:
        return _nivel_servicio_cola(marg, libre, cmu, ths[0], t)
    forma = marg.shape

    def rebanada(eje: int, desde: int, hasta: int | None) -> tuple:
        r: list[slice] = [slice(None)] * len(forma)
        r[eje] = slice(desde, hasta)
        return tuple(r)

    rejilla = np.meshgrid(*[np.arange(n, dtype=float) for n in forma], indexing="ij")
    a, pos = rejilla[:k], rejilla[k] + 1.0
    tasa = cmu + ths[k] * pos
    for i in range(k):
        tasa = tasa + lams[i] * (a[i] < forma[i] - 1) + ths[i] * a[i]
    unif = float(tasa.max()) * (1.0 + 1e-9)
    x = unif * t
    n_max = int(x + 12.0 * math.sqrt(x + 1.0) + 30.0)
    if n_max > MAX_PASOS_UNIFORMIZACION:
        raise ValueError(_t("advanced.error.erlang_a_prioridad.demasiadas_iteraciones", pasos=n_max, maximo=MAX_PASOS_UNIFORMIZACION))
    if marg.size * n_max > MAX_CELDAS_PASOS:
        raise ValueError(_t("advanced.error.erlang_a_clases.demasiado_costoso", celdas=marg.size, pasos=n_max))
    pesos = np.exp(-x + np.arange(n_max + 1) * math.log(x) - np.array([math.lgamma(i + 1.0) for i in range(n_max + 1)]))
    vacias = [np.ones(forma)]                                      # z_i: a₀ = … = a_{i−1} = 0 (el servicio libre llega hasta la clase i)
    for i in range(k):
        vacias.append(vacias[-1] * (a[i] == 0))
    # coeficiente de u(a − e_i): abandona uno de la clase i, o se atiende si es la primera clase con cola
    coef = [ths[i] * a[i] + cmu * vacias[i] * (a[i] > 0) for i in range(k)]
    u = np.zeros(forma)                                            # u_n(estado) = P(atendido tras n pasos uniformizados)
    acum = np.zeros(forma)
    quieto = (unif - tasa) / unif
    for n in range(n_max + 1):
        acum += pesos[n] * u
        nuevo = np.zeros(forma)
        for i in range(k):
            nuevo[rebanada(i, 0, -1)] += lams[i] * u[rebanada(i, 1, None)]       # llega uno de la clase i: a_i + 1
            desp = np.zeros(forma)
            desp[rebanada(i, 1, None)] = u[rebanada(i, 0, -1)]
            nuevo += coef[i] * desp                                              # sale uno de la clase i: a_i − 1
        desp = np.zeros(forma)
        desp[rebanada(k, 1, None)] = u[rebanada(k, 0, -1)]
        nuevo += ths[k] * (pos - 1.0) * desp                                     # abandona uno de la clase k por delante: m − 1
        avance = desp.copy()
        avance[rebanada(k, 0, 1)] = 1.0                                          # m = 1: queda atendido
        nuevo += cmu * vacias[k] * avance                                        # sin colas altas, el servicio libre atiende a la clase k
        u = nuevo / unif + quieto * u
    return float(min(libre + float((marg * acum).sum()), 1.0))


def _estacionaria_mu_distintos_truncada(lam1: float, lam2: float, mu1: float, mu2: float, th1: float, th2: float, c: int, q1_max: int, q2_max: int) -> tuple[np.ndarray, np.ndarray]:
    """Distribución estacionaria de M/M/c+M con dos clases, prioridad no expropiativa y tiempos de servicio distintos (μ₁ la alta, μ₂ la baja), truncada
    en q₁ ≤ q1_max y q₂ ≤ q2_max.

    Con μ distintos hay que seguir cuántos servidores ocupa cada clase. Estados: sin cola, (n₁, n₂) con n₁ + n₂ < c (región libre F, triangular); con cola,
    n₁ servidores de alta y c − n₁ de baja ocupados más (q₁, q₂) en cola. Se resuelve por niveles de q₂ con las fases (n₁, q₁) ((c + 1)(q₁_max + 1) fases): hacia
    arriba λ₂·I; hacia abajo θ₂·k·I más, solo si q₁ = 0, los servicios que terminan y dejan entrar a uno de baja (la alta que termina cambia n₁ − 1; la baja,
    no). Esa bajada ya no es diagonal, pero tiene a lo más dos entradas por fila, así que N·D se calcula sin matrices intermedias. La región F no tiene forma
    cerrada: entra en el nivel 0 (que se resuelve con GTH). Devuelve (p_F[n₁, n₂], p[n₁, q₁, q₂]).
    """
    w = q1_max + 1
    m = (c + 1) * w

    def fase(n1: int, q1: int) -> int:
        return n1 * w + q1

    T = np.zeros((m, m))
    for n1 in range(c + 1):
        n2 = c - n1
        for q1 in range(w):
            p = fase(n1, q1)
            if q1 < q1_max:
                T[p, fase(n1, q1 + 1)] += lam1                               # llega uno de alta
            if q1 > 0:
                T[p, fase(n1, q1 - 1)] += th1 * q1                           # abandona uno de alta
                if n1 > 0:
                    T[p, fase(n1, q1 - 1)] += n1 * mu1                       # termina uno de alta: entra el siguiente de alta
                if n2 > 0:
                    T[p, fase(n1 + 1, q1 - 1)] += n2 * mu2                   # termina uno de baja: entra uno de alta (n₁ + 1)
    alta_origen = np.array([fase(n1, 0) for n1 in range(1, c + 1)], dtype=int)
    alta_destino = np.array([fase(n1 - 1, 0) for n1 in range(1, c + 1)], dtype=int)
    alta_tasa = np.array([n1 * mu1 for n1 in range(1, c + 1)])
    baja_origen = np.array([fase(n1, 0) for n1 in range(c)], dtype=int)
    baja_tasa = np.array([(c - n1) * mu2 for n1 in range(c)])

    def n_por_d(Nm: np.ndarray, k: int) -> np.ndarray:
        """N·D_k con D_k = θ₂·k·I + R (R tiene a lo más dos entradas por fila)."""
        r = th2 * k * Nm
        r[:, alta_destino] += Nm[:, alta_origen] * alta_tasa
        r[:, baja_origen] += Nm[:, baja_origen] * baja_tasa
        return r

    def suma_d(k: int) -> np.ndarray:
        d = np.full(m, th2 * k)
        d[alta_origen] += alta_tasa
        d[baja_origen] += baja_tasa
        return d

    idx = np.arange(m)

    def retroceder(n_arriba: np.ndarray, k: int) -> np.ndarray:
        """N_k = (−G_k)⁻¹ a partir de N_{k+1}, con G_k = T + λ₂·N_{k+1}·D_{k+1} y la diagonal por filas, sin restas."""
        G = T + lam2 * n_por_d(n_arriba, k + 1)
        G[idx, idx] = 0.0
        G[idx, idx] = -(suma_d(k) + G.sum(axis=1))
        return np.linalg.inv(-G)

    G = T.copy()                                                            # techo: sin subida de nivel
    G[idx, idx] = -(suma_d(q2_max) + T.sum(axis=1))
    tramo = max(1, math.isqrt(q2_max))
    N_act = np.linalg.inv(-G)
    puntos = {q2_max: N_act}
    for k in range(q2_max - 1, 0, -1):
        N_act = retroceder(N_act, k)
        if k % tramo == 0:
            puntos[k] = N_act
    # nivel 0 con la región libre F (n₁ + n₂ ≤ c − 1): llegadas que la llenan pasan a (n₁', q₁ = 0); con q₁ = 0 los servicios que terminan vuelven a F
    libres = [(a, b) for a in range(c) for b in range(c - a)]
    fid = {e: i for i, e in enumerate(libres)}
    nF = len(libres)
    A = np.zeros((nF + m, nF + m))
    for (a, b), i in fid.items():
        if a + b + 1 <= c - 1:
            A[i, fid[(a + 1, b)]] += lam1
            A[i, fid[(a, b + 1)]] += lam2
        else:
            A[i, nF + fase(a + 1, 0)] += lam1
            A[i, nF + fase(a, 0)] += lam2
        if a > 0:
            A[i, fid[(a - 1, b)]] += a * mu1
        if b > 0:
            A[i, fid[(a, b - 1)]] += b * mu2
    A[nF:, nF:] += T
    if q2_max >= 1:
        A[nF:, nF:] += lam2 * n_por_d(N_act, 1)                            # N_act = N_1
    for n1 in range(c + 1):
        n2 = c - n1
        p = nF + fase(n1, 0)
        if n1 > 0:
            A[p, fid[(n1 - 1, n2)]] += n1 * mu1
        if n2 > 0:
            A[p, fid[(n1, n2 - 1)]] += n2 * mu2
    x0 = _gth(A)
    niveles = np.zeros((q2_max + 1, m))
    log_escala = np.zeros(q2_max + 1)
    niveles[0] = x0[nF:]
    k = 1
    for fin in sorted(puntos):
        seg = {fin: puntos[fin]}
        for j in range(fin - 1, k - 1, -1):
            seg[j] = retroceder(seg[j + 1], j)
        for j in range(k, fin + 1):
            v = lam2 * niveles[j - 1] @ seg[j]
            suma = float(v.sum())
            niveles[j] = v / suma
            log_escala[j] = log_escala[j - 1] + math.log(suma)
        k = fin + 1
    peso = np.exp(log_escala - log_escala.max())
    niveles = np.maximum(niveles * peso[:, None], 0.0)
    pF0 = x0[:nF] * peso[0]
    total = float(pF0.sum() + niveles.sum())
    pF = np.zeros((c + 1, c + 1))
    for (a, b), i in fid.items():
        pF[a, b] = pF0[i] / total
    niv = np.zeros((c + 1, w, q2_max + 1))
    for n1 in range(c + 1):
        for q1 in range(w):
            niv[n1, q1, :] = niveles[:, fase(n1, q1)] / total
    return pF, niv


def _estacionaria_mu_distintos(lam1: float, lam2: float, mu1: float, mu2: float, th1: float, th2: float, c: int) -> tuple[np.ndarray, np.ndarray]:
    """Dos clases con μ distintos: ``_estacionaria_mu_distintos_truncada`` ampliando el truncamiento hasta que la masa en el borde es despreciable.

    La cola total es estocásticamente menor que la de Erlang A con λ₁ + λ₂, el menor de los μ y el menor de los θ (con la cola de espera, los servidores
    siempre están ocupados y terminan a una tasa ≥ c·μ_min), y eso acota ambas colas.
    """
    q = _distribucion_erlang_a(lam1 + lam2, min(mu1, mu2), min(th1, th2), c)[c:]
    cola = np.cumsum(q[::-1])[::-1]
    cota = max(int(np.argmax(cola < 1e-13)) if (cola < 1e-13).any() else len(cola), 4)
    q1_max, q2_max = min(8, cota), min(16, cota)
    previo_1 = previo_2 = None
    while True:
        m = (c + 1) * (q1_max + 1)
        n0 = c * (c + 1) // 2 + m
        matrices = q2_max // max(1, math.isqrt(q2_max)) + 1 + math.isqrt(q2_max)
        if matrices * m**2 > MAX_ELEMENTOS_PRIORIDAD or n0**2 > MAX_ELEMENTOS_PRIORIDAD or q2_max * m**3 + n0**3 > MAX_COSTE_CLASES:
            raise ValueError(_t("advanced.error.erlang_a_prioridad.demasiados_estados"))
        pF, niv = _estacionaria_mu_distintos_truncada(lam1, lam2, mu1, mu2, th1, th2, c, q1_max, q2_max)
        f1, f2 = float(niv[:, q1_max, :].sum()), float(niv[:, :, q2_max].sum())
        crece_1, crece_2 = q1_max < cota and f1 > TOL_FRONTERA, q2_max < cota and f2 > TOL_FRONTERA
        if not (crece_1 or crece_2):
            return pF, niv
        nuevo_1 = _siguiente_tamano(q1_max, previo_1[0] if previo_1 else None, f1, previo_1[1] if previo_1 else None, 1.5, cota) if crece_1 else q1_max
        nuevo_2 = _siguiente_tamano(q2_max, previo_2[0] if previo_2 else None, f2, previo_2[1] if previo_2 else None, 2.0, cota) if crece_2 else q2_max
        previo_1, previo_2 = (q1_max, f1) if crece_1 else previo_1, (q2_max, f2) if crece_2 else previo_2
        q1_max, q2_max = nuevo_1, nuevo_2


def _nivel_servicio_mu_distintos(pF: np.ndarray, niv: np.ndarray, lam1: float, mu1: float, mu2: float, th1: float, th2: float, c: int, clase: int, t: float) -> float:
    """Nivel de servicio (atendido esperando ≤ t, con t > 0) de la clase 0 (alta) o 1 (baja) con μ distintos, por uniformización.

    Mientras espera, todos los servidores están ocupados y solo cambia n₁ (los de alta en servicio). Alta, estado (n₁, m): termina uno de alta (n₁ μ₁) o de baja
    ((c − n₁) μ₂) y entra el siguiente de alta (m − 1; con la baja, n₁ + 1); abandona uno de alta por delante θ₁(m − 1). Baja, estado (n₁, a, m) con *a*
    de alta por delante: llegan de alta (λ₁), abandonan (θ₁·a); si termina uno de alta, con a > 0 entra otro de alta (a − 1) y con a = 0 entra uno de baja
    (n₁ − 1, m − 1); si termina uno de baja, con a > 0 entra uno de alta (a − 1, n₁ + 1) y con a = 0 uno de baja (m − 1); abandona uno de baja por delante θ₂(m − 1).
    """
    libre = float(pF.sum())
    if clase == 0:
        marg = niv.sum(axis=2)                                           # P(n₁, q₁)
        forma = marg.shape
        n1 = np.arange(forma[0], dtype=float)[:, None] * np.ones(forma)
        pos = np.arange(1, forma[1] + 1, dtype=float)[None, :] * np.ones(forma)
        n2 = c - n1
        tasa = n1 * mu1 + n2 * mu2 + th1 * pos
    else:
        marg = niv
        forma = marg.shape
        q1_max = forma[1] - 1
        n1 = np.arange(forma[0], dtype=float)[:, None, None] * np.ones(forma)
        a = np.arange(forma[1], dtype=float)[None, :, None] * np.ones(forma)
        pos = np.arange(1, forma[2] + 1, dtype=float)[None, None, :] * np.ones(forma)
        n2 = c - n1
        tasa = lam1 * (a < q1_max) + th1 * a + n1 * mu1 + n2 * mu2 + th2 * pos
    unif = float(tasa.max()) * (1.0 + 1e-9)
    x = unif * t
    n_max = int(x + 12.0 * math.sqrt(x + 1.0) + 30.0)
    if n_max > MAX_PASOS_UNIFORMIZACION:
        raise ValueError(_t("advanced.error.erlang_a_prioridad.demasiadas_iteraciones", pasos=n_max, maximo=MAX_PASOS_UNIFORMIZACION))
    if marg.size * n_max > MAX_CELDAS_PASOS:
        raise ValueError(_t("advanced.error.erlang_a_clases.demasiado_costoso", celdas=marg.size, pasos=n_max))
    pesos = np.exp(-x + np.arange(n_max + 1) * math.log(x) - np.array([math.lgamma(i + 1.0) for i in range(n_max + 1)]))
    u = np.zeros(forma)
    acum = np.zeros(forma)
    quieto = (unif - tasa) / unif
    for i in range(n_max + 1):
        acum += pesos[i] * u
        if clase == 0:
            avance = np.zeros(forma)                                      # u(n₁, m − 1); con m = 1 queda atendido
            avance[:, 1:] = u[:, :-1]
            avance[:, 0] = 1.0
            avance_up = np.zeros(forma)                                   # u(n₁ + 1, m − 1); con n₁ = c no hay baja que termine
            avance_up[:-1, 1:] = u[1:, :-1]
            avance_up[:-1, 0] = 1.0
            nuevo = n1 * mu1 * avance + n2 * mu2 * avance_up
            des = np.zeros(forma)
            des[:, 1:] = u[:, :-1]
            nuevo += th1 * (pos - 1.0) * des
        else:
            nuevo = np.zeros(forma)
            nuevo[:, :-1, :] += lam1 * u[:, 1:, :]                        # llega uno de alta: a + 1
            des_a = np.zeros(forma)
            des_a[:, 1:, :] = u[:, :-1, :]                                # a − 1
            nuevo += (th1 * a + n1 * mu1 * (a > 0)) * des_a               # abandona o termina uno de alta con cola de alta
            entra_baja = np.zeros(forma)                                  # u(n₁ − 1, a = 0, m − 1)
            entra_baja[1:, 0, 1:] = u[:-1, 0, :-1]
            entra_baja[1:, 0, 0] = 1.0
            nuevo += n1 * mu1 * (a == 0) * entra_baja
            alta_entra = np.zeros(forma)                                  # termina uno de baja y entra uno de alta: u(n₁ + 1, a − 1, m)
            alta_entra[:-1, 1:, :] = u[1:, :-1, :]
            nuevo += n2 * mu2 * (a > 0) * alta_entra
            baja_entra = np.zeros(forma)                                  # termina uno de baja y entra uno de baja: u(n₁, 0, m − 1)
            baja_entra[:, 0, 1:] = u[:, 0, :-1]
            baja_entra[:, 0, 0] = 1.0
            nuevo += n2 * mu2 * (a == 0) * baja_entra
            des_m = np.zeros(forma)
            des_m[:, :, 1:] = u[:, :, :-1]
            nuevo += th2 * (pos - 1.0) * des_m                            # abandona uno de baja por delante: m − 1
        u = nuevo / unif + quieto * u
    return float(min(libre + float((marg * acum).sum()), 1.0))


@dataclass
class ErlangAPriorityResult:
    """Resultado de ``erlang_a_priority``: M/M/c+M con dos clases y prioridad no expropiativa.

    Attributes
    ----------
    servers : int
        Número de servidores *c*.
    mu : float
        Tasa de servicio por servidor (la misma para las dos clases).
    rho : float
        Utilización (λ_eff alta + λ_eff baja)/(c·μ).
    p_wait : float
        Probabilidad de que quien llega (de cualquier clase) encuentre todos los servidores ocupados.
    classes : list[dict]
        Métricas por clase (0 = alta prioridad, 1 = baja): ``class_id``, ``lam``, ``theta``, ``p_abandon``, ``lam_eff``, ``Lq`` y ``Wq``.
        ``Lq`` y ``Wq`` cuentan a todos los que llegan de la clase, también a quienes abandonan.
    """

    servers: int
    mu: float
    rho: float
    p_wait: float
    classes: list[dict]
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        """Una fila por clase."""
        return pd.DataFrame(self.classes).rename(columns={
            "class_id": _t("advanced.cabecera.to_frame.id_clase"), "lam": "λ", "theta": "θ",
            "p_abandon": _t("advanced.cabecera.to_frame.p_abandono"), "lam_eff": _t("advanced.cabecera.to_frame.eff"),
        })

    def summary(self) -> str:
        lines = [
            _t("advanced.etiqueta.summary.erlang_a_prioridad", c=self.servers, mu=self.mu, rho=self.rho, p_wait=self.p_wait),
            f"{_t('advanced.texto_en_expresion.summary.clase'):>6}  {'λ':>9}  {'θ':>8}  {_t('advanced.cabecera.to_frame.p_abandono'):>11}  {_t('advanced.cabecera.to_frame.eff'):>9}  {_t('advanced.texto_en_expresion.summary.lq'):>9}  {_t('advanced.texto_en_expresion.summary.wq'):>10}",
            "-" * 72,
        ]
        for cl in self.classes:
            lines.append(f"{cl['class_id']:>6}  {cl['lam']:>9.4g}  {cl['theta']:>8.4g}  {cl['p_abandon']:>11.4%}  {cl['lam_eff']:>9.4g}  {cl['Lq']:>9.4g}  {cl['Wq']:>10.4g}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def _validar_prioridad(lam_high: float, lam_low: float, mu: float, theta_high: float, theta_low: float, c: int) -> tuple[float, float, float, float, float, int]:
    return (as_positive(lam_high, "lam_high"), as_positive(lam_low, "lam_low"), as_positive(mu, "mu"),
            as_positive(theta_high, "theta_high"), as_positive(theta_low, "theta_low"), as_int_positive(c, "c", max=MAX_SERVIDORES))


def erlang_a_priority(lam_high: float, lam_low: float, mu: float, theta_high: float, theta_low: float, c: int) -> ErlangAPriorityResult:
    """Cola M/M/c+M con dos clases (alta y baja prioridad) que abandonan con paciencias distintas (prioridad no expropiativa).

    Los clientes de alta prioridad pasan delante en la fila pero no desplazan a nadie en servicio. Cada clase tiene su tasa de llegadas λ y su tasa de
    abandono θ (paciencia exponencial de media 1/θ); el servicio es exponencial de tasa μ para las dos. El resultado es exacto (cadena de Markov
    resuelta numéricamente por niveles, no una aproximación) y estable aunque λ ≥ c·μ. Con θ iguales, la cola total coincide con ``erlang_a``.

    Parameters
    ----------
    lam_high, lam_low : float
        Tasas de llegada de la clase de alta y de baja prioridad (ambas > 0; con una sola clase use ``erlang_a``).
    mu : float
        Tasa de servicio μ por servidor.
    theta_high, theta_low : float
        Tasas de abandono θ de cada clase.
    c : int
        Número de servidores (≥ 1).

    Returns
    -------
    ErlangAPriorityResult
        Por clase: probabilidad de abandono, tasa atendida, Lq y Wq; y la utilización y P(esperar) del sistema.

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``c`` supera 10⁶ o la cola esperada necesita un truncamiento demasiado grande (λ/θ muy grande).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = erlang_a_priority(lam_high=1.5, lam_low=2.5, mu=1.0, theta_high=0.8, theta_low=0.3, c=4)
    >>> [round(x["p_abandon"], 4) for x in r.classes]
    [0.1397, 0.158]
    >>> round(r.p_wait, 4)
    0.6647
    """
    lam1, lam2, mu, th1, th2, c = _validar_prioridad(lam_high, lam_low, mu, theta_high, theta_low, c)
    pb, niv = _estacionaria_prioridad(lam1, lam2, mu, th1, th2, c)
    eq1 = float((np.arange(niv.shape[0]) * niv.sum(axis=1)).sum())
    eq2 = float((np.arange(niv.shape[1]) * niv.sum(axis=0)).sum())
    pab1, pab2 = th1 * eq1 / lam1, th2 * eq2 / lam2              # flujo de abandonos: θ·E[cola] = λ·P(abandono)
    eff1, eff2 = lam1 * (1.0 - pab1), lam2 * (1.0 - pab2)
    clases = [
        {"class_id": 0, "lam": lam1, "theta": th1, "p_abandon": pab1, "lam_eff": eff1, "Lq": eq1, "Wq": eq1 / lam1},
        {"class_id": 1, "lam": lam2, "theta": th2, "p_abandon": pab2, "lam_eff": eff2, "Lq": eq2, "Wq": eq2 / lam2},
    ]
    return ErlangAPriorityResult(
        servers=c, mu=mu, rho=(eff1 + eff2) / (c * mu), p_wait=float(niv.sum()), classes=clases,
        params={"P(abandono) total": (lam1 * pab1 + lam2 * pab2) / (lam1 + lam2)},
    )


def erlang_a_priority_service_level(lam_high: float, lam_low: float, mu: float, theta_high: float, theta_low: float, c: int, t: float) -> tuple[float, float]:
    """Nivel de servicio de cada clase de ``erlang_a_priority``: fracción de sus llegadas que se atiende esperando como máximo *t*.

    La clase de alta prioridad solo ve a las de su clase en la fila y su nivel es una fórmula cerrada (como en ``erlang_a_service_level``). A la de baja
    prioridad la pasan las llegadas de alta durante su espera: su nivel se calcula con la cadena de su espera (clientes de alta prioridad por delante,
    posición propia) por uniformización, también exacta. Quien abandona antes de *t* no cuenta como atendido.

    Parameters
    ----------
    lam_high, lam_low, mu, theta_high, theta_low, c
        Igual que en ``erlang_a_priority``.
    t : float
        Tiempo máximo de espera (≥ 0, en las mismas unidades de tiempo que 1/λ).

    Returns
    -------
    tuple[float, float]
        (nivel de la clase alta, nivel de la clase baja), cada uno en [0, 1 − P(abandono) de su clase].

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo, o ``t`` negativo).
        Si ``c`` supera 10⁶, el truncamiento es demasiado grande o ``t`` exige demasiadas iteraciones.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> alto, bajo = erlang_a_priority_service_level(1.5, 2.5, 1.0, 0.8, 0.3, 4, t=0.7)
    >>> round(alto, 4), round(bajo, 4)
    (0.8247, 0.616)
    """
    lam1, lam2, mu, th1, th2, c = _validar_prioridad(lam_high, lam_low, mu, theta_high, theta_low, c)
    t = as_nonneg(t, "t")
    pb, niv = _estacionaria_prioridad(lam1, lam2, mu, th1, th2, c)
    libre = float(pb.sum())
    if t == 0.0:
        return libre, libre
    lams, ths = [lam1, lam2], [th1, th2]
    return _nivel_servicio_clase(niv, pb, lams, ths, mu, c, 0, t), _nivel_servicio_clase(niv, pb, lams, ths, mu, c, 1, t)


@dataclass
class ErlangAClassesResult:
    """Resultado de ``erlang_a_classes``: M/M/c+M con K clases y prioridad no expropiativa.

    Attributes
    ----------
    servers : int
        Número de servidores *c*.
    mu : float or tuple[float, ...]
        Tasa de servicio por servidor: un número si es común a todas las clases, o una tupla con la de cada clase.
    rho : float
        Utilización: servidores ocupados en promedio entre c, es decir Σ λ_eff,k /(μ_k·c).
    p_wait : float
        Probabilidad de que quien llega (de cualquier clase) encuentre todos los servidores ocupados.
    classes : list[dict]
        Métricas por clase, de mayor a menor prioridad (``class_id`` 0 = la mayor): ``class_id``, ``lam``, ``mu``, ``theta``, ``p_abandon``,
        ``lam_eff``, ``Lq`` y ``Wq``. ``Lq`` y ``Wq`` cuentan a todos los que llegan de la clase, también a quienes abandonan.
    """

    servers: int
    mu: float | tuple[float, ...]
    rho: float
    p_wait: float
    classes: list[dict]
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        """Una fila por clase."""
        return pd.DataFrame(self.classes).rename(columns={
            "class_id": _t("advanced.cabecera.to_frame.id_clase"), "lam": "λ", "mu": "μ", "theta": "θ",
            "p_abandon": _t("advanced.cabecera.to_frame.p_abandono"), "lam_eff": _t("advanced.cabecera.to_frame.eff"),
        })

    def summary(self) -> str:
        distintos = isinstance(self.mu, tuple)
        mu_txt = "(" + ", ".join(f"{x:.6g}" for x in self.mu) + ")" if isinstance(self.mu, tuple) else f"{self.mu:.6g}"
        col_mu = f"  {'μ':>8}" if distintos else ""
        lines = [
            _t("advanced.etiqueta.summary.erlang_a_clases", c=self.servers, k=len(self.classes), mu=mu_txt, rho=self.rho, p_wait=self.p_wait),
            f"{_t('advanced.texto_en_expresion.summary.clase'):>6}  {'λ':>9}{col_mu}  {'θ':>8}  {_t('advanced.cabecera.to_frame.p_abandono'):>11}  {_t('advanced.cabecera.to_frame.eff'):>9}  {_t('advanced.texto_en_expresion.summary.lq'):>9}  {_t('advanced.texto_en_expresion.summary.wq'):>10}",
            "-" * (82 if distintos else 72),
        ]
        for cl in self.classes:
            fila_mu = f"  {cl['mu']:>8.4g}" if distintos else ""
            lines.append(f"{cl['class_id']:>6}  {cl['lam']:>9.4g}{fila_mu}  {cl['theta']:>8.4g}  {cl['p_abandon']:>11.4%}  {cl['lam_eff']:>9.4g}  {cl['Lq']:>9.4g}  {cl['Wq']:>10.4g}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def _validar_clases(lam: Sequence[float], mu: float | Sequence[float], theta: Sequence[float], c: int) -> tuple[list[float], list[float], list[float], int]:
    """Valida las entradas de K clases; ``mu`` es un número común o una secuencia con uno por clase (devuelve siempre una lista de K valores)."""
    lams = as_float_list(lam, "lam", min_len=2)
    ths = as_float_list(theta, "theta", min_len=2)
    if len(lams) != len(ths):
        raise ValueError(_t("advanced.error.erlang_a_clases.lam_theta_misma_longitud", n_lam=len(lams), n_theta=len(ths)))
    if len(lams) > MAX_CLASES:
        raise ValueError(_t("advanced.error.erlang_a_clases.demasiadas_clases", max=MAX_CLASES, n=len(lams)))
    if isinstance(mu, (int, float, np.number)) and not isinstance(mu, bool):
        mus = [as_positive(mu, "mu")] * len(lams)
    else:
        if isinstance(mu, (str, bytes, bool)) or mu is None or not hasattr(mu, "__len__"):
            raise TypeError(_t("advanced.error.erlang_a_clases.mu_tipo", tipo=type(mu).__name__))
        mus = as_float_list(mu, "mu", min_len=1)
        if len(mus) != len(lams):
            raise ValueError(_t("advanced.error.erlang_a_clases.mu_longitud", n_mu=len(mus), n=len(lams)))
        if len(set(mus)) > 1 and len(lams) > 2:
            raise ValueError(_t("advanced.error.erlang_a_clases.mu_distintos_solo_dos_clases", n=len(lams)))
    return lams, mus, ths, as_int_positive(c, "c", max=MAX_SERVIDORES)


def erlang_a_classes(lam: Sequence[float], mu: float | Sequence[float], theta: Sequence[float], c: int) -> ErlangAClassesResult:
    """Cola M/M/c+M con K ≥ 2 clases que abandonan con paciencias distintas y se atienden por prioridad no expropiativa.

    ``lam[0]`` y ``theta[0]`` son los de la clase de mayor prioridad. Cada clase pasa delante de las siguientes en la fila (sin desplazar a nadie en
    servicio), tiene su tasa de llegadas λ y su tasa de abandono θ (paciencia exponencial de media 1/θ), y el servicio es exponencial. El resultado es
    exacto (cadena de Markov resuelta por niveles), no una aproximación, y estable aunque Σλ ≥ c·μ. Con dos clases y μ común coincide con
    ``erlang_a_priority``; con θ iguales, la cola total coincide con ``erlang_a``.

    ``mu`` puede ser un número (común a todas las clases) o una secuencia con la tasa de servicio de cada clase. **Tiempos de servicio distintos por clase
    solo se admiten con 2 clases**: hay que seguir cuántos servidores ocupa cada clase y el estado crece con c (la región sin cola es una malla de c(c+1)/2
    estados), así que el costo es mayor (con carga cercana a la capacidad, ≈ 0,5 s con 10 servidores, ≈ 4 s con 20 y ≈ 15 s con 30; con 40 o más supera la cota de cálculo).

    El costo crece con el producto de las colas de las clases altas: con 2 o 3 clases es de décimas de segundo; con más clases o colas largas puede
    superar la cota de cálculo y lanzar ``ValueError``.

    Parameters
    ----------
    lam : sequence of float
        Tasas de llegada de cada clase, de mayor a menor prioridad (2 a 6 valores > 0).
    mu : float or sequence of float
        Tasa de servicio μ por servidor: un número común, o una secuencia con uno por clase (distintos solo con 2 clases).
    theta : sequence of float
        Tasas de abandono θ de cada clase (mismo orden y longitud que ``lam``).
    c : int
        Número de servidores (≥ 1).

    Returns
    -------
    ErlangAClassesResult
        Por clase: probabilidad de abandono, tasa atendida, Lq y Wq; y la utilización y P(esperar) del sistema.

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo), si ``lam`` y ``theta`` no tienen la misma
        longitud o hay más de 6 clases, si ``mu`` es una secuencia de longitud distinta de la de ``lam`` o con valores distintos y más de 2 clases.
        Si ``c`` supera 10⁶ o la cola esperada necesita un truncamiento demasiado grande.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = erlang_a_classes(lam=[0.7, 1.1, 1.6], mu=1.0, theta=[0.9, 0.5, 0.25], c=4)
    >>> [round(x["p_abandon"], 4) for x in r.classes]
    [0.1051, 0.0892, 0.0996]
    >>> round(r.p_wait, 4)
    0.5179
    >>> r2 = erlang_a_classes(lam=[1.0, 2.5], mu=[2.0, 0.7], theta=[0.6, 0.3], c=4)    # la clase alta se atiende más rápido
    >>> [round(x["p_abandon"], 4) for x in r2.classes]
    [0.1198, 0.1666]
    """
    lams, mus, ths, c = _validar_clases(lam, mu, theta, c)
    comun = len(set(mus)) == 1
    if comun:
        pb, niv = _estacionaria_clases(lams, ths, mus[0], c)
        n_wait = float(niv.sum())
    else:
        pF, niv = _estacionaria_mu_distintos(lams[0], lams[1], mus[0], mus[1], ths[0], ths[1], c)
        n_wait = float(niv.sum())
    clases = []
    for k in range(len(lams)):
        if comun:
            marg = niv.sum(axis=tuple(i for i in range(niv.ndim) if i != k))
        else:                                                         # niv[n₁, q₁, q₂]
            marg = niv.sum(axis=(0, 2)) if k == 0 else niv.sum(axis=(0, 1))
        eq = float((np.arange(len(marg)) * marg).sum())
        pab = ths[k] * eq / lams[k]                                  # flujo de abandonos: θ·E[cola] = λ·P(abandono)
        clases.append({"class_id": k, "lam": lams[k], "mu": mus[k], "theta": ths[k], "p_abandon": pab, "lam_eff": lams[k] * (1.0 - pab), "Lq": eq, "Wq": eq / lams[k]})
    total = sum(lams)
    ocupados = sum(x["lam_eff"] / x["mu"] for x in clases)             # servidores ocupados en promedio: Σ λ_eff,k / μ_k
    return ErlangAClassesResult(
        servers=c, mu=mus[0] if comun else tuple(mus), rho=ocupados / c, p_wait=n_wait, classes=clases,
        params={"P(abandono) total": sum(x["lam"] * x["p_abandon"] for x in clases) / total},
    )


def erlang_a_classes_service_level(lam: Sequence[float], mu: float | Sequence[float], theta: Sequence[float], c: int, t: float) -> tuple[float, ...]:
    """Nivel de servicio de cada clase de ``erlang_a_classes``: fracción de sus llegadas que se atiende esperando como máximo *t*.

    La clase de mayor prioridad solo ve a las de su clase en la fila y su nivel es una fórmula cerrada (como en ``erlang_a_service_level``). A cada una de
    las demás la pasan las llegadas de las clases altas durante su espera: su nivel se calcula con la cadena de su espera (colas de las clases altas por
    delante, posición propia) por uniformización, también exacta. Quien abandona antes de *t* no cuenta como atendido.

    Parameters
    ----------
    lam, mu, theta, c
        Igual que en ``erlang_a_classes`` (``mu`` puede ser una secuencia con un valor por clase si hay 2 clases).
    t : float
        Tiempo máximo de espera (≥ 0, en las mismas unidades de tiempo que 1/λ).

    Returns
    -------
    tuple[float, ...]
        Un nivel por clase (de mayor a menor prioridad), cada uno en [0, 1 − P(abandono) de su clase].

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo, o ``t`` negativo), si ``lam`` y ``theta`` no
        tienen la misma longitud o hay más de 6 clases. Si ``c`` supera 10⁶, el truncamiento es demasiado grande o ``t`` exige demasiado cálculo.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> niveles = erlang_a_classes_service_level([0.7, 1.1, 1.6], 1.0, [0.9, 0.5, 0.25], 4, t=0.6)
    >>> [round(x, 4) for x in niveles]
    [0.8663, 0.8355, 0.7103]
    """
    lams, mus, ths, c = _validar_clases(lam, mu, theta, c)
    t = as_nonneg(t, "t")
    if len(set(mus)) > 1:
        pF, niv = _estacionaria_mu_distintos(lams[0], lams[1], mus[0], mus[1], ths[0], ths[1], c)
        if t == 0.0:
            return (float(pF.sum()),) * 2
        return tuple(_nivel_servicio_mu_distintos(pF, niv, lams[0], mus[0], mus[1], ths[0], ths[1], c, k, t) for k in (0, 1))
    pb, niv = _estacionaria_clases(lams, ths, mus[0], c)
    if t == 0.0:
        return tuple(float(pb.sum()) for _ in lams)
    return tuple(_nivel_servicio_clase(niv, pb, lams, ths, mus[0], c, k, t) for k in range(len(lams)))


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
