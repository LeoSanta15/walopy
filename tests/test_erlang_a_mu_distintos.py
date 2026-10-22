"""Erlang A con dos clases, prioridad y tiempos de servicio distintos por clase (0.4.13).

Oráculos independientes de la implementación (reducción por niveles con GTH y la región libre dentro del nivel 0): la cadena completa resuelta con
álgebra lineal; el caso μ₁ = μ₂ (debe dar lo de ``erlang_a_priority``); la identidad E[nₖ] = λ_eff,k/μₖ (servidores ocupados por cada clase); los límites con
una clase casi sin llegadas (la otra es ``erlang_a`` con su propio μ); la exponencial de la matriz de las cadenas de espera; y una simulación de eventos.
"""
import collections
import heapq
import itertools
import math
import random
import statistics

import numpy as np
import pytest

import walopy as wl
from walopy.advanced import (
    _estacionaria_mu_distintos,
    _estacionaria_mu_distintos_truncada,
    _estacionaria_prioridad,
    _nivel_servicio_clase,
    _nivel_servicio_mu_distintos,
)

ARGS = (1.0, 2.5, 2.0, 0.7, 0.6, 0.3, 4)         # lam1, lam2, mu1, mu2, th1, th2, c


def _cadena_completa(lam1, lam2, mu1, mu2, th1, th2, c, Q1, Q2):
    """p·Q = 0 de la cadena completa con álgebra lineal: región libre (n₁, n₂), n₁ + n₂ < c, y (n₁, q₁, q₂) con los c servidores ocupados."""
    idx = {}
    for a in range(c):
        for b in range(c - a):
            idx[("F", a, b)] = len(idx)
    for n1, q1, q2 in itertools.product(range(c + 1), range(Q1 + 1), range(Q2 + 1)):
        idx[("L", n1, q1, q2)] = len(idx)
    n = len(idx)
    Q = np.zeros((n, n))

    def add(s, t, r):
        if r > 0:
            Q[idx[s], idx[t]] += r

    for a in range(c):
        for b in range(c - a):
            s = ("F", a, b)
            if a + b + 1 <= c - 1:
                add(s, ("F", a + 1, b), lam1)
                add(s, ("F", a, b + 1), lam2)
            else:
                add(s, ("L", a + 1, 0, 0), lam1)
                add(s, ("L", a, 0, 0), lam2)
            if a > 0:
                add(s, ("F", a - 1, b), a * mu1)
            if b > 0:
                add(s, ("F", a, b - 1), b * mu2)
    for n1, q1, q2 in itertools.product(range(c + 1), range(Q1 + 1), range(Q2 + 1)):
        n2 = c - n1
        s = ("L", n1, q1, q2)
        if q1 < Q1:
            add(s, ("L", n1, q1 + 1, q2), lam1)
        if q2 < Q2:
            add(s, ("L", n1, q1, q2 + 1), lam2)
        if q1 > 0:
            add(s, ("L", n1, q1 - 1, q2), th1 * q1)
        if q2 > 0:
            add(s, ("L", n1, q1, q2 - 1), th2 * q2)
        if n1 > 0:                                             # termina uno de alta
            if q1 > 0:
                add(s, ("L", n1, q1 - 1, q2), n1 * mu1)
            elif q2 > 0:
                add(s, ("L", n1 - 1, 0, q2 - 1), n1 * mu1)
            else:
                add(s, ("F", n1 - 1, n2), n1 * mu1)
        if n2 > 0:                                             # termina uno de baja
            if q1 > 0:
                add(s, ("L", n1 + 1, q1 - 1, q2), n2 * mu2)
            elif q2 > 0:
                add(s, ("L", n1, 0, q2 - 1), n2 * mu2)
            else:
                add(s, ("F", n1, n2 - 1), n2 * mu2)
    np.fill_diagonal(Q, -Q.sum(axis=1))
    A = np.vstack([Q.T, np.ones(n)])
    b = np.zeros(n + 1)
    b[-1] = 1.0
    pi = np.linalg.lstsq(A, b, rcond=None)[0]
    pF = np.zeros((c + 1, c + 1))
    niv = np.zeros((c + 1, Q1 + 1, Q2 + 1))
    for clave, i in idx.items():
        if clave[0] == "F":
            pF[clave[1], clave[2]] = pi[i]
        else:
            niv[clave[1], clave[2], clave[3]] = pi[i]
    return pF, niv


