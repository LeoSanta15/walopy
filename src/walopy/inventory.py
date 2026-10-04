"""Modelos de inventario: EOQ, EBQ, punto de reorden, newsvendor, multi-artículo, con restricciones, dimensionado dinámico de lotes, curvas de intercambio, ABC/XYZ y MRP."""
from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import NormalDist
from typing import TYPE_CHECKING, Any

from ._i18n import t as _t
from ._utils import as_float_list, as_fraction, as_nonneg, as_positive

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    import pandas as pd


# ---------------------------------------------------------------------------
# Economic Order Quantity
# ---------------------------------------------------------------------------

# Encabezados visibles de los DataFrame que se construyen desde listas de diccionarios: clave de dato (inglés, fija) → clave del
# catálogo de textos (el encabezado se resuelve al llamar, con el idioma activo; ver `_cabeceras`).

_COL_LOTES = {
    "period": "inventory.cabecera.modulo.periodo",
    "order_qty": "inventory.cabecera.modulo.cantidad_pedido",
    "covers_periods": "inventory.cabecera.modulo.periodos_cubiertos",
}
_COL_CANTIDADES = {
    "name": "inventory.cabecera.modulo.articulo",
    "Q_eoq": "inventory.cabecera.modulo.eoq",
    "Q_optimal": "inventory.cabecera.modulo.optima",
    "n_orders": "inventory.cabecera.modulo.pedidos",
    "investment": "inventory.cabecera.modulo.inversion_2",
    "sigma_dlt": "inventory.cabecera.modulo.sigma_dlt",
    "safety_stock": "inventory.cabecera.modulo.stock_seguridad",
    "reorder_point": "inventory.cabecera.modulo.punto_reorden",
}
_COL_CURVA_CICLO = {
    "N": "inventory.cabecera.modulo.pedidos_ano",
    "I": "inventory.cabecera.modulo.inversion",
}
_COL_CURVA_SEGURIDAD = {
    "service_level": "inventory.cabecera.modulo.nivel_servicio",
    "ss_investment": "inventory.cabecera.modulo.inversion_ss",
}
_COL_ARTICULOS = {
    "name": "inventory.cabecera.modulo.articulo",
    "demand": "inventory.cabecera.modulo.demanda",
    "unit_value": "inventory.cabecera.modulo.valor_unitario",
    "annual_value": "inventory.cabecera.modulo.valor_anual",
    "index": "inventory.cabecera.modulo.indice",
    "cumulative_pct": "inventory.cabecera.modulo.pct_acumulado",
    "pct_value": "inventory.cabecera.modulo.pct_valor",
    "rank": "inventory.cabecera.modulo.posicion",
    "class": "inventory.cabecera.modulo.clase",
    "abc_class": "inventory.cabecera.modulo.clase_abc",
    "xyz_class": "inventory.cabecera.modulo.clase_xyz",
    "combined_class": "inventory.cabecera.modulo.clase_combinada",
}


def _cabeceras(mapa: dict[str, str]) -> dict[str, str]:
    """Encabezados de ``mapa`` en el idioma activo."""
    return {dato: _t(clave) for dato, clave in mapa.items()}


@dataclass
class EOQResult:
    """Resultado de la Cantidad Económica de Pedido (EOQ).

    Attributes
    ----------
    eoq : float
        Cantidad óptima de pedido Q*.
    total_cost : float
        Costo total mínimo por periodo en Q*.
    holding_cost_total : float
        Componente anual del costo de mantener en Q*.
    ordering_cost_total : float
        Componente anual del costo de ordenar en Q*.
    order_frequency : float
        Número de pedidos por periodo.
    cycle_time : float
        Tiempo promedio entre pedidos (1 / order_frequency).
    params : dict
    """

    eoq: float
    total_cost: float
    holding_cost_total: float
    ordering_cost_total: float
    order_frequency: float
    cycle_time: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            _t("inventory.etiqueta.summary.eoq_cantidad_pedido_unidades_frecuencia", eoq=self.eoq, order_frequency=self.order_frequency, cycle_time=self.cycle_time, total_cost=self.total_cost, holding_cost_total=self.holding_cost_total, ordering_cost_total=self.ordering_cost_total)
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "EOQ": self.eoq,
            _t("inventory.cabecera.to_frame.costo_total"): self.total_cost,
            _t("inventory.cabecera.to_frame.costo_mantener"): self.holding_cost_total,
            _t("inventory.cabecera.to_frame.costo_ordenar"): self.ordering_cost_total,
            _t("inventory.cabecera.to_frame.frecuencia_pedidos"): self.order_frequency,
            _t("inventory.cabecera.to_frame.tiempo_ciclo"): self.cycle_time,
        }])

    def plot(self, **kwargs) -> plt.Figure:
        from .plotting import plot_eoq
        return plot_eoq(self, **kwargs)


def eoq(
    demand_rate: float,
    ordering_cost: float,
    holding_cost: float,
) -> EOQResult:
    """Cantidad Económica de Pedido: fórmula de Wilson / Harris.

    Q* = sqrt(2 · D · K / h)

    Parameters
    ----------
    demand_rate : float
        Demanda por periodo *D* (unidades/periodo).
    ordering_cost : float
        Costo fijo por pedido *K* ($/pedido).
    holding_cost : float
        Costo de mantener por unidad y periodo *h* ($/unidad/periodo).

    Returns
    -------
    EOQResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = eoq(demand_rate=1000, ordering_cost=50, holding_cost=2)
    >>> round(r.eoq, 1)
    223.6
    """
    D = as_positive(demand_rate, "demand_rate")
    K = as_positive(ordering_cost, "ordering_cost")
    h = as_positive(holding_cost, "holding_cost")

    q   = math.sqrt(2 * D * K / h)
    n   = D / q
    hc  = (q / 2) * h
    oc  = (D / q) * K
    tc  = hc + oc  # equal at EOQ → tc = sqrt(2*D*K*h)

    return EOQResult(
        eoq=q,
        total_cost=tc,
        holding_cost_total=hc,
        ordering_cost_total=oc,
        order_frequency=n,
        cycle_time=1.0 / n,
        params={"demand_rate": D, "ordering_cost": K, "holding_cost": h},
    )


# ---------------------------------------------------------------------------
# Reorder point and safety stock
# ---------------------------------------------------------------------------

@dataclass
class ReorderResult:
    """Resultado del punto de reorden y el stock de seguridad.

    Attributes
    ----------
    reorder_point : float
        Nivel de inventario al que se emite un pedido de reposición.
    safety_stock : float
        Stock de amortiguación = z · σ_{DLT}.
    service_level : float
        Nivel de servicio por ciclo (P(no hay faltante en el ciclo)).
    z_score : float
        Factor de seguridad z correspondiente al nivel de servicio.
    mean_demand_lt : float
        Demanda esperada durante el tiempo de entrega D̄ · L̄.
    std_demand_lt : float
        Desviación estándar de la demanda durante el tiempo de entrega √(L̄σ_D² + D̄²σ_L²).
    params : dict
    """

    reorder_point: float
    safety_stock: float
    service_level: float
    z_score: float
    mean_demand_lt: float
    std_demand_lt: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            _t("inventory.etiqueta.summary.punto_reorden_unidades_stock_seguridad", reorder_point=self.reorder_point, safety_stock=self.safety_stock, service_level=self.service_level, z_score=self.z_score, mean_demand_lt=self.mean_demand_lt, std_demand_lt=self.std_demand_lt)
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            _t("inventory.cabecera.to_frame.punto_reorden"): self.reorder_point,
            _t("inventory.cabecera.to_frame.stock_seguridad"): self.safety_stock,
            _t("inventory.cabecera.to_frame.nivel_servicio"): self.service_level,
            "z": self.z_score,
            _t("inventory.cabecera.to_frame.demanda_media_lt"): self.mean_demand_lt,
            _t("inventory.cabecera.to_frame.desv_demanda_lt"): self.std_demand_lt,
        }])


def reorder_point(
    demand_rate: float,
    lead_time: float,
    *,
    demand_std: float = 0.0,
    lead_time_std: float = 0.0,
    service_level: float = 0.95,
) -> ReorderResult:
    """Calcula el punto de reorden (ROP) y el stock de seguridad.

    ROP = D̄ · L̄ + z · σ_{DLT}

    donde σ_{DLT} = √(L̄ · σ_D² + D̄² · σ_L²)  y  z es el valor normal estándar
    correspondiente al nivel de servicio por ciclo deseado.

    Parameters
    ----------
    demand_rate : float
        Tasa media de demanda D̄ (unidades/periodo).
    lead_time : float
        Tiempo de entrega medio L̄ (en las mismas unidades de tiempo que demand_rate).
    demand_std : float
        Desviación estándar de la demanda por periodo σ_D (por defecto 0).
    lead_time_std : float
        Desviación estándar del tiempo de entrega σ_L (por defecto 0).
    service_level : float
        Probabilidad de no tener faltante por ciclo de reposición ∈ (0, 1).
        Por defecto 0.95.

    Returns
    -------
    ReorderResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``service_level`` no está estrictamente entre 0 y 1.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = reorder_point(demand_rate=50, lead_time=2, demand_std=10, service_level=0.95)
    >>> r.safety_stock > 0
    True
    """
    D   = as_positive(demand_rate, "demand_rate")
    LT  = as_positive(lead_time, "lead_time")
    sd  = as_nonneg(demand_std, "demand_std")
    sl  = as_nonneg(lead_time_std, "lead_time_std")
    svc = as_fraction(service_level, "service_level")
    if svc == 0.0 or svc == 1.0:
        raise ValueError(_t("inventory.error.reorder_point.service_level_debe_estar_estrictamente"))

    mean_dlt = D * LT
    var_dlt  = LT * sd**2 + D**2 * sl**2
    std_dlt  = math.sqrt(var_dlt)

    z   = NormalDist().inv_cdf(svc)
    ss  = z * std_dlt
    rop = mean_dlt + ss

    return ReorderResult(
        reorder_point=rop,
        safety_stock=ss,
        service_level=svc,
        z_score=z,
        mean_demand_lt=mean_dlt,
        std_demand_lt=std_dlt,
        params={"demand_rate": D, "lead_time": LT, "demand_std": sd,
                "lead_time_std": sl},
    )


# ---------------------------------------------------------------------------
# Newsvendor problem
# ---------------------------------------------------------------------------

@dataclass
class NewsvendorResult:
    """Resultado del modelo newsvendor.

    Attributes
    ----------
    optimal_qty : float
        Cantidad óptima de pedido Q* = F^{-1}(CR).
    critical_ratio : float
        Cu / (Cu + Co).
    expected_profit : float
        Utilidad esperada en Q*.
    expected_sales : float
        E[min(D, Q*)].
    expected_leftover : float
        E[max(Q* - D, 0)].
    expected_stockout : float
        E[max(D - Q*, 0)].
    underage_cost : float
        Cu = precio − costo.
    overage_cost : float
        Co = costo − valor de rescate.
    params : dict
    """

    optimal_qty: float
    critical_ratio: float
    expected_profit: float
    expected_sales: float
    expected_leftover: float
    expected_stockout: float
    underage_cost: float
    overage_cost: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            _t("inventory.etiqueta.summary.cantidad_optima_unidades_razon_critica", optimal_qty=self.optimal_qty, critical_ratio=self.critical_ratio, expected_profit=self.expected_profit, expected_sales=self.expected_sales, expected_leftover=self.expected_leftover, expected_stockout=self.expected_stockout, underage_cost=self.underage_cost, overage_cost=self.overage_cost)
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "Q*": self.optimal_qty,
            _t("inventory.cabecera.to_frame.razon_critica"): self.critical_ratio,
            _t("inventory.cabecera.to_frame.utilidad_esperada"): self.expected_profit,
            _t("inventory.cabecera.to_frame.ventas_esperadas"): self.expected_sales,
            _t("inventory.cabecera.to_frame.sobrante_esperado"): self.expected_leftover,
            _t("inventory.cabecera.to_frame.faltante_esperado"): self.expected_stockout,
            "Cu": self.underage_cost,
            "Co": self.overage_cost,
        }])


