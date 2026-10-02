"""Valores de referencia calculados con herramientas externas (scipy 1.x, a mano) y guardados como constantes.

Cada constante indica su origen. Así los tests no dependen de scipy en tiempo de ejecución ni validan el
código contra sí mismo.
"""
from __future__ import annotations

import pytest

import walopy as wl

# Raíz de la ecuación de verosimilitud de Weibull resuelta con scipy.optimize.brentq (tolerancia 1e-15)
# sobre estos 10 tiempos de falla (weibull_min.fit de scipy es menos preciso: difiere en el 6.º decimal)
TIEMPOS = [12.5, 18.3, 24.1, 31.7, 38.2, 45.9, 52.4, 61.0, 70.8, 85.3]


def test_weibull_mle_coincide_con_scipy():
    r = wl.weibull_analysis(TIEMPOS)
    assert r.shape == pytest.approx(2.0960949331865226, rel=1e-10)
    assert r.scale == pytest.approx(49.855642038989785, rel=1e-10)
    assert r.mttf == pytest.approx(44.15738858857231, rel=1e-9)    # weibull_min(β, η).mean()
    assert r.b10 == pytest.approx(17.03945883486382, rel=1e-9)     # .ppf(0.10)
    assert r.b50 == pytest.approx(41.8577328531316, rel=1e-9)      # .ppf(0.50)


def test_pert_probabilidad_coincide_con_la_normal():
    acts = [
        {"name": "A", "optimistic": 1, "most_likely": 2, "pessimistic": 9, "predecessors": []},
        {"name": "B", "optimistic": 2, "most_likely": 4, "pessimistic": 6, "predecessors": ["A"]},
    ]
    r = wl.pert(acts)
    # a mano: μ = (1+8+9)/6 + 4 = 7; σ² = (8/6)² + (4/6)² = 2.2222…
    assert r.project_duration == pytest.approx(7.0)
    assert r.project_variance == pytest.approx(2.2222222222222223)
    assert r.probability(12.0) == pytest.approx(0.9996018849212046, rel=1e-9)  # scipy.stats.norm.cdf(12, 7, σ)


def test_newsvendor_cuantil_critico_coincide_con_scipy():
    nv = wl.newsvendor(100, 20, 10, 4, salvage=1)
    assert nv.critical_ratio == pytest.approx(6.0 / 9.0)
    assert nv.optimal_qty == pytest.approx(108.61454598590915, rel=1e-9)  # scipy.stats.norm.ppf(2/3, 100, 20)


def test_mmc_erlang_c_coincide_con_scipy():
    # M/M/4, λ=8, μ=3: C = B/(1-ρ(1-B)) con B = poisson.pmf(4, 8/3)/poisson.cdf(4, 8/3)
    r = wl.mmc(8.0, 3.0, 4)
    assert r.params["C(c,a) Erlang-C"] == pytest.approx(0.37841832963784167, rel=1e-9)
    assert r.Lq == pytest.approx(0.7568366592756832, rel=1e-9)


def test_koon_coincide_con_la_binomial():
    # 3-de-5, λ=0.01, t=50: Σ_{i=3..5} C(5,i) R^i (1-R)^(5-i) con R = e^{-0.5}
    assert wl.koon_system(5, 3, 0.01, t=50.0).R_t == pytest.approx(0.6937823446785008, rel=1e-12)


def test_eoq_formula_cerrada():
    assert wl.eoq(1000, 50, 2).eoq == pytest.approx(223.60679774997897)  # √(2·1000·50/2)
