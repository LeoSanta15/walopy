"""Reliability engineering: exponential failure model, series/parallel/k-of-n systems."""
from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ._utils import as_float_list, as_int_positive, as_nonneg, as_positive

if TYPE_CHECKING:
    import pandas as pd


def _validar_t_mttr(t: float | None, mttr: float | None) -> tuple:
    """Valida los argumentos opcionales t (tiempo de evaluación) y mttr (tiempo medio de reparación)."""
    t_v = None if t is None else as_nonneg(t, "t")
    mttr_v = None if mttr is None else as_nonneg(mttr, "mttr")
    return t_v, mttr_v


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

    def to_frame(self) -> pd.DataFrame:
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
    raise ValueError(f"Topología desconocida: {topology!r}")


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
    t, mttr = _validar_t_mttr(t, mttr)
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
    lams = as_float_list(failure_rates, "failure_rates")
    t, mttr = _validar_t_mttr(t, mttr)
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
    lams = as_float_list(failure_rates, "failure_rates")
    t, mttr = _validar_t_mttr(t, mttr)

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
    n = as_int_positive(n, "n")
    k = as_int_positive(k, "k")
    if k > n:
        raise ValueError(f"Debe cumplirse 1 ≤ k ≤ n (k={k}, n={n}).")
    lam = as_positive(failure_rate, "failure_rate")
    t, mttr = _validar_t_mttr(t, mttr)
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


# ---------------------------------------------------------------------------
# Weibull analysis (2-parameter)
# ---------------------------------------------------------------------------

@dataclass
class WeibullResult:
    """Two-parameter Weibull analysis result.

    The CDF is F(t) = 1 − exp(−(t/η)^β).

    Attributes
    ----------
    shape : float
        Shape parameter β.
        β < 1 → decreasing failure rate (infant mortality).
        β = 1 → constant failure rate (exponential model).
        β > 1 → increasing failure rate (wear-out).
    scale : float
        Scale parameter η (characteristic life); F(η) ≈ 63.2 %.
    mttf : float
        Mean time to failure = η · Γ(1 + 1/β).
    b10 : float
        B10 life — time at which 10 % of the population has failed.
    b50 : float
        Median life (50 % failed).
    method : str
        Estimation method: ``'MLE'`` (maximum likelihood) or
        ``'RRY'`` (rank regression on Y / probability plotting).
    n : int
        Number of failure times used.
    """

    shape: float
    scale: float
    mttf: float
    b10: float
    b50: float
    method: str
    n: int

    def R(self, t: float) -> float:
        """Reliability at time *t*: R(t) = exp(−(t/η)^β)."""
        return math.exp(-((t / self.scale) ** self.shape))

    def F(self, t: float) -> float:
        """Unreliability (CDF) at time *t*: F(t) = 1 − R(t)."""
        return 1.0 - self.R(t)

    def h(self, t: float) -> float:
        """Instantaneous hazard rate: h(t) = (β/η)·(t/η)^(β−1)."""
        return (self.shape / self.scale) * ((t / self.scale) ** (self.shape - 1.0))

    def b_life(self, pct: float) -> float:
        """Time at which *pct* percent of the population has failed.

        E.g. ``b_life(10)`` returns the B10 life.
        """
        p = pct / 100.0
        if not (0.0 < p < 1.0):
            raise ValueError("'pct' debe estar estrictamente entre 0 y 100.")
        return self.scale * (-math.log(1.0 - p)) ** (1.0 / self.shape)

    def summary(self) -> str:
        return (
            f"Method       : {self.method} (n={self.n})\n"
            f"Shape β      : {self.shape:.4f}\n"
            f"Scale η      : {self.scale:.4g}\n"
            f"MTTF         : {self.mttf:.4g}\n"
            f"B10 life     : {self.b10:.4g}\n"
            f"B50 (median) : {self.b50:.4g}"
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "shape_beta": self.shape,
            "scale_eta":  self.scale,
            "MTTF":       self.mttf,
            "B10":        self.b10,
            "B50":        self.b50,
            "method":     self.method,
            "n":          self.n,
        }])