def _lq(niv):
    return float((np.arange(niv.shape[1]) * niv.sum(axis=(0, 2))).sum()), float((np.arange(niv.shape[2]) * niv.sum(axis=(0, 1))).sum())


class TestContraLaCadenaCompleta:
    @pytest.mark.parametrize("args,Q1,Q2", [
        ((1.2, 2.0, 1.0, 0.6, 0.8, 0.3, 3), 4, 6),
        ((0.5, 0.7, 2.0, 0.5, 0.9, 0.4, 2), 4, 6),
        ((1.0, 1.5, 0.7, 1.3, 0.5, 0.5, 1), 4, 6),                 # un servidor
        ((2.0, 3.0, 1.0, 2.0, 0.4, 0.3, 4), 3, 5),                 # sobrecarga
        ((0.3, 0.4, 3.0, 0.2, 0.5, 0.2, 5), 3, 4),                 # μ muy distintos
    ])
    def test_la_reduccion_por_niveles_coincide_con_el_sistema_lineal(self, args, Q1, Q2):
        pF, niv = _estacionaria_mu_distintos_truncada(*args, Q1, Q2)
        pF2, niv2 = _cadena_completa(*args, Q1, Q2)
        assert np.abs(pF - pF2).max() < 1e-12 and np.abs(niv - niv2).max() < 1e-12

    def test_la_distribucion_suma_uno_y_es_no_negativa(self):
        pF, niv = _estacionaria_mu_distintos(*ARGS)
        assert pF.sum() + niv.sum() == pytest.approx(1.0, abs=1e-12)
        assert pF.min() >= 0.0 and niv.min() >= 0.0
        assert np.all(pF[np.add.outer(np.arange(5), np.arange(5)) > 3] == 0.0)        # n₁ + n₂ ≤ c − 1 en la región libre

    def test_el_truncamiento_adaptativo_es_lo_bastante_amplio(self):
        _, grande = _estacionaria_mu_distintos_truncada(*ARGS, 24, 70)
        r = wl.erlang_a_classes([1.0, 2.5], [2.0, 0.7], [0.6, 0.3], 4)
        eq1, eq2 = _lq(grande)
        assert r.classes[0]["Lq"] == pytest.approx(eq1, rel=1e-7) and r.classes[1]["Lq"] == pytest.approx(eq2, rel=1e-7)
        assert r.p_wait == pytest.approx(float(grande.sum()), rel=1e-7)


