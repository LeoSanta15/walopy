"""Advanced queuing models, simulation, line balancing and break-even analysis."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd

from ._utils import as_positive, as_nonneg, as_fraction, as_int_positive, as_nonempty
from .queuing import QueueResult


# ---------------------------------------------------------------------------
# Erlang B — M/M/c/c (loss system, no queue)
# ---------------------------------------------------------------------------

def erlang_b(lam: float, mu: float, c: int) -> float:
    """Erlang B formula — blocking probability for an M/M/c/c loss system.

    In a loss system there is no waiting room: arriving customers who find
    all *c* servers busy are lost (blocked).

    Parameters
    ----------
    lam : float
        Arrival rate λ.
    mu : float
        Service rate μ per server.
    c : int
        Number of servers (= system capacity).

    Returns
    -------
    float
        Blocking probability B(c, a) ∈ [0, 1].
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    c   = as_int_positive(c, "c")
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
    """M/M/1/K queue — single server with finite waiting room.

    The system capacity is *K* (server + queue).  Customers arriving when
    the system is full are lost.

    Parameters
    ----------
    lam : float
        Arrival rate λ.
    mu : float
        Service rate μ.
    K : int
        System capacity (maximum customers in system, ≥ 1).

    Returns
    -------
    QueueResult
        Note: ``rho`` here is traffic intensity λ/μ (may be ≥ 1);
        the system is always stable because of finite capacity.
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    K   = as_int_positive(K, "K")

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
        model=f"M/M/1/{K}",
        lam=lam,
        mu=mu,
        servers=1,
        rho=util,
        L=L,
        Lq=Lq,
        W=W,
        Wq=Wq,
        params={
            "K (capacity)": K,
            "P0 (idle)": Pn[0],
            "PK (blocking prob)": PK,
            "λ_eff (effective rate)": lam_eff,
        },
    )


# ---------------------------------------------------------------------------
# Monte-Carlo simulation of a G/G/1 queue
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """Result of a Monte-Carlo G/G/1 simulation.

    Attributes
    ----------
    model : str
    lam, mu : float
    rho : float
    Wq_mean : float  Average waiting time in queue.
    W_mean  : float  Average sojourn time.
    Lq : float  Average queue length (via Little's Law).
    L  : float  Average system length.
    Wq_p50, Wq_p90, Wq_p95, Wq_p99 : float  Percentiles of Wq.
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
    _Wq_array: "np.ndarray" = field(repr=False)
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "model": self.model,
            "λ": self.lam,
            "μ": self.mu,
            "ρ": self.rho,
            "Wq mean": self.Wq_mean,
            "W mean": self.W_mean,
            "Lq": self.Lq,
            "L": self.L,
            "Wq p50": self.Wq_p50,
            "Wq p90": self.Wq_p90,
            "Wq p95": self.Wq_p95,
            "Wq p99": self.Wq_p99,
            "N customers": self.n_customers,
        }])

    def summary(self) -> str:
        return (
            f"Model  : {self.model}\n"
            f"N      : {self.n_customers:,}\n"
            f"ρ      : {self.rho:.4f}\n"
            f"Wq mean: {self.Wq_mean:.6g}  (p50={self.Wq_p50:.4g}  p90={self.Wq_p90:.4g}"
            f"  p95={self.Wq_p95:.4g}  p99={self.Wq_p99:.4g})\n"
            f"W mean : {self.W_mean:.6g}\n"
            f"Lq     : {self.Lq:.6g}\n"
            f"L      : {self.L:.6g}"
        )

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> "go.Figure":
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
    """Monte-Carlo simulation of a G/G/1 single-server queue.

    Inter-arrival and service times are drawn from Gamma distributions
    matched to the given mean and squared coefficient of variation.
    When CV² = 0 the times are deterministic; when CV² = 1 they are
    exponential (recovering the M/M/1 case).

    Parameters
    ----------
    lam : float
        Arrival rate λ.
    mu : float
        Service rate μ (= 1 / mean service time).
    ca2 : float
        Squared coefficient of variation of inter-arrival times (≥ 0).
    cs2 : float
        Squared coefficient of variation of service times (≥ 0).
    n_customers : int
        Number of customers to simulate (default 20 000).
    seed : int, optional
        Random seed for reproducibility.

    Returns
    -------
    SimulationResult
    """
    lam         = as_positive(lam, "lam")
    mu          = as_positive(mu, "mu")
    ca2         = as_nonneg(ca2, "ca2")
    cs2         = as_nonneg(cs2, "cs2")
    n_customers = as_int_positive(n_customers, "n_customers")
    rho         = lam / mu
    if rho >= 1.0:
        raise ValueError(f"System unstable: ρ = {rho:.4g} ≥ 1.")

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
        model=f"G/G/1 simulation (ca²={ca2:.3g}, cs²={cs2:.3g})",
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
    """Compute takt time = available production time / customer demand.

    Parameters
    ----------
    available_time : float
        Net production time available in the period (same units as the
        result, e.g. seconds, minutes).
    demand : float
        Number of units (or customers) demanded in the same period.

    Returns
    -------
    float
        Takt time (time per unit).
    """
    return as_positive(available_time, "available_time") / as_positive(demand, "demand")