def _weibull_mle_beta(failure_times: list) -> float:
    """Solve for Weibull β via MLE using bisection (normalized for stability)."""
    n     = len(failure_times)
    ln_t  = [math.log(t) for t in failure_times]
    # Normalize by geometric mean: u_i = t_i / geom_mean.
    # The MLE equation is invariant to this scaling, and ui near 1
    # keeps u_i^beta from overflowing.
    ln_mean = sum(ln_t) / n           # log of geometric mean
    norm_ln = [lt - ln_mean for lt in ln_t]   # ln(u_i); sum = 0

    def g(beta: float) -> float:
        # u_i^beta = exp(beta * ln(u_i)); clamp to avoid overflow/underflow
        u_beta  = [math.exp(max(-700.0, min(700.0, beta * lt))) for lt in norm_ln]
        s_ub    = sum(u_beta)
        if s_ub == 0.0:
            return float("inf")
        s_ub_ln = sum(ub * lt for ub, lt in zip(u_beta, norm_ln))
        return n / beta - n * s_ub_ln / s_ub   # Σln(ui)=0 drops out

    lo, hi = 1e-4, 100.0
    if g(lo) <= 0.0:
        warnings.warn(
            f"La forma β estimada es menor o igual que la cota inferior {lo:g}; el resultado es el límite del intervalo "
            "de búsqueda, no un máximo de verosimilitud exacto.",
            UserWarning, stacklevel=3,
        )
        return lo
    if g(hi) >= 0.0:
        warnings.warn(
            f"Los tiempos de falla casi no tienen dispersión: la forma β supera la cota {hi:g}; "
            "el resultado es el límite del intervalo de búsqueda, no el estimador exacto.",
            UserWarning, stacklevel=3,
        )
        return hi
    for _ in range(120):
        mid = (lo + hi) / 2.0
        if g(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _weibull_rry(failure_times: list) -> tuple:
    """Estimate β and η via rank regression on Y (probability plotting)."""
    n       = len(failure_times)
    t_sort  = sorted(failure_times)
    # Benard's median rank approximation
    F_i     = [(i - 0.3) / (n + 0.4) for i in range(1, n + 1)]
    X       = [math.log(t) for t in t_sort]
    Y       = [math.log(-math.log(1.0 - f)) for f in F_i]
    n_pts   = float(n)
    sx      = sum(X)
    sy      = sum(Y)
    sxx     = sum(x * x for x in X)
    sxy     = sum(x * y for x, y in zip(X, Y))
    slope   = (n_pts * sxy - sx * sy) / (n_pts * sxx - sx ** 2)
    intercept = (sy - slope * sx) / n_pts
    beta    = slope
    eta     = math.exp(-intercept / beta)
    return beta, eta


def weibull_analysis(
    failure_times: Sequence[float],
    *,
    method: str = "MLE",
) -> WeibullResult:
    """Fit a two-parameter Weibull distribution to complete failure data.

    F(t) = 1 − exp(−(t/η)^β)

    Parameters
    ----------
    failure_times : sequence of float
        Observed failure times (all must be > 0).  At least 2 values required.
    method : str
        ``'MLE'`` (default) — maximum-likelihood estimation via bisection;
        ``'RRY'`` — rank regression on Y (probability-plotting method, faster).

    Returns
    -------
    WeibullResult

    Examples
    --------
    >>> import math
    >>> # Generate Weibull(β=2, η=100) data via inverse CDF
    >>> times = [100 * (-math.log(1 - p)) ** 0.5 for p in [.1,.2,.3,.4,.5,.6,.7,.8,.9]]
    >>> r = weibull_analysis(times)
    >>> 2.0 < r.shape < 3.0  # cuantiles equiespaciados: menos dispersión que una muestra aleatoria
    True
    """
    t_list = as_float_list(failure_times, "failure_times", min_len=2)
    if max(t_list) == min(t_list):
        raise ValueError(
            "Todos los tiempos de falla son iguales: la dispersión es nula y la forma β no es estimable."
        )

    m = method.upper()
    if m not in ("MLE", "RRY"):
        raise ValueError("'method' debe ser 'MLE' o 'RRY'.")

    if m == "MLE":
        beta  = _weibull_mle_beta(t_list)
        n_pts = len(t_list)
        eta   = (sum(t ** beta for t in t_list) / n_pts) ** (1.0 / beta)
    else:
        beta, eta = _weibull_rry(t_list)

    mttf = eta * math.gamma(1.0 + 1.0 / beta)
    b10  = eta * (-math.log(0.90)) ** (1.0 / beta)
    b50  = eta * math.log(2.0)     ** (1.0 / beta)

    return WeibullResult(
        shape=beta,
        scale=eta,
        mttf=mttf,
        b10=b10,
        b50=b50,
        method=m,
        n=len(t_list),
    )
