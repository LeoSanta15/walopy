"""W-29: ``c_max`` de ``solve_servers`` y ``optimize_servers`` no se validaba.

``optimize_servers`` con ``c_max`` menor que el mínimo estable fallaba con ``min() arg is an empty sequence``; ``c_max`` no entero, ``bool``, ``nan`` o ``None``
daba ``TypeError`` opacos o se aceptaba (``True``), y ``c_max <= 0`` se trataba como «sin solución».
"""
from __future__ import annotations

import numpy as np
import pytest

import walopy as wl

SOLVE = dict(target_metric="Wq", target_value=0.5, lam=4.0, mu=3.0)
OPTIMIZE = dict(lam=4.0, mu=3.0, cost_per_server=10.0, cost_per_wait=5.0)
FUNCIONES = [("solve_servers", SOLVE), ("optimize_servers", OPTIMIZE)]


@pytest.mark.parametrize("nombre,args", FUNCIONES)
@pytest.mark.parametrize("c_max", [2.5, True, "a", None, float("nan")])
def test_c_max_no_entero_es_type_error_claro(nombre, args, c_max):
    with pytest.raises(TypeError) as e:
        getattr(wl, nombre)(c_max=c_max, **args)
    assert "c_max" in str(e.value)  # (sin ``match=``: la verificación de regresión lo descarta)


@pytest.mark.parametrize("nombre,args", FUNCIONES)
@pytest.mark.parametrize("c_max", [0, -3])
def test_c_max_no_positivo_es_value_error_claro(nombre, args, c_max):
    with pytest.raises(ValueError) as e:
        getattr(wl, nombre)(c_max=c_max, **args)
    assert "c_max" in str(e.value)


@pytest.mark.parametrize("nombre,args", FUNCIONES)
def test_c_max_demasiado_grande_se_rechaza(nombre, args):
    with pytest.raises(ValueError) as e:
        getattr(wl, nombre)(c_max=10**9, **args)
    assert "c_max" in str(e.value)


def test_optimize_servers_con_c_max_menor_que_el_minimo_estable_explica_que_falta():
    # λ/μ = 1,33: hacen falta 2 servidores; antes «min() arg is an empty sequence»
    with pytest.raises(ValueError) as e:
        wl.optimize_servers(c_max=1, **OPTIMIZE)
    assert "c_max=1" in str(e.value) and "min()" not in str(e.value)
    assert "2" in str(e.value)


def test_solve_servers_con_c_max_menor_que_el_minimo_estable_sigue_siendo_value_error():
    with pytest.raises(ValueError):
        wl.solve_servers(c_max=1, **SOLVE)


@pytest.mark.parametrize("nombre,args", FUNCIONES)
def test_c_max_valido_sigue_funcionando(nombre, args):
    # Guarda: enteros de Python y de NumPy en el límite exacto
    for c_max in (2, np.int64(2), 100):
        r = getattr(wl, nombre)(c_max=c_max, **args)
        assert (r.optimal_servers if nombre == "optimize_servers" else r.value) == 2