def newsvendor(
    demand_mean: float,
    demand_std: float,
    price: float,
    cost: float,
    *,
    salvage: float = 0.0,
) -> NewsvendorResult:
    """Modelo newsvendor (inventario de un solo periodo) con demanda normal.

    Cantidad óptima Q* = F^{-1}(Cu / (Cu + Co)) donde
    Cu = precio − costo  (costo de subestimar: utilidad perdida),
    Co = costo − valor de rescate  (costo de sobrestimar: unidades no vendidas).

    Parameters
    ----------
    demand_mean : float
        Demanda media μ_D.
    demand_std : float
        Desviación estándar de la demanda σ_D (≥ 0; 0 = determinística).
    price : float
        Precio de venta por unidad.
    cost : float
        Costo de compra o producción por unidad.
    salvage : float
        Valor de rescate por unidad no vendida (por defecto 0).

    Returns
    -------
    NewsvendorResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``cost`` no es menor que ``price`` o ``salvage`` no es menor que ``cost``.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = newsvendor(demand_mean=100, demand_std=20, price=10, cost=6, salvage=2)
    >>> round(r.optimal_qty, 2)  # razón crítica 0.5 → cuantil de la mediana
    100.0
    """
    mu  = as_positive(demand_mean, "demand_mean")
    sig = as_nonneg(demand_std, "demand_std")
    p   = as_positive(price, "price")
    c   = as_positive(cost, "cost")
    s   = as_nonneg(salvage, "salvage")

    if c >= p:
        raise ValueError(_t("inventory.error.newsvendor.cost_debe_ser_menor_price"))
    if s >= c:
        raise ValueError(_t("inventory.error.newsvendor.salvage_debe_ser_menor_cost"))

    Cu = p - c          # underage cost (opportunity loss)
    Co = c - s          # overage cost  (holding/disposal loss)
    CR = Cu / (Cu + Co) # critical ratio

    nd = NormalDist(mu=mu, sigma=sig) if sig > 0 else None

    if nd is None:
        Q = mu
    else:
        Q = nd.inv_cdf(CR)

    # Expected sales  E[min(D, Q)] and leftover E[max(Q-D, 0)]
    if nd is None or sig < 1e-12:
        exp_sales    = min(mu, Q)
        exp_leftover = max(Q - mu, 0.0)
        exp_stockout = max(mu - Q, 0.0)
    else:
        # Standard normal loss function: L(z) = phi(z) - z*(1-Phi(z))
        # E[max(D-Q,0)] = sig * L(z) using standard normal N(0,1)
        from statistics import NormalDist as _ND
        _std = _ND()
        z_std   = (Q - mu) / sig
        phi_std = _std.pdf(z_std)
        Phi_std = _std.cdf(z_std)
        exp_stockout = sig * (phi_std - z_std * (1 - Phi_std))
        exp_leftover = Q - mu + exp_stockout   # identity: E[leftover] - E[stockout] = Q - mu
        exp_sales    = mu - exp_stockout

    exp_profit = (p - c) * exp_sales - (c - s) * exp_leftover

    return NewsvendorResult(
        optimal_qty=Q,
        critical_ratio=CR,
        expected_profit=exp_profit,
        expected_sales=exp_sales,
        expected_leftover=exp_leftover,
        expected_stockout=exp_stockout,
        underage_cost=Cu,
        overage_cost=Co,
        params={"demand_mean": mu, "demand_std": sig,
                "price": p, "cost": c, "salvage": s},
    )


# ---------------------------------------------------------------------------
# Economic Batch Quantity (EBQ / EPQ)
# ---------------------------------------------------------------------------

@dataclass
class EBQResult:
    """Resultado de la Cantidad Económica de Lote (EPQ).

    Attributes
    ----------
    ebq : float
        Lote óptimo de producción Q*.
    total_cost : float
        Costo total mínimo por periodo.
    holding_cost_total : float
        Componente anual del costo de mantener en Q*.
    setup_cost_total : float
        Componente anual del costo de preparación en Q*.
    max_inventory : float
        Nivel máximo de inventario = Q*(1 − D/P).
    avg_inventory : float
        Nivel promedio de inventario = max_inventory / 2.
    production_time : float
        Fracción del ciclo dedicada a producir = Q*/P.
    cycle_time : float
        Duración de un ciclo de reposición = Q*/D.
    order_frequency : float
        Número de corridas de producción por periodo = D/Q*.
    params : dict
    """

    ebq: float
    total_cost: float
    holding_cost_total: float
    setup_cost_total: float
    max_inventory: float
    avg_inventory: float
    production_time: float
    cycle_time: float
    order_frequency: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            _t("inventory.etiqueta.summary.ebq_tamano_lote_unidades_inventario", ebq=self.ebq, max_inventory=self.max_inventory, avg_inventory=self.avg_inventory, order_frequency=self.order_frequency, cycle_time=self.cycle_time, production_time=self.production_time, total_cost=self.total_cost, holding_cost_total=self.holding_cost_total, setup_cost_total=self.setup_cost_total)
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "EBQ": self.ebq,
            _t("inventory.cabecera.to_frame.costo_total"): self.total_cost,
            _t("inventory.cabecera.to_frame.costo_mantener"): self.holding_cost_total,
            _t("inventory.cabecera.to_frame.costo_preparacion"): self.setup_cost_total,
            _t("inventory.cabecera.to_frame.inventario_maximo"): self.max_inventory,
            _t("inventory.cabecera.to_frame.inventario_promedio"): self.avg_inventory,
            _t("inventory.cabecera.to_frame.frecuencia_lotes"): self.order_frequency,
            _t("inventory.cabecera.to_frame.tiempo_ciclo"): self.cycle_time,
        }])


def ebq(
    demand_rate: float,
    setup_cost: float,
    holding_cost: float,
    production_rate: float,
) -> EBQResult:
    """Cantidad Económica de Lote (Cantidad Económica de Producción).

    Q* = sqrt(2 · D · S / (h · (1 − D/P)))

    Parameters
    ----------
    demand_rate : float
        Demanda por periodo D (unidades/periodo).
    setup_cost : float
        Costo fijo de preparación por corrida de producción S ($/corrida).
    holding_cost : float
        Costo de mantener por unidad y periodo h ($/unidad/periodo).
    production_rate : float
        Tasa de producción P (unidades/periodo). Debe superar a demand_rate.

    Returns
    -------
    EBQResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``production_rate`` no supera a ``demand_rate``.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = ebq(demand_rate=1000, setup_cost=50, holding_cost=2, production_rate=4000)
    >>> round(r.ebq, 1)
    258.2
    """
    D = as_positive(demand_rate, "demand_rate")
    S = as_positive(setup_cost, "setup_cost")
    h = as_positive(holding_cost, "holding_cost")
    P = as_positive(production_rate, "production_rate")
    if D >= P:
        raise ValueError(_t("inventory.error.ebq.production_rate_debe_superar_demand", P=P, D=D))

    fraction = 1.0 - D / P
    q   = math.sqrt(2 * D * S / (h * fraction))
    n   = D / q
    max_inv = q * fraction
    avg_inv = max_inv / 2.0
    hc  = avg_inv * h
    sc  = n * S
    tc  = hc + sc

    return EBQResult(
        ebq=q,
        total_cost=tc,
        holding_cost_total=hc,
        setup_cost_total=sc,
        max_inventory=max_inv,
        avg_inventory=avg_inv,
        production_time=q / P,
        cycle_time=q / D,
        order_frequency=n,
        params={"demand_rate": D, "setup_cost": S, "holding_cost": h, "production_rate": P},
    )


# ---------------------------------------------------------------------------
# Multi-item EOQ / EBQ (independent items)
# ---------------------------------------------------------------------------

@dataclass
class MultiItemResult:
    """Resultado de un análisis de inventario independiente de varios artículos.

    Attributes
    ----------
    items : list[dict]
        Resultados por artículo con las claves: Artículo, EOQ/EBQ, Costo total,
        Costo de mantener, Costo de ordenar (o de preparación), Frecuencia, Tiempo de ciclo.
    total_cost : float
        Suma de los costos óptimos individuales.
    params : dict
    """

    items: list
    total_cost: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.items)

    def summary(self) -> str:
        df = self.to_frame()
        lines = [df.to_string(index=False), _t("inventory.etiqueta.summary.costo_total_2", total_cost=self.total_cost)]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def eoq_multi(
    demand_rates: Sequence[float],
    ordering_costs: Sequence[float],
    holding_costs: Sequence[float],
    *,
    names: Sequence[str] | None = None,
) -> MultiItemResult:
    """Cantidad Económica de Pedido independiente para varios artículos.

    Resuelve cada artículo por separado; no hay restricciones compartidas.

    Parameters
    ----------
    demand_rates : sequence of float
        Tasa de demanda D_i de cada artículo.
    ordering_costs : sequence of float
        Costo fijo de ordenar K_i de cada artículo.
    holding_costs : sequence of float
        Costo de mantener h_i por unidad y periodo de cada artículo.
    names : sequence of str, optional
        Nombres de los artículos. Por defecto Artículo-1, Artículo-2, …

    Returns
    -------
    MultiItemResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = eoq_multi([1000, 500], [50, 30], [2, 1])
    >>> len(r.items) == 2
    True
    """
    demand_rates   = list(demand_rates)
    ordering_costs = list(ordering_costs)
    holding_costs  = list(holding_costs)
    n = len(demand_rates)
    if len(ordering_costs) != n or len(holding_costs) != n:
        raise ValueError(_t("inventory.error.eoq_multi.todas_secuencias_entrada_deben_tener"))
    if names is None:
        names = [_t("inventory.valor_por_defecto.eoq_multi.articulo", expr=i + 1) for i in range(n)]

    items = []
    total_cost = 0.0
    for i in range(n):
        r = eoq(demand_rates[i], ordering_costs[i], holding_costs[i])
        items.append({
            _t("columnas.columna_df.global.articulo"): names[i],
            "EOQ": r.eoq,
            _t("columnas.columna_df.global.costo_total"): r.total_cost,
            _t("columnas.columna_df.global.costo_mantener"): r.holding_cost_total,
            _t("columnas.columna_df.global.costo_ordenar"): r.ordering_cost_total,
            _t("columnas.columna_df.global.frecuencia_pedidos"): r.order_frequency,
            _t("columnas.columna_df.global.tiempo_ciclo_2"): r.cycle_time,
        })
        total_cost += r.total_cost

    return MultiItemResult(items=items, total_cost=total_cost,
                           params={"n_items": n})


def ebq_multi(
    demand_rates: Sequence[float],
    setup_costs: Sequence[float],
    holding_costs: Sequence[float],
    production_rates: Sequence[float],
    *,
    names: Sequence[str] | None = None,
) -> MultiItemResult:
    """Cantidad Económica de Lote independiente para varios artículos.

    Parameters
    ----------
    demand_rates : sequence of float
    setup_costs : sequence of float
    holding_costs : sequence of float
    production_rates : sequence of float
    names : sequence of str, optional

    Returns
    -------
    MultiItemResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = ebq_multi([1000, 500], [50, 30], [2, 1], [4000, 2000])
    >>> len(r.items) == 2
    True
    """
    demand_rates    = list(demand_rates)
    setup_costs     = list(setup_costs)
    holding_costs   = list(holding_costs)
    production_rates = list(production_rates)
    n = len(demand_rates)
    if not (len(setup_costs) == len(holding_costs) == len(production_rates) == n):
        raise ValueError(_t("inventory.error.eoq_multi.todas_secuencias_entrada_deben_tener"))
    if names is None:
        names = [_t("inventory.valor_por_defecto.eoq_multi.articulo", expr=i + 1) for i in range(n)]

    items = []
    total_cost = 0.0
    for i in range(n):
        r = ebq(demand_rates[i], setup_costs[i], holding_costs[i], production_rates[i])
        items.append({
            _t("columnas.columna_df.global.articulo"): names[i],
            "EBQ": r.ebq,
            _t("columnas.columna_df.global.costo_total"): r.total_cost,
            _t("columnas.columna_df.global.costo_mantener"): r.holding_cost_total,
            _t("columnas.columna_df.global.costo_preparacion"): r.setup_cost_total,
            _t("columnas.columna_df.global.inventario_maximo"): r.max_inventory,
            _t("columnas.columna_df.global.inventario_promedio"): r.avg_inventory,
            _t("columnas.columna_df.global.frecuencia_lotes"): r.order_frequency,
        })
        total_cost += r.total_cost

    return MultiItemResult(items=items, total_cost=total_cost,
                           params={"n_items": n})


