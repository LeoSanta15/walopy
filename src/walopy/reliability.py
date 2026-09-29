"""Reliability engineering: exponential failure model, series/parallel/k-of-n systems."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from ._utils import as_positive, as_nonneg


def _mtbf_numeric(R_func, lam_min: float) -> float:
    """Numerically integrate R(t) from 0 to infinity (trapezoidal, ~10 000 steps)."""
    T = 20.0 / lam_min          # upper bound where R ≈ e^{-20} ≈ 2e-9
    N = 10_000
    dt = T / N
    total = 0.0
    for i in range(N):
        t_mid = (i + 0.5) * dt
        total += R_func(t_mid) * dt
    return total


@dataclass
class ReliabilityResult:
    """System reliability result.

    Attributes
    ----------
    topology : str
        ``'series'``, ``'parallel'``, ``'k-of-n'``, or ``'component'``.
    n_components : int
        Number of components in the system.
    failure_rates : list[float]
        Individual component failure rates λi (failures/time unit).
    mtbf : float
        Mean time between failures of the system.
    t : float or None
        Time at which R(t) was evaluated (if provided).
    R_t : float or None
        System reliability R(t) at the requested t.
    availability : float or None
        Steady-state availability A = MTBF / (MTBF + MTTR), if mttr given.
    mttr : float or None
        Mean time to repair, if provided.
    """

    topology: str
    n_components: int
    failure_rates: list
    mtbf: float
    t: float | None = None
    R_t: float | None = None
    availability: float | None = None
    mttr: float | None = None
    params: dict = field(default_factory=dict)

    def R(self, t: float) -> float:
        """Compute system reliability R(t) using the stored topology."""
        return _r_system(self.topology, self.failure_rates,
                         self.params.get("k"), t)

    def summary(self) -> str:
        lines = [
            f"Topology        : {self.topology}",
            f"Components      : {self.n_components}",
            f"Failure rates λ : {[f'{l:.4g}' for l in self.failure_rates]}",
            f"MTBF            : {self.mtbf:.6g}",
        ]
        if self.t is not None:
            lines.append(f"R(t={self.t:.4g})       : {self.R_t:.6g}")
        if self.availability is not None:
            lines.append(f"Availability    : {self.availability:.4%}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> "pd.DataFrame":
        import pandas as pd
        row: dict = {
            "Topology": self.topology,
            "Components": self.n_components,
            "MTBF": self.mtbf,
        }
        if self.t is not None:
            row[f"R(t={self.t})"] = self.R_t
        if self.availability is not None:
            row["Availability"] = self.availability
        return pd.DataFrame([row])


# ---------------------------------------------------------------------------
# Internal R(t) dispatcher
# ---------------------------------------------------------------------------

def _r_system(topology: str, lams: list, k, t: float) -> float:
    if topology == "series" or topology == "component":
        return math.exp(-sum(lams) * t)
    if topology == "parallel":
        result = 1.0
        for lam in lams:
            result *= (1.0 - math.exp(-lam * t))
        return 1.0 - result
    if topology == "k-of-n":
        lam = lams[0]
        n = len(lams)
        R_i = math.exp(-lam * t)
        F_i = 1.0 - R_i
        total = 0.0
        for j in range(k, n + 1):
            c = math.comb(n, j)
            total += c * (R_i ** j) * (F_i ** (n - j))
        return total
    raise ValueError(f"Unknown topology: {topology!r}")


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def mtbf_analysis(
    failure_rate: float,
    *,
    mttr: float | None = None,
    t: float | None = None,
) -> ReliabilityResult:
    """Single-component reliability with exponential failure distribution.

    Parameters
    ----------
    failure_rate : float
        Failure rate λ (failures per time unit, e.g. 0.01 failures/hour).
    mttr : float, optional
        Mean time to repair. If given, computes steady-state availability.
    t : float, optional
        Time at which R(t) = e^{−λt} is evaluated.

    Returns
    -------
    ReliabilityResult
    """
    lam = as_positive(failure_rate, "failure_rate")
    mtbf_val = 1.0 / lam
    avail = mtbf_val / (mtbf_val + mttr) if mttr is not None else None
    R_t = math.exp(-lam * t) if t is not None else None
    return ReliabilityResult(
        topology="component",
        n_components=1,
        failure_rates=[lam],
        mtbf=mtbf_val,
        t=t,
        R_t=R_t,
        availability=avail,
        mttr=mttr,
    )


def series_system(
    failure_rates: Sequence[float],
    *,
    t: float | None = None,
    mttr: float | None = None,
) -> ReliabilityResult:
    """Reliability of a series system (all components must work).

    R_sys(t) = ∏ e^{−λi·t} = e^{−(Σλi)·t}

    Parameters
    ----------
    failure_rates : sequence of float
        Component failure rates λi.
    t : float, optional
        Time for R(t) evaluation.
    mttr : float, optional
        Mean time to repair for availability calculation.

    Returns
    -------
    ReliabilityResult
    """
    lams = [as_positive(l, f"failure_rates[{i}]") for i, l in enumerate(failure_rates)]
    lam_sys = sum(lams)
    mtbf_val = 1.0 / lam_sys
    avail = mtbf_val / (mtbf_val + mttr) if mttr is not None else None
    R_t = math.exp(-lam_sys * t) if t is not None else None
    return ReliabilityResult(
        topology="series",
        n_components=len(lams),
        failure_rates=lams,
        mtbf=mtbf_val,
        t=t,
        R_t=R_t,
        availability=avail,
        mttr=mttr,
    )


def parallel_system(
    failure_rates: Sequence[float],
    *,
    t: float | None = None,
    mttr: float | None = None,
) -> ReliabilityResult:
    """Reliability of a parallel system (at least one component must work).

    R_sys(t) = 1 − ∏(1 − e^{−λi·t})

    MTBF is computed numerically (∫₀^∞ R_sys(t) dt).

    Parameters
    ----------
    failure_rates : sequence of float
        Component failure rates λi.
    t : float, optional
        Time for R(t) evaluation.
    mttr : float, optional
        Mean time to repair for availability calculation.

    Returns
    -------
    ReliabilityResult
    """
    lams = [as_positive(l, f"failure_rates[{i}]") for i, l in enumerate(failure_rates)]

    def R_func(tt: float) -> float:
        return _r_system("parallel", lams, None, tt)

    mtbf_val = _mtbf_numeric(R_func, min(lams))
    avail = mtbf_val / (mtbf_val + mttr) if mttr is not None else None
    R_t = R_func(t) if t is not None else None
    return ReliabilityResult(
        topology="parallel",
        n_components=len(lams),
        failure_rates=lams,
        mtbf=mtbf_val,
        t=t,
        R_t=R_t,
        availability=avail,
        mttr=mttr,
    )


def koon_system(
    n: int,
    k: int,
    failure_rate: float,
    *,
    t: float | None = None,
    mttr: float | None = None,
) -> ReliabilityResult:
    """Reliability of a k-out-of-n system (at least k of n identical components work).

    All components are identical with failure rate λ.

    R_sys(t) = Σ_{j=k}^{n} C(n,j) · e^{−jλt} · (1 − e^{−λt})^{n−j}

    MTBF (exact, identical exponential):
    MTBF = (1/λ) · Σ_{j=k}^{n} (−1)^{j−k} · C(n,j) · C(j−1, k−1) · (1/j)
    which simplifies to  (1/λ) · Σ_{i=k}^{n} 1/i  for the standard k-of-n.

    Parameters
    ----------
    n : int
        Total number of components.
    k : int
        Minimum number of working components required (1 ≤ k ≤ n).
    failure_rate : float
        Component failure rate λ.
    t : float, optional
        Time for R(t) evaluation.
    mttr : float, optional
        Mean time to repair for availability calculation.

    Returns
    -------
    ReliabilityResult
    """
    if not (1 <= k <= n):
        raise ValueError("Must have 1 ≤ k ≤ n.")
    lam = as_positive(failure_rate, "failure_rate")
    lams = [lam] * n

    # Exact MTBF for k-of-n identical exponential:  (1/λ) * Σ_{j=k}^{n} 1/j
    mtbf_val = (1.0 / lam) * sum(1.0 / j for j in range(k, n + 1))

    avail = mtbf_val / (mtbf_val + mttr) if mttr is not None else None
    R_t = _r_system("k-of-n", lams, k, t) if t is not None else None
    return ReliabilityResult(
        topology="k-of-n",
        n_components=n,
        failure_rates=lams,
        mtbf=mtbf_val,
        t=t,
        R_t=R_t,
        availability=avail,
        mttr=mttr,
        params={"k": k},
    )
