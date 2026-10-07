"""Solvers: encuentran parámetros óptimos o metas definidas por la persona usuaria en modelos de colas y operaciones."""
from __future__ import annotations

import inspect
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
import pandas as pd

from ._i18n import t as _t
from ._utils import MAX_SERVIDORES, as_int_positive, as_positive

if TYPE_CHECKING:
    import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Internal bisection — avoids scipy dependency; all target functions are monotone
# ---------------------------------------------------------------------------

def _bisect(f: Callable[[float], float], a: float, b: float,
            tol: float = 1e-10, max_iter: int = 300) -> float:
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        raise ValueError(
            _t("solver.error.bisect.raiz_esta_acotada_objetivo_puede", a=a, fa=fa, b=b, fb=fb)
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
    """Extrae una métrica por nombre de cualquier dataclass de resultado."""
    if not hasattr(result, metric):
        valid = [k for k in vars(result) if not k.startswith("_")]
        raise ValueError(_t("solver.error.get_metric.metrica_desconocida_opciones_validas", metric=metric, valid=valid))
    return float(getattr(result, metric))


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SolverResult:
    """Resultado de resolver un parámetro para alcanzar una meta.

    Attributes
    ----------
    param : str
        Nombre del parámetro resuelto.
    value : float
        Valor del parámetro encontrado.
    target_metric : str
        Métrica que se restringió.
    target_value : float
        Valor deseado de la métrica.
    achieved_value : float
        Valor real de la métrica en la solución.
    model_result : Any
        Resultado completo del modelo en el punto solución.
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
        status = _t("solver.etiqueta.summary.convergio_2") if self.converged else _t("solver.etiqueta.summary.convergio")
        return (
            _t("solver.etiqueta.summary.solver_parametro_resuelto_metrica_objetivo", status=status, param=self.param, value=self.value, target_metric=self.target_metric, target_value=self.target_value, target_metric2=self.target_metric, achieved_value=self.achieved_value)
        )

    def __str__(self) -> str:
        return self.summary()


@dataclass
class OptimizeResult:
    """Resultado de minimizar el costo según el número de servidores.

    Attributes
    ----------
    optimal_servers : int
        Número de servidores que minimiza el costo total.
    min_cost : float
        Costo total mínimo por unidad de tiempo.
    cost_breakdown : pd.DataFrame
        Componentes del costo para cada c evaluado.
    model_result : Any
        Resultado completo de colas en el c óptimo.
    params : dict
    """

    optimal_servers: int
    min_cost: float
    cost_breakdown: pd.DataFrame
    model_result: Any
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            _t("solver.etiqueta.summary.servidores_optimos_costo_minimo_unidad", optimal_servers=self.optimal_servers, min_cost=self.min_cost)
        )

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> go.Figure:
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
    """Encuentra la máxima tasa de llegadas λ tal que *target_metric* ≤ *target_value*.

    Parameters
    ----------
    target_metric : str
        Una de ``'Wq'``, ``'W'``, ``'Lq'``, ``'L'``, ``'rho'``.
    target_value : float
        Cota superior deseada de la métrica.
    mu : float
        Tasa de servicio (fija).
    model : {'mm1', 'mmc', 'md1', 'gg1'}
        Modelo de colas a usar.
    c : int
        Número de servidores (solo para ``'mmc'``).
    ca2, cs2 : float
        CV² (solo para ``'gg1'`` / Kingman).

    Returns
    -------
    SolverResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si la métrica o el modelo son desconocidos, o si el objetivo es infactible para el modelo.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = solve_lam(target_metric='Wq', target_value=0.5, mu=5.0)
    >>> round(r.value, 4)
    3.5714
    """
    from .queuing import kingman, md1, mm1, mmc

    mu = as_positive(mu, "mu")
    target_value = as_positive(target_value, "target_value")

    _models = {
        "mm1":  lambda lam: mm1(lam, mu),
        "mmc":  lambda lam: mmc(lam, mu, c),
        "md1":  lambda lam: md1(lam, mu),
        "gg1":  lambda lam: kingman(lam, mu, ca2, cs2),
    }
    if model not in _models:
        raise ValueError(_t("solver.error.solve_lam.modelo_desconocido_elija_entre", model=model, expr=list(_models)))

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
            _t("solver.error.solve_lam.supera_incluso_muy_baja_objetivo", target_metric=target_metric, target_value=target_value)
        )

    lam_sol = _bisect(residual, lam_min, lam_max)
    result   = fn(lam_sol)
    return SolverResult(
        param=_t("columnas.columna_df.global.lam"),
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
    """Encuentra la mínima tasa de servicio μ tal que *target_metric* ≤ *target_value*.

    Parameters
    ----------
    target_metric : str
        Una de ``'Wq'``, ``'W'``, ``'Lq'``, ``'L'``, ``'rho'``.
    target_value : float
        Cota superior deseada de la métrica.
    lam : float
        Tasa de llegadas (fija).
    model : {'mm1', 'mmc', 'md1', 'gg1'}
    c : int
        Servidores (solo para ``'mmc'``).
    ca2, cs2 : float
        CV² (solo para ``'gg1'``).

    Returns
    -------
    SolverResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si la métrica o el modelo son desconocidos, o si el objetivo es infactible para el modelo.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = solve_mu(target_metric='Wq', target_value=0.5, lam=2.0)
    >>> round(r.value, 4)
    3.2361
    """
    from .queuing import kingman, md1, mm1, mmc

    lam = as_positive(lam, "lam")
    target_value = as_positive(target_value, "target_value")

    _models = {
        "mm1": lambda mu: mm1(lam, mu),
        "mmc": lambda mu: mmc(lam, mu, c),
        "md1": lambda mu: md1(lam, mu),
        "gg1": lambda mu: kingman(lam, mu, ca2, cs2),
    }
    if model not in _models:
        raise ValueError(_t("solver.error.solve_lam.modelo_desconocido_elija_entre", model=model, expr=list(_models)))

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
            _t("solver.error.solve_mu.sigue_superando_objetivo_puede_ser", target_metric=target_metric, target_value=target_value, mu_max=mu_max)
        )

    mu_sol  = _bisect(residual, mu_min, mu_max)
    result  = fn(mu_sol)
    return SolverResult(
        param=_t("columnas.columna_df.global.mu"),
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

def _min_servidores_estables(lam: float, mu: float) -> int:
    """Menor número de servidores *c* con ρ = λ/(c·μ) < 1 (la misma condición que exige ``mmc``)."""
    c = max(1, int(lam / mu))
    while lam / (c * mu) >= 1.0:
        c += 1
    return c


def solve_servers(
    target_metric: str,
    target_value: float,
    *,
    lam: float,
    mu: float,
    c_max: int = 100,
) -> SolverResult:
    """Encuentra el mínimo número de servidores *c* tal que *target_metric* ≤ *target_value*.

    Parameters
    ----------
    target_metric : str
        Una de ``'Wq'``, ``'W'``, ``'Lq'``, ``'L'``, ``'rho'``.
    target_value : float
        Cota superior deseada.
    lam : float
        Tasa de llegadas.
    mu : float
        Tasa de servicio por servidor.
    c_max : int
        Máximo de servidores a probar (por defecto 100).

    Returns
    -------
    SolverResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si el objetivo no se alcanza con ``c_max`` servidores.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = solve_servers(target_metric='Wq', target_value=0.5, lam=4.0, mu=3.0)
    >>> round(r.value, 4)
    2.0
    """
    from .queuing import mmc

    lam = as_positive(lam, "lam")
    mu  = as_positive(mu, "mu")
    target_value = as_positive(target_value, "target_value")
    c_max = as_int_positive(c_max, "c_max", max=MAX_SERVIDORES)

    c_min_stable = _min_servidores_estables(lam, mu)

    for c in range(c_min_stable, c_max + 1):
        result = mmc(lam, mu, c)
        achieved = _get_metric(result, target_metric)
        if achieved <= target_value:
            return SolverResult(
                param=_t("columnas.columna_df.global.servidores"),
                value=float(c),
                target_metric=target_metric,
                target_value=target_value,
                achieved_value=achieved,
                model_result=result,
                params={"lam": lam, "mu": mu},
            )

    raise ValueError(
        _t("solver.error.solve_servers.pudo_cumplir_hasta_servidores_considere", target_metric=target_metric, target_value=target_value, c_max=c_max)
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
    """Encuentra el número de servidores *c* que minimiza el costo total por unidad de tiempo.

    Costo total = c × cost_per_server + Lq × cost_per_wait

    Parameters
    ----------
    lam : float
        Tasa de llegadas.
    mu : float
        Tasa de servicio por servidor.
    cost_per_server : float
        Costo por servidor por unidad de tiempo.
    cost_per_wait : float
        Costo por unidad esperando en cola por unidad de tiempo.
    c_max : int
        Máximo de servidores a evaluar (por defecto 50).

    Returns
    -------
    OptimizeResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = optimize_servers(lam=4.0, mu=3.0, cost_per_server=10.0, cost_per_wait=5.0)
    >>> round(r.min_cost, 4)
    25.3333
    """
    from .queuing import mmc

    lam             = as_positive(lam, "lam")
    mu              = as_positive(mu, "mu")
    cost_per_server = as_positive(cost_per_server, "cost_per_server")
    cost_per_wait   = as_positive(cost_per_wait, "cost_per_wait")
    c_max           = as_int_positive(c_max, "c_max", max=MAX_SERVIDORES)

    c_min = _min_servidores_estables(lam, mu)
    if c_min > c_max:
        raise ValueError(_t("solver.error.optimize_servers.sin_servidores_estables_hasta_c_max", lam=lam, mu=mu, c_min=c_min, c_max=c_max))
    rows: list[dict[str, Any]] = []

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
    """Varía un parámetro del modelo y devuelve un DataFrame con todos los KPI.

    Parameters
    ----------
    model_fn : callable
        Cualquier función de modelo de walopy (p. ej. ``mm1``, ``mmc``, ``kingman``).
    param : str
        Nombre del parámetro a variar (debe coincidir con el argumento de la función).
    values : sequence of float
        Valores a evaluar.
    **fixed_kwargs
        Todos los demás parámetros de ``model_fn`` (fijos).

    Returns
    -------
    pd.DataFrame
        Una fila por valor con el parámetro barrido y todos los campos del resultado.


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``param`` no es un parámetro de ``model_fn`` o ``values`` está vacío.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> from walopy import mm1
    >>> from walopy.solver import sensitivity
    >>> import numpy as np
    >>> df = sensitivity(mm1, "lam", np.linspace(0.5, 4.5, 20), mu=5.0)
    """
    if len(values) == 0:
        raise ValueError(_t("solver.error.sensitivity.values_no_puede_estar_vacio"))
    try:
        parametros = inspect.signature(model_fn).parameters
    except (TypeError, ValueError):   # callables sin firma inspeccionable: se intenta igualmente
        parametros = None
    if parametros is not None and param not in parametros and not any(p.kind is p.VAR_KEYWORD for p in parametros.values()):
        nombre_modelo = repr(model_fn) if not hasattr(model_fn, "__name__") else model_fn.__name__
        raise ValueError(_t("solver.error.sensitivity.param_no_es_parametro_modelo", param=param, modelo=nombre_modelo))
    rows: list[dict[str, Any]] = []
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
    df: pd.DataFrame,
    *,
    errors: str = "collect",
    **fixed_kwargs: Any,
) -> pd.DataFrame:
    """Aplica un modelo de walopy a cada fila de un DataFrame.

    Los valores de las columnas de cada fila se pasan como argumentos con nombre a *model_fn*.
    Los valores de *fixed_kwargs* sirven como predeterminados; los valores de la fila siempre
    los reemplazan. Las celdas NaN de la fila de entrada se descartan antes de la llamada, de
    modo que un DataFrame disperso puede representar varias configuraciones del modelo en una tabla.

    Parameters
    ----------
    model_fn : callable
        Cualquier función de modelo de walopy (p. ej. ``mm1``, ``mmc``, ``kingman``,
        ``oee``, ``break_even``).
    df : pd.DataFrame
        Una fila por escenario. Los nombres de columna deben coincidir con los parámetros de
        *model_fn*.
    errors : {'collect', 'raise'}
        ``'collect'`` (por defecto): una fila que falla no detiene el lote; su mensaje queda en la
        columna ``_error``. ``'raise'``: la primera excepción se propaga.
    **fixed_kwargs
        Parámetros adicionales compartidos por todas las filas (p. ej. ``mu=5.0``).
        Una columna de *df* con el mismo nombre tiene precedencia.

    Returns
    -------
    pd.DataFrame
        Una fila por cada fila de entrada con todas las columnas originales más los campos
        escalares de salida del modelo. Se conserva el índice del DataFrame de entrada. Si alguna
        fila lanza una excepción se agrega una columna ``_error`` con el mensaje de las filas
        fallidas y ``None`` en las exitosas.


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``errors`` no es ``'collect'`` ni ``'raise'``; con ``errors='raise'``, la excepción de la primera fila que falle.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> import pandas as pd
    >>> from walopy import mm1
    >>> from walopy.solver import batch_model
    >>> scenarios = pd.DataFrame({"lam": [1.0, 2.0, 3.0, 4.0], "mu": [5.0, 5.0, 5.0, 5.0]})
    >>> batch_model(mm1, scenarios)["rho"].round(2).tolist()
    [0.2, 0.4, 0.6, 0.8]
    """
    if errors not in ("collect", "raise"):
        raise ValueError(_t("solver.error.batch_model.errors_debe_ser_collect_raise"))
    rows: list[dict] = []
    has_errors = False

    # Pre-compute integer columns so iterrows() float-upcast can be reversed
    int_cols = {col for col in df.columns if pd.api.types.is_integer_dtype(df[col].dtype)}
    # Una columna entera con NaN (DataFrame disperso) pasa a float64: sus valores enteros vuelven a ser int al llamar al modelo
    sparse_int_cols = {col for col in df.columns if pd.api.types.is_float_dtype(df[col].dtype) and df[col].isna().any()}

    for _, row_series in df.iterrows():
        # Merge: fixed_kwargs as base, row values (non-NaN) take precedence
        kwargs: dict[str, Any] = dict(fixed_kwargs)
        for k, v in row_series.items():
            if isinstance(v, float) and np.isnan(v):
                continue
            # iterrows() upcasts int64 columns to float64; reverse that cast
            if k in int_cols or (k in sparse_int_cols and isinstance(v, (float, np.floating)) and float(v).is_integer()):
                kwargs[k] = int(v)
            else:
                kwargs[k] = v

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
            if errors == "raise":
                raise
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
    """Compara varios resultados de modelos de walopy lado a lado.

    Parameters
    ----------
    *results
        Cualquier objeto de resultado de walopy (``QueueResult``, ``SimulationResult``,
        ``EOQResult``, etc.) o diccionarios simples. Si la tabla ``to_frame()`` de un resultado tiene varias filas
        (pedidos, actividades…), se comparan sus campos escalares (costo total, duración del proyecto…).
    labels : sequence of str, optional
        Etiquetas de las filas. Por defecto ``'escenario_1'``, ``'escenario_2'``, …

    Returns
    -------
    pd.DataFrame
        Una fila por resultado con una columna ``label`` al inicio.


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si no se recibe ningún resultado.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> from walopy import mm1, mmc, compare
    >>> tabla = compare(mm1(2, 5), mmc(2, 5, 2), labels=["M/M/1", "M/M/2"])
    >>> tabla["c (servidores)"].tolist()
    [1, 2]
    """
    if len(results) == 0:
        raise ValueError(_t("solver.error.compare.sin_resultados"))
    rows: list[dict[str, Any]] = []
    for i, r in enumerate(results):
        label = labels[i] if (labels and i < len(labels)) else _t("solver.etiqueta.compare.escenario", expr=i + 1)
        tabla = r.to_frame() if hasattr(r, "to_frame") else None
        if tabla is not None and len(tabla) == 1:
            row = tabla.iloc[0].to_dict()
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
