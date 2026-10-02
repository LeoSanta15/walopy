"""Queuing theory models: M/M/1, M/M/c, M/D/1, G/G/1 (Kingman), Little's Law."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ._utils import MAX_SERVIDORES, as_finite_scalar, as_int_positive, as_nonneg, as_positive

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    import pandas as pd


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

    def to_frame(self) -> pd.DataFrame:
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

    def plot(self, **kwargs) -> plt.Figure:
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
        raise ValueError("Exactamente una de L, lam, W debe ser None.")
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

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el sistema es inestable (ρ ≥ 1).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = mm1(lam=2.0, mu=3.0)
    >>> round(r.L, 4)
    2.0
    """
    lam = as_positive(lam, "lam")
    mu = as_positive(mu, "mu")
    rho = lam / mu
    if rho >= 1.0:
        raise ValueError(f"Sistema inestable: ρ = {rho:.4g} ≥ 1. Se requiere λ < μ.")
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

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el sistema es inestable (ρ ≥ 1).
        Si ``c`` supera 10⁶.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = mmc(lam=2.0, mu=3.0, c=2)
    >>> round(r.L, 4)
    0.75
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    c   = as_int_positive(c, "c", max=MAX_SERVIDORES)
    rho = lam / (c * mu)
    if rho >= 1.0:
        raise ValueError(f"Sistema inestable: ρ = {rho:.4g} ≥ 1. Se requiere λ < c·μ.")
    a = lam / mu  # carga ofrecida

    # Erlang-B por recurrencia (estable para c grande) y de ahí Erlang-C y P0.
    # Las fórmulas directas a**n / n! desbordan float a partir de c ≈ 140.
    B = 1.0
    for k in range(1, c + 1):
        B = a * B / (k + a * B)
    Pq = B / (1.0 - rho * (1.0 - B))  # P(espera) = Erlang-C
    if B > 0.0:
        log_Z = c * math.log(a) - math.lgamma(c + 1)  # ln(a^c / c!)
        P0 = math.exp(math.log(B) - log_Z - math.log((1.0 - B) + B / (1.0 - rho)))
    else:  # B subdesbordado: la cola de Poisson es despreciable y P0 ≈ e^{-a}
        P0 = math.exp(-a)
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

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el sistema es inestable (ρ ≥ 1).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = md1(lam=2.0, mu=3.0)
    >>> round(r.L, 4)
    1.3333
    """
    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    rho = lam / mu
    if rho >= 1.0:
        raise ValueError(f"Sistema inestable: ρ = {rho:.4g} ≥ 1.")
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

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el sistema es inestable (ρ ≥ 1).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = kingman(lam=2.0, mu=3.0, ca2=1.0, cs2=1.0)
    >>> round(r.L, 4)
    2.0
    """
    lam  = as_positive(lam, "lam")
    mu   = as_positive(mu, "mu")
    ca2  = as_nonneg(ca2, "ca2")
    cs2  = as_nonneg(cs2, "cs2")
    rho  = lam / mu
    if rho >= 1.0:
        raise ValueError(f"Sistema inestable: ρ = {rho:.4g} ≥ 1.")
    Wq = (rho / (1 - rho)) * ((ca2 + cs2) / 2) * (1 / mu)
    Lq = lam * Wq
    W  = Wq + 1 / mu
    L  = lam * W
    return QueueResult(
        model="G/G/1 (Kingman)", lam=lam, mu=mu, servers=1,
        rho=rho, L=L, Lq=Lq, W=W, Wq=Wq,
        params={"ca² (arrival CV²)": ca2, "cs² (service CV²)": cs2},
    )


# ---------------------------------------------------------------------------
# M/G/1 — Pollaczek-Khinchine exact formula
# ---------------------------------------------------------------------------

def mg1(lam: float, mu: float, cs2: float) -> QueueResult:
    """M/G/1 queuing model — exact Pollaczek-Khinchine (P-K) mean-value formula.

    Poisson arrivals with rate λ, general service time distribution with mean
    1/μ and squared coefficient of variation cs².  The result is exact (not an
    approximation) for any service distribution that shares those two moments.

    Parameters
    ----------
    lam : float
        Arrival rate λ.
    mu : float
        Service rate μ = 1 / E[S].
    cs2 : float
        Squared coefficient of variation of service times  cs² = Var[S] / E[S]².
        Use the ``cv2_*`` helpers to compute this from distribution parameters.

    Returns
    -------
    QueueResult

    Notes
    -----
    P-K formula:  Wq = λ · E[S²] / (2 · (1 − ρ))
    where  E[S²] = (1 + cs²) / μ².

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el sistema es inestable (ρ ≥ 1).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = mg1(lam=2.0, mu=3.0, cs2=1.0)
    >>> round(r.L, 4)
    2.0
    """
    lam  = as_positive(lam, "lam")
    mu   = as_positive(mu, "mu")
    cs2  = as_nonneg(cs2, "cs2")
    rho  = lam / mu
    if rho >= 1.0:
        raise ValueError(f"Sistema inestable: ρ = {rho:.4g} ≥ 1.")
    ES2  = (1.0 + cs2) / mu**2          # E[S²]
    Wq   = lam * ES2 / (2.0 * (1.0 - rho))
    Lq   = lam * Wq
    W    = Wq + 1.0 / mu
    L    = lam * W
    return QueueResult(
        model="M/G/1 (P-K)", lam=lam, mu=mu, servers=1,
        rho=rho, L=L, Lq=Lq, W=W, Wq=Wq,
        params={"cs² (service CV²)": cs2},
    )


