"""Modelos de teoría de colas: M/M/1, M/M/c, M/D/1, M/G/1, G/G/1 (Kingman) y ley de Little."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ._i18n import etiqueta_param
from ._i18n import t as _t
from ._utils import MAX_SERVIDORES, as_finite_scalar, as_int_positive, as_nonneg, as_positive

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    import pandas as pd


@dataclass
class QueueResult:
    """Resultado del cálculo de un modelo de colas.

    Attributes
    ----------
    model : str
        Nombre del modelo (p. ej. 'M/M/1').
    lam : float
        Tasa de llegadas (unidades/tiempo).
    mu : float
        Tasa de servicio por servidor (unidades/tiempo).
    servers : int
        Número de servidores *c*.
    rho : float
        Utilización del servidor (intensidad de tráfico por servidor).
    L : float
        Número promedio de unidades en el sistema (ley de Little).
    Lq : float
        Número promedio de unidades en cola.
    W : float
        Tiempo promedio en el sistema.
    Wq : float
        Tiempo promedio en cola (tiempo de espera).
    params : dict
        Parámetros adicionales propios del modelo.
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
        """Exporta los KPI principales como un DataFrame de una fila."""
        import pandas as pd

        return pd.DataFrame([{
            "model": self.model,
            _t("queuing.cabecera.to_frame.tasa_llegada"): self.lam,
            _t("queuing.cabecera.to_frame.tasa_servicio"): self.mu,
            _t("queuing.cabecera.to_frame.servidores"): self.servers,
            _t("queuing.cabecera.to_frame.utilizacion"): self.rho,
            _t("queuing.cabecera.to_frame.sistema"): self.L,
            _t("queuing.cabecera.to_frame.lq_cola"): self.Lq,
            _t("queuing.cabecera.to_frame.tiempo_sistema"): self.W,
            _t("queuing.cabecera.to_frame.wq_tiempo_espera"): self.Wq,
            **{etiqueta_param(k): v for k, v in self.params.items()},
        }])

    def summary(self) -> str:
        lines = [
            _t("queuing.etiqueta.summary.modelo", model=self.model),
            _t("queuing.etiqueta.summary.tasa_llegada", lam=self.lam),
            _t("queuing.etiqueta.summary.tasa_servicio_servidor", mu=self.mu),
            _t("queuing.etiqueta.summary.servidores", servers=self.servers),
            _t("queuing.etiqueta.summary.utilizacion_servidor", rho=self.rho),
            _t("queuing.etiqueta.summary.unidades_promedio_sistema", L=self.L),
            _t("queuing.etiqueta.summary.lq_unidades_promedio_cola", Lq=self.Lq),
            _t("queuing.etiqueta.summary.tiempo_promedio_sistema", W=self.W),
            _t("queuing.etiqueta.summary.wq_tiempo_promedio_espera_cola", Wq=self.Wq),
        ]
        for k, v in self.params.items():
            k = etiqueta_param(k)
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
    """Resuelve la ley de Little  L = λ · W  para la variable faltante.

    Parameters
    ----------
    L :
        Número promedio de elementos en el sistema.
    lam :
        Tasa promedio de llegadas.
    W :
        Tiempo promedio que un elemento pasa en el sistema.

    Returns
    -------
    float
        Valor de la variable faltante.

    Raises
    ------
    ValueError
        Si hay cero o más de una variable igual a ``None``.

    Examples
    --------
    >>> littles_law(lam=5.0, W=0.4)   # returns L = 2.0
    2.0
    """
    provided = {k: v for k, v in {"L": L, "lam": lam, "W": W}.items() if v is not None}
    missing = [k for k, v in {"L": L, "lam": lam, "W": W}.items() if v is None]
    if len(missing) != 1:
        raise ValueError(_t("queuing.error.littles_law.exactamente_lam_debe_ser_none"))
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
    """Modelo de colas M/M/1.

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ (debe ser < μ para que el sistema sea estable).
    mu : float
        Tasa de servicio μ por servidor.

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
        raise ValueError(_t("queuing.error.mm1.sistema_inestable_requiere", rho=rho))
    Lq = rho**2 / (1 - rho)
    L  = rho / (1 - rho)
    Wq = Lq / lam
    W  = L / lam
    return QueueResult(
        model="M/M/1", lam=lam, mu=mu, servers=1,
        rho=rho, L=L, Lq=Lq, W=W, Wq=Wq,
        params={"P0 (prob. de sistema vacío)": 1 - rho},
    )


# ---------------------------------------------------------------------------
# M/M/c
# ---------------------------------------------------------------------------

def mmc(lam: float, mu: float, c: int) -> QueueResult:
    """Modelo de colas M/M/c de varios servidores.

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ por servidor.
    c : int
        Número de servidores (≥ 1).

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
        raise ValueError(_t("queuing.error.mmc.sistema_inestable_requiere", rho=rho))
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
        model=_t("queuing.modelo.mmc.texto", c=c), lam=lam, mu=mu, servers=c,
        rho=rho, L=L, Lq=Lq, W=W, Wq=Wq,
        params={
            "P0 (prob. de sistema vacío)": P0,
            "C(c,a) Erlang-C": Pq,
        },
    )


# ---------------------------------------------------------------------------
# M/D/1
# ---------------------------------------------------------------------------

