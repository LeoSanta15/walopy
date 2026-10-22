"""Erlang A con dos clases y prioridad no expropiativa (0.4.11).

Oráculos independientes de la implementación (reducción por niveles con GTH): la cadena completa resuelta con álgebra lineal, el caso de
paciencias iguales (la cola total es la de ``erlang_a``), los límites de una sola clase, la exponencial de una matriz (aplicada a un vector) para el nivel de servicio de
la clase baja y una simulación de eventos con prioridad.
"""
import collections
import heapq
import math
import random
import statistics

import numpy as np
import pytest

import walopy as wl
from walopy.advanced import _estacionaria_prioridad, _estacionaria_prioridad_truncada

ARGS = (1.5, 2.5, 1.0, 0.8, 0.3, 4)      # lam_high, lam_low, mu, theta_high, theta_low, c


def _cadena_completa(lam1, lam2, mu, th1, th2, c, Q1, Q2):
    """p·Q = 0 de la cadena (b < c) ∪ (q₁, q₂) con álgebra lineal (sin usar GTH ni la reducción por niveles de la librería)."""
    idx = {}
    for b in range(c):
        idx[("b", b)] = len(idx)
    for q1 in range(Q1 + 1):
        for q2 in range(Q2 + 1):
            idx[(q1, q2)] = len(idx)
    n = len(idx)
    Q = np.zeros((n, n))
    cmu = c * mu

    def add(s, t, r):
        if r > 0:
            Q[idx[s], idx[t]] += r

    for b in range(c):
        add(("b", b), ("b", b + 1) if b < c - 1 else (0, 0), lam1 + lam2)
        if b > 0:
            add(("b", b), ("b", b - 1), b * mu)
    for q1 in range(Q1 + 1):
        for q2 in range(Q2 + 1):
            s = (q1, q2)
            if q1 < Q1:
                add(s, (q1 + 1, q2), lam1)
            if q2 < Q2:
                add(s, (q1, q2 + 1), lam2)
            if q1 > 0:
                add(s, (q1 - 1, q2), th1 * q1 + cmu)       # abandona uno de alta o se atiende el primero de alta
            elif q2 > 0:
                add(s, (q1, q2 - 1), cmu)                  # sin cola alta, se atiende uno de baja
            else:
                add(s, ("b", c - 1), cmu)
            if q2 > 0:
                add(s, (q1, q2 - 1), th2 * q2)
    np.fill_diagonal(Q, -Q.sum(axis=1))
    A = np.vstack([Q.T, np.ones(n)])
    b = np.zeros(n + 1)
    b[-1] = 1.0
    pi = np.linalg.lstsq(A, b, rcond=None)[0]
    return pi[:c], pi[c:].reshape(Q1 + 1, Q2 + 1)


CASOS = [
    (1.2, 2.0, 1.0, 0.8, 0.3, 3),
    (1.5, 2.5, 1.0, 0.8, 0.3, 4),     # λ total = c·μ
    (3.0, 5.0, 1.0, 0.5, 0.2, 5),     # sobrecarga
    (0.4, 0.6, 2.0, 1.5, 0.1, 1),     # un solo servidor
    (2.0, 1.0, 1.0, 0.1, 2.0, 3),     # la clase alta es la más paciente
]


