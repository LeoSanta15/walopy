"""Erlang A (M/M/c+M): cola con abandono de clientes impacientes (0.4.9).

Oráculos independientes de la implementación (que usa recursiones en logaritmos): la solución directa de las ecuaciones de balance con
álgebra lineal, el caso θ = μ (equivale a M/M/∞, con estado Poisson), los límites θ → 0 (M/M/c) y θ → ∞ (Erlang B), una integración
numérica de las ecuaciones diferenciales de la espera y una simulación de eventos con intervalo de confianza.
"""
import heapq
import math
import random
import statistics

import numpy as np
import pytest

import walopy as wl


def _estacionaria_por_balance(lam, mu, theta, c, n_max):
    """Distribución estacionaria truncada en n_max resolviendo p·Q = 0 con Σp = 1 (sin usar la recursión de la librería)."""
    n = n_max + 1
    Q = np.zeros((n, n))
    for i in range(n):
        if i + 1 < n:
            Q[i, i + 1] = lam
        if i > 0:
            Q[i, i - 1] = i * mu if i <= c else c * mu + (i - c) * theta
        Q[i, i] = -Q[i].sum()
    A = np.vstack([Q.T, np.ones(n)])
    b = np.zeros(n + 1)
    b[-1] = 1.0
    return np.linalg.lstsq(A, b, rcond=None)[0]


def _indicadores_balance(lam, mu, theta, c, n_max=400):
    p = _estacionaria_por_balance(lam, mu, theta, c, n_max)
    n = np.arange(len(p))
    Lq = float((np.maximum(n - c, 0) * p).sum())
    ocupados = float((np.minimum(n, c) * p).sum())
    return {"Lq": Lq, "p_espera": float(p[c:].sum()), "p_aband": theta * Lq / lam, "ocupados": ocupados, "libre": float(p[:c].sum())}


CASOS = [
    (10.0, 1.0, 0.5, 8),     # sobrecargado (λ > cμ)
    (5.0, 1.0, 1.0, 6),
    (3.0, 2.0, 0.2, 1),
    (20.0, 1.5, 0.05, 12),
    (0.5, 1.0, 3.0, 2),
]


class TestContraBalance:
    @pytest.mark.parametrize("lam,mu,theta,c", CASOS)
    def test_coincide_con_el_sistema_lineal(self, lam, mu, theta, c):
        ref = _indicadores_balance(lam, mu, theta, c)
        r = wl.erlang_a(lam, mu, theta, c)
        assert r.Lq == pytest.approx(ref["Lq"], rel=1e-8)
        assert r.params["P(esperar)"] == pytest.approx(ref["p_espera"], rel=1e-8)
        assert r.params["P(abandono)"] == pytest.approx(ref["p_aband"], rel=1e-7)

    @pytest.mark.parametrize("lam,mu,theta,c", CASOS)
    def test_identidades_de_flujo_y_little(self, lam, mu, theta, c):
        ref = _indicadores_balance(lam, mu, theta, c)
        r = wl.erlang_a(lam, mu, theta, c)
        pab = r.params["P(abandono)"]
        # lo que se atiende es lo que ocupa servidores: λ(1 − Pab) = μ·E[ocupados]
        assert lam * (1 - pab) == pytest.approx(mu * ref["ocupados"], rel=1e-7)
        assert r.params["λ_eff (tasa atendida)"] == pytest.approx(lam * (1 - pab), rel=1e-12)
        assert r.rho == pytest.approx(lam * (1 - pab) / (c * mu), rel=1e-12)
        assert r.L == pytest.approx(lam * r.W, rel=1e-12) and r.Lq == pytest.approx(lam * r.Wq, rel=1e-12)
        assert r.L == pytest.approx(ref["Lq"] + ref["ocupados"], rel=1e-7)
        # flujo de abandonos: θ·Lq = λ·Pab
        assert theta * r.Lq == pytest.approx(lam * pab, rel=1e-7)

    @pytest.mark.parametrize("lam,mu,theta,c", CASOS)
    def test_la_espera_media_se_reparte_entre_atendidos_y_abandonos(self, lam, mu, theta, c):
        """Wq (de todos) = (1−Pab)·Wq atendidos + Pab·Wq abandonos: contrasta las recursiones U y V con Lq/λ."""
        r = wl.erlang_a(lam, mu, theta, c)
        pab = r.params["P(abandono)"]
        mezcla = (1 - pab) * r.params["Wq atendidos"] + pab * r.params["Wq abandonos"]
        assert mezcla == pytest.approx(r.Wq, rel=1e-9)

    def test_quien_abandona_espera_menos_que_su_paciencia_media(self):
        r = wl.erlang_a(10.0, 1.0, 0.5, 8)
        assert 0.0 < r.params["Wq abandonos"] < 1 / 0.5


