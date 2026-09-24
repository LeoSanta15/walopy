"""Solvers: find optimal parameters or user-defined targets for queuing / operations models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd

from ._utils import as_positive, as_nonneg


# ---------------------------------------------------------------------------
# Internal bisection — avoids scipy dependency; all target functions are monotone
# ---------------------------------------------------------------------------

def _bisect(f: Callable[[float], float], a: float, b: float,
            tol: float = 1e-10, max_iter: int = 300) -> float:
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        raise ValueError(
            f"Root not bracketed: f({a:.6g})={fa:.4g}, f({b:.6g})={fb:.4g}. "
            "Target may be outside the feasible range."
        )
    for _ in range(max_iter):
        mid = 0.5 * (a + b)
        fm  = f(mid)
        if abs(b - a) < tol or abs(fm) < tol:
            return mid
        if fa * fm < 0:
            b, fb = mid, fm
        else:
            a, fa = mid, fm
    return 0.5 * (a + b)


def _get_metric(result: Any, metric: str) -> float:
    """Extract a named metric from any result dataclass."""
    if not hasattr(result, metric):
        valid = [k for k in vars(result) if not k.startswith("_")]
        raise ValueError(f"Unknown metric '{metric}'. Valid options: {valid}")
    return float(getattr(result, metric))


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SolverResult:
    """Result of a parameter-target solve.

    Attributes
    ----------
    param : str
        Name of the parameter that was solved.
    value : float
        Found parameter value.
    target_metric : str
        Metric that was constrained.
    target_value : float
        Desired value of the metric.
    achieved_value : float
        Actual metric value at the solution.
    model_result : Any
        Full model result at the solution point.
    converged : bool
    params : dict
    """

    param: str
    value: float
    target_metric: str
    target_value: float
    achieved_value: float
    model_result: Any
    converged: bool = True
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        status = "converged" if self.converged else "NOT converged"
        return (
            f"Solver [{status}]\n"
            f"  Solved param  : {self.param} = {self.value:.6g}\n"
            f"  Target metric : {self.target_metric} ≤ {self.target_value:.6g}\n"
            f"  Achieved      : {self.target_metric} = {self.achieved_value:.6g}"
        )

    def __str__(self) -> str:
        return self.summary()


@dataclass
class OptimizeResult:
    """Result of a cost-minimization over number of servers.

    Attributes
    ----------
    optimal_servers : int
        Number of servers that minimizes total cost.
    min_cost : float
        Minimum total cost per unit time.
    cost_breakdown : pd.DataFrame
        Cost components for every c evaluated.
    model_result : Any
        Full queuing result at the optimal c.
    params : dict
    """

    optimal_servers: int
    min_cost: float
    cost_breakdown: "pd.DataFrame"
    model_result: Any
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"Optimal servers : {self.optimal_servers}\n"
            f"Minimum cost    : {self.min_cost:.6g} per unit time\n"
        )

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> "go.Figure":
        from .plotting import plot_optimize_servers
        return plot_optimize_servers(self, **kwargs)


# ---------------------------------------------------------------------------
# solve_lam — find max arrival rate to meet a target
# ---------------------------------------------------------------------------

def solve_lam(
    target_metric: str,
    target_value: float,
    *,
    mu: float,
    model: str = "mm1",
    c: int = 1,
    ca2: float = 1.0,
    cs2: float = 1.0,
) -> SolverResult:
    """Find the maximum arrival rate λ such that *target_metric* ≤ *target_value*.

    Parameters
    ----------
    target_metric : str
        One of ``'Wq'``, ``'W'``, ``'Lq'``, ``'L'``, ``'rho'``.
    target_value : float
        Desired upper bound for the metric.
    mu : float
        Service rate (fixed).
    model : {'mm1', 'mmc', 'md1', 'gg1'}
        Queuing model to use.
    c : int
        Number of servers (only for ``'mmc'``).
    ca2, cs2 : float
        Squared CVs (only for ``'gg1'`` / Kingman).

    Returns
    -------
    SolverResult
    """
    from .queuing import mm1, mmc, md1, kingman

    mu = as_positive(mu, "mu")
    target_value = as_positive(target_value, "target_value")

    _models = {
        "mm1":  lambda lam: mm1(lam, mu),
        "mmc":  lambda lam: mmc(lam, mu, c),
        "md1":  lambda lam: md1(lam, mu),
        "gg1":  lambda lam: kingman(lam, mu, ca2, cs2),
    }
    if model not in _models:
        raise ValueError(f"Unknown model '{model}'. Choose from {list(_models)}.")

    fn = _models[model]

    def residual(lam: float) -> float:
        try:
            return _get_metric(fn(lam), target_metric) - target_value
        except (ValueError, ZeroDivisionError):
            return 1e9

    lam_max = mu * (c if model == "mmc" else 1) * 0.9999
    lam_min = lam_max * 1e-6

    # Check feasibility: even at lam_min the metric might exceed target
    if residual(lam_min) > 0:
        raise ValueError(
            f"{target_metric} exceeds {target_value} even at very low λ. "
            "Target may be infeasible for this model / μ."
        )

    lam_sol = _bisect(residual, lam_min, lam_max)
    result   = fn(lam_sol)
    return SolverResult(
        param="lam",
        value=lam_sol,
        target_metric=target_metric,
        target_value=target_value,
        achieved_value=_get_metric(result, target_metric),
        model_result=result,
        params={"model": model, "mu": mu},
    )


# ---------------------------------------------------------------------------
# solve_mu — find required service rate to meet a target
# ---------------------------------------------------------------------------

def solve_mu(
    target_metric: str,
    target_value: float,
    *,
    lam: float,
    model: str = "mm1",
    c: int = 1,
    ca2: float = 1.0,
    cs2: float = 1.0,
) -> SolverResult:
    """Find the minimum service rate μ such that *target_metric* ≤ *target_value*.

    Parameters
    ----------
    target_metric : str
        One of ``'Wq'``, ``'W'``, ``'Lq'``, ``'L'``, ``'rho'``.
    target_value : float
        Desired upper bound for the metric.
    lam : float
        Arrival rate (fixed).
    model : {'mm1', 'mmc', 'md1', 'gg1'}
    c : int
        Servers (only for ``'mmc'``).
    ca2, cs2 : float
        Squared CVs (only for ``'gg1'``).

    Returns
    -------
    SolverResult
    """
    from .queuing import mm1, mmc, md1, kingman

    lam = as_positive(lam, "lam")
    target_value = as_positive(target_value, "target_value")

    _models = {
        "mm1": lambda mu: mm1(lam, mu),
        "mmc": lambda mu: mmc(lam, mu, c),
        "md1": lambda mu: md1(lam, mu),
        "gg1": lambda mu: kingman(lam, mu, ca2, cs2),
    }
    if model not in _models:
        raise ValueError(f"Unknown model '{model}'. Choose from {list(_models)}.")

    fn = _models[model]

    def residual(mu: float) -> float:
        try:
            return _get_metric(fn(mu), target_metric) - target_value
        except (ValueError, ZeroDivisionError):
            return 1e9

    mu_min = lam / (c if model == "mmc" else 1) * (1 + 1e-6)
    mu_max = mu_min * 1e6

    # Ensure the bracket is valid
    if residual(mu_max) > 0:
        raise ValueError(
            f"{target_metric} still exceeds {target_value} at μ = {mu_max:.4g}. "
            "Target may be numerically infeasible."
        )

    mu_sol  = _bisect(residual, mu_min, mu_max)
    result  = fn(mu_sol)
    return SolverResult(
        param="mu",
        value=mu_sol,
        target_metric=target_metric,
        target_value=target_value,
        achieved_value=_get_metric(result, target_metric),
        model_result=result,
        params={"model": model, "lam": lam},
    )


# ---------------------------------------------------------------------------
# solve_servers — minimum c to meet a target
# ---------------------------------------------------------------------------

def solve_servers(
    target_metric: str,
    target_value: float,
    *,
    lam: float,
    mu: float,
    c_max: int = 100,
) -> SolverResult:
    """Find the minimum number of servers *c* such that *target_metric* ≤ *target_value*.

    Parameters
    ----------
    target_metric : str
        One of ``'Wq'``, ``'W'``, ``'Lq'``, ``'L'``, ``'rho'``.
    target_value : float
        Desired upper bound.
    lam : float
        Arrival rate.
    mu : float
        Service rate per server.
    c_max : int
        Maximum number of servers to try (default 100).

    Returns
    -------
    SolverResult
    """
    from .queuing import mmc

    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    target_value = as_positive(target_value, "target_value")

    c_min_stable = int(np.ceil(lam / mu)) + 1  # min c for stability

    for c in range(c_min_stable, c_max + 1):
        result = mmc(lam, mu, c)
        achieved = _get_metric(result, target_metric)
        if achieved <= target_value:
            return SolverResult(
                param="c (servers)",
                value=float(c),
                target_metric=target_metric,
                target_value=target_value,
                achieved_value=achieved,
                model_result=result,
                params={"lam": lam, "mu": mu},
            )

    raise ValueError(
        f"Could not meet {target_metric} ≤ {target_value} with up to {c_max} servers. "
        "Consider increasing μ or relaxing the target."
    )


# ---------------------------------------------------------------------------
# optimize_servers — minimize total cost
# ---------------------------------------------------------------------------

def optimize_servers(
    lam: float,
    mu: float,
    *,
    cost_per_server: float,
    cost_per_wait: float,
    c_max: int = 50,
) -> OptimizeResult:
    """Find the number of servers *c* that minimizes total cost per unit time.

    Total cost = c × cost_per_server + Lq × cost_per_wait

    Parameters
    ----------
    lam : float
        Arrival rate.
    mu : float
        Service rate per server.
    cost_per_server : float
        Cost per server per unit time.
    cost_per_wait : float
        Cost per unit waiting in queue per unit time.
    c_max : int
        Maximum servers to evaluate (default 50).

    Returns
    -------
    OptimizeResult
    """
    from .queuing import mmc

    lam             = as_positive(lam, "lam")
    mu              = as_positive(mu, "mu")
    cost_per_server = as_positive(cost_per_server, "cost_per_server")
    cost_per_wait   = as_positive(cost_per_wait, "cost_per_wait")

    c_min = int(np.ceil(lam / mu)) + 1
    rows  = []

    for c in range(c_min, c_max + 1):
        r          = mmc(lam, mu, c)
        server_c   = c * cost_per_server
        wait_c     = r.Lq * cost_per_wait
        total_c    = server_c + wait_c
        rows.append({
            "c": c,
            "rho": r.rho,
            "Lq": r.Lq,
            "Wq": r.Wq,
            "server_cost": server_c,
            "wait_cost": wait_c,
            "total_cost": total_c,
            "_result": r,
        })
        # Early stop: cost increasing monotonically (total_cost is convex in c)
        if len(rows) >= 3 and rows[-1]["total_cost"] > rows[-2]["total_cost"] > rows[-3]["total_cost"]:
            break

    best     = min(rows, key=lambda x: x["total_cost"])
    df_rows  = [{k: v for k, v in row.items() if k != "_result"} for row in rows]

    return OptimizeResult(
        optimal_servers=int(best["c"]),
        min_cost=best["total_cost"],
        cost_breakdown=pd.DataFrame(df_rows),
        model_result=best["_result"],
        params={
            "cost_per_server": cost_per_server,
            "cost_per_wait": cost_per_wait,
        },
    )


# ---------------------------------------------------------------------------
# sensitivity — vary one parameter and collect all KPIs
# ---------------------------------------------------------------------------

def sensitivity(
    model_fn: Callable[..., Any],
    param: str,
    values: Sequence[float],
    **fixed_kwargs: Any,
) -> pd.DataFrame:
    """Vary one model parameter and return a DataFrame of all KPIs.

    Parameters
    ----------
    model_fn : callable
        Any walopy model function (e.g. ``mm1``, ``mmc``, ``kingman``).
    param : str
        Name of the parameter to vary (must match the function's argument).
    values : sequence of float
        Values to evaluate.
    **fixed_kwargs
        All other parameters of ``model_fn`` (fixed).

    Returns
    -------
    pd.DataFrame
        One row per value with the swept parameter and all result fields.

    Examples
    --------
    >>> from walopy import mm1
    >>> from walopy.solver import sensitivity
    >>> import numpy as np
    >>> df = sensitivity(mm1, "lam", np.linspace(0.5, 4.5, 20), mu=5.0)
    """
    rows = []
    for v in values:
        try:
            result = model_fn(**{param: v, **fixed_kwargs})
            row    = {param: v}
            row.update({
                k: val for k, val in vars(result).items()
                if isinstance(val, (int, float, np.floating))
                and not k.startswith("_")
            })
            rows.append(row)
        except (ValueError, ZeroDivisionError):
            rows.append({param: v})

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# batch_model — apply a model to every row of a DataFrame
# ---------------------------------------------------------------------------

def batch_model(
    model_fn: Callable[..., Any],
    df: "pd.DataFrame",
    **fixed_kwargs: Any,
) -> pd.DataFrame:
    """Apply a walopy model to every row of a DataFrame.

    Each row's column values are passed as keyword arguments to *model_fn*.
    Values in *fixed_kwargs* serve as defaults; row values always override them.
    NaN cells in the input row are dropped before the call, so a sparse
    DataFrame can represent multiple model configurations in one table.

    Parameters
    ----------
    model_fn : callable
        Any walopy model function (e.g. ``mm1``, ``mmc``, ``kingman``,
        ``oee``, ``break_even``).
    df : pd.DataFrame
        One row per scenario.  Column names must match parameter names of
        *model_fn*.
    **fixed_kwargs
        Additional parameters shared across all rows (e.g. ``mu=5.0``).
        A column in *df* with the same name takes precedence.

    Returns
    -------
    pd.DataFrame
        One row per input row with all original columns plus the model's
        scalar output fields appended.  The input DataFrame's index is
        preserved.  If any row raises an exception an ``_error`` column is
        added; it contains the error message for failed rows and ``None``
        for successful ones.

    Examples
    --------
    >>> import pandas as pd
    >>> from walopy import mm1
    >>> from walopy.solver import batch_model
    >>> scenarios = pd.DataFrame({"lam": [1.0, 2.0, 3.0, 4.0], "mu": [5.0, 5.0, 5.0, 5.0]})
    >>> batch_model(mm1, scenarios)
    """
    rows: list[dict] = []
    has_errors = False

    # Pre-compute integer columns so iterrows() float-upcast can be reversed
    int_cols = {col for col in df.columns if pd.api.types.is_integer_dtype(df[col].dtype)}

    for _, row_series in df.iterrows():
        # Merge: fixed_kwargs as base, row values (non-NaN) take precedence
        kwargs: dict[str, Any] = dict(fixed_kwargs)
        for k, v in row_series.items():
            if isinstance(v, float) and np.isnan(v):
                continue
            # iterrows() upcasts int64 columns to float64; reverse that cast
            kwargs[k] = int(v) if k in int_cols else v

        try:
            result = model_fn(**kwargs)
            row: dict[str, Any] = row_series.to_dict()
            # Restore integer columns that iterrows() upcast to float
            for k in int_cols:
                if k in row and not (isinstance(row[k], float) and np.isnan(row[k])):
                    row[k] = int(row[k])
            if hasattr(result, "__dict__"):
                row.update({
                    k: val for k, val in vars(result).items()
                    if isinstance(val, (int, float, np.floating))
                    and not k.startswith("_")
                })
            elif isinstance(result, (int, float, np.floating)):
                row["value"] = float(result)
        except Exception as exc:
            row = row_series.to_dict()
            row["_error"] = str(exc)
            has_errors = True

        rows.append(row)

    result_df = pd.DataFrame(rows, index=df.index)
    if not has_errors and "_error" in result_df.columns:
        result_df = result_df.drop(columns=["_error"])
    return result_df


# ---------------------------------------------------------------------------
# compare — side-by-side comparison of multiple results
# ---------------------------------------------------------------------------

def compare(
    *results: Any,
    labels: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Compare multiple walopy model results side by side.

    Parameters
    ----------
    *results
        Any walopy result objects (``QueueResult``, ``SimulationResult``,
        ``EOQResult``, etc.) or plain dicts.
    labels : sequence of str, optional
        Row labels.  Defaults to ``'scenario_1'``, ``'scenario_2'``, …

    Returns
    -------
    pd.DataFrame
        One row per result with a ``label`` column prepended.

    Examples
    --------
    >>> from walopy import mm1, mmc, compare
    >>> compare(mm1(2, 5), mmc(2, 5, 2), labels=["M/M/1", "M/M/2"])
    """
    rows = []
    for i, r in enumerate(results):
        label = labels[i] if (labels and i < len(labels)) else f"scenario_{i + 1}"
        if hasattr(r, "to_frame"):
            row = r.to_frame().iloc[0].to_dict()
        elif isinstance(r, dict):
            row = dict(r)
        elif hasattr(r, "__dict__"):
            row = {
                k: v for k, v in vars(r).items()
                if isinstance(v, (int, float, str, np.floating))
                and not k.startswith("_")
            }
        else:
            row = {"value": r}
        row["label"] = label
        # Move label to front
        rows.append({"label": label, **{k: v for k, v in row.items() if k != "label"}})

    return pd.DataFrame(rows)