class TestContraLaCadenaCompleta:
    @pytest.mark.parametrize("args", CASOS[:3])
    def test_la_reduccion_por_niveles_coincide_con_el_sistema_lineal(self, args):
        lam1, lam2, mu, th1, th2, c = args
        pb, niv = _estacionaria_prioridad_truncada(*args, 8, 16)
        pb2, niv2 = _cadena_completa(*args, 8, 16)
        assert np.abs(pb - pb2).max() < 1e-12 and np.abs(niv - niv2).max() < 1e-12

    @pytest.mark.parametrize("args", CASOS)
    def test_indicadores_publicos_coinciden(self, args):
        lam1, lam2, mu, th1, th2, c = args
        # misma cadena truncada que eligió la librería (la masa fuera es < 1e-13): se compara el sistema lineal contra la reducción por niveles
        _, niv_lib = _estacionaria_prioridad(*args)
        Q1, Q2 = niv_lib.shape[0] - 1, niv_lib.shape[1] - 1
        pb, niv = _cadena_completa(*args, Q1, Q2)
        eq1 = float((np.arange(Q1 + 1) * niv.sum(axis=1)).sum())
        eq2 = float((np.arange(Q2 + 1) * niv.sum(axis=0)).sum())
        r = wl.erlang_a_priority(*args)
        assert r.classes[0]["Lq"] == pytest.approx(eq1, rel=1e-7)
        assert r.classes[1]["Lq"] == pytest.approx(eq2, rel=1e-7)
        assert r.p_wait == pytest.approx(float(niv.sum()), rel=1e-7)
        assert r.classes[0]["p_abandon"] == pytest.approx(th1 * eq1 / lam1, rel=1e-7)
        ocupados = float((np.arange(c) * pb).sum()) + c * float(niv.sum())
        # lo que se atiende es lo que ocupa servidores: Σ λ_eff = μ·E[ocupados]
        assert sum(x["lam_eff"] for x in r.classes) == pytest.approx(mu * ocupados, rel=1e-7)
        assert r.rho == pytest.approx(mu * ocupados / (c * mu), rel=1e-7)

    def test_la_distribucion_suma_uno_y_es_no_negativa(self):
        pb, niv = _estacionaria_prioridad(*ARGS)
        assert pb.sum() + niv.sum() == pytest.approx(1.0, abs=1e-12)
        assert pb.min() >= 0.0 and niv.min() >= 0.0


class TestCasosLimite:
    @pytest.mark.parametrize("th", [0.2, 0.5, 1.7])
    def test_con_pacientes_iguales_la_cola_total_es_erlang_a(self, th):
        lam1, lam2, mu, c = 1.5, 2.5, 1.0, 4
        r = wl.erlang_a_priority(lam1, lam2, mu, th, th, c)
        ref = wl.erlang_a(lam1 + lam2, mu, th, c)
        assert sum(x["Lq"] for x in r.classes) == pytest.approx(ref.Lq, rel=1e-9)
        assert r.p_wait == pytest.approx(ref.params["P(esperar)"], rel=1e-9)
        assert r.params["P(abandono) total"] == pytest.approx(ref.params["P(abandono)"], rel=1e-9)
        assert r.rho == pytest.approx(ref.rho, rel=1e-9)

    def test_sin_clase_baja_la_alta_es_erlang_a(self):
        ref = wl.erlang_a(3.0, 1.0, 0.6, 4)
        r = wl.erlang_a_priority(3.0, 1e-9, 1.0, 0.6, 0.4, 4)
        assert r.classes[0]["Lq"] == pytest.approx(ref.Lq, rel=1e-6)
        assert r.classes[0]["p_abandon"] == pytest.approx(ref.params["P(abandono)"], rel=1e-6)
        assert r.p_wait == pytest.approx(ref.params["P(esperar)"], rel=1e-6)

    def test_sin_clase_alta_la_baja_es_erlang_a(self):
        ref = wl.erlang_a(3.0, 1.0, 0.4, 4)
        r = wl.erlang_a_priority(1e-9, 3.0, 1.0, 0.9, 0.4, 4)
        assert r.classes[1]["Lq"] == pytest.approx(ref.Lq, rel=1e-6)
        assert r.classes[1]["p_abandon"] == pytest.approx(ref.params["P(abandono)"], rel=1e-6)

    def test_la_prioridad_favorece_a_la_clase_alta(self):
        r = wl.erlang_a_priority(2.0, 2.0, 1.0, 0.5, 0.5, 3)
        alta, baja = r.classes
        assert alta["Wq"] < baja["Wq"] and alta["p_abandon"] < baja["p_abandon"]
        # intercambiar las clases intercambia los papeles
        s = wl.erlang_a_priority(2.0, 2.0, 1.0, 0.5, 0.5, 3)
        assert s.classes[0]["Wq"] == pytest.approx(alta["Wq"], rel=1e-12)

    def test_cambiar_la_prioridad_no_cambia_el_abandono_total_con_pacientes_iguales(self):
        """El abandono total solo depende de la cola total: con θ iguales es el mismo repartan como repartan la prioridad."""
        a = wl.erlang_a_priority(1.0, 3.0, 1.0, 0.4, 0.4, 3)
        b = wl.erlang_a_priority(3.0, 1.0, 1.0, 0.4, 0.4, 3)
        assert a.params["P(abandono) total"] == pytest.approx(b.params["P(abandono) total"], rel=1e-10)

    def test_sobrecarga_estable(self):
        r = wl.erlang_a_priority(30.0, 50.0, 1.0, 0.5, 0.2, 40)       # λ = 2·c·μ
        eff = sum(x["lam_eff"] for x in r.classes)
        assert eff == pytest.approx(40.0, rel=0.03) and r.rho > 0.97

    def test_mas_servidores_menos_abandono(self):
        pab = [wl.erlang_a_priority(1.5, 2.5, 1.0, 0.8, 0.3, c).params["P(abandono) total"] for c in range(2, 9)]
        assert pab == sorted(pab, reverse=True)