class TestCasosLimite:
    def test_theta_igual_mu_es_mm_infinito(self):
        """Con θ = μ todo cliente sale a tasa μ esté donde esté: N ~ Poisson(λ/μ)."""
        lam, mu, c = 6.0, 1.0, 4
        pm = [math.exp(-lam / mu) * (lam / mu) ** n / math.factorial(n) for n in range(120)]
        Lq = sum((n - c) * pm[n] for n in range(c, 120))
        r = wl.erlang_a(lam, mu, mu, c)
        assert r.Lq == pytest.approx(Lq, rel=1e-10)
        assert r.params["P(esperar)"] == pytest.approx(sum(pm[c:]), rel=1e-10)
        assert r.params["P(abandono)"] == pytest.approx(mu * Lq / lam, rel=1e-10)

    def test_paciencia_infinita_tiende_a_mmc(self):
        lam, mu, c = 8.0, 3.0, 4
        ref = wl.mmc(lam, mu, c)
        r = wl.erlang_a(lam, mu, 1e-9, c)
        assert r.Lq == pytest.approx(ref.Lq, rel=1e-6)
        assert r.Wq == pytest.approx(ref.Wq, rel=1e-6)
        assert r.params["P(abandono)"] == pytest.approx(0.0, abs=1e-6)

    def test_impaciencia_total_tiende_a_erlang_b(self):
        lam, mu, c = 5.0, 1.0, 6
        r = wl.erlang_a(lam, mu, 1e7, c)
        assert r.params["P(abandono)"] == pytest.approx(wl.erlang_b(lam, mu, c), rel=1e-5)
        assert r.Lq == pytest.approx(0.0, abs=1e-5)

    def test_sobrecarga_es_estable_y_atiende_casi_cmu(self):
        """Con λ = 2cμ el sistema sigue acotado: se atiende casi la capacidad (límite de fluidos) y el resto abandona."""
        c, mu = 60, 1.0
        r = wl.erlang_a(2.0 * c * mu, mu, 0.5, c)
        assert r.params["λ_eff (tasa atendida)"] == pytest.approx(c * mu, rel=0.03)
        assert r.params["P(abandono)"] == pytest.approx(0.5, abs=0.03)
        assert r.rho > 0.97

    def test_con_abandono_la_cola_es_mas_corta_que_en_mmc(self):
        """Impacientes dejan la fila: con los mismos λ, μ, c la cola es más corta que en M/M/c."""
        base = wl.mmc(8.0, 3.0, 4)
        r = wl.erlang_a(8.0, 3.0, 0.3, 4)
        assert r.Lq < base.Lq and r.Wq < base.Wq


class TestMonotonia:
    def test_mas_servidores_menos_abandono_y_espera(self):
        r = [wl.erlang_a(10.0, 1.0, 0.5, c) for c in range(2, 20)]
        pab = [x.params["P(abandono)"] for x in r]
        pw = [x.params["P(esperar)"] for x in r]
        assert pab == sorted(pab, reverse=True) and pw == sorted(pw, reverse=True)

    def test_mas_impaciencia_mas_abandono_y_menos_cola(self):
        r = [wl.erlang_a(10.0, 1.0, th, 8) for th in (0.05, 0.1, 0.5, 1.0, 5.0)]
        pab = [x.params["P(abandono)"] for x in r]
        lq = [x.Lq for x in r]
        assert pab == sorted(pab) and lq == sorted(lq, reverse=True)


