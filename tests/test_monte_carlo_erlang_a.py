"""Simulación de M/M/c+M con K clases, prioridad y μ por clase (0.4.14): ``monte_carlo_erlang_a``.

La simulación no tiene sesgo de modelo, así que se contrasta con los modelos exactos (donde existen) mediante sus propios intervalos de confianza, y con
propiedades de las réplicas: reproducibilidad, semiancho calculado a mano, orden de prioridad y tipos de entrada.
"""
import math

import numpy as np
import pytest

import walopy as wl
from walopy.advanced import _replica_contacto

SEMILLA = 20261022


def _dentro(est, hw, exacto, k=2.0):
    """El valor exacto cae a lo más a k semianchos del 95 % (k = 2 deja ≈ 1 en 10 000 de falso rechazo)."""
    return abs(est - exacto) <= k * hw


class TestContraLosModelosExactos:
    def test_dos_clases_con_mu_distintos(self):
        lam, mu, th, c, t = [1.0, 2.5], [2.0, 0.7], [0.6, 0.3], 4, 0.6
        e = wl.erlang_a_classes(lam, mu, th, c)
        niv = wl.erlang_a_classes_service_level(lam, mu, th, c, t=t)
        r = wl.monte_carlo_erlang_a(lam, mu, th, c, n_customers=100_000, n_replications=10, t=t, seed=SEMILLA)
        assert _dentro(r.p_wait, r.p_wait_halfwidth, e.p_wait)
        for k in (0, 1):
            cl = r.classes[k]
            assert _dentro(cl["p_abandon"], cl["p_abandon_halfwidth"], e.classes[k]["p_abandon"])
            assert _dentro(cl["Wq"], cl["wq_halfwidth"], e.classes[k]["Wq"])
            assert _dentro(cl["service_level"], cl["service_level_halfwidth"], niv[k])

    def test_tres_clases_con_mu_comun(self):
        lam, th, c, t = [0.7, 1.1, 1.6], [0.9, 0.5, 0.25], 4, 0.6
        e = wl.erlang_a_classes(lam, 1.0, th, c)
        niv = wl.erlang_a_classes_service_level(lam, 1.0, th, c, t=t)
        r = wl.monte_carlo_erlang_a(lam, 1.0, th, c, n_customers=100_000, n_replications=10, t=t, seed=SEMILLA)
        for k in range(3):
            cl = r.classes[k]
            assert _dentro(cl["p_abandon"], cl["p_abandon_halfwidth"], e.classes[k]["p_abandon"])
            assert _dentro(cl["Wq"], cl["wq_halfwidth"], e.classes[k]["Wq"])
            assert _dentro(cl["service_level"], cl["service_level_halfwidth"], niv[k])
        assert _dentro(r.p_wait, r.p_wait_halfwidth, e.p_wait)

    def test_una_clase_es_erlang_a(self):
        e = wl.erlang_a(10.0, 1.0, 0.5, 8)
        r = wl.monte_carlo_erlang_a([10.0], 1.0, 0.5, 8, n_customers=100_000, n_replications=10, t=2.0, seed=SEMILLA)
        cl = r.classes[0]
        assert _dentro(cl["p_abandon"], cl["p_abandon_halfwidth"], e.params["P(abandono)"])
        assert _dentro(cl["Wq"], cl["wq_halfwidth"], e.Wq)
        assert _dentro(cl["service_level"], cl["service_level_halfwidth"], wl.erlang_a_service_level(10.0, 1.0, 0.5, 8, 2.0))

    def test_muchos_agentes_contra_el_exacto_de_mu_comun(self):
        """Con c = 100 el exacto de dos clases (μ común) sigue siendo calculable: la simulación debe coincidir."""
        lam, th, c = [20.0, 80.0], [0.3, 0.1], 100
        e = wl.erlang_a_priority(lam[0], lam[1], 1.0, th[0], th[1], c)
        r = wl.monte_carlo_erlang_a(lam, 1.0, th, c, n_customers=200_000, n_replications=8, seed=SEMILLA)
        for k in (0, 1):
            cl = r.classes[k]
            assert _dentro(cl["p_abandon"], cl["p_abandon_halfwidth"], e.classes[k]["p_abandon"])
            assert _dentro(cl["Wq"], cl["wq_halfwidth"], e.classes[k]["Wq"])

    def test_la_prioridad_se_nota(self):
        r = wl.monte_carlo_erlang_a([1.0, 1.0, 1.0], 1.0, 0.5, 2, n_customers=60_000, n_replications=6, seed=SEMILLA)
        wq = [x["Wq"] for x in r.classes]
        assert wq[0] < wq[1] < wq[2]