def _accion_de_la_exponencial(M, t, v):
    """exp(M·t)·v por pasos de Taylor sobre el vector (independiente de la uniformización de la librería)."""
    pasos = max(1, int(math.ceil(np.abs(M).sum(axis=1).max() * t)))
    h = t / pasos
    for _ in range(pasos):
        termino, acumulado = v, v.copy()
        for k in range(1, 40):
            termino = h * (M @ termino) / k
            acumulado = acumulado + termino
            if np.abs(termino).max() < 1e-17:
                break
        v = acumulado
    return v


def _nivel_clase_baja_por_matriz(lam1, lam2, mu, th1, th2, c, t, niv, libre):
    """P(atendido en ≤ t) de la clase baja con la cadena (a, m) como un generador explícito y su exponencial."""
    Q1, m = niv.shape[0] - 1, niv.shape[1]
    cmu = c * mu
    idx = lambda a, mm: a * m + (mm - 1)        # noqa: E731
    n = (Q1 + 1) * m + 1                        # el último estado es «atendido» (absorbente)
    G = np.zeros((n, n))
    for a in range(Q1 + 1):
        for mm in range(1, m + 1):
            i = idx(a, mm)
            if a < Q1:
                G[i, idx(a + 1, mm)] += lam1
            if a > 0:
                G[i, idx(a - 1, mm)] += th1 * a + cmu
            else:
                G[i, n - 1 if mm == 1 else idx(0, mm - 1)] += cmu
            if mm > 1:
                G[i, idx(a, mm - 1)] += th2 * (mm - 1)
            G[i, i] -= G[i].sum() + th2          # th2: abandono propio (se pierde)
    absorbente = np.zeros(n)
    absorbente[n - 1] = 1.0
    servido = _accion_de_la_exponencial(G, t, absorbente)
    return libre + sum(niv[a, k] * servido[idx(a, k + 1)] for a in range(Q1 + 1) for k in range(m))


