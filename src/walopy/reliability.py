"""Ingeniería de confiabilidad: modelo exponencial de fallas, sistemas serie, paralelo y k-de-n, y Weibull."""
from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import NormalDist
from typing import TYPE_CHECKING

from ._i18n import t as _t
from ._utils import as_float_list, as_fraction, as_int_positive, as_nonneg, as_positive

if TYPE_CHECKING:
    import pandas as pd


def _validar_t_mttr(t: float | None, mttr: float | None) -> tuple:
    """Valida los argumentos opcionales t (tiempo de evaluación) y mttr (tiempo medio de reparación)."""
    t_v = None if t is None else as_nonneg(t, "t")
    mttr_v = None if mttr is None else as_nonneg(mttr, "mttr")
    return t_v, mttr_v


def _mtbf_numeric(R_func, lam_min: float) -> float:
    """Integra numéricamente R(t) de 0 a infinito (trapezoidal, ~10 000 pasos)."""
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
    """Resultado de confiabilidad de un sistema.

    Attributes
    ----------
    topology : str
        ``'series'``, ``'parallel'``, ``'k-of-n'`` o ``'component'``.
    n_components : int
        Número de componentes del sistema.
    failure_rates : list[float]
        Tasas de falla individuales λi de los componentes (fallas/unidad de tiempo).
    mtbf : float
        Tiempo medio entre fallas del sistema.
    t : float or None
        Tiempo en que se evaluó R(t) (si se indicó).
    R_t : float or None
        Confiabilidad del sistema R(t) en el t pedido.
    availability : float or None
        Disponibilidad en régimen estacionario A = MTBF / (MTBF + MTTR), si se indicó mttr.
    mttr : float or None
        Tiempo medio de reparación, si se indicó.
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
        """Calcula la confiabilidad R(t) del sistema con la topología almacenada."""
        return _r_system(self.topology, self.failure_rates,
                         self.params.get("k"), t)

    def summary(self) -> str:
        lines = [
            _t("reliability.etiqueta.summary.topologia", topology=self.topology),
            _t("reliability.etiqueta.summary.componentes", n_components=self.n_components),
            _t("reliability.etiqueta.summary.tasas_falla", expr=[f'{l:.4g}' for l in self.failure_rates]),
            _t("reliability.etiqueta.summary.mtbf", mtbf=self.mtbf),
        ]
        if self.t is not None:
            lines.append(_t("reliability.etiqueta.summary.texto", t=self.t, R_t=self.R_t))
        if self.availability is not None:
            lines.append(_t("reliability.etiqueta.summary.disponibilidad", availability=self.availability))
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        row: dict = {
            _t("reliability.cabecera.to_frame.topologia"): self.topology,
            _t("reliability.cabecera.to_frame.componentes"): self.n_components,
            "MTBF": self.mtbf,
        }
        if self.t is not None:
            row[_t("reliability.cabecera.to_frame.texto", t=self.t)] = self.R_t
        if self.availability is not None:
            row[_t("reliability.cabecera.to_frame.disponibilidad")] = self.availability
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
    raise ValueError(_t("reliability.error.r_system.topologia_desconocida", topology=topology))


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def mtbf_analysis(
    failure_rate: float,
    *,
    mttr: float | None = None,
    t: float | None = None,
) -> ReliabilityResult:
    """Confiabilidad de un componente con distribución exponencial de fallas.

    Parameters
    ----------
    failure_rate : float
        Tasa de falla λ (fallas por unidad de tiempo, p. ej. 0.01 fallas/hora).
    mttr : float, optional
        Tiempo medio de reparación. Si se indica, calcula la disponibilidad en régimen estacionario.
    t : float, optional
        Tiempo en que se evalúa R(t) = e^{−λt}.

    Returns
    -------
    ReliabilityResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = mtbf_analysis(failure_rate=0.01, mttr=2.0, t=10.0)
    >>> round(r.mtbf, 4)
    100.0
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
    """Confiabilidad de un sistema en serie (todos los componentes deben funcionar).

    R_sys(t) = ∏ e^{−λi·t} = e^{−(Σλi)·t}

    Parameters
    ----------
    failure_rates : sequence of float
        Tasas de falla λi de los componentes.
    t : float, optional
        Tiempo para evaluar R(t).
    mttr : float, optional
        Tiempo medio de reparación. Disponibilidad A = MTBF / (MTBF + MTTR) del sistema: mientras se repara el
        componente que falló el sistema está detenido y los demás no fallan.

    Returns
    -------
    ReliabilityResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``failure_rates`` está vacío.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = series_system(failure_rates=[0.01, 0.02], t=10.0)
    >>> round(r.mtbf, 4)
    33.3333
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


def _disponibilidad_componente(lam: float, mttr: float) -> float:
    """Disponibilidad en régimen de un componente reparable: MTBF / (MTBF + MTTR) = 1 / (1 + λ·MTTR)."""
    return 1.0 / (1.0 + lam * mttr)


def parallel_system(
    failure_rates: Sequence[float],
    *,
    t: float | None = None,
    mttr: float | None = None,
) -> ReliabilityResult:
    """Confiabilidad de un sistema en paralelo (al menos un componente debe funcionar).

    R_sys(t) = 1 − ∏(1 − e^{−λi·t})

    El MTBF se calcula numéricamente (∫₀^∞ R_sys(t) dt).

    Parameters
    ----------
    failure_rates : sequence of float
        Tasas de falla λi de los componentes.
    t : float, optional
        Tiempo para evaluar R(t).
    mttr : float, optional
        Tiempo medio de reparación de cada componente. La disponibilidad supone que cada componente se repara
        en cuanto falla, de forma independiente: A = 1 − ∏(1 − Aᵢ), con Aᵢ = MTBFᵢ / (MTBFᵢ + MTTR). El MTBF
        del resultado es el tiempo medio hasta la falla del sistema sin reparación.

    Returns
    -------
    ReliabilityResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``failure_rates`` está vacío.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = parallel_system(failure_rates=[0.01, 0.02], t=10.0)
    >>> round(r.mtbf, 4)
    116.6667
    """
    lams = as_float_list(failure_rates, "failure_rates")
    t, mttr = _validar_t_mttr(t, mttr)

    def R_func(tt: float) -> float:
        return _r_system("parallel", lams, None, tt)

    mtbf_val = _mtbf_numeric(R_func, min(lams))
    # Disponibilidad en régimen con reparación independiente de cada componente: A = 1 − ∏(1 − Aᵢ)
    avail = 1.0 - math.prod(1.0 - _disponibilidad_componente(lam, mttr) for lam in lams) if mttr is not None else None
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
    """Confiabilidad de un sistema k-de-n (funcionan al menos k de n componentes idénticos).

    Todos los componentes son idénticos con tasa de falla λ.

    R_sys(t) = Σ_{j=k}^{n} C(n,j) · e^{−jλt} · (1 − e^{−λt})^{n−j}

    MTBF (exacto, exponenciales idénticas):
    MTBF = (1/λ) · Σ_{j=k}^{n} (−1)^{j−k} · C(n,j) · C(j−1, k−1) · (1/j)
    que se simplifica a  (1/λ) · Σ_{i=k}^{n} 1/i  para el k-de-n estándar.

    Parameters
    ----------
    n : int
        Número total de componentes.
    k : int
        Número mínimo de componentes que deben funcionar (1 ≤ k ≤ n).
    failure_rate : float
        Tasa de falla λ de los componentes.
    t : float, optional
        Tiempo para evaluar R(t).
    mttr : float, optional
        Tiempo medio de reparación de cada componente. La disponibilidad supone reparación independiente de cada
        componente: A = Σ_{j=k}^{n} C(n,j)·aʲ·(1 − a)ⁿ⁻ʲ, con a = MTBF / (MTBF + MTTR) de un componente. El MTBF
        del resultado es el tiempo medio hasta la falla del sistema sin reparación. Con k = n, ``series_system``
        supone en cambio que los demás componentes no fallan mientras el sistema está detenido.

    Returns
    -------
    ReliabilityResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si no se cumple 1 ≤ k ≤ n.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = koon_system(n=3, k=2, failure_rate=0.01, t=10.0)
    >>> round(r.mtbf, 4)
    83.3333
    """
    n = as_int_positive(n, "n")
    k = as_int_positive(k, "k")
    if k > n:
        raise ValueError(_t("reliability.error.koon_system.debe_cumplirse", k=k, n=n))
    lam = as_positive(failure_rate, "failure_rate")
    t, mttr = _validar_t_mttr(t, mttr)
    lams = [lam] * n

    # Exact MTBF for k-of-n identical exponential:  (1/λ) * Σ_{j=k}^{n} 1/j
    mtbf_val = (1.0 / lam) * sum(1.0 / j for j in range(k, n + 1))

    if mttr is not None:
        # Reparación independiente: cada componente está disponible con probabilidad a, y el sistema si funcionan ≥ k
        a = _disponibilidad_componente(lam, mttr)
        avail: float | None = sum(math.comb(n, j) * a**j * (1.0 - a) ** (n - j) for j in range(k, n + 1))
    else:
        avail = None
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
    """Resultado del análisis Weibull de dos parámetros.

    La FDA es F(t) = 1 − exp(−(t/η)^β).

    Attributes
    ----------
    shape : float
        Parámetro de forma β.
        β < 1 → tasa de falla decreciente (mortalidad infantil).
        β = 1 → tasa de falla constante (modelo exponencial).
        β > 1 → tasa de falla creciente (desgaste).
    scale : float
        Parámetro de escala η (vida característica); F(η) ≈ 63.2 %.
    mttf : float
        Tiempo medio hasta la falla = η · Γ(1 + 1/β).
    b10 : float
        Vida B10: tiempo en el que ha fallado el 10 % de la población.
    b50 : float
        Vida mediana (50 % ha fallado).
    method : str
        Método de estimación: ``'MLE'`` (máxima verosimilitud) o
        ``'RRY'`` (regresión de rangos sobre Y / papel de probabilidad).
    n : int
        Número de tiempos de falla utilizados.
    n_suspended : int
        Número de unidades suspendidas (censuradas por la derecha) utilizadas.
    confidence : float or None
        Nivel de confianza de ``shape_ci`` y ``scale_ci``; ``None`` si no se calcularon.
    shape_ci, scale_ci : tuple[float, float] or None
        Intervalos de confianza de β y η (máxima verosimilitud, aproximación normal de la información observada sobre
        el logaritmo del parámetro). ``None`` con ``method='RRY'`` o si la información no es invertible.
    """

    shape: float
    scale: float
    mttf: float
    b10: float
    b50: float
    method: str
    n: int
    n_suspended: int = 0
    confidence: float | None = None
    shape_ci: tuple[float, float] | None = None
    scale_ci: tuple[float, float] | None = None

    def R(self, t: float) -> float:
        """Confiabilidad en el tiempo *t*: R(t) = exp(−(t/η)^β)."""
        return math.exp(-((t / self.scale) ** self.shape))

    def F(self, t: float) -> float:
        """No confiabilidad (FDA) en el tiempo *t*: F(t) = 1 − R(t)."""
        return 1.0 - self.R(t)

    def h(self, t: float) -> float:
        """Tasa de falla instantánea: h(t) = (β/η)·(t/η)^(β−1)."""
        return (self.shape / self.scale) * ((t / self.scale) ** (self.shape - 1.0))

    def b_life(self, pct: float) -> float:
        """Tiempo en el que ha fallado el porcentaje *pct* de la población.

        Por ejemplo, ``b_life(10)`` devuelve la vida B10.
        """
        p = pct / 100.0
        if not (0.0 < p < 1.0):
            raise ValueError(_t("reliability.error.b_life.pct_debe_estar_estrictamente_entre"))
        return self.scale * (-math.log(1.0 - p)) ** (1.0 / self.shape)

    def summary(self) -> str:
        texto = _t("reliability.etiqueta.summary.metodo_forma_escala_mttf_vida", method=self.method, n=self.n, shape=self.shape, scale=self.scale, mttf=self.mttf, b10=self.b10, b50=self.b50)
        if self.n_suspended:
            texto += "\n" + _t("reliability.etiqueta.summary.suspensiones", n_suspended=self.n_suspended)
        if self.shape_ci is not None and self.scale_ci is not None and self.confidence is not None:
            texto += "\n" + _t("reliability.etiqueta.summary.intervalos", confianza=self.confidence, b_low=self.shape_ci[0], b_high=self.shape_ci[1],
                                 e_low=self.scale_ci[0], e_high=self.scale_ci[1])
        return texto

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            _t("reliability.cabecera.to_frame.forma"):  self.shape,
            _t("reliability.cabecera.to_frame.escala"): self.scale,
            "MTTF":       self.mttf,
            "B10":        self.b10,
            "B50":        self.b50,
            _t("reliability.cabecera.to_frame.metodo"):     self.method,
            "n":          self.n,
            _t("reliability.cabecera.to_frame.suspensiones"): self.n_suspended,
            _t("reliability.cabecera.to_frame.forma_ic_inferior"): None if self.shape_ci is None else self.shape_ci[0],
            _t("reliability.cabecera.to_frame.forma_ic_superior"): None if self.shape_ci is None else self.shape_ci[1],
            _t("reliability.cabecera.to_frame.escala_ic_inferior"): None if self.scale_ci is None else self.scale_ci[0],
            _t("reliability.cabecera.to_frame.escala_ic_superior"): None if self.scale_ci is None else self.scale_ci[1],
        }])


def _weibull_mle_beta(failure_times: list, suspensions: list | None = None) -> float:
    """Resuelve la forma β de Weibull por máxima verosimilitud con bisección (normalizada por estabilidad).

    Con suspensiones (censura por la derecha) la ecuación es 1/β + media_f(ln t) − Σ_todos tᵝ ln t / Σ_todos tᵝ = 0, donde la media se toma
    solo sobre las fallas y las sumas sobre fallas y suspensiones.
    """
    r     = len(failure_times)
    ln_t  = [math.log(t) for t in failure_times]
    # Normalize by the geometric mean of the failures: u_i = t_i / geom_mean.
    # The MLE equation is invariant to this scaling, and u_i near 1
    # keeps u_i^beta from overflowing.
    ln_mean = sum(ln_t) / r           # log of geometric mean of the failures
    norm_ln = [lt - ln_mean for lt in ln_t]   # ln(u_i) of the failures; sum = 0
    todos_ln = norm_ln + [math.log(t) - ln_mean for t in (suspensions or [])]

    def g(beta: float) -> float:
        # u_i^beta = exp(beta * ln(u_i)); clamp to avoid overflow/underflow
        u_beta  = [math.exp(max(-700.0, min(700.0, beta * lt))) for lt in todos_ln]
        s_ub    = sum(u_beta)
        if s_ub == 0.0:
            return float("inf")
        s_ub_ln = sum(ub * lt for ub, lt in zip(u_beta, todos_ln))
        return r / beta - r * s_ub_ln / s_ub   # Σ_f ln(ui)=0 drops out

    lo, hi = 1e-4, 100.0
    if g(lo) <= 0.0:
        warnings.warn(
            _t("reliability.aviso.weibull_mle_beta.forma_estimada_menor_igual_cota", lo=lo),
            UserWarning, stacklevel=3,
        )
        return lo
    if g(hi) >= 0.0:
        warnings.warn(
            _t("reliability.aviso.weibull_mle_beta.tiempos_falla_casi_tienen_dispersion", hi=hi),
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


def _weibull_rry(failure_times: list, suspensions: list | None = None) -> tuple:
    """Estima β y η por regresión de rangos sobre Y (papel de probabilidad).

    Con suspensiones usa los rangos ajustados de Johnson (1964): para la falla en la posición *i* (de *n* unidades) el rango pasa de
    ``previo`` a ``previo + (n + 1 − previo) / (n − i + 2)``, y el rango mediano de Benard es (rango − 0,3) / (n + 0,4).
    """
    susp    = suspensions or []
    n       = len(failure_times) + len(susp)
    # fallas antes que suspensiones en caso de empate
    orden   = sorted([(t, 0) for t in failure_times] + [(t, 1) for t in susp])
    previo  = 0.0
    X: list[float] = []
    Y: list[float] = []
    for pos, (t, es_susp) in enumerate(orden, start=1):
        if es_susp:
            continue
        previo = previo + (n + 1 - previo) / (n - pos + 2)
        F      = (previo - 0.3) / (n + 0.4)          # rango mediano de Benard
        X.append(math.log(t))
        Y.append(math.log(-math.log(1.0 - F)))
    n_pts   = float(len(X))
    sx      = sum(X)
    sy      = sum(Y)
    sxx     = sum(x * x for x in X)
    sxy     = sum(x * y for x, y in zip(X, Y))
    slope   = (n_pts * sxy - sx * sy) / (n_pts * sxx - sx ** 2)
    intercept = (sy - slope * sx) / n_pts
    beta    = slope
    eta     = math.exp(-intercept / beta)
    return beta, eta


def _weibull_intervalos(failure_times: list, suspensions: list, beta: float, eta: float, confianza: float) -> tuple:
    """Intervalos de confianza de β y η a partir de la información observada (aproximación normal sobre el logaritmo del parámetro).

    Con r fallas y todas las unidades i (fallas y suspensiones), zᵢ = (tᵢ/η)ᵝ y Lᵢ = ln(tᵢ/η), la matriz de información observada tiene
    I_ββ = r/β² + Σ zᵢLᵢ², I_ηη = (β(β+1)Σzᵢ − rβ)/η² e I_βη = −(Σzᵢ − r + βΣzᵢLᵢ)/η. Devuelve (None, None) si no es invertible.
    """
    todos = failure_times + suspensions
    r     = len(failure_times)
    z     = [(t / eta) ** beta for t in todos]
    L     = [math.log(t / eta) for t in todos]
    sz, szl, szl2 = sum(z), sum(zi * li for zi, li in zip(z, L)), sum(zi * li * li for zi, li in zip(z, L))
    i_bb  = r / beta**2 + szl2
    i_ee  = (beta * (beta + 1.0) * sz - r * beta) / eta**2
    i_be  = -(sz - r + beta * szl) / eta
    det   = i_bb * i_ee - i_be**2
    if not (math.isfinite(det) and det > 0.0 and i_bb > 0.0 and i_ee > 0.0):
        return None, None
    var_b = i_ee / det
    var_e = i_bb / det
    q     = NormalDist().inv_cdf(0.5 + confianza / 2.0)
    se_ln_b, se_ln_e = math.sqrt(var_b) / beta, math.sqrt(var_e) / eta
    return (
        (beta * math.exp(-q * se_ln_b), beta * math.exp(q * se_ln_b)),
        (eta * math.exp(-q * se_ln_e), eta * math.exp(q * se_ln_e)),
    )


def weibull_analysis(
    failure_times: Sequence[float],
    *,
    method: str = "MLE",
    suspensions: Sequence[float] | None = None,
    confidence: float = 0.95,
) -> WeibullResult:
    """Ajusta una distribución Weibull de dos parámetros a tiempos de falla, con o sin unidades suspendidas (censura por la derecha).

    F(t) = 1 − exp(−(t/η)^β)

    En fiabilidad real casi siempre hay unidades que siguen funcionando cuando termina el estudio o que se retiran por otra causa
    (suspensiones). Ignorarlas, o tratarlas como fallas, sesga la vida estimada: con las suspensiones, la máxima verosimilitud usa
    f(t) para las fallas y R(t) para las suspendidas. Con ``method='MLE'`` el resultado incluye intervalos de confianza de β y η.

    Parameters
    ----------
    failure_times : sequence of float
        Tiempos de falla observados (todos deben ser > 0). Se requieren al menos 2 valores.
    method : str
        ``'MLE'`` (por defecto): máxima verosimilitud mediante bisección;
        ``'RRY'``: regresión de rangos sobre Y (papel de probabilidad; con suspensiones, rangos ajustados de Johnson).
    suspensions : sequence of float, optional
        Tiempos de las unidades suspendidas: siguieron funcionando hasta ese tiempo sin fallar (todos > 0).
    confidence : float
        Nivel de confianza de los intervalos de β y η (por defecto 0.95), solo con ``method='MLE'``.

    Returns
    -------
    WeibullResult


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si hay menos de 2 tiempos de falla, todos son iguales, ``method`` no es ``'MLE'`` ni ``'RRY'`` o ``confidence`` no está
        estrictamente entre 0 y 1.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> import math
    >>> # Generate Weibull(β=2, η=100) data via inverse CDF
    >>> times = [100 * (-math.log(1 - p)) ** 0.5 for p in [.1,.2,.3,.4,.5,.6,.7,.8,.9]]
    >>> r = weibull_analysis(times)
    >>> 2.0 < r.shape < 3.0  # cuantiles equiespaciados: menos dispersión que una muestra aleatoria
    True
    >>> r = weibull_analysis(times[:6], suspensions=[80.0, 90.0, 95.0])  # tres unidades siguieron funcionando
    >>> r.n, r.n_suspended
    (6, 3)
    """
    t_list = as_float_list(failure_times, "failure_times", min_len=2)
    susp_list = as_float_list(suspensions, "suspensions", min_len=1) if suspensions is not None and len(suspensions) > 0 else []
    conf = as_fraction(confidence, "confidence")
    if conf <= 0.0 or conf >= 1.0:
        raise ValueError(_t("reliability.error.weibull_analysis.confidence_entre_0_1"))
    if max(t_list) == min(t_list):
        raise ValueError(
            _t("reliability.error.weibull_analysis.todos_tiempos_falla_son_iguales")
        )

    m = method.upper()
    if m not in ("MLE", "RRY"):
        raise ValueError(_t("reliability.error.weibull_analysis.method_debe_ser_mle_rry"))

    shape_ci = scale_ci = None
    if m == "MLE":
        beta  = _weibull_mle_beta(t_list, susp_list)
        eta   = ((sum(t ** beta for t in t_list) + sum(t ** beta for t in susp_list)) / len(t_list)) ** (1.0 / beta)
        shape_ci, scale_ci = _weibull_intervalos(t_list, susp_list, beta, eta, conf)
    else:
        beta, eta = _weibull_rry(t_list, susp_list)

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
        n_suspended=len(susp_list),
        confidence=conf if shape_ci is not None else None,
        shape_ci=shape_ci,
        scale_ci=scale_ci,
    )
