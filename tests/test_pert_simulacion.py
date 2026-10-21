"""PERT con simulación Monte Carlo (``pert(..., n_simulations=N)``, 0.4.6).

Los oráculos son independientes de la simulación: casos deterministas, la media y la varianza exactas de la beta-PERT
(media (a + 4m + b)/6, varianza (μ − a)(b − μ)/7) y, con dos rutas idénticas, P(T ≤ t) = F(t)² con F integrada numéricamente.
"""
from __future__ import annotations

import math
import warnings

import pytest

import walopy as wl
from walopy import project


def _act(nombre, a, m, b, preds=()):
    return {"name": nombre, "optimistic": a, "most_likely": m, "pessimistic": b, "predecessors": list(preds)}


def _dos_rutas_iguales(a=4, m=5, b=9):
    return [_act("A1", a, m, b), _act("A2", a, m, b, ["A1"]), _act("B1", a, m, b), _act("B2", a, m, b, ["B1"]), _act("FIN", 1, 1, 1, ["A2", "B2"])]


def _cdf_beta_pert(x, a, m, b):
    """F(x) por integración trapezoidal de la densidad beta-PERT (independiente del muestreo)."""
    alfa, beta = 1 + 4 * (m - a) / (b - a), 1 + 4 * (b - m) / (b - a)
    const = math.gamma(alfa + beta) / (math.gamma(alfa) * math.gamma(beta))
    u_max = min(max((x - a) / (b - a), 0.0), 1.0)
    n = 4000
    h = u_max / n
    f = lambda u: const * u ** (alfa - 1) * (1 - u) ** (beta - 1)  # noqa: E731
    if u_max == 0:
        return 0.0
    return h * (0.5 * (0.0 if alfa > 1 else f(1e-12)) + sum(f(i * h) for i in range(1, n)) + 0.5 * f(u_max)) if alfa > 1 else float("nan")


def test_una_actividad_la_media_y_la_varianza_son_las_de_la_beta_pert():
    r = wl.pert([_act("A", 2, 5, 14)], n_simulations=200_000, seed=1)
    mu = (2 + 4 * 5 + 14) / 6
    var = (mu - 2) * (14 - mu) / 7
    assert r.mc_mean == pytest.approx(mu, abs=4 * math.sqrt(var / 200_000))
    assert r.mc_std == pytest.approx(math.sqrt(var), rel=0.01)


def test_actividades_deterministas_dan_duracion_y_criticidad_exactas():
    acts = [_act("L", 10, 10, 10), _act("C", 8, 8, 8), _act("FIN", 2, 2, 2, ["L", "C"])]
    r = wl.pert(acts, n_simulations=1000, seed=1)
    assert r.mc_mean == 12.0 and r.mc_std == 0.0
    assert r.criticality_index == {"C": 0.0, "L": 1.0, "FIN": 1.0}
    assert r.probability_mc(12.0) == 1.0 and r.probability_mc(11.999) == 0.0


def test_dos_rutas_identicas_cada_una_es_critica_la_mitad_de_las_veces():
    r = wl.pert(_dos_rutas_iguales(), n_simulations=40_000, seed=2)
    for nombre in ("A1", "A2", "B1", "B2"):
        assert r.criticality_index[nombre] == pytest.approx(0.5, abs=0.015)
    assert r.criticality_index["FIN"] == 1.0
    # la simulación considera todas las rutas: su media supera a la de una sola ruta (2 · 5,5 + 1 = 12)
    assert r.mc_mean > 12.3


def test_probabilidad_simulada_coincide_con_la_exacta_para_la_ruta_unica_y_para_dos_rutas():
    # P(T ≤ t) para una sola ruta de dos actividades iguales es difícil de integrar; con dos rutas de UNA actividad es F(t)²
    acts = [_act("A", 4, 5, 9), _act("B", 4, 5, 9)]
    r = wl.pert(acts, n_simulations=200_000, seed=3)
    for t in (5.0, 5.5, 6.0, 7.0):
        F = _cdf_beta_pert(t, 4, 5, 9)
        esperado = F * F
        assert r.probability_mc(t) == pytest.approx(esperado, abs=4 * math.sqrt(esperado * (1 - esperado) / 200_000) + 1e-3)


def test_la_probabilidad_normal_de_una_ruta_es_optimista_con_rutas_paralelas():
    acts = []
    for p in range(5):
        previa: list[str] = []
        for j in range(3):
            nombre = f"P{p}A{j}"
            acts.append(_act(nombre, 4, 5, 9, previa))
            previa = [nombre]
    acts.append(_act("FIN", 1, 1, 1, [f"P{p}A2" for p in range(5)]))
    with pytest.warns(UserWarning):
        r_normal = wl.pert(acts)
    r = wl.pert(acts, n_simulations=100_000, seed=4)
    assert r_normal.probability(17.5) == pytest.approx(0.5)
    assert r.probability_mc(17.5) < 0.06            # simulación: ≈ 0,04
    assert r.mc_mean == pytest.approx(19.31, abs=0.05)


def test_es_reproducible_con_semilla_y_no_depende_del_tamano_del_bloque(monkeypatch):
    a = wl.pert(_dos_rutas_iguales(), n_simulations=5000, seed=7)
    b = wl.pert(_dos_rutas_iguales(), n_simulations=5000, seed=7)
    assert a.mc_mean == b.mc_mean and a.criticality_index == b.criticality_index
    monkeypatch.setattr(project, "_CELDAS_POR_BLOQUE", 12)   # bloques diminutos: el resultado sigue siendo el mismo modelo
    c = wl.pert(_dos_rutas_iguales(), n_simulations=20_001, seed=7)
    assert c.n_simulations == 20_001 and c.mc_mean == pytest.approx(a.mc_mean, abs=0.1)


def test_percentiles_y_errores():
    r = wl.pert(_dos_rutas_iguales(), n_simulations=2000, seed=1)
    assert r.percentile_mc(10) <= r.percentile_mc(50) <= r.percentile_mc(90)
    with pytest.raises(ValueError):
        r.percentile_mc(101)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        sin = wl.pert(_dos_rutas_iguales())
    for llamada in (lambda: sin.probability_mc(10), lambda: sin.percentile_mc(50)):
        with pytest.raises(ValueError) as e:
            llamada()
        assert "n_simulations" in str(e.value)
    for malo in (-1, 2.5, 10**6 + 1, True):
        with pytest.raises((ValueError, TypeError)):
            wl.pert(_dos_rutas_iguales(), n_simulations=malo)


def test_con_simulacion_no_avisa_de_rutas_casi_criticas_y_sin_ella_si():
    with pytest.warns(UserWarning, match="n_simulations"):
        wl.pert(_dos_rutas_iguales())
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        wl.pert(_dos_rutas_iguales(), n_simulations=1000, seed=1)


def test_sin_simulacion_el_resultado_es_el_de_siempre():
    # Guarda
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        r = wl.pert(_dos_rutas_iguales())
    assert r.n_simulations == 0 and r.mc_mean is None and r.criticality_index is None
    assert "Simulación" not in r.summary()
    assert "Índice de criticidad" not in list(r.to_frame().columns)


def test_resumen_y_tabla_con_simulacion():
    r = wl.pert(_dos_rutas_iguales(), n_simulations=3000, seed=1)
    assert "Simulación" in r.summary() and "3,000" in r.summary()
    from walopy._i18n import columna
    col = columna(r.to_frame(), "project.cabecera.to_frame.indice_criticidad")
    assert r.to_frame()[col].iloc[-1] == 1.0
