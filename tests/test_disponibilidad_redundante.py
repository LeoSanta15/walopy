"""W-33: la disponibilidad de los sistemas redundantes suponía que nada se repara hasta que cae todo el sistema.

``parallel_system`` y ``koon_system`` calculaban ``A = MTTF_sistema / (MTTF_sistema + MTTR)``: con dos componentes en paralelo
(λ = 0,01, MTTR = 10) daban 0,9375, cuando con reparación independiente de cada componente es 1 − (1 − Aᵢ)² = 0,9917
(8 veces menos indisponibilidad). Ahora se usa la disponibilidad en régimen con reparación independiente.
"""
from __future__ import annotations

import math
import random

import pytest

import walopy as wl


def _a(lam: float, mttr: float) -> float:
    return (1 / lam) / (1 / lam + mttr)


def test_paralelo_de_dos_con_reparacion_independiente():
    r = wl.parallel_system([0.01, 0.01], mttr=10.0)
    assert r.availability == pytest.approx(1 - (1 - 100 / 110) ** 2)  # 0,9917; antes 0,9375


def test_k_de_n_es_la_binomial_de_la_disponibilidad_de_cada_componente():
    a = _a(0.01, 10.0)
    r = wl.koon_system(n=3, k=2, failure_rate=0.01, mttr=10.0)
    assert r.availability == pytest.approx(3 * a**2 * (1 - a) + a**3)


@pytest.mark.parametrize("semilla", range(40))
def test_paralelo_y_k_de_n_contra_formulas_independientes(semilla):
    r = random.Random(3300 + semilla)
    lams = [r.uniform(1e-4, 0.1) for _ in range(r.randint(2, 5))]
    mttr = r.uniform(0.1, 50)
    esperado = 1 - math.prod(1 - _a(x, mttr) for x in lams)
    assert wl.parallel_system(lams, mttr=mttr).availability == pytest.approx(esperado, rel=1e-12)
    n = r.randint(2, 6)
    k = r.randint(1, n - 1)
    a = _a(lams[0], mttr)
    binomial = sum(math.comb(n, j) * a**j * (1 - a) ** (n - j) for j in range(k, n + 1))
    assert wl.koon_system(n=n, k=k, failure_rate=lams[0], mttr=mttr).availability == pytest.approx(binomial, rel=1e-12)


def test_redundancia_nunca_es_menos_disponible_que_un_componente():
    for lam, mttr in ((0.01, 10.0), (0.2, 3.0), (1e-3, 100.0)):
        a = _a(lam, mttr)
        assert wl.parallel_system([lam, lam], mttr=mttr).availability > a
        assert wl.koon_system(n=3, k=1, failure_rate=lam, mttr=mttr).availability > a


def test_un_solo_componente_y_la_serie_no_cambian():
    # Guarda: un componente (paralelo de 1 o 1-de-1) y la serie conservan A = MTBF / (MTBF + MTTR)
    assert wl.parallel_system([0.01], mttr=10.0).availability == pytest.approx(_a(0.01, 10.0))
    assert wl.koon_system(n=1, k=1, failure_rate=0.01, mttr=10.0).availability == pytest.approx(_a(0.01, 10.0))
    assert wl.series_system([0.01, 0.02], mttr=10.0).availability == pytest.approx(1 / (1 + 0.03 * 10.0))


def test_sin_mttr_no_hay_disponibilidad():
    # Guarda
    assert wl.parallel_system([0.01, 0.02]).availability is None
    assert wl.koon_system(n=3, k=2, failure_rate=0.01).availability is None