# ---------------------------------------------------------------------------
# CV² helpers — squared coefficient of variation for common distributions
# ---------------------------------------------------------------------------

def cv2_triangular(a: float, m: float, b: float) -> float:
    """CV² for a Triangular(a, m, b) distribution.

    Parameters
    ----------
    a : float  Lower bound.
    m : float  Mode (peak).
    b : float  Upper bound.

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si no se cumple a ≤ m ≤ b o la media de la distribución es 0.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = cv2_triangular(a=1.0, m=2.0, b=3.0)
    >>> round(r, 4)
    0.0417
    """
    a = as_finite_scalar(a, "a")
    m = as_finite_scalar(m, "m")
    b = as_finite_scalar(b, "b")
    if not (a <= m <= b):
        raise ValueError("La triangular requiere a ≤ m ≤ b.")
    mean = (a + m + b) / 3.0
    if mean == 0.0:
        raise ValueError("La media de la distribución es 0: CV² no está definido.")
    var  = (a**2 + m**2 + b**2 - a*m - a*b - m*b) / 18.0
    return var / mean**2


def cv2_uniform(a: float, b: float) -> float:
    """CV² for a Uniform(a, b) distribution.

    Parameters
    ----------
    a : float  Lower bound.
    b : float  Upper bound (> a).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si b ≤ a o la media de la distribución es 0.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = cv2_uniform(a=1.0, b=3.0)
    >>> round(r, 4)
    0.0833
    """
    a = as_finite_scalar(a, "a")
    b = as_finite_scalar(b, "b")
    if b <= a:
        raise ValueError("La uniforme requiere b > a.")
    mean = (a + b) / 2.0
    if mean == 0.0:
        raise ValueError("La media de la distribución es 0: CV² no está definido.")
    var  = (b - a)**2 / 12.0
    return var / mean**2


def cv2_normal(mean: float, std: float) -> float:
    """CV² for a Normal(mean, std) distribution.

    Parameters
    ----------
    mean : float  Mean (> 0 for service/inter-arrival times).
    std  : float  Standard deviation (≥ 0).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = cv2_normal(mean=5.0, std=1.0)
    >>> round(r, 4)
    0.04
    """
    as_positive(mean, "mean")
    as_nonneg(std, "std")
    return (std / mean) ** 2


def cv2_erlang(k: int) -> float:
    """CV² for an Erlang-k distribution.  cv² = 1/k.

    Parameters
    ----------
    k : int  Shape parameter (≥ 1).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``k`` no es un entero ≥ 1.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = cv2_erlang(k=3)
    >>> round(r, 4)
    0.3333
    """
    k = as_int_positive(k, "k")
    return 1.0 / k


def cv2_gamma(shape: float) -> float:
    """CV² for a Gamma(shape, scale) distribution.  cv² = 1/shape.

    Parameters
    ----------
    shape : float  Shape parameter α (> 0).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = cv2_gamma(shape=2.0)
    >>> round(r, 4)
    0.5
    """
    as_positive(shape, "shape")
    return 1.0 / shape


def cv2_lognormal(mean: float, std: float) -> float:
    """CV² for a LogNormal distribution parameterised by its *actual* mean and std.

    Parameters
    ----------
    mean : float  Mean of the lognormal variable (> 0).
    std  : float  Standard deviation of the lognormal variable (> 0).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = cv2_lognormal(mean=5.0, std=1.0)
    >>> round(r, 4)
    0.04
    """
    as_positive(mean, "mean")
    as_positive(std, "std")
    return (std / mean) ** 2


def cv2_weibull(shape: float) -> float:
    """CV² for a Weibull(shape, scale) distribution.

    cv² = Γ(1 + 2/k) / Γ(1 + 1/k)² − 1

    Parameters
    ----------
    shape : float  Shape parameter k (> 0).

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = cv2_weibull(shape=1.5)
    >>> round(r, 4)
    0.461
    """
    as_positive(shape, "shape")
    return math.gamma(1.0 + 2.0 / shape) / math.gamma(1.0 + 1.0 / shape) ** 2 - 1.0