# ---------------------------------------------------------------------------
# Constrained multi-item EOQ (Lagrangian relaxation)
# ---------------------------------------------------------------------------

def _eoq_lagrangian_bisect(
    D: list, K: list, h: list,
    weights: list, bound: float,
    other_lambdas: list | None = None,
    other_weights: list | None = None,
    tol: float = 1e-9,
) -> tuple[float, list[float]]:
    """Encuentra λ por bisección para una restricción sum(w_i * Q_i(λ)) = cota."""
    n = len(D)

    def h_eff(i: int, lam: float) -> float:
        base = h[i] + lam * weights[i]
        if other_lambdas and other_weights:
            for lj, wj in zip(other_lambdas, other_weights):
                base += lj * wj[i]
        return max(base, 1e-15)

    def Q_i(i: int, lam: float) -> float:
        return math.sqrt(2 * D[i] * K[i] / h_eff(i, lam))

    def total(lam: float) -> float:
        return sum(weights[i] * Q_i(i, lam) for i in range(n))

    # If unconstrained is feasible, λ = 0
    if total(0.0) <= bound + tol:
        return 0.0, [Q_i(i, 0.0) for i in range(n)]

    # Find upper bound for λ
    hi = 1.0
    for _ in range(200):
        if total(hi) <= bound:
            break
        hi *= 2.0
    else:
        raise ValueError(_t("inventory.error.eoq_lagrangian_bisect.restriccion_puede_satisfacer_ninguna_cantidad"))

    lo = 0.0
    for _ in range(120):
        mid = (lo + hi) / 2.0
        if total(mid) > bound:
            lo = mid
        else:
            hi = mid
        if (hi - lo) < tol:
            break

    lam_opt = (lo + hi) / 2.0
    return lam_opt, [Q_i(i, lam_opt) for i in range(n)]


@dataclass
class ConstrainedMultiEOQResult:
    """Resultado del EOQ multi-artículo con restricciones (relajación lagrangiana).

    Attributes
    ----------
    items : list[dict]
        Cantidades óptimas y costos por artículo.
    total_cost : float
        Costo total de inventario en las cantidades óptimas.
    unconstrained_total_cost : float
        Costo total del EOQ sin restricciones (cota inferior).
    lagrange_multipliers : dict[str, float]
        Multiplicador de Lagrange λ de cada restricción.
    binding_constraints : list[str]
        Nombres de las restricciones activas.
    params : dict
    """

    items: list
    total_cost: float
    unconstrained_total_cost: float
    lagrange_multipliers: dict
    binding_constraints: list
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.items)

    def summary(self) -> str:
        lines = [
            _t("inventory.etiqueta.summary.costo_total_restricciones", total_cost=self.total_cost),
            _t("inventory.etiqueta.summary.costo_total_sin_restricciones", unconstrained_total_cost=self.unconstrained_total_cost),
            _t("inventory.etiqueta.summary.restricciones_activas", expr=', '.join(self.binding_constraints) or _t('inventory.texto_en_expresion.summary.ninguna')),
            "",
        ]
        for row in self.items:
            lines.append(
                _t("inventory.etiqueta.summary.ct", expr=row[_t('columnas.columna_df.global.articulo')], expr2=row['Q*'], expr3=row[_t('columnas.columna_df.global.costo_total')])
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def eoq_multi_constrained(
    demand_rates: Sequence[float],
    ordering_costs: Sequence[float],
    holding_costs: Sequence[float],
    *,
    names: Sequence[str] | None = None,
    budget: float | None = None,
    budget_unit_costs: Sequence[float] | None = None,
    space: float | None = None,
    space_per_unit: Sequence[float] | None = None,
    constraints: list[dict] | None = None,
) -> ConstrainedMultiEOQResult:
    """EOQ multi-artículo con restricciones mediante relajación lagrangiana.

    Minimiza la suma de costos de inventario sujeta a restricciones lineales sobre las
    cantidades de pedido:  sum_i(w_ij · Q_i) ≤ B_j.

    Atajos de uso frecuente
    -----------------------
    budget / budget_unit_costs
        Restricción de presupuesto sobre la inversión *promedio* en inventario:
        sum(c_i · Q_i / 2) ≤ budget.
        Indique ``budget_unit_costs`` = costos unitarios de compra c_i.
    space / space_per_unit
        Restricción de espacio sobre el inventario promedio:
        sum(s_i · Q_i / 2) ≤ space.

    Restricciones genéricas
    -----------------------
    constraints : list of dict, cada uno con las claves
        ``name`` (str), ``weights`` (lista de floats a_i),
        ``bound`` (float B): impone sum(a_i · Q_i) ≤ B.

    Parameters
    ----------
    demand_rates, ordering_costs, holding_costs : sequence of float
    names : sequence of str, optional
    budget : float, optional
    budget_unit_costs : sequence of float, optional
    space : float, optional
    space_per_unit : sequence of float, optional
    constraints : list of dict, optional

    Returns
    -------
    ConstrainedMultiEOQResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
        Si ``budget``/``space`` no son positivos o falta la lista de costos/espacios asociada.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = eoq_multi_constrained(
    ...     [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
    ...     budget=5000, budget_unit_costs=[10, 8, 12],
    ... )
    >>> r.total_cost > 0
    True
    """
    D = as_float_list(demand_rates, "demand_rates")
    K = as_float_list(ordering_costs, "ordering_costs")
    h = as_float_list(holding_costs, "holding_costs")
    n = len(D)
    if len(K) != n or len(h) != n:
        raise ValueError(_t("inventory.error.eoq_multi.todas_secuencias_entrada_deben_tener"))
    if names is None:
        names = [_t("inventory.valor_por_defecto.eoq_multi.articulo", expr=i + 1) for i in range(n)]

    # Build constraint list
    all_constraints: list[dict] = []
    if budget is not None:
        if budget_unit_costs is None:
            raise ValueError(_t("inventory.error.eoq_multi_constrained.budget_unit_costs_obligatorio_cuando"))
        bc = as_float_list(budget_unit_costs, "budget_unit_costs", kind="nonneg")
        if len(bc) != n:
            raise ValueError(_t("inventory.error.eoq_multi_constrained.budget_unit_costs_debe_tener"))
        all_constraints.append(
            {"name": "budget", "weights": [c / 2 for c in bc], "bound": as_positive(budget, "budget")}
        )
    if space is not None:
        if space_per_unit is None:
            raise ValueError(_t("inventory.error.eoq_multi_constrained.space_per_unit_obligatorio_cuando"))
        sw = as_float_list(space_per_unit, "space_per_unit", kind="nonneg")
        if len(sw) != n:
            raise ValueError(_t("inventory.error.eoq_multi_constrained.space_per_unit_debe_tener"))
        all_constraints.append(
            {"name": "space", "weights": [s / 2 for s in sw], "bound": as_positive(space, "space")}
        )
    if constraints:
        for j, c in enumerate(constraints):
            if not isinstance(c, dict) or not {"name", "weights", "bound"} <= set(c):
                raise ValueError(_t("inventory.error.eoq_multi_constrained.constraints_debe_ser_diccionario_name", j=j))
            w = as_float_list(c["weights"], f"constraints[{j}]['weights']", kind="nonneg")
            if len(w) != n:
                raise ValueError(_t("inventory.error.eoq_multi_constrained.restriccion_weights_tiene_longitud_distinta", expr=c['name']))
            all_constraints.append(
                {"name": c["name"], "weights": w, "bound": as_positive(c["bound"], f"constraints[{j}]['bound']")}
            )

    # Unconstrained solution
    Q_unc = [math.sqrt(2 * D[i] * K[i] / h[i]) for i in range(n)]
    tc_unc = sum((h[i] * Q_unc[i] / 2 + D[i] * K[i] / Q_unc[i]) for i in range(n))

    if not all_constraints:
        # No constraints — return unconstrained
        items = []
        for i in range(n):
            tc_i = h[i] * Q_unc[i] / 2 + D[i] * K[i] / Q_unc[i]
            items.append({_t("columnas.columna_df.global.articulo"): names[i], "Q*": Q_unc[i], _t("columnas.columna_df.global.costo_total"): tc_i,
                          _t("columnas.columna_df.global.costo_mantener"): h[i] * Q_unc[i] / 2, _t("columnas.columna_df.global.costo_ordenar"): D[i] * K[i] / Q_unc[i]})
        return ConstrainedMultiEOQResult(
            items=items, total_cost=tc_unc, unconstrained_total_cost=tc_unc,
            lagrange_multipliers={}, binding_constraints=[], params={"n_items": n})

    # Coordinate descent on Lagrange multipliers
    lambdas = {c["name"]: 0.0 for c in all_constraints}
    Q_opt = Q_unc[:]
    binding: list[str] = []

    for _iter in range(200):
        Q_prev = Q_opt[:]
        for c in all_constraints:
            cname = c["name"]
            w = c["weights"]
            b = c["bound"]
            # Effective holding cost from other lambdas
            h_eff = [h[i] for i in range(n)]
            for c2 in all_constraints:
                if c2["name"] != cname:
                    lj = lambdas[c2["name"]]
                    for i in range(n):
                        h_eff[i] += lj * c2["weights"][i]

            # Check if this constraint is violated with current λ_others
            Q_check = [math.sqrt(2 * D[i] * K[i] / max(h_eff[i], 1e-15)) for i in range(n)]
            if sum(w[i] * Q_check[i] for i in range(n)) <= b + 1e-9:
                lambdas[cname] = 0.0
                Q_opt = [math.sqrt(2 * D[i] * K[i] / max(h_eff[i], 1e-15)) for i in range(n)]
            else:
                lam_j, Q_j = _eoq_lagrangian_bisect(D, K, h_eff, w, b)
                lambdas[cname] = lam_j
                Q_opt = Q_j

        if max(abs(Q_opt[i] - Q_prev[i]) for i in range(n)) < 1e-8:
            break

    # Final Q using all lambdas
    h_final = [h[i] + sum(lambdas[c["name"]] * c["weights"][i] for c in all_constraints) for i in range(n)]
    Q_opt = [math.sqrt(2 * D[i] * K[i] / max(h_final[i], 1e-15)) for i in range(n)]

    # Binding = constraints where λ > 1e-10
    binding = [c["name"] for c in all_constraints if lambdas[c["name"]] > 1e-10]

    tc_opt = sum(h[i] * Q_opt[i] / 2 + D[i] * K[i] / Q_opt[i] for i in range(n))
    items = []
    for i in range(n):
        tc_i = h[i] * Q_opt[i] / 2 + D[i] * K[i] / Q_opt[i]
        items.append({_t("columnas.columna_df.global.articulo"): names[i], "Q*": Q_opt[i], _t("columnas.columna_df.global.costo_total"): tc_i,
                      _t("columnas.columna_df.global.costo_mantener"): h[i] * Q_opt[i] / 2, _t("columnas.columna_df.global.costo_ordenar"): D[i] * K[i] / Q_opt[i]})

    return ConstrainedMultiEOQResult(
        items=items,
        total_cost=tc_opt,
        unconstrained_total_cost=tc_unc,
        lagrange_multipliers=lambdas,
        binding_constraints=binding,
        params={"n_items": n},
    )


# ---------------------------------------------------------------------------
# Dynamic lot-sizing: Lot-for-Lot and Silver-Meal
# ---------------------------------------------------------------------------

@dataclass
class LotSizingResult:
    """Resultado del dimensionado dinámico de lotes.

    Attributes
    ----------
    orders : list[dict]
        Cada diccionario: {period, order_qty, covers_periods}.
    total_cost : float
        Costo total de preparación + mantener en el horizonte.
    total_setup_cost : float
    total_holding_cost : float
    n_orders : int
    method : str
    params : dict
    """

    orders: list
    total_cost: float
    total_setup_cost: float
    total_holding_cost: float
    n_orders: int
    method: str
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.orders).rename(columns=_cabeceras(_COL_LOTES))

    def summary(self) -> str:
        lines = [
            _t("inventory.etiqueta.summary.metodo", method=self.method),
            _t("inventory.etiqueta.summary.numero_pedidos", n_orders=self.n_orders),
            _t("inventory.etiqueta.summary.costo_total", total_cost=self.total_cost),
            _t("inventory.etiqueta.summary.costo_preparacion", total_setup_cost=self.total_setup_cost),
            _t("inventory.etiqueta.summary.costo_mantener", total_holding_cost=self.total_holding_cost),
            "",
            f"{_t('inventory.texto_en_expresion.summary.periodo'):<8} {_t('inventory.texto_en_expresion.summary.cantidad'):>10} {_t('inventory.texto_en_expresion.summary.cubre'):>20}",
            "-" * 42,
        ]
        for o in self.orders:
            covers = str(o["covers_periods"])
            lines.append(f"{o['period']:<8} {o['order_qty']:>10.4g} {covers:>20}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def lot_for_lot(
    demands: Sequence[float],
    setup_cost: float,
    holding_cost: float,
) -> LotSizingResult:
    """Heurística de dimensionado dinámico de lotes Lote por Lote (L4L).

    Pide exactamente la demanda de cada periodo: no se arrastra inventario.
    Minimiza el costo de mantener a costa de una preparación por cada periodo con demanda > 0.

    Parameters
    ----------
    demands : sequence of float
        Demanda d_t de los periodos t = 1, 2, …, T.
    setup_cost : float
        Costo fijo de preparación S por pedido.
    holding_cost : float
        Costo de mantener h por unidad y periodo.

    Returns
    -------
    LotSizingResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = lot_for_lot([100, 80, 120, 60], setup_cost=200, holding_cost=1)
    >>> r.total_holding_cost
    0.0
    """
    demands    = as_float_list(demands, "demands", kind="nonneg")
    setup_cost = as_positive(setup_cost, "setup_cost")
    holding_cost = as_positive(holding_cost, "holding_cost")

    orders = []
    total_setup = 0.0
    for t, d in enumerate(demands, 1):
        if d > 0:
            orders.append({"period": t, "order_qty": d, "covers_periods": [t]})
            total_setup += setup_cost

    return LotSizingResult(
        orders=orders,
        total_cost=total_setup,
        total_setup_cost=total_setup,
        total_holding_cost=0.0,
        n_orders=len(orders),
        method=_t("inventory.modelo.lot_for_lot.lote_lote"),
        params={"setup_cost": setup_cost, "holding_cost": holding_cost},
    )