# ---------------------------------------------------------------------------
# Line balance analysis
# ---------------------------------------------------------------------------

@dataclass
class LineBalanceResult:
    """Result of a production line balance analysis.

    Attributes
    ----------
    takt : float
        Takt time.
    n_stations : int
        Number of stations analysed.
    balance_efficiency : float
        Sum of cycle times / (n_stations × takt).
    theoretical_min_stations : int
        ceil(sum(cycle times) / takt).
    stations : pd.DataFrame
        Per-station metrics: name, cycle_time, idle_time, utilization, overloaded.
    bottleneck : str
        Station with the highest cycle time.
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
            f"Takt time               : {self.takt:.6g}\n"
            f"Stations                : {self.n_stations}\n"
            f"Theoretical minimum     : {self.theoretical_min_stations}\n"
            f"Balance efficiency      : {self.balance_efficiency:.2%}\n"
            f"Bottleneck station      : {self.bottleneck}\n"
        )

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> "go.Figure":
        from .plotting import plot_line_balance
        return plot_line_balance(self, **kwargs)


def line_balance(
    station_names: Sequence[str],
    cycle_times: Sequence[float],
    takt: float,
) -> LineBalanceResult:
    """Analyse the balance of a production or service line.

    Parameters
    ----------
    station_names : sequence of str
        Station names.
    cycle_times : sequence of float
        Actual cycle time per station.
    takt : float
        Takt time (available time / demand).

    Returns
    -------
    LineBalanceResult
    """
    names  = list(station_names)
    as_nonempty(names, "station_names")
    cts    = [as_positive(ct, f"cycle_times[{i}]") for i, ct in enumerate(cycle_times)]
    takt   = as_positive(takt, "takt")
    n      = len(names)

    if len(cts) != n:
        raise ValueError("'station_names' and 'cycle_times' must have the same length.")

    idle        = [max(takt - ct, 0.0) for ct in cts]
    utils       = [ct / takt for ct in cts]
    overloaded  = [ct > takt for ct in cts]
    sum_ct      = sum(cts)
    bn_idx      = int(np.argmax(cts))
    eff         = sum_ct / (n * takt)
    min_stat    = math.ceil(sum_ct / takt)

    df = pd.DataFrame({
        "Station":    names,
        "CycleTime":  cts,
        "IdleTime":   idle,
        "Utilization": utils,
        "Overloaded": overloaded,
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
    """Break-even analysis result.

    Attributes
    ----------
    bep_units : float
        Break-even volume in units.
    bep_revenue : float
        Break-even revenue.
    contribution_margin : float
        Price − variable cost per unit.
    contribution_margin_ratio : float
        Contribution margin / price.
    margin_of_safety_units : float
        Actual units − break-even units (if actual_units given).
    margin_of_safety_pct : float
        Margin of safety as fraction of actual units.
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
            "BEP (units)": self.bep_units,
            "BEP (revenue)": self.bep_revenue,
            "Contribution margin": self.contribution_margin,
            "CM ratio": self.contribution_margin_ratio,
            "Margin of safety (units)": self.margin_of_safety_units,
            "Margin of safety (%)": self.margin_of_safety_pct,
        }])

    def summary(self) -> str:
        lines = [
            f"Break-even (units)  : {self.bep_units:.4g}",
            f"Break-even (revenue): {self.bep_revenue:.4g}",
            f"Contribution margin : {self.contribution_margin:.4g}",
            f"CM ratio            : {self.contribution_margin_ratio:.2%}",
        ]
        if self.margin_of_safety_units:
            lines.append(f"Margin of safety    : {self.margin_of_safety_units:.4g} units ({self.margin_of_safety_pct:.2%})")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> "go.Figure":
        from .plotting import plot_break_even
        return plot_break_even(self, **kwargs)