class TestRelacionesExactas:
    def test_con_mu_iguales_da_lo_de_erlang_a_priority(self):
        lam1, lam2, mu, th1, th2, c = 1.5, 2.5, 1.0, 0.8, 0.3, 4
        pF, niv = _estacionaria_mu_distintos(lam1, lam2, mu, mu, th1, th2, c)
        pb, niv2 = _estacionaria_prioridad(lam1, lam2, mu, th1, th2, c)
        eq1, eq2 = _lq(niv)
        ref = wl.erlang_a_priority(lam1, lam2, mu, th1, th2, c)
        assert eq1 == pytest.approx(ref.classes[0]["Lq"], rel=1e-8) and eq2 == pytest.approx(ref.classes[1]["Lq"], rel=1e-8)
        assert float(niv.sum()) == pytest.approx(ref.p_wait, rel=1e-8)
        assert float(pF.sum()) == pytest.approx(float(pb.sum()), rel=1e-8)
        for k in (0, 1):
            esperado = _nivel_servicio_clase(niv2, pb, [lam1, lam2], [th1, th2], mu, c, k, 0.7)
            assert _nivel_servicio_mu_distintos(pF, niv, lam1, mu, mu, th1, th2, c, k, 0.7) == pytest.approx(esperado, abs=1e-8)

    @pytest.mark.parametrize("args", [ARGS, (0.6, 1.4, 0.5, 1.5, 0.8, 0.2, 3), (3.0, 4.0, 1.0, 2.0, 0.5, 0.4, 6)])
    def test_servidores_ocupados_por_cada_clase_son_lambda_efectiva_sobre_mu(self, args):
        """E[nₖ] = λ_eff,k / μₖ (ley de Little del servicio de cada clase): lo que ocupa cada clase es lo que se le atiende."""
        lam1, lam2, mu1, mu2, th1, th2, c = args
        pF, niv = _estacionaria_mu_distintos(*args)
        r = wl.erlang_a_classes([lam1, lam2], [mu1, mu2], [th1, th2], c)
        en1 = float((np.arange(c + 1)[:, None] * pF).sum() + (np.arange(c + 1)[:, None, None] * niv).sum())
        en2 = float((np.arange(c + 1)[None, :] * pF).sum() + ((c - np.arange(c + 1))[:, None, None] * niv).sum())
        assert en1 == pytest.approx(r.classes[0]["lam_eff"] / mu1, rel=1e-8)
        assert en2 == pytest.approx(r.classes[1]["lam_eff"] / mu2, rel=1e-8)
        assert r.rho == pytest.approx((en1 + en2) / c, rel=1e-8)

    def test_sin_clase_baja_la_alta_es_erlang_a_con_su_mu(self):
        ref = wl.erlang_a(3.0, 1.5, 0.6, 4)
        r = wl.erlang_a_classes([3.0, 1e-9], [1.5, 0.4], [0.6, 0.4], 4)
        assert r.classes[0]["p_abandon"] == pytest.approx(ref.params["P(abandono)"], rel=1e-6)
        assert r.classes[0]["Wq"] == pytest.approx(ref.Wq, rel=1e-6)

    def test_sin_clase_alta_la_baja_es_erlang_a_con_su_mu(self):
        ref = wl.erlang_a(3.0, 0.8, 0.4, 4)
        r = wl.erlang_a_classes([1e-9, 3.0], [2.5, 0.8], [0.9, 0.4], 4)
        assert r.classes[1]["p_abandon"] == pytest.approx(ref.params["P(abandono)"], rel=1e-6)
        assert r.classes[1]["Wq"] == pytest.approx(ref.Wq, rel=1e-6)
        for t in (0.0, 0.5, 2.0):
            nivel = wl.erlang_a_classes_service_level([1e-9, 3.0], [2.5, 0.8], [0.9, 0.4], 4, t=t)[1]
            assert nivel == pytest.approx(wl.erlang_a_service_level(3.0, 0.8, 0.4, 4, t), abs=1e-6)

    def test_servir_mas_rapido_a_la_clase_alta_baja_su_espera_y_su_abandono(self):
        base = wl.erlang_a_classes([1.0, 2.5], [1.0, 0.7], [0.6, 0.3], 4)
        rapida = wl.erlang_a_classes([1.0, 2.5], [2.0, 0.7], [0.6, 0.3], 4)
        assert rapida.classes[0]["Wq"] < base.classes[0]["Wq"] and rapida.classes[0]["p_abandon"] < base.classes[0]["p_abandon"]
        assert rapida.classes[1]["Wq"] < base.classes[1]["Wq"]               # y se libera capacidad para la baja

    def test_una_lista_de_mu_iguales_es_lo_mismo_que_un_numero(self):
        a = wl.erlang_a_classes([1.5, 2.5], 1.0, [0.8, 0.3], 4)
        b = wl.erlang_a_classes([1.5, 2.5], [1.0, 1.0], [0.8, 0.3], 4)
        assert a.mu == 1.0 and b.mu == 1.0
        for x, y in zip(a.classes, b.classes):
            assert x["p_abandon"] == y["p_abandon"] and x["Wq"] == y["Wq"]


