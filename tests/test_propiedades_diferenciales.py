"""Relaciones que deben cumplir funciones distintas del mismo modelo, sobre escenarios aleatorios con semilla fija.

Complementan a los tests de valores concretos: detectan errores que un caso a mano no cubre (como W-27). Carga moderada
(``N`` escenarios por familia); la semilla fija hace que un fallo sea reproducible.
"""
from __future__ import annotations

import math
import random

import walopy as wl

N = 300
SEMILLA = 20261007


def _cerca(a: float, b: float, rel: float = 1e-7) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-12)


def _costo_eoq(D: float, K: float, h: float, q: float) -> float:
    return D / q * K + h * q / 2


def _escenarios(familia: str):
    r = random.Random(f"{SEMILLA}-{familia}")
    return [random.Random(r.random()) for _ in range(N)]


def _cola(r):
    mu = r.uniform(0.2, 50)
    lam = r.uniform(0.01, 0.97) * mu
    return lam, mu, wl.mm1(lam, mu)


def test_mg1_con_cs2_igual_a_1_es_mm1():
    for r in _escenarios("mg1"):
        lam, mu, m = _cola(r)
        g = wl.mg1(lam, mu, 1.0)
        assert _cerca(g.L, m.L) and _cerca(g.Wq, m.Wq), (lam, mu)


def test_kingman_con_cv_1_coincide_con_mm1():
    for r in _escenarios("kingman"):
        lam, mu, m = _cola(r)
        assert _cerca(wl.kingman(lam, mu, 1.0, 1.0).Wq, m.Wq), (lam, mu)


def test_md1_tiene_la_mitad_de_cola_que_mm1():
    for r in _escenarios("md1"):
        lam, mu, m = _cola(r)
        assert _cerca(wl.md1(lam, mu).Lq, m.Lq / 2), (lam, mu)


def test_mmc_con_un_servidor_es_mm1():
    for r in _escenarios("mmc1"):
        lam, mu, m = _cola(r)
        c1 = wl.mmc(lam, mu, 1)
        assert _cerca(c1.Wq, m.Wq) and _cerca(c1.L, m.L), (lam, mu)


def test_erlang_b_decrece_al_añadir_servidores():
    for r in _escenarios("erlang"):
        c, a = r.randint(1, 40), r.uniform(0.1, 60)
        b0, b1 = wl.erlang_b(a, 1.0, c), wl.erlang_b(a, 1.0, c + 1)
        assert 0 <= b1 <= b0 + 1e-15 and b0 <= 1, (a, c, b0, b1)


def test_mmc_la_espera_decrece_al_añadir_un_servidor():
    for r in _escenarios("mmc_c"):
        c, mu = r.randint(1, 15), r.uniform(1, 20)
        lam = r.uniform(0.05, 0.95) * c * mu
        w1, w2 = wl.mmc(lam, mu, c).Wq, wl.mmc(lam, mu, c + 1).Wq
        assert w2 <= w1 + 1e-12, (lam, mu, c, w1, w2)


def test_lotes_wagner_whitin_no_supera_a_las_heuristicas():
    for r in _escenarios("lotes"):
        d = [r.choice([0, 0, r.uniform(1, 200)]) for _ in range(r.randint(2, 12))]
        if sum(d) == 0:
            continue
        S, h = r.uniform(1, 500), r.uniform(0.05, 5)
        ww = wl.wagner_whitin(d, S, h).total_cost
        assert ww <= wl.silver_meal(d, S, h).total_cost + 1e-6, (d, S, h)
        assert ww <= wl.lot_for_lot(d, S, h).total_cost + 1e-6, (d, S, h)


def test_fiabilidad_serie_y_paralelo_acotan_a_los_componentes():
    for r in _escenarios("fiabilidad"):
        n = r.randint(2, 6)
        lams = [r.uniform(1e-3, 0.2) for _ in range(n)]
        t = r.uniform(0.5, 100)
        Ri = [math.exp(-x * t) for x in lams]
        assert wl.series_system(lams, t=t).R_t <= min(Ri) + 1e-12, (lams, t)
        assert wl.parallel_system(lams, t=t).R_t >= max(Ri) - 1e-12, (lams, t)


def test_k_de_n_esta_entre_serie_y_paralelo():
    for r in _escenarios("koon"):
        n = r.randint(2, 6)
        k, lam, t = r.randint(1, n), r.uniform(1e-3, 0.2), r.uniform(0.5, 100)
        rk = wl.koon_system(n=n, k=k, failure_rate=lam, t=t).R_t
        assert math.exp(-lam * t) ** n - 1e-12 <= rk <= 1 - (1 - math.exp(-lam * t)) ** n + 1e-12, (n, k, lam, t)


def test_eoq_es_el_minimo_del_costo_y_coincide_con_la_formula():
    for r in _escenarios("eoq"):
        D, K, h = r.uniform(1, 5000), r.uniform(1, 500), r.uniform(0.01, 10)
        e = wl.eoq(D, K, h)

        assert _cerca(e.total_cost, _costo_eoq(D, K, h, e.eoq), 1e-9), (D, K, h)
        assert all(e.total_cost <= _costo_eoq(D, K, h, e.eoq * f) + 1e-9 for f in (0.5, 0.9, 1.1, 2)), (D, K, h)


def test_eoq_decrece_con_el_costo_de_mantener():
    for r in _escenarios("eoq_h"):
        D, K, h = r.uniform(1, 5000), r.uniform(1, 500), r.uniform(0.01, 10)
        assert wl.eoq(D, K, h * 1.5).eoq < wl.eoq(D, K, h).eoq, (D, K, h)