def break_even(
    fixed_cost: float,
    price_per_unit: float,
    variable_cost_per_unit: float,
    *,
    actual_units: float | None = None,
) -> BreakEvenResult:
    """Compute break-even point and contribution margin.

    Parameters
    ----------
    fixed_cost : float
        Total fixed cost for the period.
    price_per_unit : float
        Selling price per unit.
    variable_cost_per_unit : float
        Variable cost per unit.
    actual_units : float, optional
        Actual production/sales volume (for margin-of-safety calculation).

    Returns
    -------
    BreakEvenResult
    """
    fixed_cost             = as_positive(fixed_cost, "fixed_cost")
    price_per_unit         = as_positive(price_per_unit, "price_per_unit")
    variable_cost_per_unit = as_nonneg(variable_cost_per_unit, "variable_cost_per_unit")

    cm  = price_per_unit - variable_cost_per_unit
    if cm <= 0:
        raise ValueError("price_per_unit must exceed variable_cost_per_unit for a positive contribution margin.")

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
# Queue length PMF and sojourn CDF for M/M/1
# ---------------------------------------------------------------------------

def queue_length_pmf(lam: float, mu: float, n_max: int = 30) -> pd.DataFrame:
    """Probability mass function of the number of customers in an M/M/1 system.

    P(N = n) = (1 − ρ) · ρ^n

    Parameters
    ----------
    lam : float
        Arrival rate λ.
    mu : float
        Service rate μ.
    n_max : int
        Maximum queue length to compute (default 30).

    Returns
    -------
    pd.DataFrame
        Columns: ``n``, ``P(N=n)``, ``P(N<=n)``.
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    rho = lam / mu
    if rho >= 1.0:
        raise ValueError(f"System unstable: ρ = {rho:.4g} ≥ 1.")
    ns    = np.arange(0, n_max + 1)
    pmf   = (1 - rho) * rho**ns
    return pd.DataFrame({"n": ns, "P(N=n)": pmf, "P(N<=n)": np.cumsum(pmf)})


def sojourn_cdf(lam: float, mu: float, t_max: float | None = None, n_points: int = 200) -> pd.DataFrame:  # noqa: E501
    """CDF of the sojourn time (time in system) for an M/M/1 queue.

    F(t) = 1 − exp(−(μ − λ)·t)

    Parameters
    ----------
    lam : float
        Arrival rate λ.
    mu : float
        Service rate μ.
    t_max : float, optional
        Upper bound of time axis (defaults to 5 × mean sojourn time).
    n_points : int
        Number of evaluation points.

    Returns
    -------
    pd.DataFrame
        Columns: ``t``, ``F(t)`` (CDF), ``f(t)`` (PDF).
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    rho = lam / mu
    if rho >= 1.0:
        raise ValueError(f"System unstable: ρ = {rho:.4g} ≥ 1.")
    W_mean = 1.0 / (mu - lam)
    t_upper = t_max if t_max is not None else 5.0 * W_mean
    t       = np.linspace(0, t_upper, n_points)
    rate    = mu - lam
    cdf     = 1.0 - np.exp(-rate * t)
    pdf     = rate * np.exp(-rate * t)
    return pd.DataFrame({"t": t, "F(t)": cdf, "f(t)": pdf})