def _accion_de_la_exponencial(M, t, v):
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


def _nivel_por_matriz(lam1, mu1, mu2, th1, th2, c, clase, t, pF, niv):
    """P(atendido en ≤ t) con la cadena de espera como generador explícito (transiciones escritas una a una) y la acción de su exponencial."""
    libre = float(pF.sum())
    if clase == 0:
        marg = niv.sum(axis=2)                                          # P(n₁, q₁)
    else:
        marg = niv
    forma = marg.shape
    estados = {e: i for i, e in enumerate(np.ndindex(*forma))}
    n = len(estados) + 1                                                # último: «atendido»
    G = np.zeros((n, n))
    for e, i in estados.items():
        n1 = e[0]
        n2 = c - n1
        if clase == 0:
            m_idx = e[1]                                                # posición m = m_idx + 1 entre los de alta
            siguiente = n - 1 if m_idx == 0 else None
            if n1 > 0:
                G[i, siguiente if siguiente is not None else estados[(n1, m_idx - 1)]] += n1 * mu1
            if n2 > 0:
                G[i, siguiente if siguiente is not None else estados[(n1 + 1, m_idx - 1)]] += n2 * mu2
            if m_idx > 0:
                G[i, estados[(n1, m_idx - 1)]] += th1 * m_idx
            G[i, i] -= G[i].sum() + th1
        else:
            a, m_idx = e[1], e[2]
            if a < forma[1] - 1:
                G[i, estados[(n1, a + 1, m_idx)]] += lam1
            if a > 0:
                G[i, estados[(n1, a - 1, m_idx)]] += th1 * a
            if n1 > 0:                                                   # termina uno de alta
                if a > 0:
                    G[i, estados[(n1, a - 1, m_idx)]] += n1 * mu1
                else:
                    G[i, n - 1 if m_idx == 0 else estados[(n1 - 1, 0, m_idx - 1)]] += n1 * mu1
            if n2 > 0:                                                   # termina uno de baja
                if a > 0:
                    G[i, estados[(n1 + 1, a - 1, m_idx)]] += n2 * mu2
                else:
                    G[i, n - 1 if m_idx == 0 else estados[(n1, 0, m_idx - 1)]] += n2 * mu2
            if m_idx > 0:
                G[i, estados[(n1, a, m_idx - 1)]] += th2 * m_idx
            G[i, i] -= G[i].sum() + th2
    absorbente = np.zeros(n)
    absorbente[n - 1] = 1.0
    servido = _accion_de_la_exponencial(G, t, absorbente)
    return libre + sum(marg[e] * servido[i] for e, i in estados.items())


class TestNivelDeServicio:
    def test_t_cero_es_la_fraccion_que_no_espera(self):
        pF, _ = _estacionaria_mu_distintos(*ARGS)
        niveles = wl.erlang_a_classes_service_level([1.0, 2.5], [2.0, 0.7], [0.6, 0.3], 4, t=0.0)
        assert niveles == pytest.approx((float(pF.sum()),) * 2, rel=1e-12)

    def test_t_grande_es_uno_menos_abandono_de_cada_clase(self):
        r = wl.erlang_a_classes([1.0, 2.5], [2.0, 0.7], [0.6, 0.3], 4)
        niveles = wl.erlang_a_classes_service_level([1.0, 2.5], [2.0, 0.7], [0.6, 0.3], 4, t=60.0)
        for x, cl in zip(niveles, r.classes):
            assert x == pytest.approx(1 - cl["p_abandon"], abs=1e-9)

    def test_creciente_en_t(self):
        v = [wl.erlang_a_classes_service_level([1.0, 2.5], [2.0, 0.7], [0.6, 0.3], 4, t=t) for t in (0.0, 0.2, 0.7, 2.0, 8.0)]
        for k in (0, 1):
            col = [x[k] for x in v]
            assert col == sorted(col)

    @pytest.mark.parametrize("args,Q1,Q2,t", [
        ((1.5, 2.5, 1.0, 0.5, 0.8, 0.3, 3), 4, 6, 0.7),
        ((0.8, 1.2, 2.0, 0.6, 0.5, 0.6, 2), 4, 6, 1.5),
        ((1.0, 1.5, 0.6, 1.4, 0.4, 0.5, 3), 3, 5, 0.9),
    ])
    @pytest.mark.parametrize("clase", [0, 1])
    def test_contra_la_exponencial_de_la_matriz(self, args, Q1, Q2, t, clase):
        pF, niv = _estacionaria_mu_distintos_truncada(*args, Q1, Q2)                  # misma malla en los dos lados
        lam1, lam2, mu1, mu2, th1, th2, c = args
        esperado = _nivel_por_matriz(lam1, mu1, mu2, th1, th2, c, clase, t, pF, niv)
        assert _nivel_servicio_mu_distintos(pF, niv, lam1, mu1, mu2, th1, th2, c, clase, t) == pytest.approx(esperado, abs=1e-8)


