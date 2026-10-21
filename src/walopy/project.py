"""Programación de proyectos: CPM (método de la ruta crítica) y PERT."""
from __future__ import annotations

import math
import warnings
from collections import deque
from dataclasses import dataclass, field
from statistics import NormalDist
from typing import TYPE_CHECKING

import numpy as np

from ._i18n import t as _t
from ._utils import as_finite_scalar, as_int_positive, as_nonneg

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class ActivityResult:
    """Actividad programada por CPM / PERT.

    Attributes
    ----------
    name : str
    duration : float
        Duración determinística (CPM) o duración esperada tₑ de PERT.
    predecessors : list[str]
    es : float
        Inicio más temprano.
    ef : float
        Fin más temprano.
    ls : float
        Inicio más tardío.
    lf : float
        Fin más tardío.
    total_float : float
        Holgura total = LS − ES.
    free_float : float
        Holgura libre = min(ES de los sucesores) − EF.
    is_critical : bool
    optimistic : float | None
        Solo PERT.
    most_likely : float | None
        Solo PERT.
    pessimistic : float | None
        Solo PERT.
    variance : float | None
        ((b − a) / 6)² — solo PERT.
    """

    name: str
    duration: float
    predecessors: list
    es: float
    ef: float
    ls: float
    lf: float
    total_float: float
    free_float: float
    is_critical: bool
    optimistic: float | None = None
    most_likely: float | None = None
    pessimistic: float | None = None
    variance: float | None = None


@dataclass
class ProjectResult:
    """Resultado de la programación de un proyecto con CPM / PERT.

    Attributes
    ----------
    activities : list[ActivityResult]
    critical_path : list[str]
        Nombres de las actividades de la ruta crítica en orden topológico.
    project_duration : float
        Menor tiempo de terminación del proyecto (duración esperada en PERT).
    method : str
        ``'CPM'`` o ``'PERT'``.
    project_variance : float | None
        Suma de las varianzas de la ruta crítica (solo PERT).
    project_std : float | None
        √(project_variance) (solo PERT).
    """

    activities: list
    critical_path: list
    project_duration: float
    method: str
    project_variance: float | None = None
    project_std: float | None = None
    n_simulations: int = 0
    mc_mean: float | None = None
    mc_std: float | None = None
    criticality_index: dict | None = None
    _mc_durations: np.ndarray | None = field(default=None, repr=False)

    def probability_mc(self, target: float) -> float:
        """P(duración del proyecto ≤ objetivo) estimada por simulación (requiere ``pert(..., n_simulations=N)``).

        A diferencia de ``probability`` (normal sobre una sola ruta), considera todas las rutas: con varias rutas casi
        críticas es bastante menor.

        Parameters
        ----------
        target : float
            Tiempo objetivo T de terminación del proyecto.

        Returns
        -------
        float
        """
        target = as_finite_scalar(target, "target")
        if self._mc_durations is None:
            raise ValueError(_t("project.error.probability_mc.requiere_simulacion"))
        return float(np.mean(self._mc_durations <= target))

    def percentile_mc(self, q: float) -> float:
        """Percentil *q* (0 a 100) de la duración simulada del proyecto (requiere ``pert(..., n_simulations=N)``).

        Parameters
        ----------
        q : float
            Percentil entre 0 y 100.

        Returns
        -------
        float
        """
        q = as_finite_scalar(q, "q")
        if self._mc_durations is None:
            raise ValueError(_t("project.error.probability_mc.requiere_simulacion"))
        if not 0.0 <= q <= 100.0:
            raise ValueError(_t("project.error.percentile_mc.q_entre_0_100", q=q))
        return float(np.percentile(self._mc_durations, q))

    def probability(self, target: float) -> float:
        """P(duración del proyecto ≤ objetivo) mediante aproximación normal (solo PERT).

        Parameters
        ----------
        target : float
            Tiempo objetivo T de terminación del proyecto.

        Returns
        -------
        float
        """
        target = as_finite_scalar(target, "target")
        if self.project_std is None or self.project_std == 0.0:
            raise ValueError(_t("project.error.probability.probability_requiere_resultado_pert_varianza"))
        z = (target - self.project_duration) / self.project_std
        return NormalDist().cdf(z)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            _t("project.cabecera.to_frame.actividad"):    a.name,
            _t("project.cabecera.to_frame.duracion"):    a.duration,
            _t("project.cabecera.to_frame.predecesoras"): ", ".join(str(p) for p in a.predecessors),
            "ES": a.es,  "EF": a.ef,
            "LS": a.ls,  "LF": a.lf,
            _t("project.cabecera.to_frame.ht"): a.total_float,
            _t("project.cabecera.to_frame.hl"): a.free_float,
            _t("project.cabecera.to_frame.critica"): a.is_critical,
            **({_t("project.cabecera.to_frame.indice_criticidad"): self.criticality_index[a.name]} if self.criticality_index is not None else {}),
        } for a in self.activities])

    def summary(self) -> str:
        lines = [
            _t("project.etiqueta.summary.metodo", method=self.method),
            _t("project.etiqueta.summary.duracion_proyecto", project_duration=self.project_duration),
            _t("project.etiqueta.summary.ruta_critica", expr=' → '.join(self.critical_path)),
        ]
        if self.project_variance is not None:
            lines += [
                _t("project.etiqueta.summary.varianza_proyecto", project_variance=self.project_variance),
                _t("project.etiqueta.summary.proyecto", project_std=self.project_std),
            ]
        if self._mc_durations is not None:
            lines.append(_t("project.etiqueta.summary.simulacion", n=self.n_simulations, mc_mean=self.mc_mean, mc_std=self.mc_std,
                            p50=self.percentile_mc(50), p90=self.percentile_mc(90)))
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _leer_actividades(activities) -> list:
    """Valida la lista de actividades: tipo, nombres obligatorios y sin duplicados."""
    if isinstance(activities, (str, bytes, dict)) or not hasattr(activities, "__iter__"):
        raise TypeError(_t("project.error.leer_actividades.activities_debe_ser_lista_diccionarios"))
    activities = list(activities)
    if not activities:
        raise ValueError(_t("project.error.leer_actividades.activities_debe_contener_menos_actividad"))
    vistos: set = set()
    for i, a in enumerate(activities):
        if not isinstance(a, dict):
            raise TypeError(_t("project.error.leer_actividades.activities_debe_ser_diccionario_recibio", i=i, __name__=type(a).__name__))
        if "name" not in a:
            raise ValueError(_t("project.error.leer_actividades.activities_falta_clave_name", i=i))
        nm = str(a["name"])
        if nm in vistos:
            raise ValueError(_t("project.error.leer_actividades.nombre_actividad_duplicado_cada_actividad", nm=nm))
        vistos.add(nm)
        preds = a.get("predecessors", [])
        if isinstance(preds, (str, bytes)) or not hasattr(preds, "__iter__"):
            raise TypeError(_t("project.error.leer_actividades.activities_predecessors_debe_ser_lista", i=i))
    return activities


