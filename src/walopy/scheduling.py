"""Production scheduling: single-machine dispatching rules and Johnson's flow-shop."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from ._utils import as_positive, as_nonneg


@dataclass
class JobSchedule:
    """Per-job result after scheduling."""

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
    """Single-machine scheduling result.

    Attributes
    ----------
    rule : str
        Dispatching rule used.
    sequence : list[str]
        Job names in processing order.
    jobs : list[JobSchedule]
        Per-job schedule details.
    makespan : float
        Total elapsed time (sum of all processing times).
    total_completion_time : float
        Sum of job completion times ΣCj.
    total_weighted_completion_time : float
        Sum of weighted completion times ΣwjCj.
    max_lateness : float
        Maximum lateness max(Lj).
    total_tardiness : float
        Sum of tardiness ΣTj.
    n_tardy : int
        Number of tardy jobs.
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

    def to_frame(self) -> "pd.DataFrame":
        import pandas as pd
        return pd.DataFrame([{
            "Name": j.name,
            "p": j.processing_time,
            "d": j.due_date,
            "w": j.weight,
            "Start": j.start_time,
            "C": j.completion_time,
            "L": j.lateness,
            "T": j.tardiness,
            "Tardy": j.is_tardy,
        } for j in self.jobs])

    def summary(self) -> str:
        lines = [
            f"Rule                    : {self.rule}",
            f"Sequence                : {' → '.join(self.sequence)}",
            f"Makespan (Cmax)         : {self.makespan:.4g}",
            f"Total completion ΣCj    : {self.total_completion_time:.4g}",
            f"Weighted completion ΣwCj: {self.total_weighted_completion_time:.4g}",
            f"Max lateness            : {self.max_lateness:.4g}",
            f"Total tardiness ΣTj     : {self.total_tardiness:.4g}",
            f"Tardy jobs              : {self.n_tardy}",
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
    """Single-machine scheduling with classic priority dispatching rules.

    Parameters
    ----------
    processing_times : sequence of float
        Processing time pj for each job (> 0).
    rule : str
        Dispatching rule:

        - ``'SPT'``  Shortest Processing Time — minimises ΣCj.
        - ``'EDD'``  Earliest Due Date — minimises max lateness.
        - ``'WSPT'`` Weighted SPT (Smith's rule) — minimises ΣwjCj.
        - ``'CR'``   Critical Ratio — jobs ordered by dj / pj.
        - ``'FIFO'`` Input order (baseline).

    due_dates : sequence of float, optional
        Due date dj for each job. Required for EDD and CR.
    weights : sequence of float, optional
        Importance weight wj (> 0). Required for WSPT. Default 1.
    names : sequence of str, optional
        Job labels. Default 'J1', 'J2', …

    Returns
    -------
    ScheduleResult
    """
    n = len(processing_times)
    if names is None:
        names = [f"J{i + 1}" for i in range(n)]
    if weights is None:
        weights = [1.0] * n
    dd = list(due_dates) if due_dates is not None else [None] * n

    if len(dd) != n or len(weights) != n or len(names) != n:
        raise ValueError("All input sequences must have the same length.")

    rule_up = rule.upper()
    valid = {"SPT", "EDD", "WSPT", "CR", "FIFO"}
    if rule_up not in valid:
        raise ValueError(f"rule must be one of {valid}.")
    if rule_up in ("EDD", "CR") and all(d is None for d in dd):
        raise ValueError(f"rule='{rule}' requires due_dates.")

    for i, p in enumerate(processing_times):
        as_positive(p, f"processing_times[{i}]")
    for i, w in enumerate(weights):
        as_positive(w, f"weights[{i}]")

    jobs = [{"name": str(names[i]), "p": float(processing_times[i]),
             "d": float(dd[i]) if dd[i] is not None else None,
             "w": float(weights[i])} for i in range(n)]

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
    """Johnson's 2-machine flow-shop result.

    Attributes
    ----------
    sequence : list[str]
        Optimal job processing sequence.
    makespan : float
        Total elapsed time (completion of last job on machine 2).
    machine1_schedule : list[dict]
        Per-job dicts with keys ``name``, ``start``, ``end``.
    machine2_schedule : list[dict]
        Per-job dicts with keys ``name``, ``start``, ``end``.
    """

    sequence: list
    makespan: float
    machine1_schedule: list
    machine2_schedule: list

    def to_frame(self) -> "pd.DataFrame":
        import pandas as pd
        rows = []
        for a, b in zip(self.machine1_schedule, self.machine2_schedule):
            rows.append({
                "Job": a["name"],
                "M1 start": a["start"], "M1 end": a["end"],
                "M2 start": b["start"], "M2 end": b["end"],
            })
        return pd.DataFrame(rows)

    def summary(self) -> str:
        return (
            f"Sequence : {' → '.join(self.sequence)}\n"
            f"Makespan : {self.makespan:.4g}"
        )

    def __str__(self) -> str:
        return self.summary()


def johnson_flowshop(
    m1_times: Sequence[float],
    m2_times: Sequence[float],
    *,
    names: Sequence[str] | None = None,
) -> FlowShopResult:
    """Johnson's algorithm for the 2-machine flow-shop problem.

    All jobs are processed first on machine 1 and then on machine 2 in
    the **same** sequence.  The algorithm finds the sequence that minimises
    makespan.

    Parameters
    ----------
    m1_times : sequence of float
        Processing time on machine 1 for each job (aj > 0).
    m2_times : sequence of float
        Processing time on machine 2 for each job (bj > 0).
    names : sequence of str, optional
        Job labels. Default 'J1', 'J2', …

    Returns
    -------
    FlowShopResult
    """
    n = len(m1_times)
    if len(m2_times) != n:
        raise ValueError("m1_times and m2_times must have the same length.")
    if names is None:
        names = [f"J{i + 1}" for i in range(n)]
    for i, (a, b) in enumerate(zip(m1_times, m2_times)):
        as_positive(a, f"m1_times[{i}]")
        as_positive(b, f"m2_times[{i}]")

    jobs = [{"name": str(names[i]), "a": float(m1_times[i]), "b": float(m2_times[i])}
            for i in range(n)]

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