class TestNivelDeServicio:
    LAM, MU, TH, C = 10.0, 1.0, 0.5, 8

    def test_t_cero_es_la_fraccion_que_no_espera(self):
        ref = _indicadores_balance(self.LAM, self.MU, self.TH, self.C)
        assert wl.erlang_a_service_level(self.LAM, self.MU, self.TH, self.C, 0.0) == pytest.approx(ref["libre"], rel=1e-8)

    def test_t_grande_es_uno_menos_abandono(self):
        r = wl.erlang_a(self.LAM, self.MU, self.TH, self.C)
        sl = wl.erlang_a_service_level(self.LAM, self.MU, self.TH, self.C, 200.0)
        assert sl == pytest.approx(1 - r.params["P(abandono)"], rel=1e-9)

    def test_creciente_en_t(self):
        v = [wl.erlang_a_service_level(self.LAM, self.MU, self.TH, self.C, t) for t in (0, 0.1, 0.5, 1, 2, 5, 20)]
        assert v == sorted(v) and v[0] < v[-1]

    def test_mmc_en_el_limite_de_paciencia_infinita(self):
        """M/M/c: P(Wq ≤ t) = 1 − P(esperar)·e^{−(cμ−λ)t}."""
        lam, mu, c = 8.0, 3.0, 4
        ref = _indicadores_balance(lam, mu, 1e-9, c, n_max=300)["p_espera"]
        for t in (0.0, 0.2, 1.0, 3.0):
            esperado = 1.0 - ref * math.exp(-(c * mu - lam) * t)
            assert wl.erlang_a_service_level(lam, mu, 1e-9, c, t) == pytest.approx(esperado, abs=1e-6)

    def test_contra_integracion_numerica_de_las_ecuaciones(self):
        """g_j(t) = P(atenderse antes de t | posición j) cumple g_j' = (cμ+(j−1)θ)(g_{j−1} − g_j) − θ g_j con g_0 ≡ 1 (RK4)."""
        lam, mu, th, c, t = 6.0, 1.0, 0.7, 4, 1.3
        p = _estacionaria_por_balance(lam, mu, th, c, 300)
        J = 300 - c
        j = np.arange(1, J + 1, dtype=float)
        cmu = c * mu

        def f(g):
            previo = np.concatenate(([1.0], g[:-1]))
            return (cmu + (j - 1) * th) * (previo - g) - th * g

        g = np.zeros(J)
        pasos = 4000
        h = t / pasos
        for _ in range(pasos):
            k1 = f(g)
            k2 = f(g + h / 2 * k1)
            k3 = f(g + h / 2 * k2)
            k4 = f(g + h * k3)
            g = g + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        esperado = p[:c].sum() + float((p[c:c + J] * g).sum())
        assert wl.erlang_a_service_level(lam, mu, th, c, t) == pytest.approx(esperado, abs=2e-6)


def _simular(lam, mu, theta, c, n, semilla, t_sl, calentamiento=2000):
    """FIFO con abandono: la espera virtual de quien llega es lo que falta para el primer servidor libre; quien abandona no usa servidor."""
    rng = random.Random(semilla)
    t = 0.0
    libres = [0.0] * c
    heapq.heapify(libres)
    m = atendidos = abandonos = demorados = nivel = 0
    esp_atendidos = esp_abandonos = 0.0
    for i in range(n + calentamiento):
        t += rng.expovariate(lam)
        f = libres[0]
        w = max(0.0, f - t)
        paciencia = rng.expovariate(theta)
        sirve = w <= paciencia
        if sirve:
            heapq.heapreplace(libres, max(f, t) + rng.expovariate(mu))
        if i < calentamiento:
            continue
        m += 1
        demorados += w > 0
        if sirve:
            atendidos += 1
            esp_atendidos += w
            nivel += w <= t_sl
        else:
            abandonos += 1
            esp_abandonos += paciencia
    return abandonos / m, demorados / m, esp_atendidos / atendidos, esp_abandonos / max(abandonos, 1), nivel / m


def test_coincide_con_simulacion_de_eventos():
    lam, mu, th, c, t_sl = 10.0, 1.0, 0.5, 8, 2.0
    r = wl.erlang_a(lam, mu, th, c)
    ref = [r.params["P(abandono)"], r.params["P(esperar)"], r.params["Wq atendidos"], r.params["Wq abandonos"],
           wl.erlang_a_service_level(lam, mu, th, c, t_sl)]
    reps = [_simular(lam, mu, th, c, 40_000, s, t_sl) for s in range(12)]
    for i in range(5):
        xs = [x[i] for x in reps]
        se = statistics.stdev(xs) / len(xs) ** 0.5
        assert abs(statistics.mean(xs) - ref[i]) < 4.0 * se, (i, statistics.mean(xs), ref[i], se)