def _toposort_and_succ(acts: dict) -> tuple:
    """Algoritmo de Kahn. Devuelve (orden_topológico, diccionario_de_sucesores)."""
    in_deg: dict = {name: 0 for name in acts}
    succ:   dict = {name: [] for name in acts}
    for name, act in acts.items():
        for pred in act["predecessors"]:
            if pred not in acts:
                raise ValueError(
                    _t("project.error.toposort_and_succ.actividad_referencia_predecesor_desconocido", name=name, pred=pred)
                )
            succ[pred].append(name)
            in_deg[name] += 1
    queue = deque(sorted(n for n in acts if in_deg[n] == 0))
    order: list = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for s in succ[node]:
            in_deg[s] -= 1
            if in_deg[s] == 0:
                queue.append(s)
    if len(order) != len(acts):
        raise ValueError(_t("project.error.toposort_and_succ.actividades_contienen_ciclo"))
    return order, succ


def _forward_backward(acts: dict, durations: dict) -> tuple:
    """Pasada hacia adelante y hacia atrás. Devuelve (ES, EF, LS, LF, T, sucesores)."""
    order, succ = _toposort_and_succ(acts)

    ES: dict = {}
    EF: dict = {}
    for name in order:
        ES[name] = max((EF[p] for p in acts[name]["predecessors"]), default=0.0)
        EF[name] = ES[name] + durations[name]

    T = max(EF.values())

    LS: dict = {}
    LF: dict = {}
    for name in reversed(order):
        LF[name] = min((LS[s] for s in succ[name]), default=T)
        LS[name] = LF[name] - durations[name]

    return ES, EF, LS, LF, T, succ


