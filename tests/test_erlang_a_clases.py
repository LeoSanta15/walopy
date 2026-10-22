"""Erlang A con K clases y prioridad no expropiativa (0.4.12).

Oráculos independientes de la implementación (reducción por niveles con GTH y malla de fases): la cadena completa resuelta con álgebra lineal para
K = 3 y 4, el caso de dos clases (``erlang_a_priority``), paciencias iguales (la cola total es la de ``erlang_a``), límites con una clase casi sin
llegadas, la exponencial de la matriz de la cadena de espera de las clases de menor prioridad y una simulación de eventos con K clases.
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
from walopy.advanced import _estacionaria_clases, _estacionaria_clases_truncada, _nivel_servicio_clase

LAM, TH, MU, C = [0.7, 1.1, 1.6], [0.9, 0.5, 0.25], 1.0, 4


def _cadena_completa(lams, ths, mu, c, s_max, q_bajo):
    """p·Q = 0 de la cadena (b < c) ∪ (q₀, …, q_{K−1}) con q₀ + … + q_{K−2} ≤ s_max y q_{K−1} ≤ q_bajo, con álgebra lineal (sin GTH, sin niveles ni corte de flujo)."""
    k_clases, cmu = len(lams), c * mu
    estados = [q for q in itertools.product(*([range(s_max + 1)] * (k_clases - 1) + [range(q_bajo + 1)])) if sum(q[:-1]) <= s_max]
    idx = {}
    for b in range(c):
        idx[("b", b)] = len(idx)
    for q in estados:
        idx[q] = len(idx)
    n = len(idx)
    Q = np.zeros((n, n))

    def add(s, t, r):
        if r > 0:
            Q[idx[s], idx[t]] += r

    lam = sum(lams)
    for b in range(c):
        add(("b", b), ("b", b + 1) if b < c - 1 else tuple([0] * k_clases), lam)
        if b > 0:
            add(("b", b), ("b", b - 1), b * mu)
    for q in estados:
        for i in range(k_clases):
            sube = q[:i] + (q[i] + 1,) + q[i + 1:]
            if sube in idx:                                    # fuera del símplex o de q_bajo, la llegada se bloquea
                add(q, sube, lams[i])
            if q[i] > 0:
                add(q, q[:i] + (q[i] - 1,) + q[i + 1:], ths[i] * q[i])
        primera = next((i for i in range(k_clases) if q[i] > 0), None)
        if primera is None:
            add(q, ("b", c - 1), cmu)
        else:
            add(q, q[:primera] + (q[primera] - 1,) + q[primera + 1:], cmu)
    np.fill_diagonal(Q, -Q.sum(axis=1))
    A = np.vstack([Q.T, np.ones(n)])
    b = np.zeros(n + 1)
    b[-1] = 1.0
    pi = np.linalg.lstsq(A, b, rcond=None)[0]
    niv = np.zeros((s_max + 1,) * (k_clases - 1) + (q_bajo + 1,))
    for q in estados:
        niv[q] = pi[idx[q]]
    return pi[:c], niv


def _lq(niv, k):
    eje = tuple(i for i in range(niv.ndim) if i != k)
    return float((np.arange(niv.shape[k]) * niv.sum(axis=eje)).sum())


class TestContraLaCadenaCompleta:
    @pytest.mark.parametrize("lams,ths,c,s_max,q_bajo", [
        ([0.8, 1.2, 1.5], [0.9, 0.5, 0.25], 3, 5, 8),
        ([2.0, 3.0, 4.0], [0.4, 0.3, 0.2], 3, 6, 10),                       # sobrecarga
        ([0.5, 0.7, 0.9, 1.4], [1.0, 0.7, 0.4, 0.2], 3, 4, 6),               # cuatro clases
        ([0.3, 0.4, 0.5], [0.6, 0.6, 0.6], 1, 4, 6),                         # un servidor
        ([0.4, 0.5], [0.7, 0.3], 2, 6, 9),                                   # dos clases
    ])
    def test_la_reduccion_por_niveles_coincide_con_el_sistema_lineal(self, lams, ths, c, s_max, q_bajo):
        pb, niv = _estacionaria_clases_truncada(lams, ths, 1.0, c, s_max, q_bajo)
        pb2, niv2 = _cadena_completa(lams, ths, 1.0, c, s_max, q_bajo)
        assert np.abs(pb - pb2).max() < 1e-12 and np.abs(niv - niv2).max() < 1e-12

    def test_el_truncamiento_adaptativo_es_lo_bastante_amplio(self):
        """Los indicadores públicos coinciden con los de una malla mucho mayor (la masa fuera del truncamiento es despreciable)."""
        _, grande = _estacionaria_clases_truncada(LAM, TH, MU, C, 18, 40)
        r = wl.erlang_a_classes(LAM, MU, TH, C)
        for k, cl in enumerate(r.classes):
            assert cl["Lq"] == pytest.approx(_lq(grande, k), rel=1e-7)
            assert cl["p_abandon"] == pytest.approx(TH[k] * _lq(grande, k) / LAM[k], rel=1e-7)
        assert r.p_wait == pytest.approx(float(grande.sum()), rel=1e-7)

    def test_la_distribucion_suma_uno_y_es_no_negativa(self):
        pb, niv = _estacionaria_clases(LAM, TH, MU, C)
        assert pb.sum() + niv.sum() == pytest.approx(1.0, abs=1e-12)
        assert pb.min() >= 0.0 and niv.min() >= 0.0


class TestRelacionesExactas:
    def test_con_dos_clases_coincide_con_erlang_a_priority(self):
        a = wl.erlang_a_classes([1.5, 2.5], 1.0, [0.8, 0.3], 4)
        b = wl.erlang_a_priority(1.5, 2.5, 1.0, 0.8, 0.3, 4)
        for x, y in zip(a.classes, b.classes):
            for clave in ("lam", "theta", "p_abandon", "lam_eff", "Lq", "Wq"):
                assert x[clave] == pytest.approx(y[clave], rel=1e-12)
        assert a.p_wait == pytest.approx(b.p_wait, rel=1e-12) and a.rho == pytest.approx(b.rho, rel=1e-12)
        assert wl.erlang_a_classes_service_level([1.5, 2.5], 1.0, [0.8, 0.3], 4, t=0.7) == pytest.approx(
            wl.erlang_a_priority_service_level(1.5, 2.5, 1.0, 0.8, 0.3, 4, t=0.7), rel=1e-12)

    @pytest.mark.parametrize("n_clases", [2, 3, 4])
    def test_con_pacientes_iguales_la_cola_total_es_erlang_a(self, n_clases):
        lams = [0.3, 0.4, 0.5, 0.6][:n_clases]
        th = 0.45
        r = wl.erlang_a_classes(lams, 1.0, [th] * n_clases, 4)
        ref = wl.erlang_a(sum(lams), 1.0, th, 4)
        assert sum(x["Lq"] for x in r.classes) == pytest.approx(ref.Lq, rel=1e-8)
        assert r.p_wait == pytest.approx(ref.params["P(esperar)"], rel=1e-8)
        assert r.params["P(abandono) total"] == pytest.approx(ref.params["P(abandono)"], rel=1e-8)
        assert r.rho == pytest.approx(ref.rho, rel=1e-8)

    def test_una_clase_casi_sin_llegadas_no_cambia_a_las_demas(self):
        base = wl.erlang_a_classes([1.5, 2.5], 1.0, [0.8, 0.3], 4)
        for pos in (0, 1, 2):
            lam = [1.5, 2.5]
            th = [0.8, 0.3]
            lam.insert(pos, 1e-9)
            th.insert(pos, 0.5)
            r = wl.erlang_a_classes(lam, 1.0, th, 4)
            otras = [x for x in r.classes if x["class_id"] != pos]
            for x, y in zip(otras, base.classes):
                assert x["p_abandon"] == pytest.approx(y["p_abandon"], rel=1e-6)
                assert x["Wq"] == pytest.approx(y["Wq"], rel=1e-6)

    def test_la_prioridad_ordena_las_esperas_y_el_abandono(self):
        r = wl.erlang_a_classes([0.3, 0.4, 0.5, 0.6], 1.0, [0.45] * 4, 4)
        wq = [x["Wq"] for x in r.classes]
        pab = [x["p_abandon"] for x in r.classes]
        assert wq == sorted(wq) and pab == sorted(pab) and wq[0] < wq[-1]

    def test_con_pacientes_iguales_el_abandono_total_no_depende_del_orden(self):
        a = wl.erlang_a_classes([1.0, 2.0, 3.0], 1.0, [0.4] * 3, 4)
        b = wl.erlang_a_classes([3.0, 1.0, 2.0], 1.0, [0.4] * 3, 4)
        assert a.params["P(abandono) total"] == pytest.approx(b.params["P(abandono) total"], rel=1e-9)

    def test_identidad_de_flujo_servicio_igual_a_lo_atendido(self):
        r = wl.erlang_a_classes(LAM, MU, TH, C)
        pb, niv = _estacionaria_clases(LAM, TH, MU, C)
        ocupados = float((np.arange(C) * pb).sum()) + C * float(niv.sum())
        assert sum(x["lam_eff"] for x in r.classes) == pytest.approx(MU * ocupados, rel=1e-9)

    def test_sobrecarga_estable(self):
        r = wl.erlang_a_classes([1.5, 2.0, 2.5], 1.0, [0.8, 0.5, 0.4], 3)           # Σλ = 2·c·μ
        assert sum(x["lam_eff"] for x in r.classes) == pytest.approx(3.0, rel=0.05) and r.rho > 0.95


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


def _nivel_por_matriz(lams, ths, mu, c, k, t, niv, libre):
    """P(atendido en ≤ t) de la clase k ≥ 1 con la cadena (a₀ … a_{k−1}, m) como generador explícito y la acción de su exponencial."""
    marg = niv.sum(axis=tuple(range(k + 1, niv.ndim))) if k + 1 < niv.ndim else niv
    forma = marg.shape
    cmu = c * mu
    estados = {e: i for i, e in enumerate(np.ndindex(*forma))}
    n = len(estados) + 1                                  # último: «atendido» (absorbente)
    G = np.zeros((n, n))
    for e, i in estados.items():
        a, m_idx = e[:k], e[k]
        for j in range(k):
            if a[j] < forma[j] - 1:
                G[i, estados[e[:j] + (a[j] + 1,) + e[j + 1:]]] += lams[j]
            if a[j] > 0:
                G[i, estados[e[:j] + (a[j] - 1,) + e[j + 1:]]] += ths[j] * a[j]
        primera = next((j for j in range(k) if a[j] > 0), None)
        if primera is not None:
            G[i, estados[e[:primera] + (a[primera] - 1,) + e[primera + 1:]]] += cmu
        else:
            G[i, n - 1 if m_idx == 0 else estados[e[:k] + (m_idx - 1,)]] += cmu
        if m_idx > 0:
            G[i, estados[e[:k] + (m_idx - 1,)]] += ths[k] * m_idx          # abandona uno de la clase k por delante
        G[i, i] -= G[i].sum() + ths[k]                                      # + abandono propio (se pierde)
    absorbente = np.zeros(n)
    absorbente[n - 1] = 1.0
    servido = _accion_de_la_exponencial(G, t, absorbente)
    return libre + sum(marg[e] * servido[i] for e, i in estados.items())


class TestNivelDeServicio:
    def test_t_cero_es_la_fraccion_que_no_espera(self):
        pb, _ = _estacionaria_clases(LAM, TH, MU, C)
        niveles = wl.erlang_a_classes_service_level(LAM, MU, TH, C, t=0.0)
        assert len(niveles) == 3 and all(x == pytest.approx(float(pb.sum()), rel=1e-12) for x in niveles)

    @pytest.mark.parametrize("lam,th", [(LAM, TH), ([0.3, 0.4, 0.5, 0.6], [1.0, 0.7, 0.4, 0.3])])
    def test_t_grande_es_uno_menos_abandono_de_cada_clase(self, lam, th):
        r = wl.erlang_a_classes(lam, MU, th, C)
        niveles = wl.erlang_a_classes_service_level(lam, MU, th, C, t=60.0)
        for x, cl in zip(niveles, r.classes):
            assert x == pytest.approx(1 - cl["p_abandon"], abs=1e-9)

    def test_creciente_en_t_y_decreciente_con_la_prioridad_con_pacientes_iguales(self):
        v = [wl.erlang_a_classes_service_level([0.7, 1.1, 1.6], 1.0, [0.4] * 3, 4, t=t) for t in (0.0, 0.3, 1.0, 3.0, 9.0)]
        for k in range(3):
            col = [x[k] for x in v]
            assert col == sorted(col)
        assert all(x[0] >= x[1] >= x[2] for x in v)

    def test_la_clase_alta_es_el_nivel_de_erlang_a_si_las_demas_casi_no_llegan(self):
        for t in (0.0, 0.5, 2.0):
            alta = wl.erlang_a_classes_service_level([3.0, 1e-9, 1e-9], 1.0, [0.6, 0.4, 0.4], 4, t=t)[0]
            assert alta == pytest.approx(wl.erlang_a_service_level(3.0, 1.0, 0.6, 4, t), abs=1e-6)

    @pytest.mark.parametrize("lam,th,c,t,k,s_max,q_bajo", [
        ([1.5, 2.5, 1.2], [0.8, 0.3, 0.5], 3, 0.7, 1, 4, 6),
        ([1.5, 2.5, 1.2], [0.8, 0.3, 0.5], 3, 0.7, 2, 4, 6),
        ([0.8, 1.2, 1.0], [0.5, 0.6, 0.4], 2, 1.5, 2, 5, 7),
        ([0.6, 0.5, 0.4, 0.7], [0.9, 0.5, 0.7, 0.3], 3, 0.8, 3, 3, 4),
        ([0.6, 0.5, 0.4, 0.7], [0.9, 0.5, 0.7, 0.3], 3, 0.8, 2, 3, 4),
    ])
    def test_clases_bajas_contra_la_exponencial_de_la_matriz(self, lam, th, c, t, k, s_max, q_bajo):
        pb, niv = _estacionaria_clases_truncada(lam, th, 1.0, c, s_max, q_bajo)          # misma malla en los dos lados
        esperado = _nivel_por_matriz(lam, th, 1.0, c, k, t, niv, float(pb.sum()))
        assert _nivel_servicio_clase(niv, pb, lam, th, 1.0, c, k, t) == pytest.approx(esperado, abs=1e-8)


def _simular(lams, ths, mu, c, n, semilla, t_sl, calentamiento=3000):
    """Simulación de eventos: cada cliente abandona a su tasa; al liberarse un servidor se atiende a la primera clase con cola (FIFO dentro de la clase)."""
    k_clases, rng = len(lams), random.Random(semilla)
    lam = sum(lams)
    acum = [sum(lams[:i + 1]) / lam for i in range(k_clases)]
    ev = [(rng.expovariate(lam), 0, None)]
    ocupados = llegadas = sig = 0
    colas = [collections.deque() for _ in range(k_clases)]
    estado = {}
    est = [{"n": 0, "aband": 0, "esp": 0.0, "sl": 0, "espera_pos": 0} for _ in range(k_clases)]
    while ev and llegadas < n + calentamiento:
        t, tipo, d = heapq.heappop(ev)
        if tipo == 0:
            llegadas += 1
            u = rng.random()
            clase = next(i for i in range(k_clases) if u < acum[i] or i == k_clases - 1)
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
                heapq.heappush(ev, (t + rng.expovariate(ths[clase]), 2, cid))
        elif tipo == 1:
            ocupados -= 1
            for k in range(k_clases):
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


def test_tres_clases_coinciden_con_simulacion_de_eventos():
    t_sl = 0.6
    r = wl.erlang_a_classes(LAM, MU, TH, C)
    niveles = wl.erlang_a_classes_service_level(LAM, MU, TH, C, t=t_sl)
    reps = [_simular(LAM, TH, MU, C, 25_000, s, t_sl) for s in range(10)]
    ref = {"pw": r.p_wait}
    sim = {"pw": [sum(x[k]["espera_pos"] for k in range(3)) / sum(x[k]["n"] for k in range(3)) for x in reps]}
    for k in range(3):
        ref[f"pab{k}"], ref[f"wq{k}"], ref[f"sl{k}"] = r.classes[k]["p_abandon"], r.classes[k]["Wq"], niveles[k]
        sim[f"pab{k}"] = [x[k]["aband"] / x[k]["n"] for x in reps]
        sim[f"wq{k}"] = [x[k]["esp"] / x[k]["n"] for x in reps]
        sim[f"sl{k}"] = [x[k]["sl"] / x[k]["n"] for x in reps]
    for clave, v in ref.items():
        se = statistics.stdev(sim[clave]) / len(sim[clave]) ** 0.5
        assert abs(statistics.mean(sim[clave]) - v) < 4.0 * se, (clave, statistics.mean(sim[clave]), v, se)


class TestEntradasYSalida:
    BASE = dict(lam=[0.7, 1.1, 1.6], mu=1.0, theta=[0.9, 0.5, 0.25], c=4)

    @pytest.mark.parametrize("kw", [
        dict(lam=[0.7]), dict(lam=[0.7, 1.1], theta=[0.9, 0.5, 0.25]), dict(theta=[0.9, 0.5]),
        dict(lam=[0.7, 0.0, 1.6]), dict(lam=[0.7, -1.0, 1.6]), dict(theta=[0.9, float("nan"), 0.25]), dict(theta=[0.9, 0.0, 0.25]),
        dict(lam=[0.7, float("inf"), 1.6]), dict(mu=0.0), dict(c=0), dict(lam=[1.0] * 7, theta=[1.0] * 7),
    ])
    def test_rechaza_valores_invalidos(self, kw):
        with pytest.raises(ValueError):
            wl.erlang_a_classes(**{**self.BASE, **kw})

    def test_tipos_invalidos(self):
        with pytest.raises(TypeError):
            wl.erlang_a_classes(lam=["a", "b"], mu=1.0, theta=[0.5, 0.5], c=2)
        with pytest.raises(TypeError):
            wl.erlang_a_classes(lam=5, mu=1.0, theta=[0.5, 0.5], c=2)

    def test_t_negativo(self):
        with pytest.raises(ValueError):
            wl.erlang_a_classes_service_level(**self.BASE, t=-1.0)

    def test_colas_largas_superan_la_cota_de_calculo(self, monkeypatch):
        # con una cota de cálculo baja se rechaza de inmediato (con la real puede tardar ~15 s en rendirse)
        monkeypatch.setattr("walopy.advanced.MAX_COSTE_CLASES", 10**6)
        with pytest.raises(ValueError, match="truncamiento"):
            wl.erlang_a_classes([6.0] * 4, 1.0, [0.05] * 4, 3)

    def test_demasiadas_iteraciones_en_el_nivel_de_servicio(self):
        with pytest.raises(ValueError, match="iteraciones"):
            wl.erlang_a_classes_service_level(self.BASE["lam"], 1.0, self.BASE["theta"], 4, t=1e6)

    def test_demasiado_calculo_en_el_nivel_de_servicio(self, monkeypatch):
        monkeypatch.setattr("walopy.advanced.MAX_CELDAS_PASOS", 1000)
        with pytest.raises(ValueError, match="cálculo"):
            wl.erlang_a_classes_service_level(self.BASE["lam"], 1.0, self.BASE["theta"], 4, t=0.6)

    def test_resultado(self):
        r = wl.erlang_a_classes(**self.BASE)
        assert isinstance(r, wl.ErlangAClassesResult) and r.servers == 4 and len(r.classes) == 3
        assert "3 clases" in r.summary() and "P(abandono)" in r.summary() and str(r) == r.summary()
        fila = r.to_frame()
        assert list(fila.columns)[:6] == ["id_clase", "λ", "μ", "θ", "P(abandono)", "λ_eff"] and len(fila) == 3

    def test_etiquetas_en_ingles(self):
        wl.set_language("en")
        try:
            r = wl.erlang_a_classes(**self.BASE)
            texto, columnas = r.summary(), list(r.to_frame().columns)
        finally:
            wl.set_language("es")
        assert "3 classes" in texto and "P(abandonment)" in columnas
