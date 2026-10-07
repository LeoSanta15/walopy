"""Algoritmos de secuenciación, redes, colas finitas, lotes y MRP contra oráculos independientes (escenarios aleatorios con semilla fija).

Cada oráculo está escrito aparte del código de ``walopy`` (fuerza bruta, camino más largo, ecuaciones de balance, fórmula cerrada), y se comprueba que
discrimina: NEH, que es una heurística, se compara con el óptimo solo como cota. Carga moderada (``N`` escenarios por familia).
"""
from __future__ import annotations

import itertools
import math
import random
import warnings

import walopy as wl

N = 120
SEMILLA = 20261008


def _cerca(a: float, b: float, rel: float = 1e-7) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


def _escenarios(familia: str):
    r = random.Random(f"{SEMILLA}-{familia}")
    return [random.Random(r.random()) for _ in range(N)]


def _makespan(tiempos, perm):
    c = [0.0] * len(tiempos[0])
    for j in perm:
        c[0] += tiempos[j][0]
        for k in range(1, len(c)):
            c[k] = max(c[k], c[k - 1]) + tiempos[j][k]
    return c[-1]


def _indices(secuencia):
    return [int(s[1:]) - 1 for s in secuencia]


def test_neh_devuelve_una_permutacion_coherente_y_no_mejor_que_el_optimo():
    for r in _escenarios("neh"):
        n, m = r.randint(2, 6), r.randint(2, 4)
        T = [[r.randint(1, 20) for _ in range(m)] for _ in range(n)]
        res = wl.neh_flowshop(T)
        sec = _indices(res.sequence)
        optimo = min(_makespan(T, p) for p in itertools.permutations(range(n)))
        assert sorted(sec) == list(range(n)), T
        assert _cerca(res.makespan, _makespan(T, sec)), T
        assert res.makespan >= optimo - 1e-9, T


def test_johnson_es_optimo_con_dos_maquinas():
    for r in _escenarios("johnson"):
        n = r.randint(2, 6)
        a, b = [r.randint(1, 20) for _ in range(n)], [r.randint(1, 20) for _ in range(n)]
        T = [[x, y] for x, y in zip(a, b)]
        res = wl.johnson_flowshop(a, b)
        optimo = min(_makespan(T, p) for p in itertools.permutations(range(n)))
        assert _cerca(res.makespan, optimo), (a, b)
        assert _cerca(_makespan(T, _indices(res.sequence)), optimo), (a, b)


def _terminaciones(p, perm):
    t, out = 0, {}
    for j in perm:
        t += p[j]
        out[j] = t
    return out


def _camino_mas_largo(acts, i, memo):
    if i not in memo:
        previos = [_camino_mas_largo(acts, int(q[1:]), memo) for q in acts[i]["predecessors"]]
        memo[i] = acts[i]["duration"] + max(previos or [0])
    return memo[i]


def test_reglas_de_secuenciacion_en_una_maquina_son_optimas_en_su_criterio():
    for r in _escenarios("una_maquina"):
        n = r.randint(2, 6)
        p = [r.randint(1, 15) for _ in range(n)]
        d = [r.randint(1, 40) for _ in range(n)]
        w = [r.randint(1, 5) for _ in range(n)]
        perms = list(itertools.permutations(range(n)))

        total = min(sum(_terminaciones(p, q).values()) for q in perms)
        ponderado = min(sum(w[j] * c for j, c in _terminaciones(p, q).items()) for q in perms)
        retraso = min(max(c - d[j] for j, c in _terminaciones(p, q).items()) for q in perms)
        assert _cerca(wl.schedule_single(p, rule="SPT").total_completion_time, total), p
        assert _cerca(wl.schedule_single(p, rule="WSPT", weights=w).total_weighted_completion_time, ponderado), (p, w)
        assert _cerca(wl.schedule_single(p, rule="EDD", due_dates=d).max_lateness, retraso), (p, d)


def test_cpm_la_duracion_es_el_camino_mas_largo():
    for r in _escenarios("cpm"):
        na = r.randint(1, 9)
        acts = [
            {"name": f"A{i}", "duration": r.randint(1, 12), "predecessors": [f"A{j}" for j in range(i) if r.random() < 0.35]}
            for i in range(na)
        ]
        memo: dict[int, int] = {}
        assert _cerca(wl.cpm(acts).project_duration, max(_camino_mas_largo(acts, i, memo) for i in range(na))), acts