def _ruta_critica_de_mayor_varianza(acts: dict, crit: list, variances: dict, ES: dict, EF: dict, T: float) -> tuple:
    """Ruta crítica (de inicio a fin) con la mayor varianza y esa varianza.

    Con varias rutas críticas empatadas, la varianza del proyecto es la de **una** ruta (la convención es la de mayor
    varianza), no la suma de todas las actividades críticas.
    """
    criticas = set(crit)
    mejor: dict[str, float] = {}
    previa: dict[str, str | None] = {}
    for nm in [n for n in _toposort_and_succ(acts)[0] if n in criticas]:
        candidatas = [p for p in acts[nm]["predecessors"] if p in criticas and abs(EF[p] - ES[nm]) < 1e-9]
        p_max = max(candidatas, key=lambda p: mejor[p], default=None)
        mejor[nm] = variances[nm] + (mejor[p_max] if p_max is not None else 0.0)
        previa[nm] = p_max
    finales = [nm for nm in mejor if abs(EF[nm] - T) < 1e-9]
    if not finales:
        return [], 0.0
    final = max(finales, key=lambda n: mejor[n])
    varianza = mejor[final]
    nodo: str | None = final
    ruta: list[str] = []
    while nodo is not None:
        ruta.append(nodo)
        nodo = previa[nodo]
    return ruta[::-1], varianza


def _build_results(acts: dict, durations: dict, ES, EF, LS, LF, T, succ,
                   opt=None, ml=None, pess=None, variances=None) -> list:
    results = []
    for name in acts:
        tf  = LS[name] - ES[name]
        ff  = min((ES[s] for s in succ[name]), default=T) - EF[name]
        results.append(ActivityResult(
            name=name,
            duration=durations[name],
            predecessors=acts[name]["predecessors"],
            es=ES[name], ef=EF[name],
            ls=LS[name], lf=LF[name],
            total_float=round(tf, 10) + 0.0,  # + 0.0 convierte -0.0 en 0.0
            free_float=round(ff, 10) + 0.0,
            is_critical=abs(tf) < 1e-9,
            optimistic=opt[name]       if opt       else None,
            most_likely=ml[name]       if ml        else None,
            pessimistic=pess[name]     if pess      else None,
            variance=variances[name]   if variances else None,
        ))
    results.sort(key=lambda a: (a.es, a.name))
    return results


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def cpm(activities: list) -> ProjectResult:
    """Método de la Ruta Crítica (CPM) para la programación determinística de proyectos.

    Calcula los tiempos de inicio y fin más tempranos y más tardíos, las holguras total y
    libre, e identifica la ruta crítica (actividades con holgura total cero).

    Parameters
    ----------
    activities : list of dict
        Cada diccionario debe tener:

        - ``'name'``: identificador de la actividad (str).
        - ``'duration'``: tiempo de proceso determinístico (float ≥ 0).
        - ``'predecessors'``: lista de nombres de predecesoras (vacía en las actividades iniciales).

    Returns
    -------
    ProjectResult
        ``method = 'CPM'``. ``project_variance`` y ``project_std`` son
        ``None`` en CPM.


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``activities`` está vacío, hay nombres duplicados, un predecesor desconocido o un ciclo.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> acts = [
    ...     {"name": "A", "duration": 3, "predecessors": []},
    ...     {"name": "B", "duration": 4, "predecessors": ["A"]},
    ...     {"name": "C", "duration": 2, "predecessors": ["A"]},
    ...     {"name": "D", "duration": 1, "predecessors": ["B", "C"]},
    ... ]
    >>> r = cpm(acts)
    >>> r.project_duration
    8.0
    """
    acts: dict = {}
    for a in _leer_actividades(activities):
        nm = str(a["name"])
        if "duration" not in a:
            raise ValueError(_t("project.error.cpm.actividad_falta_clave_duration", nm=nm))
        dur = as_nonneg(a["duration"], f"activities['{nm}']['duration']")
        acts[nm] = {
            "duration":     dur,
            "predecessors": [str(p) for p in a.get("predecessors", [])],
        }

    durations = {nm: acts[nm]["duration"] for nm in acts}
    ES, EF, LS, LF, T, succ = _forward_backward(acts, durations)
    results = _build_results(acts, durations, ES, EF, LS, LF, T, succ)
    crit = [a.name for a in results if a.is_critical]

    return ProjectResult(
        activities=results,
        critical_path=crit,
        project_duration=T,
        method="CPM",
    )