class TestServidoresMinimos:
    def test_es_el_minimo_que_cumple_el_abandono(self):
        r = wl.erlang_a_servers(10.0, 1.0, 0.5, max_abandon=0.02)
        assert r.params["P(abandono)"] <= 0.02
        assert wl.erlang_a(10.0, 1.0, 0.5, r.servers - 1).params["P(abandono)"] > 0.02
        assert r.servers == 14

    def test_varios_objetivos_a_la_vez(self):
        r = wl.erlang_a_servers(10.0, 1.0, 0.5, max_abandon=0.05, max_wait_prob=0.2,
                                min_service_level=0.9, t=0.5)
        c = r.servers
        assert r.params["P(abandono)"] <= 0.05 and r.params["P(esperar)"] <= 0.2
        assert wl.erlang_a_service_level(10.0, 1.0, 0.5, c, 0.5) >= 0.9
        previo = wl.erlang_a(10.0, 1.0, 0.5, c - 1)
        assert (previo.params["P(abandono)"] > 0.05 or previo.params["P(esperar)"] > 0.2
                or wl.erlang_a_service_level(10.0, 1.0, 0.5, c - 1, 0.5) < 0.9)

    def test_cada_objetivo_por_separado(self):
        r1 = wl.erlang_a_servers(10.0, 1.0, 0.5, max_wait_prob=0.3)
        assert r1.params["P(esperar)"] <= 0.3
        assert wl.erlang_a(10.0, 1.0, 0.5, r1.servers - 1).params["P(esperar)"] > 0.3
        r2 = wl.erlang_a_servers(10.0, 1.0, 0.5, min_service_level=0.9, t=0.25)
        assert wl.erlang_a_service_level(10.0, 1.0, 0.5, r2.servers, 0.25) >= 0.9
        assert wl.erlang_a_service_level(10.0, 1.0, 0.5, r2.servers - 1, 0.25) < 0.9

    def test_un_servidor_basta_para_una_carga_ligera(self):
        assert wl.erlang_a_servers(0.1, 5.0, 1.0, max_abandon=0.5).servers == 1

    def test_inalcanzable(self):
        with pytest.raises(ValueError, match="c_max"):
            wl.erlang_a_servers(100.0, 1.0, 0.5, max_abandon=0.001, c_max=5)

    @pytest.mark.parametrize("kw", [{}, {"min_service_level": 0.8}, {"max_abandon": 1.0}, {"max_abandon": 0.0},
                                    {"max_wait_prob": 1.5}, {"min_service_level": 0.8, "t": -1.0}])
    def test_objetivos_invalidos(self, kw):
        with pytest.raises(ValueError):
            wl.erlang_a_servers(10.0, 1.0, 0.5, **kw)


class TestEntradas:
    @pytest.mark.parametrize("kw", [dict(lam=0.0), dict(lam=-1.0), dict(mu=0.0), dict(theta=0.0), dict(theta=-0.5),
                                    dict(theta=float("nan")), dict(lam=float("inf")), dict(c=0), dict(c=-2)])
    def test_rechaza_valores_invalidos(self, kw):
        base = dict(lam=10.0, mu=1.0, theta=0.5, c=8)
        with pytest.raises(ValueError):
            wl.erlang_a(**{**base, **kw})

    def test_c_debe_ser_entero(self):
        with pytest.raises((TypeError, ValueError)):
            wl.erlang_a(10.0, 1.0, 0.5, 2.5)

    def test_t_negativo(self):
        with pytest.raises(ValueError):
            wl.erlang_a_service_level(10.0, 1.0, 0.5, 8, -1.0)

    def test_cola_demasiado_grande(self):
        with pytest.raises(ValueError, match="estados"):
            wl.erlang_a(1e9, 1.0, 1e-3, 2)

    def test_resultado_es_un_queue_result(self):
        r = wl.erlang_a(10.0, 1.0, 0.5, 8)
        assert isinstance(r, wl.QueueResult)
        assert r.model == "M/M/8+M (Erlang A)"
        assert "P(abandono)" in r.summary() and "Erlang A" in r.summary()
        assert "P(abandono)" in r.to_frame().columns

    def test_etiquetas_en_ingles(self):
        wl.set_language("en")
        try:
            r = wl.erlang_a(10.0, 1.0, 0.5, 8)
            texto = r.summary()
            columnas = list(r.to_frame().columns)
        finally:
            wl.set_language("es")
        assert "P(abandonment)" in texto and "P(abandonment)" in columnas