class TestNivelDeServicio:
    def test_t_cero_es_la_fraccion_que_no_espera(self):
        pb, _ = _estacionaria_prioridad(*ARGS)
        alta, baja = wl.erlang_a_priority_service_level(*ARGS, t=0.0)
        assert alta == pytest.approx(float(pb.sum()), rel=1e-12) and baja == alta

    def test_t_grande_es_uno_menos_abandono_de_cada_clase(self):
        r = wl.erlang_a_priority(*ARGS)
        alta, baja = wl.erlang_a_priority_service_level(*ARGS, t=60.0)
        assert alta == pytest.approx(1 - r.classes[0]["p_abandon"], abs=1e-9)
        assert baja == pytest.approx(1 - r.classes[1]["p_abandon"], abs=1e-9)

    def test_creciente_en_t_y_la_alta_supera_a_la_baja_con_pacientes_iguales(self):
        args = (1.5, 2.5, 1.0, 0.4, 0.4, 4)
        v = [wl.erlang_a_priority_service_level(*args, t=t) for t in (0.0, 0.2, 0.7, 2.0, 8.0)]
        for k in (0, 1):
            col = [x[k] for x in v]
            assert col == sorted(col)
        assert all(a >= b for a, b in v)

    def test_alta_con_baja_casi_nula_es_el_nivel_de_erlang_a(self):
        for t in (0.0, 0.5, 2.0):
            alta, _ = wl.erlang_a_priority_service_level(3.0, 1e-9, 1.0, 0.6, 0.4, 4, t=t)
            assert alta == pytest.approx(wl.erlang_a_service_level(3.0, 1.0, 0.6, 4, t), abs=1e-6)

    def test_baja_sin_clase_alta_es_el_nivel_de_erlang_a(self):
        for t in (0.0, 0.5, 2.0):
            _, baja = wl.erlang_a_priority_service_level(1e-9, 3.0, 1.0, 0.9, 0.4, 4, t=t)
            assert baja == pytest.approx(wl.erlang_a_service_level(3.0, 1.0, 0.4, 4, t), abs=1e-6)

    @pytest.mark.parametrize("args,t", [((1.5, 2.5, 1.0, 0.8, 0.3, 3), 0.7), ((0.8, 1.2, 1.0, 0.5, 0.6, 2), 1.5), ((2.0, 1.0, 1.0, 0.1, 2.0, 3), 0.4)])
    def test_clase_baja_contra_la_exponencial_de_la_matriz(self, args, t):
        lam1, lam2, mu, th1, th2, c = args
        pb, niv = _estacionaria_prioridad(*args)
        esperado = _nivel_clase_baja_por_matriz(*args, t, niv, float(pb.sum()))
        assert wl.erlang_a_priority_service_level(*args, t=t)[1] == pytest.approx(esperado, abs=1e-8)


def _simular(lam1, lam2, mu, th1, th2, c, n, semilla, t_sl, calentamiento=3000):
    """Simulación de eventos con prioridad: cada cliente abandona a su tasa; al liberarse un servidor se atiende primero a la clase alta (FIFO dentro de la clase)."""
    rng = random.Random(semilla)
    lam = lam1 + lam2
    ev = [(rng.expovariate(lam), 0, None)]
    ocupados = llegadas = sig = 0
    colas = [collections.deque(), collections.deque()]
    estado = {}
    est = [dict(n=0, aband=0, esp=0.0, sl=0, espera_pos=0) for _ in range(2)]
    while ev and llegadas < n + calentamiento:
        t, tipo, d = heapq.heappop(ev)
        if tipo == 0:
            llegadas += 1
            clase = 0 if rng.random() < lam1 / lam else 1
            cid, sig = sig, sig + 1
            medir = llegadas > calentamiento
            estado[cid] = [clase, t, True, medir]
            heapq.heappush(ev, (t + rng.expovariate(lam), 0, None))
            est[clase]["n"] += medir
            if ocupados < c:
                ocupados += 1
                heapq.heappush(ev, (t + rng.expovariate(mu), 1, cid))
                est[clase]["sl"] += medir
            else:
                colas[clase].append(cid)
                est[clase]["espera_pos"] += medir
                heapq.heappush(ev, (t + rng.expovariate(th1 if clase == 0 else th2), 2, cid))
        elif tipo == 1:
            ocupados -= 1
            for k in (0, 1):
                atendido = False
                while colas[k]:
                    cid = colas[k].popleft()
                    cl, ta, activo, medir = estado[cid]
                    if not activo:
                        continue
                    estado[cid][2] = False
                    ocupados += 1
                    heapq.heappush(ev, (t + rng.expovariate(mu), 1, cid))
                    if medir:
                        est[cl]["esp"] += t - ta
                        est[cl]["sl"] += (t - ta) <= t_sl
                    atendido = True
                    break
                if atendido:
                    break
        else:
            cl, ta, activo, medir = estado[d]
            if activo:
                estado[d][2] = False
                if medir:
                    est[cl]["aband"] += 1
                    est[cl]["esp"] += t - ta
    return est