def _simular(lam1, lam2, mu1, mu2, th1, th2, c, n, semilla, t_sl, calentamiento=3000):
    """Simulación de eventos: servicio exponencial con la tasa de la clase; al liberarse un servidor entra el primero de la clase alta con cola, y si no el de la baja."""
    rng = random.Random(semilla)
    lam = lam1 + lam2
    mus, ths = (mu1, mu2), (th1, th2)
    ev = [(rng.expovariate(lam), 0, None)]
    ocupados = [0, 0]
    llegadas = sig = 0
    colas = [collections.deque(), collections.deque()]
    estado = {}
    est = [{"n": 0, "aband": 0, "esp": 0.0, "espera_pos": 0, "sl": 0} for _ in range(2)]

    def iniciar(cid, clase, t):
        ocupados[clase] += 1
        heapq.heappush(ev, (t + rng.expovariate(mus[clase]), 1, clase))

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
            if sum(ocupados) < c:
                iniciar(cid, clase, t)
                est[clase]["sl"] += medir
            else:
                colas[clase].append(cid)
                est[clase]["espera_pos"] += medir
                heapq.heappush(ev, (t + rng.expovariate(ths[clase]), 2, cid))
        elif tipo == 1:
            ocupados[d] -= 1
            for k in (0, 1):
                atendido = False
                while colas[k]:
                    cid = colas[k].popleft()
                    cl, ta, activo, medir = estado[cid]
                    if not activo:
                        continue
                    estado[cid][2] = False
                    iniciar(cid, cl, t)
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
    lam1, lam2, mu1, mu2, th1, th2, c = ARGS
    t_sl = 0.6
    r = wl.erlang_a_classes([lam1, lam2], [mu1, mu2], [th1, th2], c)
    niveles = wl.erlang_a_classes_service_level([lam1, lam2], [mu1, mu2], [th1, th2], c, t=t_sl)
    reps = [_simular(lam1, lam2, mu1, mu2, th1, th2, c, 25_000, s, t_sl) for s in range(10)]
    ref = {"pw": r.p_wait}
    sim = {"pw": [(x[0]["espera_pos"] + x[1]["espera_pos"]) / (x[0]["n"] + x[1]["n"]) for x in reps]}
    for k in (0, 1):
        ref[f"pab{k}"], ref[f"wq{k}"], ref[f"sl{k}"] = r.classes[k]["p_abandon"], r.classes[k]["Wq"], niveles[k]
        sim[f"pab{k}"] = [x[k]["aband"] / x[k]["n"] for x in reps]
        sim[f"wq{k}"] = [x[k]["esp"] / x[k]["n"] for x in reps]
        sim[f"sl{k}"] = [x[k]["sl"] / x[k]["n"] for x in reps]
    for clave, v in ref.items():
        se = statistics.stdev(sim[clave]) / len(sim[clave]) ** 0.5
        assert abs(statistics.mean(sim[clave]) - v) < 4.0 * se, (clave, statistics.mean(sim[clave]), v, se)