MAX_SIMULACIONES_PERT = 10**6
_CELDAS_POR_BLOQUE = 500_000   # actividades × simulaciones por bloque (acota la memoria)


def _simular_pert(acts: dict, opt: dict, ml: dict, pess: dict, n_sim: int, seed: int | None) -> tuple:
    """Simulación Monte Carlo de PERT con duraciones beta-PERT: a + (b − a)·Beta(1 + 4(m − a)/(b − a), 1 + 4(b − m)/(b − a)).

    Devuelve (duraciones del proyecto, índice de criticidad por actividad). El índice es la fracción de simulaciones en que la actividad
    está en la ruta crítica (siguiendo, desde la última en terminar, el predecesor que fija el inicio de cada actividad).
    """
    orden, _ = _toposort_and_succ(acts)
    rng = np.random.default_rng(seed)
    n_act = len(orden)
    bloque = max(1, min(n_sim, _CELDAS_POR_BLOQUE // n_act))
    duraciones = np.empty(n_sim)
    cuenta = {nm: 0 for nm in orden}
    hecho = 0
    while hecho < n_sim:
        c = min(bloque, n_sim - hecho)
        ef: dict = {}
        pred_idx: dict = {}
        for nm in orden:
            a, m, b = opt[nm], ml[nm], pess[nm]
            if b > a:
                alfa, beta = 1.0 + 4.0 * (m - a) / (b - a), 1.0 + 4.0 * (b - m) / (b - a)
                dur = a + (b - a) * rng.beta(alfa, beta, size=c)
            else:
                dur = np.full(c, float(a))
            preds = acts[nm]["predecessors"]
            if preds:
                matriz = np.stack([ef[p] for p in preds])
                pred_idx[nm] = matriz.argmax(axis=0)
                inicio = matriz.max(axis=0)
            else:
                inicio = np.zeros(c)
            ef[nm] = inicio + dur
        todas = np.stack([ef[nm] for nm in orden])
        fin_idx = todas.argmax(axis=0)
        duraciones[hecho:hecho + c] = todas.max(axis=0)
        critica = {nm: fin_idx == k for k, nm in enumerate(orden)}
        for nm in reversed(orden):
            preds = acts[nm]["predecessors"]
            for k, p in enumerate(preds):
                critica[p] = critica[p] | (critica[nm] & (pred_idx[nm] == k))
        for nm in orden:
            cuenta[nm] += int(critica[nm].sum())
        hecho += c
    return duraciones, {nm: cuenta[nm] / n_sim for nm in orden}


def pert(activities: list, *, n_simulations: int = 0, seed: int | None = None) -> ProjectResult:
    """Programación de proyectos PERT (Técnica de Evaluación y Revisión de Programas).

    Usa la aproximación de la distribución beta con tres estimaciones:

        te = (a + 4m + b) / 6       (duración esperada)
        σ² = ((b − a) / 6)²         (varianza)

    La distribución de la duración del proyecto se aproxima como normal con
    μ = longitud esperada de la ruta crítica y σ² = suma de las varianzas de la ruta crítica.

    Parameters
    ----------
    activities : list of dict
        Cada diccionario debe tener:

        - ``'name'``: identificador de la actividad.
        - ``'optimistic'`` (a): duración en el mejor caso.
        - ``'most_likely'`` (m): duración más probable.
        - ``'pessimistic'`` (b): duración en el peor caso.
        - ``'predecessors'``: lista de nombres de predecesoras.

    n_simulations : int
        Si es mayor que 0, además simula el proyecto ``n_simulations`` veces con duraciones beta-PERT (a + (b − a)·Beta(α, β), con
        α = 1 + 4(m − a)/(b − a) y β = 1 + 4(b − m)/(b − a), que tiene media (a + 4m + b)/6). Considera **todas** las rutas, a diferencia
        de la aproximación normal sobre una sola ruta, que es optimista cuando convergen varias rutas casi críticas. Añade
        ``mc_mean``, ``mc_std``, ``criticality_index`` (fracción de simulaciones en que cada actividad es crítica),
        ``probability_mc(T)`` y ``percentile_mc(q)``. Máximo 1 000 000.
    seed : int, optional
        Semilla de la simulación (reproducibilidad).

    Returns
    -------
    ProjectResult
        ``project_duration`` es la longitud esperada de la ruta crítica.
        Llame a ``.probability(T)`` para P(terminación ≤ T) (normal, una ruta) o, con ``n_simulations``,
        a ``.probability_mc(T)`` (todas las rutas).


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``activities`` está vacío, hay nombres duplicados, un predecesor desconocido, un ciclo o no se cumple optimistic ≤ most_likely ≤ pessimistic.
        Si ``n_simulations`` no es un entero entre 0 y 1 000 000.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> acts = [
    ...     {"name": "A", "optimistic": 1, "most_likely": 3, "pessimistic": 5, "predecessors": []},
    ...     {"name": "B", "optimistic": 2, "most_likely": 4, "pessimistic": 6, "predecessors": ["A"]},
    ... ]
    >>> r = pert(acts)
    >>> round(r.project_duration, 4)
    7.0
    >>> r = pert(acts, n_simulations=2000, seed=1)
    >>> r.n_simulations, round(r.criticality_index["A"], 2)
    (2000, 1.0)
    """
    if n_simulations != 0:
        n_sim = as_int_positive(n_simulations, "n_simulations", max=MAX_SIMULACIONES_PERT)
    else:
        n_sim = 0
    acts:      dict = {}
    opt_d:     dict = {}
    ml_d:      dict = {}
    pess_d:    dict = {}

    for a in _leer_actividades(activities):
        nm = str(a["name"])
        for clave in ("optimistic", "most_likely", "pessimistic"):
            if clave not in a:
                raise ValueError(_t("project.error.pert.actividad_falta_clave", nm=nm, clave=clave))
        o = as_nonneg(a["optimistic"], f"activities['{nm}']['optimistic']")
        m = as_nonneg(a["most_likely"], f"activities['{nm}']['most_likely']")
        b = as_nonneg(a["pessimistic"], f"activities['{nm}']['pessimistic']")
        if not (o <= m <= b):
            raise ValueError(
                _t("project.error.pert.actividad_requiere_optimistic_most_likely", nm=nm)
            )
        te = (o + 4.0 * m + b) / 6.0
        acts[nm] = {
            "duration":     te,
            "predecessors": [str(p) for p in a.get("predecessors", [])],
        }
        opt_d[nm], ml_d[nm], pess_d[nm] = o, m, b

    durations  = {nm: acts[nm]["duration"] for nm in acts}
    variances  = {nm: ((pess_d[nm] - opt_d[nm]) / 6.0) ** 2 for nm in acts}
    ES, EF, LS, LF, T, succ = _forward_backward(acts, durations)
    results = _build_results(acts, durations, ES, EF, LS, LF, T, succ,
                             opt=opt_d, ml=ml_d, pess=pess_d, variances=variances)
    crit     = [a.name for a in results if a.is_critical]
    ruta, proj_var = _ruta_critica_de_mayor_varianza(acts, crit, variances, ES, EF, T)
    sigma = math.sqrt(proj_var)
    casi_criticas = [a.name for a in results if a.name not in ruta and a.total_float <= sigma + 1e-9]
    if sigma > 0 and casi_criticas and n_sim == 0:
        warnings.warn(
            _t("project.aviso.pert.rutas_casi_criticas", n=len(casi_criticas), actividades=", ".join(casi_criticas[:5]), sigma=sigma),
            UserWarning, stacklevel=2,
        )

    duraciones = indice = None
    if n_sim > 0:
        duraciones, indice = _simular_pert(acts, opt_d, ml_d, pess_d, n_sim, seed)

    return ProjectResult(
        activities=results,
        critical_path=crit,
        project_duration=T,
        method="PERT",
        project_variance=proj_var,
        project_std=math.sqrt(proj_var),
        n_simulations=n_sim,
        mc_mean=None if duraciones is None else float(duraciones.mean()),
        mc_std=None if duraciones is None else float(duraciones.std(ddof=1)) if len(duraciones) > 1 else 0.0,
        criticality_index=indice,
        _mc_durations=duraciones,
    )
