"""Project scheduling: CPM (Critical Path Method) and PERT."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from statistics import NormalDist
from typing import TYPE_CHECKING

from ._utils import as_finite_scalar, as_nonneg

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class ActivityResult:
    """Scheduled activity from CPM / PERT.

    Attributes
    ----------
    name : str
    duration : float
        Deterministic duration (CPM) or PERT expected duration te.
    predecessors : list[str]
    es : float
        Early start.
    ef : float
        Early finish.
    ls : float
        Late start.
    lf : float
        Late finish.
    total_float : float
        Total float (slack) = LS − ES.
    free_float : float
        Free float = min(ES of successors) − EF.
    is_critical : bool
    optimistic : float | None
        PERT only.
    most_likely : float | None
        PERT only.
    pessimistic : float | None
        PERT only.
    variance : float | None
        ((b − a) / 6)² — PERT only.
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
    """CPM / PERT project schedule result.

    Attributes
    ----------
    activities : list[ActivityResult]
    critical_path : list[str]
        Activity names on the critical path in topological order.
    project_duration : float
        Earliest project completion time (expected duration for PERT).
    method : str
        ``'CPM'`` or ``'PERT'``.
    project_variance : float | None
        Sum of critical-path variances (PERT only).
    project_std : float | None
        √(project_variance) (PERT only).
    """

    activities: list
    critical_path: list
    project_duration: float
    method: str
    project_variance: float | None = None
    project_std: float | None = None

    def probability(self, target: float) -> float:
        """P(project duration ≤ target) via normal approximation (PERT only).

        Parameters
        ----------
        target : float
            Target project completion time T.

        Returns
        -------
        float
        """
        target = as_finite_scalar(target, "target")
        if self.project_std is None or self.project_std == 0.0:
            raise ValueError("probability() requiere un resultado PERT con varianza distinta de cero.")
        z = (target - self.project_duration) / self.project_std
        return NormalDist().cdf(z)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "Activity":    a.name,
            "Duration":    a.duration,
            "Predecessors": ", ".join(str(p) for p in a.predecessors),
            "ES": a.es,  "EF": a.ef,
            "LS": a.ls,  "LF": a.lf,
            "TF": a.total_float,
            "FF": a.free_float,
            "Critical": a.is_critical,
        } for a in self.activities])

    def summary(self) -> str:
        lines = [
            f"Method           : {self.method}",
            f"Project duration : {self.project_duration:.4g}",
            f"Critical path    : {' → '.join(self.critical_path)}",
        ]
        if self.project_variance is not None:
            lines += [
                f"Project variance : {self.project_variance:.4g}",
                f"Project σ        : {self.project_std:.4g}",
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
        raise TypeError("'activities' debe ser una lista de diccionarios.")
    activities = list(activities)
    if not activities:
        raise ValueError("'activities' debe contener al menos una actividad.")
    vistos: set = set()
    for i, a in enumerate(activities):
        if not isinstance(a, dict):
            raise TypeError(f"activities[{i}] debe ser un diccionario, se recibió {type(a).__name__!r}.")
        if "name" not in a:
            raise ValueError(f"activities[{i}]: falta la clave 'name'.")
        nm = str(a["name"])
        if nm in vistos:
            raise ValueError(f"Nombre de actividad duplicado: '{nm}'. Cada actividad debe tener un nombre único.")
        vistos.add(nm)
        preds = a.get("predecessors", [])
        if isinstance(preds, (str, bytes)) or not hasattr(preds, "__iter__"):
            raise TypeError(f"activities[{i}]['predecessors'] debe ser una lista de nombres.")
    return activities


def _toposort_and_succ(acts: dict) -> tuple:
    """Kahn's algorithm. Returns (topo_order, successors_dict)."""
    in_deg: dict = {name: 0 for name in acts}
    succ:   dict = {name: [] for name in acts}
    for name, act in acts.items():
        for pred in act["predecessors"]:
            if pred not in acts:
                raise ValueError(
                    f"Activity '{name}' references unknown predecessor '{pred}'."
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
        raise ValueError("Activities contain a cycle.")
    return order, succ


def _forward_backward(acts: dict, durations: dict) -> tuple:
    """Forward + backward pass. Returns (ES, EF, LS, LF, T, succ)."""
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
            total_float=round(tf, 10),
            free_float=round(ff, 10),
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
    """Critical Path Method (CPM) for deterministic project scheduling.

    Computes early/late start and finish times, total and free float, and
    identifies the critical path (activities with zero total float).

    Parameters
    ----------
    activities : list of dict
        Each dict must have:

        - ``'name'``: activity identifier (str).
        - ``'duration'``: deterministic processing time (float ≥ 0).
        - ``'predecessors'``: list of predecessor names (empty for start activities).

    Returns
    -------
    ProjectResult
        ``method = 'CPM'``.  ``project_variance`` and ``project_std`` are
        ``None`` for CPM.

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
            raise ValueError(f"Actividad '{nm}': falta la clave 'duration'.")
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
    """PERT (Program Evaluation and Review Technique) project scheduling.

    Uses the three-estimate beta-distribution approximation:

        te = (a + 4m + b) / 6       (expected duration)
        σ² = ((b − a) / 6)²         (variance)

    The project duration distribution is approximated as normal with
    μ = expected critical-path length and σ² = sum of critical-path variances.

    Parameters
    ----------
    activities : list of dict
        Each dict must have:

        - ``'name'``: activity identifier.
        - ``'optimistic'`` (a): best-case duration.
        - ``'most_likely'`` (m): most probable duration.
        - ``'pessimistic'`` (b): worst-case duration.
        - ``'predecessors'``: list of predecessor names.

    Returns
    -------
    ProjectResult
        ``project_duration`` is the expected critical-path length.
        Call ``.probability(T)`` for P(completion ≤ T).

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
                raise ValueError(f"Actividad '{nm}': falta la clave '{clave}'.")
        o = as_nonneg(a["optimistic"], f"activities['{nm}']['optimistic']")
        m = as_nonneg(a["most_likely"], f"activities['{nm}']['most_likely']")
        b = as_nonneg(a["pessimistic"], f"activities['{nm}']['pessimistic']")
        if not (o <= m <= b):
            raise ValueError(
                f"Actividad '{nm}': se requiere optimistic ≤ most_likely ≤ pessimistic."
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