def test_colas_finitas_coinciden_con_las_ecuaciones_de_balance():
    for r in _escenarios("mmck"):
        c = r.randint(1, 5)
        K = c + r.randint(0, 10)
        mu = r.uniform(0.5, 10)
        lam = r.uniform(0.1, 2.0) * c * mu
        pesos = [1.0]
        for k in range(1, K + 1):
            pesos.append(pesos[-1] * lam / (min(k, c) * mu))
        pi = [x / sum(pesos) for x in pesos]
        L = sum(k * pi[k] for k in range(K + 1))
        Lq = sum((k - c) * pi[k] for k in range(c + 1, K + 1))
        q = wl.mmck(lam, mu, c, K)
        assert _cerca(q.L, L, 1e-6) and _cerca(q.Lq, Lq, 1e-6), (lam, mu, c, K)
        assert _cerca(q.W, L / (lam * (1 - pi[K])), 1e-6), (lam, mu, c, K)
        q1, qc = wl.mm1k(lam, mu, K), wl.mmck(lam, mu, 1, K)
        assert _cerca(q1.L, qc.L) and _cerca(q1.W, qc.W), (lam, mu, K)


def test_prioridades_conservan_el_numero_total_en_el_sistema():
    for r in _escenarios("prioridad"):
        lams = [r.uniform(0.05, 0.8) for _ in range(r.randint(2, 4))]
        mu = sum(lams) / r.uniform(0.1, 0.95)
        pr = wl.mm1_priority(lams, mu)
        assert _cerca(sum(c["L"] for c in pr.classes), wl.mm1(sum(lams), mu).L, 1e-6), (lams, mu)


def _phi(z: float) -> float:
    return math.exp(-z * z / 2) / math.sqrt(2 * math.pi)


def _gran_phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _ganancia(Q, media, sd, precio, costo, rescate):
    """Ganancia esperada con demanda normal: precio·E[ventas] + rescate·E[sobrante] − costo·Q."""
    z = (Q - media) / sd
    ventas = media - sd * (_phi(z) - z * (1 - _gran_phi(z)))
    return precio * ventas + rescate * (Q - ventas) - costo * Q


def test_newsvendor_el_optimo_maximiza_la_ganancia_esperada():
    for r in _escenarios("newsvendor"):
        media = r.uniform(20, 500)
        sd = media * r.uniform(0.05, 0.3)
        precio = r.uniform(5, 30)
        costo = precio * r.uniform(0.1, 0.8)
        rescate = costo * r.uniform(0, 0.6)

        datos = (media, sd, precio, costo, rescate)
        res = wl.newsvendor(media, sd, precio, costo, salvage=rescate)
        rejilla = [media * (0.2 + i * 0.01) for i in range(300)]
        assert _ganancia(res.optimal_qty, *datos) >= max(_ganancia(g, *datos) for g in rejilla) - 1e-6, datos
        assert _cerca(res.expected_profit, _ganancia(res.optimal_qty, *datos), 1e-6), datos


def test_politicas_de_lotes_son_coherentes_con_sus_pedidos():
    for r in _escenarios("lotes"):
        dem = [r.choice([0, 0, r.uniform(1, 200)]) for _ in range(r.randint(1, 12))]
        S, h = r.uniform(1, 500), r.uniform(0.05, 5)
        for fn in (wl.silver_meal, wl.lot_for_lot):
            res = fn(dem, S, h)
            costo = len(res.orders) * S + h * sum(
                dem[t - 1] * (t - o["period"]) for o in res.orders for t in o["covers_periods"]
            )
            assert all(o["order_qty"] > 0 for o in res.orders), (fn.__name__, dem)
            assert _cerca(sum(o["order_qty"] for o in res.orders), sum(dem), 1e-9), (fn.__name__, dem)
            assert _cerca(res.total_cost, costo, 1e-9), (fn.__name__, dem, S, h)
            assert res.n_orders == len(res.orders), (fn.__name__, dem)


def test_mrp_cumple_el_balance_de_inventario():
    for r in _escenarios("mrp"):
        T = r.randint(2, 10)
        bruto = [r.choice([0, r.randint(1, 50)]) for _ in range(T)]
        inicial, lt, ss = r.randint(0, 60), r.randint(0, 3), r.randint(0, 10)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # liberaciones vencidas (W-16): aviso esperado con lead_time largo
            res = wl.mrp(bruto, initial_on_hand=inicial, lead_time=lt, safety_stock=ss)
        previo = inicial
        for t in range(T):
            esperado = previo + res.scheduled_receipts[t] + res.planned_receipts[t] - bruto[t]
            assert _cerca(res.projected_on_hand[t], esperado, 1e-9), (bruto, inicial, lt, ss, t)
            assert res.projected_on_hand[t] >= ss - 1e-9, (bruto, inicial, lt, ss, t)
            sin_recepcion = previo + res.scheduled_receipts[t] - bruto[t]
            if res.planned_receipts[t] > 1e-9:
                assert sin_recepcion < ss - 1e-9, (bruto, inicial, lt, ss, t)  # solo se recibe lo necesario (LFL)
            previo = res.projected_on_hand[t]
