"""W-28: ``solve_servers`` y ``optimize_servers`` empezaban a buscar un servidor después del mínimo estable.

``c_min = ceil(λ/μ) + 1`` solo es el menor ``c`` estable cuando λ/μ es entero; si no lo es, el menor es ``ceil(λ/μ)`` y la búsqueda saltaba ese valor
(con λ=4, μ=3, Wq ≤ 0,5 devolvía 3 servidores cuando 2 ya cumplen con Wq = 0,267; con λ=1, μ=5 nunca consideraba M/M/1).
"""
from __future__ import annotations

import math
import random

import pytest

import walopy as wl

METRICAS = ("Wq", "W", "Lq", "L", "rho")


def _estable(lam: float, mu: float, c: int) -> bool:
    return lam / (c * mu) < 1.0


def _metrica(lam: float, mu: float, c: int, nombre: str) -> float:
    return getattr(wl.mmc(lam, mu, c), nombre) if _estable(lam, mu, c) else math.inf


def test_solve_servers_devuelve_el_minimo_cuando_la_razon_no_es_entera():
    r = wl.solve_servers("Wq", 0.5, lam=4.0, mu=3.0)
    assert r.value == 2.0  # antes 3.0
    assert r.achieved_value == pytest.approx(wl.mmc(4.0, 3.0, 2).Wq)


def test_solve_servers_con_poca_carga_usa_un_servidor():
    r = wl.solve_servers("Wq", 10.0, lam=1.0, mu=5.0)
    assert r.value == 1.0  # antes 2.0: M/M/1 nunca se consideraba


def test_optimize_servers_considera_el_minimo_estable():
    r = wl.optimize_servers(lam=4.0, mu=3.0, cost_per_server=10.0, cost_per_wait=5.0)
    assert r.optimal_servers == 2  # antes 3
    assert r.min_cost == pytest.approx(2 * 10.0 + wl.mmc(4.0, 3.0, 2).Lq * 5.0)
    assert int(r.cost_breakdown["c"].iloc[0]) == 2


def test_optimize_servers_con_poca_carga_usa_un_servidor():
    assert wl.optimize_servers(lam=1.0, mu=5.0, cost_per_server=10.0, cost_per_wait=5.0).optimal_servers == 1


def test_razon_entera_el_minimo_estable_es_el_siguiente():
    # λ/μ = 2: con 2 servidores ρ = 1 (inestable), el menor estable es 3. (Guarda: ya era correcto.)
    r = wl.solve_servers("rho", 0.99, lam=6.0, mu=3.0)
    assert r.value == 3.0
    assert wl.optimize_servers(lam=6.0, mu=3.0, cost_per_server=10.0, cost_per_wait=5.0).cost_breakdown["c"].iloc[0] == 3


@pytest.mark.parametrize("semilla", range(60))
def test_solve_servers_es_el_minimo_por_enumeracion(semilla):
    r = random.Random(100 + semilla)
    lam, mu, metrica = r.uniform(1, 30), r.uniform(1, 10), r.choice(METRICAS)
    c0 = max(1, math.ceil(lam / mu))
    objetivo = _metrica(lam, mu, c0 + r.randint(0, 3), metrica) * r.uniform(0.5, 1.5)
    if not objetivo > 0:
        objetivo = 1.0
    enumerado = next((c for c in range(1, 101) if _metrica(lam, mu, c, metrica) <= objetivo), None)
    if enumerado is None:
        with pytest.raises(ValueError):
            wl.solve_servers(metrica, objetivo, lam=lam, mu=mu)
    else:
        assert wl.solve_servers(metrica, objetivo, lam=lam, mu=mu).value == enumerado


@pytest.mark.parametrize("semilla", range(60))
def test_optimize_servers_es_el_minimo_por_enumeracion(semilla):
    r = random.Random(500 + semilla)
    lam, mu, por_servidor, por_espera = r.uniform(0.5, 20), r.uniform(0.5, 10), r.uniform(1, 100), r.uniform(1, 200)
    costos = {c: c * por_servidor + wl.mmc(lam, mu, c).Lq * por_espera for c in range(1, 61) if _estable(lam, mu, c)}
    mejor = min(costos, key=lambda c: costos[c])
    res = wl.optimize_servers(lam, mu, cost_per_server=por_servidor, cost_per_wait=por_espera, c_max=60)
    assert res.optimal_servers == mejor
    assert res.min_cost == pytest.approx(costos[mejor])
