"""Análisis de cuellos de botella en sistemas de producción o servicio con varias estaciones."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ._utils import as_nonempty, as_nonneg, as_positive

if TYPE_CHECKING:
    import matplotlib.pyplot as plt


@dataclass
class StationResult:
    """Métricas de una estación individual en una línea de flujo."""

    name: str
    demand_rate: float
    capacity: float
    utilization: float
    is_bottleneck: bool
    slack: float          # capacity - demand_rate
    params: dict = field(default_factory=dict)


@dataclass
class BottleneckResult:
    """Resultado de un análisis de cuello de botella sobre varias estaciones.

    Attributes
    ----------
    stations : list[StationResult]
        Métricas por estación.
    bottleneck : str
        Nombre de la estación cuello de botella.
    system_throughput : float
        Throughput máximo sostenible (limitado por el cuello de botella).
    demand_rate : float
        Throughput requerido (tasa de llegada al sistema).
    params : dict
    """

    stations: list[StationResult]
    bottleneck: str
    system_throughput: float
    demand_rate: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        """Exporta las métricas por estación como un DataFrame."""
        rows = []
        for s in self.stations:
            rows.append({
                "Estación": s.name,
                "Tasa de demanda": s.demand_rate,
                "Capacidad": s.capacity,
                "Utilización": s.utilization,
                "Holgura": s.slack,
                "Cuello de botella": s.is_bottleneck,
            })
        return pd.DataFrame(rows)

    def summary(self) -> str:
        lines = [
            f"Estación cuello de botella: {self.bottleneck}",
            f"Throughput del sistema    : {self.system_throughput:.6g}",
            f"Tasa de demanda           : {self.demand_rate:.6g}",
            "",
            f"{'Estación':<20} {'Demanda':>10} {'Capacidad':>10} {'Util.':>8} {'Holgura':>10}",
            "-" * 62,
        ]
        for s in self.stations:
            marker = " ← CB" if s.is_bottleneck else ""
            lines.append(
                f"{s.name:<20} {s.demand_rate:>10.4g} {s.capacity:>10.4g} "
                f"{s.utilization:>7.2%} {s.slack:>10.4g}{marker}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> plt.Figure:
        from .plotting import plot_bottleneck
        return plot_bottleneck(self, **kwargs)


def bottleneck_analysis(
    station_names: Sequence[str],
    capacities: Sequence[float],
    demand_rate: float,
    *,
    routing_fractions: Sequence[float] | None = None,
) -> BottleneckResult:
    """Identifica el cuello de botella de un sistema con varias estaciones.

    El cuello de botella es la estación con mayor utilización
    (demand_rate × fracción_de_ruteo / capacidad).

    Parameters
    ----------
    station_names : sequence of str
        Nombres de las estaciones (en orden de flujo).
    capacities : sequence of float
        Throughput máximo de cada estación por unidad de tiempo.
    demand_rate : float
        Tasa de llegada (demanda) que entra al sistema.
    routing_fractions : sequence of float, optional
        Fracción del flujo que visita cada estación. Por defecto 1.0 en
        todas (todas las unidades visitan todas las estaciones en secuencia).

    Returns
    -------
    BottleneckResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = bottleneck_analysis(station_names=['a', 'b'], capacities=[5.0, 3.0], demand_rate=2.0)
    >>> round(r.system_throughput, 4)
    3.0
    """
    station_names  = list(station_names)
    as_nonempty(station_names, "station_names")
    capacities     = [as_positive(c, f"capacity[{i}]") for i, c in enumerate(capacities)]
    demand_rate    = as_positive(demand_rate, "demand_rate")
    n              = len(station_names)

    if len(capacities) != n:
        raise ValueError("'station_names' y 'capacities' deben tener la misma longitud.")

    if routing_fractions is None:
        routing_fractions = [1.0] * n
    elif len(routing_fractions) != n:
        raise ValueError("'routing_fractions' debe tener un valor por estación.")
    routing_fractions = [as_nonneg(f, f"routing_fractions[{i}]") for i, f in enumerate(routing_fractions)]

    demand_rates = [demand_rate * rf for rf in routing_fractions]
    utilizations = [dr / cap for dr, cap in zip(demand_rates, capacities)]
    bn_idx       = int(np.argmax(utilizations))

    stations = [
        StationResult(
            name=name,
            demand_rate=dr,
            capacity=cap,
            utilization=u,
            is_bottleneck=(i == bn_idx),
            slack=cap - dr,
        )
        for i, (name, dr, cap, u) in enumerate(
            zip(station_names, demand_rates, capacities, utilizations)
        )
    ]
    system_throughput = capacities[bn_idx] / routing_fractions[bn_idx] if routing_fractions[bn_idx] > 0 else 0.0

    return BottleneckResult(
        stations=stations,
        bottleneck=station_names[bn_idx],
        system_throughput=system_throughput,
        demand_rate=demand_rate,
    )
