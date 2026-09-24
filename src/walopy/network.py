"""Open Jackson network of queues."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from ._utils import as_positive, as_nonneg, as_int_positive, as_nonempty


@dataclass
class StationMetrics:
    """Per-station metrics in a Jackson network.

    Attributes
    ----------
    name : str
    lam_total : float
        Total arrival rate (external + routed from other stations).
    lam_external : float
        External (Poisson) arrival rate.
    mu : float
        Service rate per server.
    servers : int
        Number of servers.
    rho : float
        Utilization = lam_total / (servers × mu).
    L, Lq, W, Wq : float
        Standard M/M/c metrics.
    """

    name: str
    lam_total: float
    lam_external: float
    mu: float
    servers: int
    rho: float
    L: float
    Lq: float
    W: float
    Wq: float


@dataclass
class JacksonResult:
    """Result of an open Jackson network analysis.

    Attributes
    ----------
    stations : list[StationMetrics]
        Per-station metrics.
    L_system : float
        Total expected customers across all stations (sum of L_j).
    W_system : float
        Mean sojourn time through the network = L_system / total external arrival rate.
    params : dict
    """

    stations: list[StationMetrics]
    L_system: float
    W_system: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> "pd.DataFrame":
        import pandas as pd
        return pd.DataFrame([{
            "Station":   s.name,
            "λ_ext":     s.lam_external,
            "λ_total":   s.lam_total,
            "μ":         s.mu,
            "c":         s.servers,
            "ρ":         s.rho,
            "L":         s.L,
            "Lq":        s.Lq,
            "W":         s.W,
            "Wq":        s.Wq,
        } for s in self.stations])

    def summary(self) -> str:
        hdr = (
            f"{'Station':<20} {'λ_ext':>8} {'λ_tot':>8} {'c':>4} "
            f"{'ρ':>6} {'L':>8} {'Lq':>8} {'W':>10} {'Wq':>10}"
        )
        sep = "-" * len(hdr)
        lines = [hdr, sep]
        for s in self.stations:
            lines.append(
                f"{s.name:<20} {s.lam_external:>8.4g} {s.lam_total:>8.4g} "
                f"{s.servers:>4d} {s.rho:>6.3f} {s.L:>8.4g} {s.Lq:>8.4g} "
                f"{s.W:>10.4g} {s.Wq:>10.4g}"
            )
        lines += [
            sep,
            f"L_system : {self.L_system:.6g}  (total customers in network)",
            f"W_system : {self.W_system:.6g}  (mean sojourn time through network)",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def jackson_network(
    station_names: Sequence[str],
    mu: Sequence[float],
    gamma: Sequence[float],
    routing: Sequence[Sequence[float]],
    *,
    servers: Sequence[int] | None = None,
) -> JacksonResult:
    """Analyse an open Jackson network of queues.

    In an open Jackson network, customers arrive from outside according to
    Poisson processes (rates *gamma*), receive exponential service at each
    station they visit, and are routed probabilistically between stations
    until they leave the system.  By the Jackson theorem each station
    behaves as an independent M/M/c queue with the effective arrival rate
    obtained from the traffic equations.

    Parameters
    ----------
    station_names : sequence of str
        Names of the J stations.
    mu : sequence of float
        Service rate μ_j per server at each station.
    gamma : sequence of float
        External (Poisson) arrival rate γ_j at each station (0 if none).
    routing : (J, J) array-like
        Routing matrix P where P[i][j] = probability of going from
        station *i* to station *j* after service at *i*.
        Rows must sum to ≤ 1; the remaining fraction leaves the system.
    servers : sequence of int, optional
        Number of servers c_j at each station.  Defaults to 1 everywhere.

    Returns
    -------
    JacksonResult

    Raises
    ------
    ValueError
        If the system is unstable (ρ_j ≥ 1 at any station).

    Examples
    --------
    >>> # Two stations in tandem (all customers go station 1 → 2 → exit)
    >>> r = jackson_network(
    ...     ["Intake", "Processing"],
    ...     mu=[10.0, 8.0],
    ...     gamma=[5.0, 0.0],
    ...     routing=[[0.0, 1.0], [0.0, 0.0]],
    ... )
    >>> r.stations[0].lam_total, r.stations[1].lam_total
    (5.0, 5.0)
    """
    names = list(station_names)
    as_nonempty(names, "station_names")
    J = len(names)

    mu_arr    = np.array([as_positive(m, f"mu[{i}]") for i, m in enumerate(mu)], dtype=float)
    gamma_arr = np.array([as_nonneg(g, f"gamma[{i}]") for i, g in enumerate(gamma)], dtype=float)

    if len(mu_arr) != J or len(gamma_arr) != J:
        raise ValueError("'mu', 'gamma' and 'station_names' must have the same length.")

    P = np.array(routing, dtype=float)
    if P.shape != (J, J):
        raise ValueError(f"'routing' must be a ({J}×{J}) matrix, got shape {P.shape}.")
    if np.any(P < 0):
        raise ValueError("All routing probabilities must be ≥ 0.")
    row_sums = P.sum(axis=1)
    if np.any(row_sums > 1.0 + 1e-10):
        raise ValueError("Routing matrix rows must sum to ≤ 1.")

    if servers is None:
        c_arr = np.ones(J, dtype=int)
    else:
        c_arr = np.array([as_int_positive(c, f"servers[{i}]") for i, c in enumerate(servers)], dtype=int)
        if len(c_arr) != J:
            raise ValueError("'servers' must have the same length as 'station_names'.")

    # Traffic equations: λ = γ + P^T λ  →  (I − P^T) λ = γ
    A   = np.eye(J) - P.T
    lam = np.linalg.solve(A, gamma_arr)

    if np.any(lam < 0):
        raise ValueError("Negative effective arrival rates — check routing matrix for closed loops.")

    # Analyse each station as M/M/c
    from .queuing import mmc, mm1

    station_list: list[StationMetrics] = []
    for j in range(J):
        lj  = float(lam[j])
        muj = float(mu_arr[j])
        cj  = int(c_arr[j])
        rho_j = lj / (cj * muj)
        if rho_j >= 1.0:
            raise ValueError(
                f"Station '{names[j]}' is unstable: ρ = {rho_j:.4g} ≥ 1. "
                "Increase capacity or reduce arrival rates."
            )
        res = mm1(lj, muj) if cj == 1 else mmc(lj, muj, cj)
        station_list.append(StationMetrics(
            name=names[j],
            lam_total=lj,
            lam_external=float(gamma_arr[j]),
            mu=muj,
            servers=cj,
            rho=res.rho,
            L=res.L,
            Lq=res.Lq,
            W=res.W,
            Wq=res.Wq,
        ))

    L_system = sum(s.L for s in station_list)
    total_ext = float(gamma_arr.sum())
    W_system  = L_system / total_ext if total_ext > 0 else float("inf")

    return JacksonResult(
        stations=station_list,
        L_system=L_system,
        W_system=W_system,
        params={"J": J, "total_gamma": total_ext},
    )