class TestEntradasYSalida:
    BASE = dict(lam=[1.0, 2.5], mu=[2.0, 0.7], theta=[0.6, 0.3], c=4)

    @pytest.mark.parametrize("kw", [
        dict(mu=[2.0]), dict(mu=[2.0, 0.7, 1.0]), dict(mu=[2.0, 0.0]), dict(mu=[2.0, -0.7]), dict(mu=[2.0, float("nan")]), dict(mu=[float("inf"), 0.7]),
        dict(mu=0.0),
    ])
    def test_rechaza_mu_invalidos(self, kw):
        with pytest.raises(ValueError):
            wl.erlang_a_classes(**{**self.BASE, **kw})

    @pytest.mark.parametrize("malo", ["abc", None, True, ["a", "b"]])
    def test_mu_no_numericos(self, malo):
        with pytest.raises(TypeError):
            wl.erlang_a_classes(**{**self.BASE, "mu": malo})

    def test_el_mensaje_de_tipo_dice_que_un_numero_tambien_vale(self):
        with pytest.raises(TypeError, match="número o una secuencia"):
            wl.erlang_a_classes(**{**self.BASE, "mu": "abc"})

    def test_mu_distintos_solo_con_dos_clases(self):
        with pytest.raises(ValueError, match="2 clases"):
            wl.erlang_a_classes([0.5, 0.5, 0.5], [1.0, 2.0, 1.0], [0.5] * 3, 4)
        wl.erlang_a_classes([0.5, 0.5, 0.5], [1.0, 1.0, 1.0], [0.5] * 3, 4)         # iguales: sí

    def test_el_nivel_de_servicio_tambien_valida_mu(self):
        with pytest.raises(ValueError):
            wl.erlang_a_classes_service_level([1.0, 2.5], [2.0], [0.6, 0.3], 4, t=0.5)

    def test_demasiado_calculo(self, monkeypatch):
        monkeypatch.setattr("walopy.advanced.MAX_COSTE_CLASES", 10**5)
        with pytest.raises(ValueError, match="truncamiento"):
            wl.erlang_a_classes(**self.BASE)

    def test_demasiadas_iteraciones_en_el_nivel_de_servicio(self):
        with pytest.raises(ValueError, match="iteraciones"):
            wl.erlang_a_classes_service_level(self.BASE["lam"], self.BASE["mu"], self.BASE["theta"], 4, t=1e6)

    def test_demasiado_calculo_en_el_nivel_de_servicio(self, monkeypatch):
        monkeypatch.setattr("walopy.advanced.MAX_CELDAS_PASOS", 1000)
        with pytest.raises(ValueError, match="cálculo"):
            wl.erlang_a_classes_service_level(self.BASE["lam"], self.BASE["mu"], self.BASE["theta"], 4, t=0.6)

    def test_resultado(self):
        r = wl.erlang_a_classes(**self.BASE)
        assert r.mu == (2.0, 0.7) and [x["mu"] for x in r.classes] == [2.0, 0.7]
        resumen = r.summary()
        assert "μ=(2, 0.7)" in resumen and "P(abandono)" in resumen
        assert list(r.to_frame().columns)[:6] == ["id_clase", "λ", "μ", "θ", "P(abandono)", "λ_eff"]
        assert r.rho == pytest.approx(sum(x["lam_eff"] / x["mu"] for x in r.classes) / 4, rel=1e-12)

    def test_con_mu_comun_el_resumen_no_cambia(self):
        r = wl.erlang_a_classes([0.7, 1.1, 1.6], 1.0, [0.9, 0.5, 0.25], 4)
        assert "μ=1," in r.summary() and r.mu == 1.0 and "  μ " not in r.summary().splitlines()[1]

    def test_etiquetas_en_ingles(self):
        wl.set_language("en")
        try:
            r = wl.erlang_a_classes(**self.BASE)
            texto, columnas = r.summary(), list(r.to_frame().columns)
        finally:
            wl.set_language("es")
        assert "2 classes" in texto and "P(abandonment)" in columnas