def test_coincide_con_simulacion_de_eventos():
    args, t_sl = ARGS, 0.7
    r = wl.erlang_a_priority(*args)
    alta, baja = wl.erlang_a_priority_service_level(*args, t=t_sl)
    ref = {"pab0": r.classes[0]["p_abandon"], "pab1": r.classes[1]["p_abandon"], "wq0": r.classes[0]["Wq"], "wq1": r.classes[1]["Wq"],
           "sl0": alta, "sl1": baja, "pw": r.p_wait}
    reps = [_simular(*args, 30_000, s, t_sl) for s in range(10)]
    sim = {
        "pab0": [x[0]["aband"] / x[0]["n"] for x in reps], "pab1": [x[1]["aband"] / x[1]["n"] for x in reps],
        "wq0": [x[0]["esp"] / x[0]["n"] for x in reps], "wq1": [x[1]["esp"] / x[1]["n"] for x in reps],
        "sl0": [x[0]["sl"] / x[0]["n"] for x in reps], "sl1": [x[1]["sl"] / x[1]["n"] for x in reps],
        "pw": [(x[0]["espera_pos"] + x[1]["espera_pos"]) / (x[0]["n"] + x[1]["n"]) for x in reps],
    }
    for k, v in ref.items():
        se = statistics.stdev(sim[k]) / len(sim[k]) ** 0.5
        assert abs(statistics.mean(sim[k]) - v) < 4.0 * se, (k, statistics.mean(sim[k]), v, se)


class TestEntradasYSalida:
    @pytest.mark.parametrize("kw", [dict(lam_high=0.0), dict(lam_low=0.0), dict(lam_high=-1.0), dict(mu=0.0), dict(theta_high=0.0),
                                    dict(theta_low=-0.1), dict(theta_low=float("nan")), dict(lam_low=float("inf")), dict(c=0)])
    def test_rechaza_valores_invalidos(self, kw):
        base = dict(lam_high=1.5, lam_low=2.5, mu=1.0, theta_high=0.8, theta_low=0.3, c=4)
        with pytest.raises(ValueError):
            wl.erlang_a_priority(**{**base, **kw})

    def test_t_negativo(self):
        with pytest.raises(ValueError):
            wl.erlang_a_priority_service_level(*ARGS, t=-1.0)

    def test_truncamiento_demasiado_grande(self):
        # colas de unos 2 000 clientes: el truncamiento necesario (q₁·(q₂+1)²) supera la cota de memoria
        with pytest.raises(ValueError, match="truncamiento"):
            wl.erlang_a_priority(1000.0, 1002.0, 1.0, 1.0, 1.0, 2)

    def test_demasiadas_iteraciones_de_uniformizacion(self):
        with pytest.raises(ValueError, match="iteraciones"):
            wl.erlang_a_priority_service_level(1.5, 2.5, 1.0, 0.8, 0.3, 4, t=1e7)

    def test_resultado(self):
        r = wl.erlang_a_priority(*ARGS)
        assert isinstance(r, wl.ErlangAPriorityResult) and r.servers == 4
        assert "prioridad" in r.summary() and "P(abandono)" in r.summary() and str(r) == r.summary()
        fila = r.to_frame()
        assert list(fila.columns)[:5] == ["id_clase", "λ", "θ", "P(abandono)", "λ_eff"] and len(fila) == 2

    def test_etiquetas_en_ingles(self):
        wl.set_language("en")
        try:
            r = wl.erlang_a_priority(*ARGS)
            texto, columnas = r.summary(), list(r.to_frame().columns)
        finally:
            wl.set_language("es")
        assert "non-preemptive" in texto and "P(abandonment)" in columnas