class TestReplicasEIntervalos:
    ARGS = dict(lam=[0.5, 1.5], mu=[0.4, 0.25], theta=[0.1, 0.3], c=6)

    def test_reproducible_con_semilla(self):
        a = wl.monte_carlo_erlang_a(**self.ARGS, n_customers=5000, n_replications=3, seed=5)
        b = wl.monte_carlo_erlang_a(**self.ARGS, n_customers=5000, n_replications=3, seed=5)
        c = wl.monte_carlo_erlang_a(**self.ARGS, n_customers=5000, n_replications=3, seed=6)
        assert a.classes == b.classes and a.p_wait == b.p_wait
        assert a.classes != c.classes

    def test_el_semiancho_es_t_por_desviacion_sobre_raiz_de_r(self):
        """Se recalcula con las mismas réplicas (mismos flujos) y la fórmula del intervalo t de Student."""
        n, r_, calent = 4000, 4, 400
        res = wl.monte_carlo_erlang_a(**self.ARGS, n_customers=n, n_replications=r_, warmup=calent, seed=11)
        flujos = [np.random.default_rng(s) for s in np.random.SeedSequence(11).spawn(r_)]
        reps = [_replica_contacto(self.ARGS["lam"], self.ARGS["mu"], self.ARGS["theta"], 6, n, g, calent, None) for g in flujos]
        pab = np.array([x["abandonos"][1] / x["n"][1] for x in reps])
        assert res.classes[1]["p_abandon"] == pytest.approx(pab.mean(), rel=1e-12)
        t3 = 3.182446305284263                                            # scipy.stats.t.ppf(0.975, 3)
        assert res.classes[1]["p_abandon_halfwidth"] == pytest.approx(t3 * pab.std(ddof=1) / math.sqrt(r_), rel=1e-4)             # t_cuantil_975 usa una tabla de 4 decimales

    def test_mas_llegadas_estrechan_el_intervalo(self):
        corto = wl.monte_carlo_erlang_a(**self.ARGS, n_customers=10_000, n_replications=8, seed=SEMILLA)
        largo = wl.monte_carlo_erlang_a(**self.ARGS, n_customers=160_000, n_replications=8, seed=SEMILLA)
        razon = corto.classes[1]["p_abandon_halfwidth"] / largo.classes[1]["p_abandon_halfwidth"]
        assert 2.0 < razon < 8.0                                          # ≈ √16 = 4

    def test_mas_servidores_menos_abandono(self):
        a = wl.monte_carlo_erlang_a([2.0, 3.0], 1.0, 0.5, 4, n_customers=40_000, n_replications=4, seed=SEMILLA)
        b = wl.monte_carlo_erlang_a([2.0, 3.0], 1.0, 0.5, 7, n_customers=40_000, n_replications=4, seed=SEMILLA)
        assert all(y["p_abandon"] < x["p_abandon"] for x, y in zip(a.classes, b.classes))

    def test_mu_y_theta_numericos_se_repiten_por_clase(self):
        a = wl.monte_carlo_erlang_a([0.5, 1.5], 0.3, 0.2, 6, n_customers=4000, n_replications=2, seed=3)
        b = wl.monte_carlo_erlang_a([0.5, 1.5], [0.3, 0.3], [0.2, 0.2], 6, n_customers=4000, n_replications=2, seed=3)
        assert a.classes == b.classes

    def test_probabilidades_y_esperas_en_rango(self):
        r = wl.monte_carlo_erlang_a([3.0, 3.0], [1.0, 1.0], [0.4, 0.4], 3, n_customers=10_000, n_replications=3, t=0.5, seed=1)
        for cl in r.classes:
            assert 0.0 <= cl["p_abandon"] <= 1.0 and cl["Wq"] >= 0.0 and 0.0 <= cl["service_level"] <= 1.0 - cl["p_abandon"] + 1e-9
        assert 0.0 <= r.p_wait <= 1.0


class TestEntradasYSalida:
    BASE = dict(lam=[0.5, 1.5], mu=[0.4, 0.25], theta=[0.1, 0.3], c=6, n_customers=3000, n_replications=2, seed=1)

    @pytest.mark.parametrize("kw", [
        dict(lam=[]), dict(lam=[1.0] * 7, mu=1.0, theta=1.0), dict(lam=[0.5, 0.0]), dict(lam=[0.5, -1.0]), dict(mu=[0.4]), dict(mu=[0.4, 0.0]),
        dict(theta=[0.1, 0.2, 0.3]), dict(theta=[0.1, float("nan")]), dict(c=0), dict(n_customers=0), dict(n_replications=1), dict(n_replications=0),
        dict(warmup=3000), dict(warmup=-1), dict(warmup=1.5), dict(t=-1.0), dict(seed=-3),
    ])
    def test_rechaza_valores_invalidos(self, kw):
        with pytest.raises(ValueError):
            wl.monte_carlo_erlang_a(**{**self.BASE, **kw})

    @pytest.mark.parametrize("kw", [dict(mu="abc"), dict(theta=None), dict(lam=5), dict(warmup="x"), dict(n_customers=2.5), dict(mu=True), dict(seed=True), dict(seed=1.5), dict(seed="a")])
    def test_tipos_invalidos(self, kw):
        with pytest.raises((TypeError, ValueError)):
            wl.monte_carlo_erlang_a(**{**self.BASE, **kw})

    def test_demasiadas_llegadas_en_total(self, monkeypatch):
        monkeypatch.setattr("walopy.advanced.MAX_CLIENTES_TOTAL", 5000)
        with pytest.raises(ValueError, match="llegadas"):
            wl.monte_carlo_erlang_a(**self.BASE)

    def test_resultado(self):
        r = wl.monte_carlo_erlang_a(**self.BASE, t=0.5)
        assert isinstance(r, wl.ErlangASimulationResult) and r.servers == 6 and r.warmup == 300 and r.t == 0.5
        resumen = r.summary()
        assert "Simulación M/M/6+M" in resumen and "Nivel de servicio" in resumen and str(r) == resumen
        assert list(r.to_frame().columns)[:5] == ["id_clase", "λ", "μ", "θ", "P(abandono)"] and len(r.to_frame()) == 2
        sin_t = wl.monte_carlo_erlang_a(**self.BASE)
        assert "Nivel de servicio" not in sin_t.summary() and "Nivel de servicio" not in sin_t.to_frame().columns

    def test_etiquetas_en_ingles(self):
        wl.set_language("en")
        try:
            r = wl.monte_carlo_erlang_a(**self.BASE, t=0.5)
            texto, columnas = r.summary(), list(r.to_frame().columns)
        finally:
            wl.set_language("es")
        assert "simulation" in texto and "Service level" in texto and "P(abandonment)" in columnas
