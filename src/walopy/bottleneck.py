"""Bottleneck analysis for multi-station production / service systems."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd

from ._utils import as_positive, as_nonneg, as_nonempty


@dataclass
class StationResult:
    """Metrics for a single station in a flow line."""

    name: str
    demand_rate: float
    capacity: float
    utilization: float
    is_bottleneck: bool
    slack: float          # capacity - demand_rate
    params: dict = field(default_factory=dict)


@dataclass
class BottleneckResult:
    """Result of a bottleneck analysis across multiple stations.

    Attributes
    ----------
    stations : list[StationResult]
        Per-station metrics.
    bottleneck : str
        Name of the bottleneck station.
    system_throughput : float
        Maximum sustainable throughput (limited by the bottleneck).
    demand_rate : float
        Required throughput (arrival rate to the system).
    params : dict
    """

    stations: list[StationResult]
    bottleneck: str
    system_throughput: float
    demand_rate: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        """Export per-station metrics as a DataFrame."""
        rows = []
        for s in self.stations:
            rows.append({
                "Station": s.name,
                "Demand rate": s.demand_rate,
                "Capacity": s.capacity,
                "Utilization": s.utilization,
                "Slack": s.slack,
                "Bottleneck": s.is_bottleneck,
            })
        return pd.DataFrame(rows)

    def summary(self) -> str:
        lines = [
            f"Bottleneck station  : {self.bottleneck}",
            f"System throughput   : {self.system_throughput:.6g}",
            f"Demand rate         : {self.demand_rate:.6g}",
            "",
            f"{'Station':<20} {'Demand':>10} {'Capacity':>10} {'Util':>8} {'Slack':>10}",
            "-" * 62,
        ]
        for s in self.stations:
            marker = " ← BN" if s.is_bottleneck else ""
            lines.append(
                f"{s.name:<20} {s.demand_rate:>10.4g} {s.capacity:>10.4g} "
                f"{s.utilization:>7.2%} {s.slack:>10.4g}{marker}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> "plt.Figure":
        from .plotting import plot_bottleneck
        return plot_bottleneck(self, **kwargs)


def bottleneck_analysis(
    station_names: Sequence[str],
    capacities: Sequence[float],
    demand_rate: float,
    *,
    routing_fractions: Sequence[float] | None = None,
) -> BottleneckResult:
    """Identify the bottleneck in a multi-station system.

    The bottleneck is the station with the highest utilization
    (demand_rate × routing_fraction / capacity).

    Parameters
    ----------
    station_names : sequence of str
        Names of the stations (in flow order).
    capacities : sequence of float
        Maximum throughput of each station per unit time.
    demand_rate : float
        Arrival (demand) rate entering the system.
    routing_fractions : sequence of float, optional
        Fraction of the flow visiting each station.  Defaults to 1.0 for
        every station (all units visit all stations sequentially).

    Returns
    -------
    BottleneckResult
    """
    station_names  = list(station_names)
    as_nonempty(station_names, "station_names")
    capacities     = [as_positive(c, f"capacity[{i}]") for i, c in enumerate(capacities)]
    demand_rate    = as_positive(demand_rate, "demand_rate")
    n              = len(station_names)

    if len(capacities) != n:
        raise ValueError("'station_names' and 'capacities' must have the same length.")

    if routing_fractions is None:
        routing_fractions = [1.0] * n
    elif len(routing_fractions) != n:
        raise ValueError("'routing_fractions' must match the number of stations.")
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
