"""Queuing theory models: M/M/1, M/M/c, M/D/1, G/G/1 (Kingman), Little's Law."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ._utils import as_positive, as_nonneg, as_fraction


@dataclass
class QueueResult:
    """Result of a queuing model computation.

    Attributes
    ----------
    model : str
        Model name (e.g. 'M/M/1').
    lam : float
        Arrival rate (units/time).
    mu : float
        Service rate per server (units/time).
    servers : int
        Number of servers *c*.
    rho : float
        Server utilization (traffic intensity per server).
    L : float
        Average number of units in the system (Little's Law).
    Lq : float
        Average number of units in the queue.
    W : float
        Average time in the system.
    Wq : float
        Average time in the queue (waiting time).
    params : dict
        Additional model-specific parameters.
    """

    model: str
    lam: float
    mu: float
    servers: int
    rho: float
    L: float
    Lq: float
    W: float
    Wq: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> "pd.DataFrame":
        """Export key KPIs as a one-row DataFrame."""
        import pandas as pd

        return pd.DataFrame([{
            "model": self.model,
            "λ (arrival rate)": self.lam,
            "μ (service rate)": self.mu,
            "c (servers)": self.servers,
            "ρ (utilization)": self.rho,
            "L (system)": self.L,
            "Lq (queue)": self.Lq,
            "W (system time)": self.W,
            "Wq (wait time)": self.Wq,
            **self.params,
        }])

    def summary(self) -> str:
        lines = [
            f"Model : {self.model}",
            f"λ     : {self.lam:.6g}  (arrival rate)",
            f"μ     : {self.mu:.6g}  (service rate per server)",
            f"c     : {self.servers}  (servers)",
            f"ρ     : {self.rho:.6g}  (utilization per server)",
            f"L     : {self.L:.6g}  (avg units in system)",
            f"Lq    : {self.Lq:.6g}  (avg units in queue)",
            f"W     : {self.W:.6g}  (avg time in system)",
            f"Wq    : {self.Wq:.6g}  (avg wait time in queue)",
        ]
        for k, v in self.params.items():
            lines.append(f"  {k:8s}: {v:.6g}" if isinstance(v, float) else f"  {k:8s}: {v}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> "plt.Figure":
        from .plotting import plot_queue_sensitivity
        return plot_queue_sensitivity(self, **kwargs)


# ---------------------------------------------------------------------------
# Little's Law
# ---------------------------------------------------------------------------

def littles_law(
    *,
    L: float | None = None,
    lam: float | None = None,
    W: float | None = None,
) -> float:
    """Solve Little's Law  L = λ · W  for the missing variable.

    Parameters
    ----------
    L :
        Average number of items in the system.
    lam :
        Average arrival rate.
    W :
        Average time an item spends in the system.

    Returns
    -------
    float
        The value of the missing variable.

    Raises
    ------
    ValueError
        If zero or more than one variable is None.

    Examples
    --------
    >>> littles_law(lam=5.0, W=0.4)   # returns L = 2.0
    2.0
    """
    provided = {k: v for k, v in {"L": L, "lam": lam, "W": W}.items() if v is not None}
    missing = [k for k, v in {"L": L, "lam": lam, "W": W}.items() if v is None]
    if len(missing) != 1:
        raise ValueError("Exactly one of L, lam, W must be None.")
    for k, v in provided.items():
        as_positive(v, k)
    if missing[0] == "L":
        return provided["lam"] * provided["W"]
    if missing[0] == "lam":
        return provided["L"] / provided["W"]
    return provided["L"] / provided["lam"]


# ---------------------------------------------------------------------------
# M/M/1
# ---------------------------------------------------------------------------

def mm1(lam: float, mu: float) -> QueueResult:
    """M/M/1 queuing model.

    Parameters
    ----------
    lam : float
        Arrival rate λ (must be < μ for stability).
    mu : float
        Service rate μ per server.

    Returns
    -------
    QueueResult
    """
    lam = as_positive(lam, "lam")
    mu = as_positive(mu, "mu")
    rho = lam / mu
    if rho >= 1.0:
        raise ValueError(f"System unstable: ρ = {rho:.4g} ≥ 1.  Need λ < μ.")
    Lq = rho**2 / (1 - rho)
    L  = rho / (1 - rho)
    Wq = Lq / lam
    W  = L / lam
    return QueueResult(
        model="M/M/1", lam=lam, mu=mu, servers=1,
        rho=rho, L=L, Lq=Lq, W=W, Wq=Wq,
        params={"P0 (idle probability)": 1 - rho},
    )


# ---------------------------------------------------------------------------
# M/M/c
# ---------------------------------------------------------------------------

def mmc(lam: float, mu: float, c: int) -> QueueResult:
    """M/M/c multi-server queuing model.

    Parameters
    ----------
    lam : float
        Arrival rate λ.
    mu : float
        Service rate μ per server.
    c : int
        Number of servers (≥ 1).

    Returns
    -------
    QueueResult
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    if not isinstance(c, int) or c < 1:
        raise ValueError(f"'c' must be a positive integer, got {c!r}.")
    rho = lam / (c * mu)
    if rho >= 1.0:
        raise ValueError(f"System unstable: ρ = {rho:.4g} ≥ 1.  Need λ < c·μ.")
    a = lam / mu  # offered load

    # Erlang-C formula for P0
    sum_terms = sum((a**n) / math.factorial(n) for n in range(c))
    last_term = (a**c) / (math.factorial(c) * (1 - rho))
    P0 = 1.0 / (sum_terms + last_term)

    Pq = (a**c / (math.factorial(c) * (1 - rho))) * P0  # P(wait) = Erlang-C
    Lq = Pq * rho / (1 - rho)
    Wq = Lq / lam
    W  = Wq + 1 / mu
    L  = lam * W
    return QueueResult(
        model=f"M/M/{c}", lam=lam, mu=mu, servers=c,
        rho=rho, L=L, Lq=Lq, W=W, Wq=Wq,
        params={
            "P0 (idle probability)": P0,
            "C(c,a) Erlang-C": Pq,
        },
    )


# ---------------------------------------------------------------------------
# M/D/1
# ---------------------------------------------------------------------------

def md1(lam: float, mu: float) -> QueueResult:
    """M/D/1 model — Poisson arrivals, deterministic (constant) service time.

    Parameters
    ----------
    lam : float
        Arrival rate λ.
    mu : float
        Service rate μ = 1 / service_time.

    Returns
    -------
    QueueResult
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    rho = lam / mu
    if rho >= 1.0:
        raise ValueError(f"System unstable: ρ = {rho:.4g} ≥ 1.")
    Lq = rho**2 / (2 * (1 - rho))
    L  = rho + Lq
    Wq = Lq / lam
    W  = L / lam
    return QueueResult(
        model="M/D/1", lam=lam, mu=mu, servers=1,
        rho=rho, L=L, Lq=Lq, W=W, Wq=Wq,
    )


# ---------------------------------------------------------------------------
# G/G/1 — Kingman's approximation
# ---------------------------------------------------------------------------

def kingman(
    lam: float,
    mu: float,
    ca2: float,
    cs2: float,
) -> QueueResult:
    """G/G/1 queuing model via Kingman's (VUT) approximation.

    The mean queue waiting time is approximated as::

        Wq ≈ (ρ / (1 − ρ)) · ((ca² + cs²) / 2) · (1 / μ)

    Parameters
    ----------
    lam : float
        Arrival rate λ.
    mu : float
        Service rate μ (= 1 / mean_service_time).
    ca2 : float
        Squared coefficient of variation of inter-arrival times (≥ 0).
    cs2 : float
        Squared coefficient of variation of service times (≥ 0).

    Returns
    -------
    QueueResult
    """
    lam  = as_positive(lam, "lam")
    mu   = as_positive(mu, "mu")
    ca2  = as_nonneg(ca2, "ca2")
    cs2  = as_nonneg(cs2, "cs2")
    rho  = lam / mu
    if rho >= 1.0:
        raise ValueError(f"System unstable: ρ = {rho:.4g} ≥ 1.")
    Wq = (rho / (1 - rho)) * ((ca2 + cs2) / 2) * (1 / mu)
    Lq = lam * Wq
    W  = Wq + 1 / mu
    L  = lam * W
    return QueueResult(
        model="G/G/1 (Kingman)", lam=lam, mu=mu, servers=1,
        rho=rho, L=L, Lq=Lq, W=W, Wq=Wq,
        params={"ca² (arrival CV²)": ca2, "cs² (service CV²)": cs2},
    )
