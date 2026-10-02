"""Programación de la producción: reglas de despacho de una máquina, flow-shop de Johnson y heurística NEH."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypedDict

from ._utils import as_float_list, as_positive


class _Trabajo(TypedDict):
    name: str
    p: float
    d: Optional[float]
    w: float


class _TrabajoJohnson(TypedDict):
    name: str
    a: float
    b: float


if TYPE_CHECKING:
    import pandas as pd


@dataclass
class JobSchedule:
    """Resultado por trabajo tras la programación."""

    name: str
    processing_time: float
    due_date: float | None
    weight: float
    start_time: float
    completion_time: float
    lateness: float       # Cj − dj (negative = early)
    tardiness: float      # max(0, Cj − dj)
    is_tardy: bool


@dataclass
class ScheduleResult:
    """Resultado de la programación de una máquina.

    Attributes
    ----------
    rule : str
        Regla de despacho utilizada.
    sequence : list[str]
        Nombres de los trabajos en orden de procesamiento.
    jobs : list[JobSchedule]
        Detalle de la programación por trabajo.
    makespan : float
        Tiempo total transcurrido (suma de todos los tiempos de proceso).
    total_completion_time : float
        Suma de los tiempos de finalización ΣCj.
    total_weighted_completion_time : float
        Suma ponderada de los tiempos de finalización ΣwjCj.
    max_lateness : float
        Retraso máximo max(Lj).
    total_tardiness : float
        Suma de las tardanzas ΣTj.
    n_tardy : int
        Número de trabajos con retraso.
    """

    rule: str
    sequence: list
    jobs: list
    makespan: float
    total_completion_time: float
    total_weighted_completion_time: float
    max_lateness: float
    total_tardiness: float
    n_tardy: int

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "Trabajo": j.name,
            "p": j.processing_time,
            "d": j.due_date,
            "w": j.weight,
            "Inicio": j.start_time,
            "C": j.completion_time,
            "L": j.lateness,
            "T": j.tardiness,
            "Con retraso": j.is_tardy,
        } for j in self.jobs])

    def summary(self) -> str:
        lines = [
            f"Regla                   : {self.rule}",
            f"Secuencia               : {' → '.join(self.sequence)}",
            f"Makespan (Cmax)         : {self.makespan:.4g}",
            f"Finalización total ΣCj  : {self.total_completion_time:.4g}",
            f"Finalización pond. ΣwCj : {self.total_weighted_completion_time:.4g}",
            f"Retraso máximo          : {self.max_lateness:.4g}",
            f"Tardanza total ΣTj      : {self.total_tardiness:.4g}",
            f"Trabajos con retraso    : {self.n_tardy}",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def _build_schedule(jobs_sorted: list, rule: str) -> ScheduleResult:
    t = 0.0
    scheduled = []
    for job in jobs_sorted:
        start = t
        t += job["p"]
        if job["d"] is not None:
            lateness = t - job["d"]
            tardiness = max(0.0, lateness)
            tardy = tardiness > 0
        else:
            lateness = 0.0
            tardiness = 0.0
            tardy = False
        scheduled.append(JobSchedule(
            name=job["name"],
            processing_time=job["p"],
            due_date=job["d"],
            weight=job["w"],
            start_time=start,
            completion_time=t,
            lateness=lateness,
            tardiness=tardiness,
            is_tardy=tardy,
        ))

    latenesses = [j.lateness for j in scheduled if j.due_date is not None]
    return ScheduleResult(
        rule=rule,
        sequence=[j.name for j in scheduled],
        jobs=scheduled,
        makespan=t,
        total_completion_time=sum(j.completion_time for j in scheduled),
        total_weighted_completion_time=sum(j.weight * j.completion_time for j in scheduled),
        max_lateness=max(latenesses) if latenesses else 0.0,
        total_tardiness=sum(j.tardiness for j in scheduled),
        n_tardy=sum(1 for j in scheduled if j.is_tardy),
    )


def schedule_single(
    processing_times: Sequence[float],
    *,
    rule: str = "SPT",
    due_dates: Sequence[float] | None = None,
    weights: Sequence[float] | None = None,
    names: Sequence[str] | None = None,
) -> ScheduleResult:
    """Programación de una máquina con reglas clásicas de despacho por prioridad.

    Parameters
    ----------
    processing_times : sequence of float
        Tiempo de proceso pj de cada trabajo (> 0).
    rule : str
        Regla de despacho:

        - ``'SPT'``  Menor tiempo de proceso primero — minimiza ΣCj.
        - ``'EDD'``  Fecha de entrega más próxima primero — minimiza el retraso máximo.
        - ``'WSPT'`` SPT ponderado (regla de Smith) — minimiza ΣwjCj.
        - ``'CR'``   Razón crítica — trabajos ordenados por dj / pj.
        - ``'FIFO'`` Orden de llegada (referencia).

    due_dates : sequence of float, optional
        Fecha de entrega dj de cada trabajo. Obligatoria para EDD y CR.
    weights : sequence of float, optional
        Peso de importancia wj (> 0). Obligatorio para WSPT. Por defecto 1.
    names : sequence of str, optional
        Etiquetas de los trabajos. Por defecto 'J1', 'J2', …

    Returns
    -------
    ScheduleResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
        Si ``rule`` no es una de SPT, EDD, WSPT, CR, FIFO, o falta ``due_dates`` para EDD/CR.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = schedule_single(processing_times=[3.0, 1.0, 2.0])
    >>> round(r.makespan, 4)
    6.0
    """
    processing_times = as_float_list(processing_times, "processing_times")
    n = len(processing_times)
    if names is None:
        names = [f"J{i + 1}" for i in range(n)]
    if weights is None:
        weights = [1.0] * n
    dd = list(due_dates) if due_dates is not None else [None] * n

    if len(dd) != n or len(weights) != n or len(names) != n:
        raise ValueError("Todas las secuencias de entrada deben tener la misma longitud.")

    rule_up = rule.upper()
    valid = {"SPT", "EDD", "WSPT", "CR", "FIFO"}
    if rule_up not in valid:
        raise ValueError(f"'rule' debe ser una de {valid}.")
    if rule_up in ("EDD", "CR") and all(d is None for d in dd):
        raise ValueError(f"rule='{rule}' requiere due_dates.")

    for i, p in enumerate(processing_times):
        as_positive(p, f"processing_times[{i}]")
    for i, w in enumerate(weights):
        as_positive(w, f"weights[{i}]")

    jobs: list[_Trabajo] = []
    for i in range(n):
        d_i = dd[i]
        jobs.append({"name": str(names[i]), "p": float(processing_times[i]),
                     "d": float(d_i) if d_i is not None else None,
                     "w": float(weights[i])})

    if rule_up == "SPT":
        jobs_sorted = sorted(jobs, key=lambda j: j["p"])
    elif rule_up == "EDD":
        jobs_sorted = sorted(jobs, key=lambda j: (j["d"] if j["d"] is not None else math.inf))
    elif rule_up == "WSPT":
        jobs_sorted = sorted(jobs, key=lambda j: j["p"] / j["w"])
    elif rule_up == "CR":
        jobs_sorted = sorted(jobs, key=lambda j: (
            (j["d"] / j["p"]) if j["d"] is not None else math.inf))
    else:
        jobs_sorted = jobs

    return _build_schedule(jobs_sorted, rule_up)


# ---------------------------------------------------------------------------
# Johnson's 2-machine flow-shop
# ---------------------------------------------------------------------------

@dataclass
class FlowShopResult:
    """Resultado del flow-shop de dos máquinas de Johnson.

    Attributes
    ----------
    sequence : list[str]
        Secuencia óptima de procesamiento de los trabajos.
    makespan : float
        Tiempo total transcurrido (finalización del último trabajo en la máquina 2).
    machine1_schedule : list[dict]
        Un diccionario por trabajo con las claves ``name``, ``start``, ``end``.
    machine2_schedule : list[dict]
        Un diccionario por trabajo con las claves ``name``, ``start``, ``end``.
    """

    sequence: list
    makespan: float
    machine1_schedule: list
    machine2_schedule: list

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        rows = []
        for a, b in zip(self.machine1_schedule, self.machine2_schedule):
            rows.append({
                "Trabajo": a["name"],
                "M1 inicio": a["start"], "M1 fin": a["end"],
                "M2 inicio": b["start"], "M2 fin": b["end"],
            })
        return pd.DataFrame(rows)

    def summary(self) -> str:
        return (
            f"Secuencia : {' → '.join(self.sequence)}\n"
            f"Makespan  : {self.makespan:.4g}"
        )

    def __str__(self) -> str:
        return self.summary()


def johnson_flowshop(
    m1_times: Sequence[float],
    m2_times: Sequence[float],
    *,
    names: Sequence[str] | None = None,
) -> FlowShopResult:
    """Algoritmo de Johnson para el flow-shop de dos máquinas.

    Todos los trabajos se procesan primero en la máquina 1 y luego en la máquina 2 en la
    **misma** secuencia. El algoritmo encuentra la secuencia que minimiza el makespan.

    Parameters
    ----------
    m1_times : sequence of float
        Tiempo de proceso en la máquina 1 de cada trabajo (aj > 0).
    m2_times : sequence of float
        Tiempo de proceso en la máquina 2 de cada trabajo (bj > 0).
    names : sequence of str, optional
        Etiquetas de los trabajos. Por defecto 'J1', 'J2', …

    Returns
    -------
    FlowShopResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si una secuencia está vacía o las secuencias tienen longitudes distintas.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = johnson_flowshop(m1_times=[3.0, 1.0, 2.0], m2_times=[2.0, 4.0, 1.0])
    >>> round(r.makespan, 4)
    8.0
    """
    n = len(m1_times)
    if len(m2_times) != n:
        raise ValueError("m1_times y m2_times deben tener la misma longitud.")
    if names is None:
        names = [f"J{i + 1}" for i in range(n)]
    for i, (a, b) in enumerate(zip(m1_times, m2_times)):
        as_positive(a, f"m1_times[{i}]")
        as_positive(b, f"m2_times[{i}]")

    jobs: list[_TrabajoJohnson] = [
        {"name": str(names[i]), "a": float(m1_times[i]), "b": float(m2_times[i])} for i in range(n)
    ]

    # Johnson's rule: jobs where min(a,b)=a → sorted ascending by a (go first)
    #                  jobs where min(a,b)=b → sorted descending by b (go last)
    set1 = sorted([j for j in jobs if j["a"] <= j["b"]], key=lambda j: j["a"])
    set2 = sorted([j for j in jobs if j["a"] >  j["b"]], key=lambda j: -j["b"])
    sequence = set1 + set2

    # Compute actual start/end times
    m1_end = 0.0
    m2_end = 0.0
    m1_sched: list = []
    m2_sched: list = []
    for job in sequence:
        m1_start = m1_end
        m1_end   = m1_start + job["a"]
        m2_start = max(m1_end, m2_end)
        m2_end   = m2_start + job["b"]
        m1_sched.append({"name": job["name"], "start": m1_start, "end": m1_end})
        m2_sched.append({"name": job["name"], "start": m2_start, "end": m2_end})

    return FlowShopResult(
        sequence=[j["name"] for j in sequence],
        makespan=m2_end,
        machine1_schedule=m1_sched,
        machine2_schedule=m2_sched,
    )


# ---------------------------------------------------------------------------
# NEH heuristic — m-machine permutation flow-shop
# ---------------------------------------------------------------------------

def _flowshop_cmax(seq: list, T: list) -> tuple:
    """Devuelve (makespan, matriz de tiempos de finalización) de un flow-shop de permutación.

    T[trabajo][máquina] = tiempo de proceso; seq = lista de índices de trabajos.
    """
    n = len(seq)
    if n == 0:
        return 0.0, []
    m = len(T[seq[0]])
    C: list = [[0.0] * m for _ in range(n)]
    for i, job in enumerate(seq):
        for j in range(m):
            C[i][j] = T[job][j] + max(
                C[i - 1][j] if i > 0 else 0.0,
                C[i][j - 1] if j > 0 else 0.0,
            )
    return C[-1][-1], C


def _mejor_insercion(seq: list, job: int, T: list, m: int) -> int:
    """Posición de inserción de ``job`` en ``seq`` que minimiza el makespan (aceleración de Taillard).

    Calcula una sola vez las finalizaciones hacia adelante ``e`` y las colas hacia atrás ``q`` de la
    secuencia parcial; cada posición candidata se evalúa en O(m). En total NEH queda en O(n²·m)
    (recalcular el makespan completo por posición costaba O(n³·m)). Empata a favor de la posición menor.
    """
    L = len(seq)
    e = [[0.0] * m for _ in range(L + 1)]
    for i in range(1, L + 1):
        p_i = T[seq[i - 1]]
        for j in range(m):
            e[i][j] = max(e[i][j - 1] if j > 0 else 0.0, e[i - 1][j]) + p_i[j]
    q = [[0.0] * m for _ in range(L + 2)]
    for i in range(L - 1, -1, -1):
        p_i = T[seq[i]]
        for j in range(m - 1, -1, -1):
            q[i][j] = max(q[i][j + 1] if j < m - 1 else 0.0, q[i + 1][j]) + p_i[j]
    p_k = T[job]
    mejor_cmax, mejor_pos = math.inf, 0
    for pos in range(L + 1):
        f_prev = 0.0
        cmax = 0.0
        for j in range(m):
            f_prev = max(f_prev, e[pos][j]) + p_k[j]
            cmax = max(cmax, f_prev + q[pos][j])
        # Un empate se resuelve a favor de la posición menor; la tolerancia evita que el ruido de
        # redondeo en datos decimales convierta un empate exacto en una "mejora" espuria.
        if cmax < mejor_cmax - 1e-12 * max(1.0, abs(mejor_cmax)) or mejor_cmax == math.inf:
            mejor_cmax, mejor_pos = cmax, pos
    return mejor_pos


@dataclass
class NEHResult:
    """Resultado de la heurística NEH para el flow-shop de permutación con m máquinas.

    Attributes
    ----------
    sequence : list[str]
        Orden de procesamiento de los trabajos encontrado por NEH.
    makespan : float
        Mejor makespan (Cmax) alcanzado.
    n_machines : int
        Número de máquinas.
    machine_schedules : list[list[dict]]
        ``machine_schedules[m_idx][j]``: diccionario ``{name, start, end}`` del
        *j*-ésimo trabajo (en orden de secuencia) en la máquina *m_idx*.
    """

    sequence: list
    makespan: float
    n_machines: int
    machine_schedules: list

    def to_frame(self) -> pd.DataFrame:
        """Devuelve un DataFrame de Gantt con inicio y fin por máquina para cada trabajo."""
        import pandas as pd
        rows = []
        for idx, job in enumerate(self.sequence):
            row: dict = {"Trabajo": job}
            for mi, m_sched in enumerate(self.machine_schedules):
                row[f"M{mi + 1}_inicio"] = m_sched[idx]["start"]
                row[f"M{mi + 1}_fin"]   = m_sched[idx]["end"]
            rows.append(row)
        return pd.DataFrame(rows)

    def summary(self) -> str:
        return (
            f"Algoritmo : heurística NEH\n"
            f"Máquinas  : {self.n_machines}\n"
            f"Secuencia : {' → '.join(str(s) for s in self.sequence)}\n"
            f"Makespan  : {self.makespan:.4g}"
        )

    def __str__(self) -> str:
        return self.summary()


def neh_flowshop(
    times_matrix: Sequence[Sequence[float]],
    *,
    names: Sequence[str] | None = None,
) -> NEHResult:
    """Heurística NEH para el flow-shop de permutación con *m* máquinas.

    Nawaz, Enscore y Ham (1983) construyen una permutación de alta calidad insertando cada trabajo
    en su mejor posición. Con la aceleración de Taillard corre en O(n²·m); es la heurística estándar
    del flow-shop de permutación. Con *m = 2* obtiene soluciones óptimas o casi óptimas, comparables
    al algoritmo de Johnson.

    Parameters
    ----------
    times_matrix : sequence of sequences of float
        ``times_matrix[i][j]``: tiempo de proceso del trabajo *i* en la máquina *j*.
        Todos los valores deben ser > 0; todas las filas deben tener el mismo número de columnas.
    names : sequence of str, optional
        Etiquetas de los trabajos. Por defecto ``'J1', 'J2', …``.

    Returns
    -------
    NEHResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si la matriz está vacía, es irregular o ``names`` tiene otra longitud.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = neh_flowshop(times_matrix=[[3.0, 2.0, 4.0], [1.0, 4.0, 2.0], [2.0, 1.0, 3.0]])
    >>> round(r.makespan, 4)
    13.0
    """
    n = len(times_matrix)
    if n == 0:
        raise ValueError("'times_matrix' debe contener al menos un trabajo.")
    m_cnt = len(times_matrix[0])
    if m_cnt == 0:
        raise ValueError("Cada trabajo debe tener tiempos de proceso para al menos una máquina.")
    for i, row in enumerate(times_matrix):
        if len(row) != m_cnt:
            raise ValueError(
                f"Todas las filas deben tener la misma longitud; la fila {i} tiene {len(row)} ≠ {m_cnt}."
            )
        for j, p in enumerate(row):
            as_positive(float(p), f"times_matrix[{i}][{j}]")

    if names is None:
        names_list = [f"J{i + 1}" for i in range(n)]
    else:
        names_list = [str(s) for s in names]
    if len(names_list) != n:
        raise ValueError("'names' debe tener la misma longitud que 'times_matrix'.")

    T_mat = [[float(times_matrix[i][j]) for j in range(m_cnt)] for i in range(n)]

    # Step 1: sort job indices descending by total processing time
    order = sorted(range(n), key=lambda i: -sum(T_mat[i]))

    # Step 2: iterative best-insertion
    seq = [order[0]]
    for k in range(1, n):
        job = order[k]
        pos = _mejor_insercion(seq, job, T_mat, m_cnt)
        seq = seq[:pos] + [job] + seq[pos:]

    makespan, C_mat = _flowshop_cmax(seq, T_mat)

    machine_schedules = []
    for j in range(m_cnt):
        m_sched = []
        for i, job in enumerate(seq):
            end   = C_mat[i][j]
            start = end - T_mat[job][j]
            m_sched.append({"name": names_list[job], "start": start, "end": end})
        machine_schedules.append(m_sched)

    return NEHResult(
        sequence=[names_list[j] for j in seq],
        makespan=makespan,
        n_machines=m_cnt,
        machine_schedules=machine_schedules,
    )
