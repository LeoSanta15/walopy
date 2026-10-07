"""W-27: ``wagner_whitin`` cobraba preparación en periodos sin demanda y obligaba a pedir en el periodo 1."""
from __future__ import annotations

import math
import random

import pytest

import walopy as wl
from tests.test_complejidad import _ww_fuerza_bruta


def _pedidos(r):
    return [(o["period"], o["order_qty"]) for o in r.orders]


def test_ceros_iniciales_no_obligan_a_pedir_en_el_periodo_1():
    r = wl.wagner_whitin([0, 0, 100, 0, 0], setup_cost=100, holding_cost=1)
    assert r.total_cost == pytest.approx(100.0)  # antes 200: pedido vacío en el periodo 1 + el real
    assert _pedidos(r) == [(3, 100.0)]


def test_ceros_intermedios_no_pagan_preparacion():
    r = wl.wagner_whitin([0, 50, 0, 100], setup_cost=100, holding_cost=1)
    assert r.total_cost == pytest.approx(200.0)  # antes 250
    assert _pedidos(r) == [(2, 50.0), (4, 100.0)]


def test_horizonte_sin_demanda_cuesta_cero_y_no_pide():
    r = wl.wagner_whitin([0, 0, 0], setup_cost=100, holding_cost=1)
    assert r.total_cost == 0.0
    assert r.orders == [] and r.n_orders == 0
    assert r.total_setup_cost == 0.0 and r.total_holding_cost == 0.0


def test_ningun_pedido_es_de_cantidad_cero():
    r = random.Random(27)
    for _ in range(200):
        d = [r.choice([0, 0, r.randint(1, 40)]) for _ in range(r.randint(1, 12))]
        res = wl.wagner_whitin(d, r.randint(5, 80), r.choice([0.5, 1, 2]))
        assert all(o["order_qty"] > 0 for o in res.orders)
        assert sum(o["order_qty"] for o in res.orders) == pytest.approx(sum(d))


@pytest.mark.parametrize("semilla", range(150))
def test_costo_optimo_exacto_con_ceros_en_cualquier_posicion(semilla):
    r = random.Random(7000 + semilla)
    d = [r.choice([0, 0, r.randint(1, 60)]) for _ in range(r.randint(1, 10))]
    S, h = r.uniform(1, 200), r.uniform(0.05, 3)
    res = wl.wagner_whitin(d, S, h)
    assert res.total_cost == pytest.approx(_ww_fuerza_bruta(d, S, h), rel=1e-9, abs=1e-9)
    assert res.total_cost == pytest.approx(res.total_setup_cost + res.total_holding_cost)
    assert res.total_setup_cost == pytest.approx(res.n_orders * S)


def test_con_demanda_positiva_el_resultado_no_cambia():
    # Caso de referencia del docstring: sin ceros el plan es el de siempre.
    r = wl.wagner_whitin([100, 80, 120, 60], setup_cost=200, holding_cost=1)
    assert r.total_cost == pytest.approx(_ww_fuerza_bruta([100, 80, 120, 60], 200, 1))
    assert r.orders[0]["period"] == 1
    assert math.isfinite(r.total_cost)
