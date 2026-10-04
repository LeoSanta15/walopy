"""Contrato de entradas (auditoría 2026-10): ninguna función pública de ``walopy.__all__`` debe aceptar
NaN/inf/cadenas/None/listas vacías o con elementos inválidos en silencio, fallar con una excepción
distinta de ``ValueError``/``TypeError`` ni quedarse bloqueada.

Cada función se prueba con una llamada válida de referencia y se sustituye un argumento cada vez.
"""
from __future__ import annotations

import copy
import inspect
import signal
import warnings

import numpy as np
import pytest

import walopy as wl

NAN, INF = float("nan"), float("inf")

IT_EX = [
    {"name": "A", "demand": 1000, "ordering_cost": 50, "holding_cost": 2, "unit_value": 10},
    {"name": "B", "demand": 500, "ordering_cost": 30, "holding_cost": 1, "unit_value": 5},
]
IT_SS = [
    {"name": "A", "demand_rate": 100, "demand_std": 10, "lead_time": 2, "unit_value": 10},
    {"name": "B", "demand_rate": 50, "demand_std": 5, "lead_time": 1, "unit_value": 5},
]
IT_ABC = [
    {"name": "A", "demand": 50, "unit_value": 10, "cv": 0.2},
    {"name": "B", "demand": 30, "unit_value": 10, "cv": 0.7},
    {"name": "C", "demand": 100, "unit_value": 1, "cv": 1.5},
]
CPM = [
    {"name": "A", "duration": 3, "predecessors": []},
    {"name": "B", "duration": 4, "predecessors": ["A"]},
]
PERT = [
    {"name": "A", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": []},
    {"name": "B", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": ["A"]},
]

BASE = {
    "set_language": dict(lang="es"),
    "get_language": dict(),
    "language": dict(lang="es"),
    "littles_law": dict(L=None, lam=2.0, W=3.0),
    "mm1": dict(lam=2.0, mu=3.0),
    "mmc": dict(lam=2.0, mu=3.0, c=2),
    "md1": dict(lam=2.0, mu=3.0),
    "kingman": dict(lam=2.0, mu=3.0, ca2=1.0, cs2=1.0),
    "mg1": dict(lam=2.0, mu=3.0, cs2=1.0),
    "cv2_triangular": dict(a=1.0, m=2.0, b=3.0),
    "cv2_uniform": dict(a=1.0, b=3.0),
    "cv2_normal": dict(mean=5.0, std=1.0),
    "cv2_erlang": dict(k=3),
    "cv2_gamma": dict(shape=2.0),
    "cv2_lognormal": dict(mean=5.0, std=1.0),
    "cv2_weibull": dict(shape=1.5),
    "oee": dict(availability=0.9, performance=0.9, quality=0.9),
    "utilization_efficiency": dict(actual_output=75.0, capacity=100.0),
    "unit_cost": dict(fixed_cost=1000.0, variable_cost_per_unit=5.0, units_produced=100.0),
    "bottleneck_analysis": dict(station_names=["a", "b"], capacities=[5.0, 3.0], demand_rate=2.0),
    "oee_kpi_tree": dict(availability=0.9, performance=0.9, quality=0.9),
    "throughput_kpi_tree": dict(actual_throughput=80.0, capacity=100.0, defect_rate=0.05),
    "roi_kpi_tree": dict(revenue=1000.0, fixed_cost=200.0, variable_cost_per_unit=3.0, units_sold=100.0, investment=500.0),
    "solve_lam": dict(target_metric="Wq", target_value=0.5, mu=5.0),
    "solve_mu": dict(target_metric="Wq", target_value=0.5, lam=2.0),
    "solve_servers": dict(target_metric="Wq", target_value=0.5, lam=4.0, mu=3.0),
    "optimize_servers": dict(lam=4.0, mu=3.0, cost_per_server=10.0, cost_per_wait=5.0),
    "erlang_b": dict(lam=2.0, mu=3.0, c=2),
    "mm1k": dict(lam=2.0, mu=3.0, K=5),
    "mmck": dict(lam=2.0, mu=3.0, c=2, K=5),
    "mm1_priority": dict(lam_list=[1.0, 0.5], mu=3.0),
    "monte_carlo_gg1": dict(lam=2.0, mu=3.0, ca2=1.0, cs2=1.0, n_customers=500, seed=1),
    "takt_time": dict(available_time=480.0, demand=60.0),
    "line_balance": dict(station_names=["A", "B"], cycle_times=[5.0, 9.0], takt=10.0),
    "break_even": dict(fixed_cost=1000.0, price_per_unit=10.0, variable_cost_per_unit=4.0),
    "break_even_multi": dict(fixed_cost=1000.0, prices=[10.0, 20.0], variable_costs=[4.0, 8.0], sales_mix=[0.5, 0.5]),
    "break_even_sales": dict(fixed_cost=1000.0, variable_cost_ratio=0.4),
    "queue_length_pmf": dict(lam=2.0, mu=3.0, n_max=10),
    "sojourn_cdf": dict(lam=2.0, mu=3.0, n_points=20),
    "fit_from_data": dict(inter_arrivals=np.array([1.0, 2.0, 1.5, 2.2, 0.9]), service_times=np.array([0.5, 0.7, 0.6, 0.9, 0.4])),
    "eoq": dict(demand_rate=1000.0, ordering_cost=50.0, holding_cost=2.0),
    "ebq": dict(demand_rate=1000.0, setup_cost=50.0, holding_cost=2.0, production_rate=2000.0),
    "eoq_multi": dict(demand_rates=[1000.0, 500.0], ordering_costs=[50.0, 30.0], holding_costs=[2.0, 1.0]),
    "ebq_multi": dict(demand_rates=[1000.0, 500.0], setup_costs=[50.0, 30.0], holding_costs=[2.0, 1.0], production_rates=[3000.0, 2000.0]),
    "eoq_multi_constrained": dict(demand_rates=[1000.0, 500.0], ordering_costs=[50.0, 30.0], holding_costs=[2.0, 1.0], budget=5000.0, budget_unit_costs=[10.0, 5.0]),
    "lot_for_lot": dict(demands=[10.0, 20.0, 30.0], setup_cost=50.0, holding_cost=1.0),
    "silver_meal": dict(demands=[10.0, 20.0, 30.0], setup_cost=50.0, holding_cost=1.0),
    "wagner_whitin": dict(demands=[10.0, 20.0, 30.0], setup_cost=50.0, holding_cost=1.0),
    "eoq_quantity_discount": dict(demand_rate=1000.0, ordering_cost=50.0, holding_cost_rate=0.2, price_breaks=[(0, 10.0), (500, 9.5)]),
    "reorder_point": dict(demand_rate=10.0, lead_time=2.0, demand_std=2.0),
    "newsvendor": dict(demand_mean=100.0, demand_std=20.0, price=10.0, cost=4.0),
    "jackson_network": dict(station_names=["A", "B"], mu=[5.0, 6.0], gamma=[2.0, 0.0], routing=[[0.0, 1.0], [0.0, 0.0]]),
    "rq_policy": dict(demand_rate=100.0, ordering_cost=50.0, holding_cost=2.0, lead_time=2.0, demand_std=5.0),
    "rs_policy": dict(demand_rate=100.0, ordering_cost=50.0, holding_cost=2.0, lead_time=2.0, review_period=1.0, demand_std=5.0),
    "exchange_curve": dict(items=IT_EX, target_orders=10.0),
    "safety_stock_curve": dict(items=IT_SS, target_service_level=0.95),
    "abc_analysis": dict(items=IT_ABC),
    "xyz_analysis": dict(items=IT_ABC),
    "abc_xyz": dict(items=IT_ABC),
    "mrp": dict(gross_requirements=[10.0, 20.0, 30.0, 40.0], initial_on_hand=5.0, lead_time=1),
    "schedule_single": dict(processing_times=[3.0, 1.0, 2.0]),
    "johnson_flowshop": dict(m1_times=[3.0, 1.0, 2.0], m2_times=[2.0, 4.0, 1.0]),
    "neh_flowshop": dict(times_matrix=[[3.0, 2.0, 4.0], [1.0, 4.0, 2.0], [2.0, 1.0, 3.0]]),
    "mtbf_analysis": dict(failure_rate=0.01, mttr=2.0, t=10.0),
    "series_system": dict(failure_rates=[0.01, 0.02], t=10.0),
    "parallel_system": dict(failure_rates=[0.01, 0.02], t=10.0),
    "koon_system": dict(n=3, k=2, failure_rate=0.01, t=10.0),
    "weibull_analysis": dict(failure_times=[10.0, 20.0, 35.0, 50.0, 80.0, 120.0]),
    "cpm": dict(activities=CPM),
    "pert": dict(activities=PERT),
}


# Valores que NUNCA deben aceptarse como argumento escalar.
ESCALARES_INVALIDOS = [NAN, INF, -INF, "abc", True]
# Variantes inválidas de argumentos que son listas.
LISTAS_INVALIDAS = [[], [NAN, 1.0], [INF, 1.0], ["x", 1.0], [None, 1.0]]
# Argumentos de tipo registro (lista de diccionarios / actividades / matrices).
ARGUMENTOS_ESTRUCTURA = {"items", "activities", "price_breaks", "routing", "times_matrix"}
# Argumentos de texto con vocabulario fijo.
ARGUMENTOS_TEXTO = {"target_metric", "rule", "method", "time_unit", "currency", "model", "lot_size", "item_name"}
# Combinaciones (función, argumento, valor) legítimas que sí se aceptan.
ACEPTADOS = {
    ("monte_carlo_gg1", "seed", True),      # una semilla booleana es un entero válido para numpy
    ("mrp", "lot_size", "abc"),             # se valida con su propio mensaje (ver test dedicado)
    ("fit_from_data", "inter_arrivals", "truncada"),  # las dos muestras pueden tener distinto tamaño
    ("fit_from_data", "service_times", "truncada"),
}


class _Truncada(list):
    """Marca una lista acortada para distinguirla en las excepciones de ACEPTADOS."""


class _Bloqueo(Exception):
    pass


def _alarma(*_):
    raise _Bloqueo()


def _llamar(fn, kwargs, segundos=10):
    """Ejecuta ``fn(**kwargs)``; devuelve ('ok', resultado) o ('exc', excepción) o ('hang', None)."""
    usa_alarma = hasattr(signal, "SIGALRM")
    if usa_alarma:
        signal.signal(signal.SIGALRM, _alarma)
        signal.alarm(segundos)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return "ok", fn(**kwargs)
    except _Bloqueo:
        return "hang", None
    except BaseException as e:  # noqa: BLE001 - se inspecciona el tipo exacto
        return "exc", e
    finally:
        if usa_alarma:
            signal.alarm(0)


def _candidatos(nombre, valor_base, defecto, n_listas_paralelas):
    """Valores inválidos a probar para un argumento, según su tipo.

    Una lista más corta solo es inválida cuando hay otras listas de la misma longitud (arreglos paralelos).
    """
    if nombre in ARGUMENTOS_ESTRUCTURA:
        return [[], "abc", None]
    if isinstance(valor_base, (list, tuple, np.ndarray)):
        son_textos = len(valor_base) > 0 and all(isinstance(v, str) for v in valor_base)
        c = [[]] if son_textos else list(LISTAS_INVALIDAS)
        if len(valor_base) > 1 and n_listas_paralelas >= 2:
            c.append(_Truncada(list(valor_base)[:-1]))
        return c
    if isinstance(valor_base, str):
        return [5] + ([None] if defecto is not None else [])
    c = list(ESCALARES_INVALIDOS)
    if defecto is not inspect.Parameter.empty and defecto is None:
        pass  # None significa "no indicado": es válido
    else:
        c.append(None)
    return c


@pytest.mark.parametrize("nombre_fn", sorted(BASE))
def test_contrato_de_entradas(nombre_fn):
    fn = getattr(wl, nombre_fn)
    base = BASE[nombre_fn]
    params = inspect.signature(fn).parameters
    fallos = []
    longitudes = [len(v) for v in base.values() if isinstance(v, (list, tuple, np.ndarray))]
    for arg, valor in base.items():
        defecto = params[arg].default if arg in params else inspect.Parameter.empty
        n_par = longitudes.count(len(valor)) if isinstance(valor, (list, tuple, np.ndarray)) else 0
        for malo in _candidatos(arg, valor, defecto, n_par):
            clave = "truncada" if isinstance(malo, _Truncada) else (None if isinstance(malo, list) else malo)
            if (nombre_fn, arg, clave) in ACEPTADOS:
                continue
            kw = copy.deepcopy(base)
            kw[arg] = malo
            estado, res = _llamar(fn, kw)
            etiqueta = f"{nombre_fn}({arg}={malo!r})"
            if estado == "hang":
                fallos.append(f"{etiqueta}: se quedó bloqueada")
            elif estado == "exc" and not isinstance(res, (ValueError, TypeError)):
                fallos.append(f"{etiqueta}: {type(res).__name__}: {str(res)[:60]}")
            elif estado == "ok":
                fallos.append(f"{etiqueta}: aceptó el valor sin error")
    assert not fallos, "\n".join(fallos)


@pytest.mark.parametrize("nombre_fn", sorted(BASE))
def test_llamada_valida_de_referencia_funciona(nombre_fn):
    estado, res = _llamar(getattr(wl, nombre_fn), copy.deepcopy(BASE[nombre_fn]))
    assert estado == "ok", f"{nombre_fn}: {res!r}"


def test_todas_las_funciones_publicas_tienen_llamada_de_referencia():
    publicas = {n for n in wl.__all__ if inspect.isfunction(getattr(wl, n))}
    # batch_model, sensitivity y compare reciben funciones/resultados: se prueban en sus propios tests.
    exentas = {"batch_model", "sensitivity", "compare"}
    assert publicas - exentas - set(BASE) == set()