def silver_meal(
    demands: Sequence[float],
    setup_cost: float,
    holding_cost: float,
) -> LotSizingResult:
    """Heurística de Silver-Meal para el dimensionado dinámico de lotes.

    Extiende cada pedido para cubrir periodos adicionales mientras el costo promedio
    por periodo (preparación + mantener) siga disminuyendo.

    Parameters
    ----------
    demands : sequence of float
        Demanda d_t de los periodos t = 1, 2, …, T.
    setup_cost : float
        Costo fijo de preparación S por pedido.
    holding_cost : float
        Costo de mantener h por unidad y periodo (se carga por los periodos en inventario).

    Returns
    -------
    LotSizingResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = silver_meal([100, 80, 120, 60], setup_cost=200, holding_cost=1)
    >>> r.total_cost <= lot_for_lot([100, 80, 120, 60], 200, 1).total_cost
    True
    """
    demands    = as_float_list(demands, "demands", kind="nonneg")
    setup_cost = as_positive(setup_cost, "setup_cost")
    holding_cost = as_positive(holding_cost, "holding_cost")
    T = len(demands)

    orders: list[dict] = []
    total_setup   = 0.0
    total_holding = 0.0
    t = 0
    while t < T:
        if demands[t] == 0:
            t += 1
            continue
        # Extend coverage greedily while avg cost/period decreases
        order_qty  = demands[t]
        hold_accum = 0.0
        prev_avg   = setup_cost  # avg cost for k=1
        covers     = [t + 1]
        k = 1
        while t + k < T:
            hold_accum += k * holding_cost * demands[t + k]
            new_avg = (setup_cost + hold_accum) / (k + 1)
            if new_avg >= prev_avg:
                break
            prev_avg   = new_avg
            order_qty += demands[t + k]
            covers.append(t + k + 1)
            k += 1

        # Recompute holding cost for this run
        run_holding = sum(j * holding_cost * demands[t + j] for j in range(1, len(covers)))
        orders.append({"period": t + 1, "order_qty": order_qty, "covers_periods": covers})
        total_setup   += setup_cost
        total_holding += run_holding
        t += len(covers)

    return LotSizingResult(
        orders=orders,
        total_cost=total_setup + total_holding,
        total_setup_cost=total_setup,
        total_holding_cost=total_holding,
        n_orders=len(orders),
        method=_t("inventory.modelo.silver_meal.silver_meal"),
        params={"setup_cost": setup_cost, "holding_cost": holding_cost},
    )


# ---------------------------------------------------------------------------
# EOQ with all-units quantity discount
# ---------------------------------------------------------------------------

@dataclass
class QuantityDiscountResult:
    """Resultado del EOQ con descuentos por cantidad en todas las unidades.

    Attributes
    ----------
    optimal_qty : float
        Cantidad óptima de pedido considerando los tramos de precio.
    unit_price : float
        Precio unitario en optimal_qty.
    total_cost : float
        Costo total anual mínimo (compra + ordenar + mantener).
    purchase_cost : float
        Costo anual de compra D * unit_price.
    ordering_cost_total : float
        Costo anual de ordenar (D/Q) * K.
    holding_cost_total : float
        Costo anual de mantener (Q/2) * h * unit_price.
    break_idx : int
        Índice del tramo de precio seleccionado.
    candidates : list[dict]
        Todos los candidatos evaluados (uno por tramo).
    params : dict
    """

    optimal_qty: float
    unit_price: float
    total_cost: float
    purchase_cost: float
    ordering_cost_total: float
    holding_cost_total: float
    break_idx: int
    candidates: list
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            _t("inventory.etiqueta.summary.cantidad_optima_unidades_precio_unitario", optimal_qty=self.optimal_qty, unit_price=self.unit_price, total_cost=self.total_cost, purchase_cost=self.purchase_cost, ordering_cost_total=self.ordering_cost_total, holding_cost_total=self.holding_cost_total)
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.candidates)


def eoq_quantity_discount(
    demand_rate: float,
    ordering_cost: float,
    holding_cost_rate: float,
    price_breaks: Sequence[tuple],
) -> QuantityDiscountResult:
    """EOQ con descuentos por cantidad en todas las unidades.

    Para cada tramo de precio calcula el EOQ con h = holding_cost_rate × precio_unitario
    y comprueba si cae dentro del rango válido. Devuelve el tramo de menor
    costo anual total (compra + ordenar + mantener).

    Parameters
    ----------
    demand_rate : float
        Demanda anual D.
    ordering_cost : float
        Costo fijo de ordenar por pedido K.
    holding_cost_rate : float
        Costo de mantener como fracción del precio unitario (p. ej. 0.20 = 20 % anual).
    price_breaks : sequence of (min_qty, unit_price) tuples
        Ordenados ascendentemente por min_qty. Ejemplo: [(0, 10), (500, 9.5), (1000, 9)].

    Returns
    -------
    QuantityDiscountResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``price_breaks`` está vacío o mal formado.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = eoq_quantity_discount(
    ...     demand_rate=1000, ordering_cost=50, holding_cost_rate=0.2,
    ...     price_breaks=[(0, 10.0), (500, 9.5), (1000, 9.0)],
    ... )
    >>> r.total_cost > 0
    True
    """
    D  = as_positive(demand_rate, "demand_rate")
    K  = as_positive(ordering_cost, "ordering_cost")
    Ih = as_positive(holding_cost_rate, "holding_cost_rate")

    breaks = list(price_breaks)
    if len(breaks) < 1:
        raise ValueError(_t("inventory.error.eoq_quantity_discount.price_breaks_debe_contener_menos"))

    # Sort by min_qty
    breaks.sort(key=lambda x: x[0])
    # Upper bounds for each break
    upper_bounds = [breaks[j + 1][0] - 1e-9 for j in range(len(breaks) - 1)] + [math.inf]

    candidates: list[dict] = []
    best: dict | None = None

    for idx, (min_q, price) in enumerate(breaks):
        h = Ih * price
        q_eoq = math.sqrt(2 * D * K / h)
        # Adjust to valid range
        lo = min_q
        hi = upper_bounds[idx]
        q_adj = max(lo, min(q_eoq, hi))

        pc = D * price
        oc = (D / q_adj) * K
        hc = (q_adj / 2) * h
        tc = pc + oc + hc
        candidates.append({
            _t("columnas.columna_df.global.indice_tramo"): idx,
            _t("columnas.columna_df.global.cantidad_min"): min_q,
            _t("columnas.columna_df.global.precio_unitario"): price,
            "EOQ": q_eoq,
            _t("columnas.columna_df.global.ajustada"): q_adj,
            _t("columnas.columna_df.global.costo_compra"): pc,
            _t("columnas.columna_df.global.costo_ordenar"): oc,
            _t("columnas.columna_df.global.costo_mantener"): hc,
            _t("columnas.columna_df.global.costo_total"): tc,
            _t("columnas.columna_df.global.factible"): lo <= q_adj <= (upper_bounds[idx] + 1e-9),
        })
        if best is None or tc < best[_t("columnas.columna_df.global.costo_total")]:
            best = candidates[-1]

    if best is None:
        raise ValueError(_t("inventory.error.eoq_quantity_discount.feasible_price_break_found"))

    return QuantityDiscountResult(
        optimal_qty=best[_t("columnas.columna_df.global.ajustada")],
        unit_price=best[_t("columnas.columna_df.global.precio_unitario")],
        total_cost=best[_t("columnas.columna_df.global.costo_total")],
        purchase_cost=best[_t("columnas.columna_df.global.costo_compra")],
        ordering_cost_total=best[_t("columnas.columna_df.global.costo_ordenar")],
        holding_cost_total=best[_t("columnas.columna_df.global.costo_mantener")],
        break_idx=best[_t("columnas.columna_df.global.indice_tramo")],
        candidates=candidates,
        params={"demand_rate": D, "ordering_cost": K, "holding_cost_rate": Ih},
    )


# ---------------------------------------------------------------------------
# Wagner-Whitin (optimal dynamic lot-sizing)
# ---------------------------------------------------------------------------

def wagner_whitin(
    demands: Sequence[float],
    setup_cost: float,
    holding_cost: float,
) -> LotSizingResult:
    """Dimensionado dinámico óptimo de lotes de Wagner-Whitin mediante programación dinámica.

    Encuentra la política de pedidos de costo mínimo exacto en un horizonte finito,
    a diferencia de Silver-Meal (heurística). Complejidad temporal O(n²).

    Parameters
    ----------
    demands : sequence of float
        Demanda d_t de los periodos t = 1, 2, …, T.
    setup_cost : float
        Costo fijo de preparación u ordenar S por pedido.
    holding_cost : float
        Costo de mantener h por unidad y periodo.

    Returns
    -------
    LotSizingResult
        ``method`` es ``'Wagner-Whitin'``.


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = wagner_whitin([100, 80, 120, 60], setup_cost=200, holding_cost=1)
    >>> r.total_cost <= silver_meal([100, 80, 120, 60], setup_cost=200, holding_cost=1).total_cost
    True
    """
    demands_v = as_float_list(demands, "demands", kind="nonneg")
    K = as_positive(setup_cost, "setup_cost")
    h = as_positive(holding_cost, "holding_cost")
    n = len(demands_v)

    INF = float("inf")
    dp = [INF] * (n + 1)   # dp[j] = min cost to satisfy demands 0..j-1
    dp[0] = 0.0
    last = [-1] * (n + 1)  # last[j] = period i where order was placed

    # Recursión hacia adelante: el costo de mantener se acumula de forma incremental
    # (O(n²) en total; antes se recalculaba la suma completa para cada par (i, j): O(n³)).
    for i in range(1, n + 1):
        acum = 0.0  # Σ_{k=i..j} (k - i) · d_k
        for j in range(i, n + 1):
            acum += (j - i) * demands_v[j - 1]
            # Pedido al inicio del periodo i que cubre las demandas i..j (índices desde 1)
            cost = dp[i - 1] + K + h * acum
            if cost < dp[j]:
                dp[j] = cost
                last[j] = i

    # Reconstruct orders
    orders = []
    j = n
    while j > 0:
        i = last[j]
        qty = sum(demands_v[k - 1] for k in range(i, j + 1))
        orders.append({
            "period": i,
            "order_qty": qty,
            "covers_periods": list(range(i, j + 1)),
        })
        j = i - 1
    orders.reverse()

    total_setup = len(orders) * K
    total_holding = dp[n] - total_setup
    return LotSizingResult(
        orders=orders,
        total_cost=dp[n],
        total_setup_cost=total_setup,
        total_holding_cost=total_holding,
        n_orders=len(orders),
        method=_t("inventory.modelo.wagner_whitin.wagner_whitin"),
        params={"setup_cost": K, "holding_cost": h},
    )