def md1(lam: float, mu: float) -> QueueResult:
    """Modelo M/D/1: llegadas de Poisson y tiempo de servicio determinístico (constante).

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ = 1 / tiempo_de_servicio.

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
        raise ValueError(_t("queuing.error.md1.sistema_inestable", rho=rho))
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
    """Modelo de colas G/G/1 mediante la aproximación de Kingman (VUT).

    El tiempo medio de espera en cola se aproxima como::

        Wq ≈ (ρ / (1 − ρ)) · ((ca² + cs²) / 2) · (1 / μ)

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ (= 1 / tiempo_medio_de_servicio).
    ca2 : float
        Coeficiente de variación al cuadrado de los tiempos entre llegadas (≥ 0).
    cs2 : float
        Coeficiente de variación al cuadrado de los tiempos de servicio (≥ 0).

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
        raise ValueError(_t("queuing.error.md1.sistema_inestable", rho=rho))
    Wq = (rho / (1 - rho)) * ((ca2 + cs2) / 2) * (1 / mu)
    Lq = lam * Wq
    W  = Wq + 1 / mu
    L  = lam * W
    return QueueResult(
        model=_t("queuing.modelo.kingman.kingman"), lam=lam, mu=mu, servers=1,
        rho=rho, L=L, Lq=Lq, W=W, Wq=Wq,
        params={"ca² (CV² de llegadas)": ca2, "cs² (CV² de servicio)": cs2},
    )


# ---------------------------------------------------------------------------
# M/G/1 — Pollaczek-Khinchine exact formula
# ---------------------------------------------------------------------------

def mg1(lam: float, mu: float, cs2: float) -> QueueResult:
    """Modelo de colas M/G/1: fórmula exacta de valores medios de Pollaczek-Khinchine (P-K).

    Llegadas de Poisson con tasa λ y distribución general del tiempo de servicio con media
    1/μ y coeficiente de variación al cuadrado cs². El resultado es exacto (no una
    aproximación) para cualquier distribución de servicio que comparta esos dos momentos.

    Parameters
    ----------
    lam : float
        Tasa de llegadas λ.
    mu : float
        Tasa de servicio μ = 1 / E[S].
    cs2 : float
        Coeficiente de variación al cuadrado del servicio  cs² = Var[S] / E[S]².
        Use las funciones ``cv2_*`` para calcularlo a partir de los parámetros de la distribución.

    Returns
    -------
    QueueResult

    Notes
    -----
    Fórmula P-K:  Wq = λ · E[S²] / (2 · (1 − ρ))
    donde  E[S²] = (1 + cs²) / μ².

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
        raise ValueError(_t("queuing.error.md1.sistema_inestable", rho=rho))
    ES2  = (1.0 + cs2) / mu**2          # E[S²]
    Wq   = lam * ES2 / (2.0 * (1.0 - rho))
    Lq   = lam * Wq
    W    = Wq + 1.0 / mu
    L    = lam * W
    return QueueResult(
        model="M/G/1 (P-K)", lam=lam, mu=mu, servers=1,
        rho=rho, L=L, Lq=Lq, W=W, Wq=Wq,
        params={"cs² (CV² de servicio)": cs2},
    )


# ---------------------------------------------------------------------------
# CV² helpers — squared coefficient of variation for common distributions
# ---------------------------------------------------------------------------

def cv2_triangular(a: float, m: float, b: float) -> float:
    """CV² de una distribución Triangular(a, m, b).

    Parameters
    ----------
    a : float  Cota inferior.
    m : float  Moda (pico).
    b : float  Cota superior.

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
        raise ValueError(_t("queuing.error.cv2_triangular.triangular_requiere"))
    mean = (a + m + b) / 3.0
    if mean == 0.0:
        raise ValueError(_t("queuing.error.cv2_triangular.media_distribucion_cv2_esta_definido"))
    var  = (a**2 + m**2 + b**2 - a*m - a*b - m*b) / 18.0
    return var / mean**2


def cv2_uniform(a: float, b: float) -> float:
    """CV² de una distribución Uniforme(a, b).

    Parameters
    ----------
    a : float  Cota inferior.
    b : float  Cota superior (> a).

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
        raise ValueError(_t("queuing.error.cv2_uniform.uniforme_requiere"))
    mean = (a + b) / 2.0
    if mean == 0.0:
        raise ValueError(_t("queuing.error.cv2_triangular.media_distribucion_cv2_esta_definido"))
    var  = (b - a)**2 / 12.0
    return var / mean**2


def cv2_normal(mean: float, std: float) -> float:
    """CV² de una distribución Normal(media, desviación).

    Parameters
    ----------
    mean : float  Media (> 0 para tiempos de servicio o entre llegadas).
    std  : float  Desviación estándar (≥ 0).

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
    """CV² de una distribución Erlang-k.  cv² = 1/k.

    Parameters
    ----------
    k : int  Parámetro de forma (≥ 1).

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
    """CV² de una distribución Gamma(forma, escala).  cv² = 1/forma.

    Parameters
    ----------
    shape : float  Parámetro de forma α (> 0).

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
    """CV² de una distribución Lognormal parametrizada por su media y desviación *reales*.

    Parameters
    ----------
    mean : float  Media de la variable lognormal (> 0).
    std  : float  Desviación estándar de la variable lognormal (> 0).

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
    """CV² de una distribución Weibull(forma, escala).

    cv² = Γ(1 + 2/k) / Γ(1 + 1/k)² − 1

    Parameters
    ----------
    shape : float  Parámetro de forma k (> 0).

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
