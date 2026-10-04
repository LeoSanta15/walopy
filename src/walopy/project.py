"""Programación de proyectos: CPM (método de la ruta crítica) y PERT."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from statistics import NormalDist
from typing import TYPE_CHECKING

from ._i18n import t as _t
from ._utils import as_finite_scalar, as_nonneg

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


def pert(activities: list) -> ProjectResult:
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

    Returns
    -------
    ProjectResult
        ``project_duration`` es la longitud esperada de la ruta crítica.
        Llame a ``.probability(T)`` para P(terminación ≤ T).


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``activities`` está vacío, hay nombres duplicados, un predecesor desconocido, un ciclo o no se cumple optimistic ≤ most_likely ≤ pessimistic.
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
    """
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
    proj_var = sum(variances[nm] for nm in crit)

    return ProjectResult(
        activities=results,
        critical_path=crit,
        project_duration=T,
        method="PERT",
        project_variance=proj_var,
        project_std=math.sqrt(proj_var),
    )