# ---------------------------------------------------------------------------
# (r, Q) Continuous review policy
# ---------------------------------------------------------------------------

@dataclass
class RQPolicyResult:
    """Resultado de la política de inventario (r, Q) de revisión continua.

    Attributes
    ----------
    order_qty : float
        Cantidad de pedido Q* basada en el EOQ.
    reorder_point : float
        Punto de reorden r = demanda media durante el tiempo de entrega + stock de seguridad.
    safety_stock : float
        Stock de seguridad SS = z · σ_DLT.
    service_level : float
        Nivel de servicio por ciclo P(no hay faltante en el ciclo).
    avg_inventory : float
        Inventario promedio disponible ≈ Q*/2 + SS.
    total_cost : float
        Costo anual de mantener + ordenar en (Q*, r).
    """

    order_qty: float
    reorder_point: float
    safety_stock: float
    service_level: float
    avg_inventory: float
    total_cost: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            _t("inventory.etiqueta.summary.politica_revision_continua_cantidad_pedido", order_qty=self.order_qty, reorder_point=self.reorder_point, safety_stock=self.safety_stock, service_level=self.service_level, avg_inventory=self.avg_inventory, total_cost=self.total_cost)
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "Q*": self.order_qty,
            "r": self.reorder_point,
            _t("inventory.cabecera.to_frame.stock_seguridad"): self.safety_stock,
            _t("inventory.cabecera.to_frame.nivel_servicio"): self.service_level,
            _t("inventory.cabecera.to_frame.inventario_promedio"): self.avg_inventory,
            _t("inventory.cabecera.to_frame.costo_total"): self.total_cost,
        }])


def rq_policy(
    demand_rate: float,
    ordering_cost: float,
    holding_cost: float,
    lead_time: float,
    *,
    demand_std: float = 0.0,
    lead_time_std: float = 0.0,
    service_level: float = 0.95,
) -> RQPolicyResult:
    """Política de inventario (r, Q) de revisión continua.

    Combina el EOQ como cantidad de pedido con un punto de reorden obtenido estadísticamente.
    Ambas decisiones se determinan de forma independiente.

    Parameters
    ----------
    demand_rate : float
        Demanda media por periodo D̄.
    ordering_cost : float
        Costo fijo de ordenar K por pedido.
    holding_cost : float
        Costo de mantener h por unidad y periodo.
    lead_time : float
        Tiempo de entrega medio de reposición L̄.
    demand_std : float
        Desviación estándar de la demanda por periodo σ_D (por defecto 0).
    lead_time_std : float
        Desviación estándar del tiempo de entrega σ_L (por defecto 0).
    service_level : float
        Nivel de servicio por ciclo ∈ (0, 1). Por defecto 0.95.

    Returns
    -------
    RQPolicyResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``service_level`` no está estrictamente entre 0 y 1.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = rq_policy(
    ...     demand_rate=100.0,
    ...     ordering_cost=50.0,
    ...     holding_cost=2.0,
    ...     lead_time=2.0,
    ...     demand_std=5.0,
    ... )
    >>> round(r.order_qty, 4)
    70.7107
    """
    from statistics import NormalDist
    D   = as_positive(demand_rate,  "demand_rate")
    K   = as_positive(ordering_cost, "ordering_cost")
    h   = as_positive(holding_cost,  "holding_cost")
    LT  = as_positive(lead_time,     "lead_time")
    sd  = as_nonneg(demand_std,      "demand_std")
    sl  = as_nonneg(lead_time_std,   "lead_time_std")
    svc = as_fraction(service_level, "service_level")
    if svc <= 0.0 or svc >= 1.0:
        raise ValueError(_t("inventory.error.reorder_point.service_level_debe_estar_estrictamente"))

    Q   = math.sqrt(2 * D * K / h)
    mean_dlt = D * LT
    std_dlt  = math.sqrt(LT * sd**2 + D**2 * sl**2)
    z   = NormalDist().inv_cdf(svc)
    SS  = z * std_dlt
    r   = mean_dlt + SS
    avg_inv  = Q / 2 + SS
    total_cost = (D / Q) * K + avg_inv * h

    return RQPolicyResult(
        order_qty=Q,
        reorder_point=r,
        safety_stock=SS,
        service_level=svc,
        avg_inventory=avg_inv,
        total_cost=total_cost,
        params={"demand_rate": D, "ordering_cost": K, "holding_cost": h,
                "lead_time": LT, "demand_std": sd, "lead_time_std": sl},
    )


# ---------------------------------------------------------------------------
# (R, S) Periodic review policy
# ---------------------------------------------------------------------------

@dataclass
class RSPolicyResult:
    """Resultado de la política de inventario (R, S) de revisión periódica.

    Attributes
    ----------
    review_period : float
        Intervalo de revisión R.
    order_up_to : float
        Nivel de reposición S = demanda media en (R+L) + stock de seguridad.
    safety_stock : float
        Stock de seguridad SS = z · σ_{R+L}.
    service_level : float
        Nivel de servicio por ciclo.
    avg_inventory : float
        Inventario promedio disponible ≈ D·R/2 + SS.
    total_cost : float
        Costo anual de mantener + ordenar en (R, S).
    """

    review_period: float
    order_up_to: float
    safety_stock: float
    service_level: float
    avg_inventory: float
    total_cost: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            _t("inventory.etiqueta.summary.politica_revision_periodica_periodo_revision", review_period=self.review_period, order_up_to=self.order_up_to, safety_stock=self.safety_stock, service_level=self.service_level, avg_inventory=self.avg_inventory, total_cost=self.total_cost)
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "R": self.review_period,
            "S": self.order_up_to,
            _t("inventory.cabecera.to_frame.stock_seguridad"): self.safety_stock,
            _t("inventory.cabecera.to_frame.nivel_servicio"): self.service_level,
            _t("inventory.cabecera.to_frame.inventario_promedio"): self.avg_inventory,
            _t("inventory.cabecera.to_frame.costo_total"): self.total_cost,
        }])


def rs_policy(
    demand_rate: float,
    ordering_cost: float,
    holding_cost: float,
    lead_time: float,
    review_period: float,
    *,
    demand_std: float = 0.0,
    lead_time_std: float = 0.0,
    service_level: float = 0.95,
) -> RSPolicyResult:
    """Política de inventario (R, S) de revisión periódica.

    La posición de inventario se revisa cada R periodos y se emite un pedido
    para llevarla hasta S.

    Parameters
    ----------
    demand_rate : float
        Demanda media por periodo D̄.
    ordering_cost : float
        Costo fijo de ordenar K por pedido.
    holding_cost : float
        Costo de mantener h por unidad y periodo.
    lead_time : float
        Tiempo de entrega medio de reposición L̄.
    review_period : float
        Intervalo de revisión R (periodos entre revisiones de inventario).
    demand_std : float
        Desviación estándar de la demanda por periodo σ_D (por defecto 0).
    lead_time_std : float
        Desviación estándar del tiempo de entrega σ_L (por defecto 0).
    service_level : float
        Nivel de servicio por ciclo ∈ (0, 1). Por defecto 0.95.

    Returns
    -------
    RSPolicyResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``service_level`` no está estrictamente entre 0 y 1.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = rs_policy(
    ...     demand_rate=100.0,
    ...     ordering_cost=50.0,
    ...     holding_cost=2.0,
    ...     lead_time=2.0,
    ...     review_period=1.0,
    ...     demand_std=5.0,
    ... )
    >>> round(r.total_cost, 4)
    178.4897
    """
    from statistics import NormalDist
    D   = as_positive(demand_rate,   "demand_rate")
    K   = as_positive(ordering_cost, "ordering_cost")
    h   = as_positive(holding_cost,  "holding_cost")
    LT  = as_positive(lead_time,     "lead_time")
    R   = as_positive(review_period, "review_period")
    sd  = as_nonneg(demand_std,      "demand_std")
    sl  = as_nonneg(lead_time_std,   "lead_time_std")
    svc = as_fraction(service_level, "service_level")
    if svc <= 0.0 or svc >= 1.0:
        raise ValueError(_t("inventory.error.reorder_point.service_level_debe_estar_estrictamente"))

    # Exposure period = R + L
    RL = R + LT
    mean_rl = D * RL
    std_rl  = math.sqrt(RL * sd**2 + D**2 * sl**2)
    z       = NormalDist().inv_cdf(svc)
    SS      = z * std_rl
    S       = mean_rl + SS
    avg_inv = D * R / 2 + SS
    total_cost = (1.0 / R) * K + avg_inv * h

    return RSPolicyResult(
        review_period=R,
        order_up_to=S,
        safety_stock=SS,
        service_level=svc,
        avg_inventory=avg_inv,
        total_cost=total_cost,
        params={"demand_rate": D, "ordering_cost": K, "holding_cost": h,
                "lead_time": LT, "review_period": R, "demand_std": sd,
                "lead_time_std": sl},
    )


# ---------------------------------------------------------------------------
# Exchange curves
# ---------------------------------------------------------------------------