# ---------------------------------------------------------------------------
# M/M/c/K — multi-server finite capacity queue
# ---------------------------------------------------------------------------

def mmck(lam: float, mu: float, c: int, K: int) -> QueueResult:
    """M/M/c/K queue — *c* servers, system capacity *K* (including servers).

    Customers arriving when the system is full are blocked (lost).
    The system is always stable regardless of ρ because of the finite
    capacity.

    Parameters
    ----------
    lam : float
        Arrival rate λ.
    mu : float
        Service rate μ per server.
    c : int
        Number of servers (≥ 1).
    K : int
        System capacity (maximum customers in system, ≥ c).

    Returns
    -------
    QueueResult
        ``rho`` is server utilization λ_eff / (c · μ).
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    c   = as_int_positive(c, "c")
    K   = as_int_positive(K, "K")
    if K < c:
        raise ValueError(f"'K' (system capacity) must be ≥ c (servers); got K={K}, c={c}.")

    a   = lam / mu           # offered load
    rho = a / c              # traffic intensity per server

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
        model=f"M/M/{c}/{K}",
        lam=lam, mu=mu, servers=c,
        rho=util, L=L, Lq=Lq, W=W, Wq=Wq,
        params={
            "K (capacity)": K,
            "P0 (idle)": Pn[0],
            "PK (blocking prob)": PK,
            "λ_eff (effective rate)": lam_eff,
        },
    )


# ---------------------------------------------------------------------------
# M/M/1 non-preemptive Head-of-Line priority queue
# ---------------------------------------------------------------------------

@dataclass
class PriorityQueueResult:
    """Result of a non-preemptive HOL priority queue analysis.

    Each entry in *classes* is a dict with keys:
    ``class_id``, ``lam``, ``rho``, ``Wq``, ``W``, ``Lq``, ``L``.

    Attributes
    ----------
    classes : list[dict]
        Per-class metrics in priority order (class 0 = highest priority).
    rho_total : float
        Total server utilization = sum(λ_k) / μ.
    mu : float
        Service rate.
    """

    classes: list[dict]
    rho_total: float
    mu: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> "pd.DataFrame":
        return pd.DataFrame(self.classes)

    def summary(self) -> str:
        lines = [
            f"M/M/1 Non-preemptive HOL priority  (μ={self.mu:.6g}, ρ={self.rho_total:.4g})",
            f"{'Class':>6}  {'λ':>10}  {'ρ':>8}  {'Wq':>12}  {'W':>12}  {'Lq':>10}  {'L':>10}",
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
    """Non-preemptive Head-of-Line priority M/M/1 queue.

    Class 0 has the highest priority; class N−1 the lowest.  Service is
    FCFS within each priority class and non-preemptive (a lower-priority
    customer in service is not interrupted).

    The formula (Kleinrock, 1975):

    .. code-block:: text

        Wq_k = R / ((1 − σ_{k−1}) · (1 − σ_k))
        where R = ρ / μ,  σ_k = Σ_{i=0}^{k} λ_i / μ,  σ_{−1} = 0.

    Parameters
    ----------
    lam_list : sequence of float
        Arrival rates λ_k for each class in *descending* priority order
        (index 0 = highest priority).
    mu : float
        Service rate μ (same exponential server for all classes).
    class_names : sequence of str, optional
        Labels for the priority classes.  Defaults to '0', '1', …

    Returns
    -------
    PriorityQueueResult

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
        raise ValueError("'lam_list' must contain at least one class.")

    rho_total = sum(lams) / mu
    if rho_total >= 1.0:
        raise ValueError(f"System unstable: ρ_total = {rho_total:.4g} ≥ 1.")

    names = list(class_names) if class_names else [str(i) for i in range(N)]
    if len(names) != N:
        raise ValueError("'class_names' must have the same length as 'lam_list'.")

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
        params={"N_classes": N, "R (residual)": R},
    )