@dataclass
class ExchangeCurveResult:
    """Resultado agregado de la curva de intercambio para una familia de artículos.

    Attributes
    ----------
    n_orders_eoq : float
        Total de pedidos por año en el punto de EOQ individual (k = 1).
    investment_eoq : float
        Inversión promedio total en inventario en el punto EOQ.
    multiplier : float
        Factor de escala k aplicado a todas las cantidades EOQ (k = 1 → EOQ).
    n_orders_optimal : float
        Total de pedidos por año en el punto de política elegido.
    investment_optimal : float
        Inversión promedio total en inventario en el punto de política elegido.
    target : str
        Descripción del objetivo usado (``'eoq'``, ``'orders'`` o
        ``'investment'``).
    optimal_quantities : list[dict]
        Diccionarios por artículo con las claves ``name``, ``Q_eoq``, ``Q_optimal``,
        ``n_orders``, ``investment``.
    curve_points : list[dict]
        Puntos de la hipérbola de intercambio: ``[{'N': …, 'I': …}, …]``.
    """

    n_orders_eoq: float
    investment_eoq: float
    multiplier: float
    n_orders_optimal: float
    investment_optimal: float
    target: str
    optimal_quantities: list
    curve_points: list

    def to_frame(self) -> pd.DataFrame:
        """DataFrame de cantidades por artículo: artículo, Q_eoq, Q_óptima, n_pedidos, inversión."""
        import pandas as pd
        return pd.DataFrame(self.optimal_quantities).rename(columns=_cabeceras(_COL_CANTIDADES))

    def curve_to_frame(self) -> pd.DataFrame:
        """DataFrame de la hipérbola de intercambio: columnas N (pedidos/año) e I (inversión)."""
        import pandas as pd
        return pd.DataFrame(self.curve_points).rename(columns=_cabeceras(_COL_CURVA_CICLO))

    def summary(self) -> str:
        lines = [
            _t("inventory.etiqueta.summary.objetivo", target=self.target),
            _t("inventory.etiqueta.summary.multiplicador", multiplier=self.multiplier),
            _t("inventory.etiqueta.summary.pedidos_ano_eoq", n_orders_eoq=self.n_orders_eoq),
            _t("inventory.etiqueta.summary.pedidos_ano_optimo", n_orders_optimal=self.n_orders_optimal),
            _t("inventory.etiqueta.summary.inversion_eoq", investment_eoq=self.investment_eoq),
            _t("inventory.etiqueta.summary.inversion_optimo", investment_optimal=self.investment_optimal),
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def exchange_curve(
    items: list,
    *,
    target_orders: float | None = None,
    target_investment: float | None = None,
    n_curve_points: int = 50,
) -> ExchangeCurveResult:
    """Curva de intercambio agregada para una familia de artículos de inventario.

    Para una familia de artículos gestionados cada uno con política EOQ, variar un
    multiplicador común *k* sobre todas las cantidades de pedido traza una hipérbola en el plano
    (N pedidos/año, inversión promedio):

        N(k) = N* / k        I(k) = k · I*       →    N · I = N* · I*

    La función calcula el punto EOQ (k=1) y, si se indica una meta, resuelve el k que la
    cumple y reescala todas las cantidades.

    Parameters
    ----------
    items : list of dict
        Cada diccionario debe contener:

        - ``demand`` (float) — demanda anual Di.
        - ``ordering_cost`` (float) — costo de preparación u ordenar Ki.
        - ``holding_cost`` (float) — costo de mantener por unidad y año hi.

        Claves opcionales:

        - ``unit_value`` (float) — valor unitario vi para calcular la inversión
          (por defecto 1).
        - ``name`` (str) — etiqueta del artículo (por defecto ``'I1'``, ``'I2'``, …).

    target_orders : float, optional
        Total de pedidos por año deseado. Resuelve k = N* / target_orders.
    target_investment : float, optional
        Inversión promedio total en inventario deseada. Resuelve k = target / I*.
    n_curve_points : int
        Número de puntos de la hipérbola graficada (por defecto 50).

    Returns
    -------
    ExchangeCurveResult

    Notes
    -----
    Solo se puede indicar uno de *target_orders* o *target_investment*.
    Si no se da ninguno se devuelve el punto EOQ (k = 1).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``items`` está vacío o algún elemento no es un diccionario con las claves requeridas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = exchange_curve(
    ...     items=[{'name': 'A', 'demand': 1000, 'ordering_cost': 50, 'holding_cost': 2, 'unit_value': 10}, {'name': 'B', 'demand': 500, 'ordering_cost': 30, 'holding_cost': 1, 'unit_value': 5}],
    ...     target_orders=10.0,
    ... )
    >>> round(r.n_orders_eoq, 4)
    7.3589
    """
    if target_orders is not None and target_investment is not None:
        raise ValueError(
            _t("inventory.error.exchange_curve.indique_como_maximo_uno_target")
        )
    if len(items) == 0:
        raise ValueError(_t("inventory.error.exchange_curve.items_debe_contener_menos_elemento"))

    parsed: list[dict[str, Any]] = []
    for idx, it in enumerate(items):
        D  = as_positive(float(it["demand"]),        f"items[{idx}]['demand']")
        K  = as_positive(float(it["ordering_cost"]), f"items[{idx}]['ordering_cost']")
        h  = as_positive(float(it["holding_cost"]),  f"items[{idx}]['holding_cost']")
        v  = float(it.get("unit_value", 1.0))
        nm = str(it.get("name", _t("inventory.valor_por_defecto.exchange_curve.texto", expr=idx + 1)))
        if v <= 0:
            raise ValueError(_t("inventory.error.exchange_curve.items_unit_value_debe_ser", idx=idx))
        Q_eoq = math.sqrt(2 * D * K / h)
        parsed.append({"name": nm, "D": D, "K": K, "h": h, "v": v, "Q_eoq": Q_eoq})

    N_star = sum(p["D"] / p["Q_eoq"] for p in parsed)
    I_star = sum(p["Q_eoq"] * p["v"] / 2.0 for p in parsed)

    if target_orders is not None:
        to = as_positive(target_orders, "target_orders")
        k = N_star / to
        target_label = _t("inventory.etiqueta.exchange_curve.pedidos", to=to)
    elif target_investment is not None:
        ti = as_positive(target_investment, "target_investment")
        k = ti / I_star
        target_label = _t("inventory.etiqueta.exchange_curve.inversion", ti=ti)
    else:
        k = 1.0
        target_label = _t("inventory.etiqueta.exchange_curve.eoq")

    N_opt = N_star / k
    I_opt = k * I_star

    opt_qtys = []
    for p in parsed:
        Q_opt = k * p["Q_eoq"]
        n_i   = p["D"] / Q_opt
        inv_i = Q_opt * p["v"] / 2.0
        opt_qtys.append({
            "name":       p["name"],
            "Q_eoq":      round(p["Q_eoq"], 6),
            "Q_optimal":  round(Q_opt, 6),
            "n_orders":   round(n_i, 6),
            "investment": round(inv_i, 6),
        })

    # Hyperbola points: vary k from 0.1 to 5 × EOQ point
    product = N_star * I_star
    n_min = N_star * 0.1
    n_max = N_star * 10.0
    step  = (n_max - n_min) / (n_curve_points - 1)
    curve_pts = [
        {"N": round(n_min + i * step, 6),
         "I": round(product / (n_min + i * step), 6)}
        for i in range(n_curve_points)
    ]

    return ExchangeCurveResult(
        n_orders_eoq=N_star,
        investment_eoq=I_star,
        multiplier=k,
        n_orders_optimal=N_opt,
        investment_optimal=I_opt,
        target=target_label,
        optimal_quantities=opt_qtys,
        curve_points=curve_pts,
    )


# ---------------------------------------------------------------------------
# Safety-stock exchange curve (Type 2)
# ---------------------------------------------------------------------------

@dataclass
class SafetyStockCurveResult:
    """Resultado de la curva de intercambio de stock de seguridad para una familia de artículos.

    Usa una política de **z común** para todos los artículos, que es el enfoque
    agregado estándar: todos comparten el mismo nivel de servicio por ciclo Φ(z).

    Attributes
    ----------
    z : float
        Valor z común (cuantil de la normal estándar) aplicado.
    service_level : float
        Nivel de servicio por ciclo = Φ(z).
    ss_investment : float
        Inversión total en stock de seguridad = z · Σ σᵢ_DLT · vᵢ.
    target : str
        Descripción del objetivo usado.
    optimal_quantities : list[dict]
        Diccionarios por artículo: ``name``, ``sigma_dlt``, ``safety_stock``,
        ``investment``, ``reorder_point`` (solo si se indicó ``demand_rate``).
    curve_points : list[dict]
        Puntos de la curva: ``[{'z': …, 'service_level': …,
        'ss_investment': …}, …]``.
    """

    z: float
    service_level: float
    ss_investment: float
    target: str
    optimal_quantities: list
    curve_points: list

    def to_frame(self) -> pd.DataFrame:
        """DataFrame de stock de seguridad por artículo."""
        import pandas as pd
        return pd.DataFrame(self.optimal_quantities).rename(columns=_cabeceras(_COL_CANTIDADES))

    def curve_to_frame(self) -> pd.DataFrame:
        """DataFrame de la curva de intercambio completa: z, nivel_de_servicio, inversión_ss."""
        import pandas as pd
        return pd.DataFrame(self.curve_points).rename(columns=_cabeceras(_COL_CURVA_SEGURIDAD))

    def summary(self) -> str:
        lines = [
            _t("inventory.etiqueta.summary.objetivo_2", target=self.target),
            _t("inventory.etiqueta.summary.texto_4", z=self.z),
            _t("inventory.etiqueta.summary.nivel_servicio", service_level=self.service_level),
            _t("inventory.etiqueta.summary.inversion_ss", ss_investment=self.ss_investment),
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def safety_stock_curve(
    items: list,
    *,
    target_service_level: float | None = None,
    target_ss_investment: float | None = None,
    n_curve_points: int = 60,
) -> SafetyStockCurveResult:
    """Curva de intercambio del stock de seguridad para una familia de artículos (política de z común).

    Con un **z común** todos los artículos comparten el mismo nivel de servicio por ciclo Φ(z).
    Variar z traza la curva de intercambio entre la inversión agregada en SS y
    el nivel de servicio:

        Inversión_SS(z) = z · Σ σᵢ_DLT · vᵢ

    Parameters
    ----------
    items : list of dict
        Cada diccionario debe contener:

        - ``demand_std`` (float) — desviación estándar de la demanda por unidad de tiempo.
        - ``lead_time`` (float) — tiempo de entrega de reposición (misma unidad de tiempo).

        Claves opcionales:

        - ``lead_time_std`` (float) — desviación estándar del tiempo de entrega (por defecto 0).
        - ``demand_rate`` (float) — demanda media por unidad de tiempo; sirve para
          calcular el punto de reorden r = D·L + SS (por defecto: se omite).
        - ``unit_value`` (float) — valor unitario para la inversión (por defecto 1).
        - ``name`` (str) — etiqueta del artículo (por defecto ``'I1'``, ``'I2'``, …).

    target_service_level : float, optional
        Nivel de servicio por ciclo deseado ∈ (0, 1). Resuelve z = Φ⁻¹(NS).
    target_ss_investment : float, optional
        Inversión total en SS deseada. Resuelve z = objetivo / (Σ σᵢ_DLT · vᵢ).
    n_curve_points : int
        Número de puntos de la curva graficada (por defecto 60, z de −2 a 4).

    Returns
    -------
    SafetyStockCurveResult

    Notes
    -----
    Solo se puede indicar uno de *target_service_level* o *target_ss_investment*.
    Si no se da ninguno se usa z = 0 (nivel de servicio del 50 %) como línea base;
    indique ``target_service_level=0.95`` para el valor típico.

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``items`` está vacío o algún elemento no es un diccionario con las claves requeridas.
        Si ``target_service_level`` no está estrictamente entre 0 y 1.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = safety_stock_curve(
    ...     items=[{'name': 'A', 'demand_rate': 100, 'demand_std': 10, 'lead_time': 2, 'unit_value': 10}, {'name': 'B', 'demand_rate': 50, 'demand_std': 5, 'lead_time': 1, 'unit_value': 5}],
    ...     target_service_level=0.95,
    ... )
    >>> round(r.z, 4)
    1.6449
    """
    if target_service_level is not None and target_ss_investment is not None:
        raise ValueError(
            _t("inventory.error.safety_stock_curve.indique_como_maximo_uno_target")
        )
    if len(items) == 0:
        raise ValueError(_t("inventory.error.exchange_curve.items_debe_contener_menos_elemento"))

    _norm = NormalDist()

    parsed: list[dict[str, Any]] = []
    for idx, it in enumerate(items):
        sd   = as_nonneg(float(it["demand_std"]),  f"items[{idx}]['demand_std']")
        L    = as_positive(float(it["lead_time"]), f"items[{idx}]['lead_time']")
        sl   = float(it.get("lead_time_std", 0.0))
        v    = float(it.get("unit_value", 1.0))
        nm   = str(it.get("name", _t("inventory.valor_por_defecto.exchange_curve.texto", expr=idx + 1)))
        D    = it.get("demand_rate")
        D    = float(D) if D is not None else None
        if v <= 0:
            raise ValueError(_t("inventory.error.exchange_curve.items_unit_value_debe_ser", idx=idx))
        if sl < 0:
            raise ValueError(_t("inventory.error.safety_stock_curve.items_lead_time_std_debe", idx=idx))
        # σ_DLT = √(L·σ_D² + D²·σ_L²)  — reduces to σ_D·√L when σ_L=0
        if D is not None and sl > 0:
            sigma_dlt = math.sqrt(L * sd**2 + D**2 * sl**2)
        else:
            sigma_dlt = sd * math.sqrt(L)
        parsed.append({"name": nm, "sigma_dlt": sigma_dlt, "v": v, "D": D, "L": L})

    total_sigma_v = sum(p["sigma_dlt"] * p["v"] for p in parsed)

    # Solve for z
    if target_service_level is not None:
        sl_val = float(target_service_level)
        if not (0.0 < sl_val < 1.0):
            raise ValueError(_t("inventory.error.safety_stock_curve.target_service_level_debe_estar"))
        z = _norm.inv_cdf(sl_val)
        target_label = _t("inventory.etiqueta.safety_stock_curve.nivel_servicio", sl_val=sl_val)
    elif target_ss_investment is not None:
        ti = as_positive(float(target_ss_investment), "target_ss_investment")
        if total_sigma_v == 0.0:
            raise ValueError(
                _t("inventory.error.safety_stock_curve.todos_articulos_tienen_demand_std")
            )
        z = ti / total_sigma_v
        target_label = _t("inventory.etiqueta.safety_stock_curve.inversion_ss", ti=ti)
    else:
        z = 0.0
        target_label = _t("inventory.etiqueta.safety_stock_curve.base")

    sl_result = _norm.cdf(z)
    ss_inv    = z * total_sigma_v

    opt_qtys = []
    for p in parsed:
        ss_i   = z * p["sigma_dlt"]
        inv_i  = z * p["sigma_dlt"] * p["v"]
        row: dict = {
            "name":          p["name"],
            "sigma_dlt":     round(p["sigma_dlt"], 6),
            "safety_stock":  round(ss_i, 6),
            "investment":    round(inv_i, 6),
        }
        if p["D"] is not None:
            row["reorder_point"] = round(p["D"] * p["L"] + ss_i, 6)
        opt_qtys.append(row)

    # Curve: z from −2 to 4
    z_min, z_max = -2.0, 4.0
    step = (z_max - z_min) / (n_curve_points - 1)
    curve_pts = []
    for i in range(n_curve_points):
        zi   = z_min + i * step
        sli  = _norm.cdf(zi)
        ssi  = zi * total_sigma_v
        curve_pts.append({
            "z":             round(zi, 4),
            "service_level": round(sli, 6),
            "ss_investment": round(ssi, 6),
        })

    return SafetyStockCurveResult(
        z=z,
        service_level=sl_result,
        ss_investment=ss_inv,
        target=target_label,
        optimal_quantities=opt_qtys,
        curve_points=curve_pts,
    )


# ---------------------------------------------------------------------------
# ABC / XYZ / ABC-XYZ classification
# ---------------------------------------------------------------------------

@dataclass
class ABCResult:
    """Resultado de la clasificación ABC de Pareto.

    Attributes
    ----------
    items : list[dict]
        Artículos ordenados de mayor a menor valor anual; cada diccionario tiene las claves
        ``name``, ``demand``, ``unit_value``, ``annual_value``,
        ``cumulative_pct``, ``pct_value``, ``rank``, ``class``.
    class_summary : dict
        ``{A: {count, pct_items, pct_value}, B: …, C: …}``.
    total_value : float
        Valor anual total del inventario.
    thresholds : dict
        ``{a: float, b: float}`` usados en la clasificación.
    """

    items: list
    class_summary: dict
    total_value: float
    thresholds: dict

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.items).rename(columns=_cabeceras(_COL_ARTICULOS))

    def summary(self) -> str:
        lines = [
            _t("inventory.etiqueta.summary.valor_anual_total", total_value=self.total_value),
            f"{_t('inventory.texto_en_expresion.summary.clase'):<6} {_t('inventory.texto_en_expresion.summary.artic_2'):>6}  {_t('inventory.texto_en_expresion.summary.artic'):>7}  {_t('inventory.texto_en_expresion.summary.valor'):>7}",
            "-" * 32,
        ]
        for cls in [_t("inventory.etiqueta.summary.texto"), _t("inventory.etiqueta.summary.texto_2"), _t("inventory.etiqueta.summary.texto_3")]:
            s = self.class_summary[cls]
            lines.append(
                f"  {cls}    {s['count']:>4}    {s['pct_items']:>6.1%}   {s['pct_value']:>6.1%}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


@dataclass
class XYZResult:
    """Resultado de la clasificación XYZ por variabilidad de la demanda.

    Attributes
    ----------
    items : list[dict]
        Cada diccionario tiene las claves ``name``, ``cv``, ``class``.
    class_summary : dict
        ``{X: {count, pct_items}, Y: …, Z: …}``.
    thresholds : dict
        ``{x: float, y: float}`` límites de CV.
    """

    items: list
    class_summary: dict
    thresholds: dict

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.items).rename(columns=_cabeceras(_COL_ARTICULOS))

    def summary(self) -> str:
        t = self.thresholds
        ranges = {
            _t("inventory.etiqueta.summary.texto_5"): _t("inventory.etiqueta.summary.cv_2", expr=t['x']),
            _t("inventory.etiqueta.summary.texto_6"): _t("inventory.etiqueta.summary.cv_3", expr=t['x'], expr2=t['y']),
            _t("inventory.etiqueta.summary.texto_7"): _t("inventory.etiqueta.summary.cv", expr=t['y']),
        }
        lines = [
            f"{_t('inventory.texto_en_expresion.summary.clase'):<6} {_t('inventory.texto_en_expresion.summary.artic_2'):>6}  {_t('inventory.texto_en_expresion.summary.artic'):>7}  {_t('inventory.texto_en_expresion.summary.rango_cv')}",
            "-" * 42,
        ]
        for cls in [_t("inventory.etiqueta.summary.texto_5"), _t("inventory.etiqueta.summary.texto_6"), _t("inventory.etiqueta.summary.texto_7")]:
            s = self.class_summary[cls]
            lines.append(
                f"  {cls}    {s['count']:>4}    {s['pct_items']:>6.1%}   {ranges[cls]}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


@dataclass
class ABCXYZResult:
    """Resultado de la clasificación combinada ABC-XYZ.

    Attributes
    ----------
    items : list[dict]
        Cada diccionario tiene las claves ``name``, ``annual_value``, ``cv``,
        ``abc_class``, ``xyz_class``, ``combined_class``.
    matrix : dict
        ``{(abc, xyz): conteo}`` para las 9 celdas.
    """

    items: list
    matrix: dict

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.items).rename(columns=_cabeceras(_COL_ARTICULOS))

    def matrix_frame(self) -> pd.DataFrame:
        """Tabla dinámica ABC (filas) × XYZ (columnas) con el conteo de artículos."""
        import pandas as pd
        data = {
            xyz: {abc: self.matrix.get((abc, xyz), 0) for abc in ["A", "B", "C"]}
            for xyz in ["X", "Y", "Z"]
        }
        return pd.DataFrame(data, index=["A", "B", "C"])

    def summary(self) -> str:
        lines = [_t("inventory.etiqueta.summary.abc_xyz_total")]
        for abc in [_t("inventory.etiqueta.summary.texto"), _t("inventory.etiqueta.summary.texto_2"), _t("inventory.etiqueta.summary.texto_3")]:
            row_total = sum(self.matrix.get((abc, xyz), 0) for xyz in [_t("inventory.etiqueta.summary.texto_5"), _t("inventory.etiqueta.summary.texto_6"), _t("inventory.etiqueta.summary.texto_7")])
            lines.append(
                f"   {abc}    "
                + "".join(f"  {self.matrix.get((abc, xyz), 0):3d}" for xyz in [_t("inventory.etiqueta.summary.texto_5"), _t("inventory.etiqueta.summary.texto_6"), _t("inventory.etiqueta.summary.texto_7")])
                + f"   {row_total:4d}"
            )
        col_totals = [sum(self.matrix.get((abc, xyz), 0) for abc in [_t("inventory.etiqueta.summary.texto"), _t("inventory.etiqueta.summary.texto_2"), _t("inventory.etiqueta.summary.texto_3")]) for xyz in [_t("inventory.etiqueta.summary.texto_5"), _t("inventory.etiqueta.summary.texto_6"), _t("inventory.etiqueta.summary.texto_7")]]
        grand = sum(col_totals)
        lines.append(_t("inventory.etiqueta.summary.total") + "".join(f"  {c:3d}" for c in col_totals) + f"   {grand:4d}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def _leer_items(items, nombre: str = "items") -> list:
    """Valida que ``items`` sea una lista no vacía de diccionarios."""
    if isinstance(items, (str, bytes, dict)) or not hasattr(items, "__iter__"):
        raise TypeError(_t("inventory.error.leer_items.debe_ser_lista_diccionarios_recibio", nombre=nombre, __name__=type(items).__name__))
    items = list(items)
    if not items:
        raise ValueError(_t("inventory.error.leer_items.debe_contener_menos_elemento", nombre=nombre))
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise TypeError(_t("inventory.error.leer_items.debe_ser_diccionario_recibio", nombre=nombre, i=i, __name__=type(it).__name__))
    return items


def _clave(it: dict, i: int, clave: str, nombre: str = "items"):
    """Devuelve ``it[clave]`` o lanza un ValueError que indica el elemento y la clave que faltan."""
    if clave not in it:
        raise ValueError(_t("inventory.error.clave.falta_clave", nombre=nombre, i=i, clave=clave))
    return it[clave]


def abc_analysis(
    items: list,
    *,
    a_threshold: float = 0.80,
    b_threshold: float = 0.95,
) -> ABCResult:
    """Clasificación ABC de Pareto de artículos de inventario por valor anual.

    Los artículos se ordenan de mayor a menor valor anual (demanda × valor_unitario).
    La clasificación sigue el porcentaje acumulado del valor total:

    - **A**: artículos cuyo valor acumulado aún no ha superado
      *a_threshold* (típicamente ~80 % del valor, ~20 % de los artículos).
    - **B**: la siguiente banda hasta *b_threshold* (~15 % del valor).
    - **C**: el resto (~5 % del valor, ~50 % de los artículos).

    Parameters
    ----------
    items : list of dict
        Cada diccionario debe tener ``'demand'`` (demanda anual) y
        ``'unit_value'``. Clave opcional ``'name'``.
    a_threshold : float
        Fracción de valor acumulado que cierra la clase A (por defecto 0.80).
    b_threshold : float
        Fracción de valor acumulado que cierra la clase B (por defecto 0.95).

    Returns
    -------
    ABCResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``items`` está vacío o algún elemento no es un diccionario con las claves requeridas.
        Si los umbrales no cumplen 0 < a < b < 1 o el valor anual total es cero.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = abc_analysis(
    ...     items=[{'name': 'A', 'demand': 50, 'unit_value': 10, 'cv': 0.2}, {'name': 'B', 'demand': 30, 'unit_value': 10, 'cv': 0.7}, {'name': 'C', 'demand': 100, 'unit_value': 1, 'cv': 1.5}],
    ... )
    >>> round(r.total_value, 4)
    900.0
    """
    items = _leer_items(items)
    if not (0.0 < a_threshold < b_threshold < 1.0):
        raise ValueError(_t("inventory.error.abc_analysis.debe_cumplirse_threshold_threshold"))

    enriched: list[dict[str, Any]] = []
    for i, it in enumerate(items):
        nm  = it.get("name", _t("inventory.valor_por_defecto.abc_analysis.articulo", expr=i + 1))
        D   = as_nonneg(_clave(it, i, "demand"), f"items[{i}]['demand']")
        v   = as_positive(_clave(it, i, "unit_value"), f"items[{i}]['unit_value']")
        enriched.append({"name": str(nm), "demand": D, "unit_value": v,
                         "annual_value": D * v, "index": i})

    enriched.sort(key=lambda x: -x["annual_value"])
    n           = len(enriched)
    total_value = sum(e["annual_value"] for e in enriched)
    if total_value <= 0.0:
        raise ValueError(_t("inventory.error.abc_analysis.valor_anual_total_cero_todas"))

    cum = 0.0
    class_agg: dict = {"A": {"count": 0, "value": 0.0},
                        "B": {"count": 0, "value": 0.0},
                        "C": {"count": 0, "value": 0.0}}
    for i, e in enumerate(enriched):
        prev_pct = cum / total_value
        cum += e["annual_value"]
        e["cumulative_pct"] = cum / total_value
        e["pct_value"]      = e["annual_value"] / total_value
        e["rank"]           = i + 1
        if prev_pct < a_threshold:
            cls = "A"
        elif prev_pct < b_threshold:
            cls = "B"
        else:
            cls = "C"
        e["class"] = cls
        class_agg[cls]["count"] += 1
        class_agg[cls]["value"] += e["annual_value"]

    class_summary = {
        cls: {
            "count":     class_agg[cls]["count"],
            "pct_items": class_agg[cls]["count"] / n,
            "pct_value": class_agg[cls]["value"] / total_value,
        }
        for cls in ["A", "B", "C"]
    }

    return ABCResult(
        items=enriched,
        class_summary=class_summary,
        total_value=total_value,
        thresholds={"a": a_threshold, "b": b_threshold},
    )


def xyz_analysis(
    items: list,
    *,
    x_threshold: float = 0.5,
    y_threshold: float = 1.0,
) -> XYZResult:
    """Clasificación XYZ de artículos de inventario por variabilidad de la demanda (CV).

    - **X**: CV ≤ *x_threshold* — demanda estable y predecible.
    - **Y**: *x_threshold* < CV ≤ *y_threshold* — variabilidad moderada.
    - **Z**: CV > *y_threshold* — errática, difícil de pronosticar.

    Parameters
    ----------
    items : list of dict
        Cada diccionario debe aportar el coeficiente de variación de una de dos formas:

        - ``'cv'`` directamente, **o**
        - ``'demand_std'`` **+** (``'demand_mean'`` o ``'demand_rate'``).

        Clave opcional ``'name'``.
    x_threshold : float
        Límite superior de CV de la clase X (por defecto 0.5).
    y_threshold : float
        Límite superior de CV de la clase Y (por defecto 1.0).

    Returns
    -------
    XYZResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``items`` está vacío o algún elemento no es un diccionario con las claves requeridas.
        Si los umbrales no cumplen 0 ≤ x < y o falta el CV (o la desviación y la media).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = xyz_analysis([{"name": "a", "cv": 0.2}, {"name": "b", "cv": 0.7}, {"name": "c", "cv": 1.5}])
    >>> [e["class"] for e in r.items]
    ['X', 'Y', 'Z']
    """
    items = _leer_items(items)
    if not (0.0 <= x_threshold < y_threshold):
        raise ValueError(_t("inventory.error.xyz_analysis.debe_cumplirse_threshold_threshold"))

    enriched: list[dict[str, Any]] = []
    for i, it in enumerate(items):
        nm = it.get("name", _t("inventory.valor_por_defecto.abc_analysis.articulo", expr=i + 1))
        if "cv" in it:
            cv = as_nonneg(it["cv"], f"items[{i}]['cv']")
        else:
            std  = as_nonneg(_clave(it, i, "demand_std"), f"items[{i}]['demand_std']")
            if "demand_mean" in it:
                mean = it["demand_mean"]
            elif "demand_rate" in it:
                mean = it["demand_rate"]
            else:
                raise ValueError(_t("inventory.error.xyz_analysis.items_falta_cv_demand_std", i=i))
            mean = as_positive(mean, f"items[{i}]['demand_mean']")
            cv = std / mean
        if cv <= x_threshold:
            cls = "X"
        elif cv <= y_threshold:
            cls = "Y"
        else:
            cls = "Z"
        enriched.append({"name": str(nm), "cv": cv, "class": cls})

    n = len(enriched)
    class_agg: dict = {"X": 0, "Y": 0, "Z": 0}
    for e in enriched:
        class_agg[e["class"]] += 1

    class_summary = {
        cls: {"count": class_agg[cls], "pct_items": class_agg[cls] / n}
        for cls in ["X", "Y", "Z"]
    }

    return XYZResult(
        items=enriched,
        class_summary=class_summary,
        thresholds={"x": x_threshold, "y": y_threshold},
    )


def abc_xyz(
    items: list,
    *,
    a_threshold: float = 0.80,
    b_threshold: float = 0.95,
    x_threshold: float = 0.5,
    y_threshold: float = 1.0,
) -> ABCXYZResult:
    """Clasificación combinada ABC-XYZ.

    Cada artículo requiere los campos de ABC (``demand``, ``unit_value``) y
    de XYZ (``cv`` o ``demand_std`` + ``demand_mean``/``demand_rate``).

    Parameters
    ----------
    items : list of dict
        Debe aportar los campos que exigen :func:`abc_analysis` y
        :func:`xyz_analysis`. ``name`` es opcional.
    a_threshold, b_threshold : float
        Umbrales ABC (ver :func:`abc_analysis`).
    x_threshold, y_threshold : float
        Umbrales XYZ (ver :func:`xyz_analysis`).

    Returns
    -------
    ABCXYZResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``items`` está vacío o algún elemento no es un diccionario con las claves requeridas.
        Si algún umbral es inválido.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = abc_xyz([{"name": "a", "demand": 100, "unit_value": 10, "cv": 0.2},
    ...             {"name": "b", "demand": 5, "unit_value": 1, "cv": 1.5}])
    >>> [e["combined_class"] for e in r.items]
    ['AX', 'CZ']
    """
    abc_r = abc_analysis(items, a_threshold=a_threshold, b_threshold=b_threshold)
    xyz_r = xyz_analysis(items, x_threshold=x_threshold, y_threshold=y_threshold)

    combined = []
    matrix: dict = {}
    for e_abc in abc_r.items:
        nm      = e_abc["name"]
        e_xyz   = xyz_r.items[e_abc["index"]]
        abc_cls = e_abc["class"]
        xyz_cls = e_xyz["class"]
        key     = (abc_cls, xyz_cls)
        matrix[key] = matrix.get(key, 0) + 1
        combined.append({
            "name":          nm,
            "annual_value":  e_abc["annual_value"],
            "cv":            e_xyz["cv"],
            "abc_class":     abc_cls,
            "xyz_class":     xyz_cls,
            "combined_class": f"{abc_cls}{xyz_cls}",
        })

    return ABCXYZResult(items=combined, matrix=matrix)


# ---------------------------------------------------------------------------
# MRP — single-level Material Requirements Planning
# ---------------------------------------------------------------------------

@dataclass
class MRPResult:
    """Resultado del MRP de un nivel.

    Attributes
    ----------
    item_name : str
    periods : list
        Etiquetas de periodo (1, 2, … o las que indique la persona usuaria).
    gross_requirements : list[float]
    scheduled_receipts : list[float]
    projected_on_hand : list[float]
        Inventario disponible al final de cada periodo tras todas las transacciones.
    net_requirements : list[float]
    planned_receipts : list[float]
        Recepciones planificadas de órdenes que llegan en el periodo.
    planned_releases : list[float]
        Liberaciones planificadas de órdenes (emitidas *lead_time* periodos antes de la recepción).
    past_due_releases : float
        Cantidad total de órdenes planificadas cuya liberación debió ocurrir antes del
        periodo 1 (el lead time no cabe en el horizonte); no aparece en ``planned_releases``.
    """

    item_name: str
    periods: list
    gross_requirements: list
    scheduled_receipts: list
    projected_on_hand: list
    net_requirements: list
    planned_receipts: list
    planned_releases: list
    past_due_releases: float = 0.0

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame({
            _t("inventory.cabecera.to_frame.periodo"):         self.periods,
            _t("inventory.cabecera.to_frame.req_bruto"):       self.gross_requirements,
            _t("inventory.cabecera.to_frame.recep_prog"):      self.scheduled_receipts,
            _t("inventory.cabecera.to_frame.exist_proy"):      self.projected_on_hand,
            _t("inventory.cabecera.to_frame.req_neto"):        self.net_requirements,
            _t("inventory.cabecera.to_frame.recep_plan"):      self.planned_receipts,
            _t("inventory.cabecera.to_frame.lib_plan"):        self.planned_releases,
        })

    def summary(self) -> str:
        hdr = f"{_t('inventory.texto_en_expresion.summary.periodo'):>8} {_t('inventory.texto_en_expresion.summary.rb'):>8} {_t('inventory.texto_en_expresion.summary.rp'):>8} {_t('inventory.texto_en_expresion.summary.ep'):>8} {_t('inventory.texto_en_expresion.summary.rn'):>8} {_t('inventory.texto_en_expresion.summary.rpl'):>8} {_t('inventory.texto_en_expresion.summary.lpl'):>8}"
        lines = [_t("inventory.etiqueta.summary.articulo", item_name=self.item_name), hdr, "-" * len(hdr)]
        for i, p in enumerate(self.periods):
            lines.append(
                f"{p!s:>8} {self.gross_requirements[i]:>8.2f}"
                f" {self.scheduled_receipts[i]:>8.2f}"
                f" {self.projected_on_hand[i]:>8.2f}"
                f" {self.net_requirements[i]:>8.2f}"
                f" {self.planned_receipts[i]:>8.2f}"
                f" {self.planned_releases[i]:>8.2f}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def mrp(
    gross_requirements: Sequence[float],
    *,
    initial_on_hand: float = 0.0,
    scheduled_receipts: Sequence[float] | None = None,
    lead_time: int = 1,
    lot_size: float | str = "LFL",
    safety_stock: float = 0.0,
    item_name: str | None = None,
    periods: Sequence | None = None,
) -> MRPResult:
    """Planeación de requerimientos de materiales (MRP) de un nivel.

    Calcula la tabla MRP estándar: requerimientos brutos → requerimientos netos →
    recepciones planificadas → liberaciones planificadas de órdenes.

    Parameters
    ----------
    gross_requirements : sequence of float
        Demanda de cada periodo (longitud T).
    initial_on_hand : float
        Inventario disponible al inicio del periodo 1 (por defecto 0).
    scheduled_receipts : sequence of float, optional
        Recepciones ya ordenadas que llegan en cada periodo (longitud T, por defecto todas 0).
    lead_time : int
        Tiempo de entrega de reposición en periodos (por defecto 1).
    lot_size : float or ``'LFL'``
        Política de pedido: ``'LFL'`` (lote por lote) pide exactamente el requerimiento neto;
        un número positivo redondea hacia arriba al múltiplo más cercano de esa cantidad.
    safety_stock : float
        Inventario final mínimo deseado en cada periodo (por defecto 0).
    item_name : str
        Etiqueta del artículo (por defecto ``'Artículo'``, o su traducción según el idioma activo).
    periods : sequence, optional
        Etiquetas de periodo (por defecto 1, 2, …, T).

    Returns
    -------
    MRPResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``gross_requirements`` está vacío, ``lead_time`` no es un entero ≥ 0, ``lot_size`` no es ``'LFL'`` ni positivo, o las longitudes no coinciden.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = mrp([0, 50, 0, 30, 60, 20], initial_on_hand=40, lead_time=1, lot_size=40, safety_stock=10)
    >>> r.planned_receipts
    [0.0, 40.0, 0.0, 40.0, 40.0, 40.0]
    """
    GR  = as_float_list(gross_requirements, "gross_requirements", kind="nonneg")
    T   = len(GR)

    SR  = [0.0] * T
    if scheduled_receipts is not None:
        SR = as_float_list(scheduled_receipts, "scheduled_receipts", kind="nonneg", min_len=0)
        if len(SR) != T:
            raise ValueError(_t("inventory.error.mrp.scheduled_receipts_debe_tener_misma"))

    if isinstance(lead_time, bool) or not isinstance(lead_time, int) or lead_time < 0:
        raise ValueError(_t("inventory.error.mrp.lead_time_debe_ser_entero"))

    SS = as_nonneg(safety_stock, "safety_stock")
    initial_on_hand = as_nonneg(initial_on_hand, "initial_on_hand")
    if item_name is None:
        item_name = _t("inventory.valor_por_defecto.mrp.articulo")
    if isinstance(lot_size, str):
        if lot_size.upper() != "LFL":
            raise ValueError(_t("inventory.error.mrp.lot_size_debe_ser_lfl"))
        lot_q: float | None = None
    else:
        lot_q = as_positive(lot_size, "lot_size")

    if periods is not None and len(list(periods)) != T:
        raise ValueError(_t("inventory.error.mrp.periods_debe_tener_misma_longitud"))

    pds = list(periods) if periods is not None else list(range(1, T + 1))

    OH  = initial_on_hand
    NR_out: list  = [0.0] * T
    PR_out: list  = [0.0] * T
    OH_out: list  = [0.0] * T

    for t in range(T):
        available = OH + SR[t] - GR[t]
        nr = max(0.0, SS - available)
        if nr > 0.0:
            pr = nr if lot_q is None else math.ceil(nr / lot_q) * lot_q
        else:
            pr = 0.0
        OH = available + pr
        NR_out[t] = nr
        PR_out[t] = pr
        OH_out[t] = OH

    # Planned releases: release at period (t - lead_time) for receipt at t
    POR: list = [0.0] * T
    past_due = 0.0
    for t in range(T):
        if PR_out[t] > 0.0:
            rel = t - lead_time
            if rel < 0:
                past_due += PR_out[t]
            else:
                POR[rel] += PR_out[t]
    if past_due > 0.0:
        warnings.warn(
            _t("inventory.aviso.mrp.unidades_planificadas_debieron_liberarse_antes", past_due=past_due, lead_time=lead_time),
            UserWarning, stacklevel=2,
        )

    return MRPResult(
        item_name=item_name,
        periods=pds,
        gross_requirements=GR,
        scheduled_receipts=SR,
        projected_on_hand=OH_out,
        net_requirements=NR_out,
        planned_receipts=PR_out,
        planned_releases=POR,
        past_due_releases=past_due,
    )
