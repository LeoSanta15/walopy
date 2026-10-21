"""Réplicas, calentamiento e intervalo de confianza de ``monte_carlo_gg1`` (0.4.6).

Una sola réplica puede alejarse mucho del valor esperado (con ρ = 0,95 y 20 000 clientes, Wq salió entre 11 y 27 con un valor exacto
de 19). Las pruebas usan M/M/1, cuyo Wq exacto es λ / (μ(μ − λ)), como oráculo independiente.
"""
from __future__ import annotations

import warnings

import numpy as np
import pytest

import walopy as wl
from walopy._utils import t_cuantil_975


def _wq_exacto(lam: float, mu: float) -> float:
    return lam / (mu * (mu - lam))


def test_una_replica_sin_calentamiento_reproduce_el_flujo_de_siempre():
    # Guarda: 0.4.5 daba L = 2,0169 con esta semilla
    r = wl.monte_carlo_gg1(2.0, 3.0, 1.0, 1.0, n_customers=50_000, seed=1)
    assert round(r.L, 4) == 2.0169
    assert r.n_replications == 1 and r.warmup == 0 and r.Wq_halfwidth is not None


def test_las_replicas_son_reproducibles_e_independientes():
    a = wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=3000, seed=5, n_replications=6)
    b = wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=3000, seed=5, n_replications=6)
    c = wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=3000, seed=6, n_replications=6)
    assert a.Wq_mean == b.Wq_mean and a.Wq_halfwidth == b.Wq_halfwidth
    assert a.Wq_mean != c.Wq_mean
    pooled = a._Wq_array
    assert len(pooled) == 6 * 3000
    # réplicas independientes: los bloques de la réplica 0 y la 1 no son el mismo flujo
    assert not np.array_equal(pooled[:3000], pooled[3000:6000])


@pytest.mark.filterwarnings("ignore::UserWarning")  # muestra pequeña a propósito
def test_las_replicas_equivalen_a_corridas_sueltas_con_los_flujos_derivados_de_la_semilla():
    """Oráculo independiente: R corridas de una réplica con los hijos de SeedSequence(seed) dan la misma media, y el semiancho es t·s/√R."""
    n_rep, n, w = 5, 3000, 200
    juntas = wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=n, seed=77, n_replications=n_rep, warmup=w)
    medias = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        for hijo in np.random.SeedSequence(77).spawn(n_rep):
            medias.append(wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=n, seed=hijo, warmup=w).Wq_mean)  # type: ignore[arg-type]
    assert juntas.Wq_mean == pytest.approx(float(np.mean(medias)), rel=1e-12)
    esperado = t_cuantil_975(n_rep - 1) * float(np.std(medias, ddof=1)) / np.sqrt(n_rep)
    assert juntas.Wq_halfwidth == pytest.approx(esperado, rel=1e-9)
    assert t_cuantil_975(n_rep - 1) == pytest.approx(2.7764, abs=1e-4)   # con 5 réplicas el multiplicador es la t con 4 g.l., no 1,96


@pytest.mark.filterwarnings("ignore::UserWarning")  # muestra pequeña a propósito
def test_el_calentamiento_descarta_clientes_iniciales_de_cada_replica():
    r = wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=2000, seed=2, n_replications=3, warmup=500)
    assert len(r._Wq_array) == 3 * (2000 - 500) and r.warmup == 500


def test_el_intervalo_de_confianza_cubre_el_valor_exacto_con_frecuencia_cercana_a_95():
    exacto = _wq_exacto(1.0, 2.0)
    cubre, total = 0, 40
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        for semilla in range(total):
            r = wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=2000, seed=900 + semilla, n_replications=15, warmup=200)
            low, high = r.Wq_ci
            cubre += low <= exacto <= high
    assert cubre >= 0.85 * total, f"el IC al 95 % cubrió el valor exacto solo {cubre}/{total} veces"


def test_el_semiancho_baja_con_mas_replicas():
    def semiancho(n_rep: int) -> float:
        vals = []
        for s in range(6):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                vals.append(wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=1500, seed=40 + s, n_replications=n_rep).Wq_halfwidth)
        return float(np.mean(vals))

    assert semiancho(32) < 0.6 * semiancho(4)   # ≈ 1/√8 de la teoría, con holgura


def test_con_muchas_replicas_la_estimacion_es_precisa_y_no_avisa():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        r = wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=5000, seed=3, n_replications=30, warmup=300)
    assert abs(r.Wq_mean - 0.5) < 3 * r.Wq_halfwidth + 0.02


def test_una_sola_replica_con_rho_alto_avisa_y_con_muchas_mejora_el_intervalo():
    with pytest.warns(UserWarning, match="n_replications"):
        wl.monte_carlo_gg1(0.95, 1.0, 1.0, 1.0, n_customers=20_000, seed=1)


def test_errores_de_replicas_y_calentamiento():
    for malo in (0, -1, 2.5):
        with pytest.raises((ValueError, TypeError)):
            wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_replications=malo)
    with pytest.raises(ValueError, match="n_replications"):
        wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_replications=10_001)
    for malo in (-1, 20_000, 2.5, "auto"):
        with pytest.raises(ValueError, match="warmup"):
            wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=20_000, warmup=malo)
    with pytest.raises(ValueError, match="clientes"):
        wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=5_000_000, n_replications=3)


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_resumen_y_tabla_incluyen_el_intervalo():
    r = wl.monte_carlo_gg1(1.0, 2.0, 1.0, 1.0, n_customers=2000, seed=1, n_replications=4, warmup=100)
    assert "IC 95" in r.summary() and "4 réplica" in r.summary()
    assert len(r.to_frame()) == 1


def test_cuantiles_t_de_student():
    # valores de tablas: t_{0,975}
    for gl, esperado in ((1, 12.7062), (5, 2.5706), (19, 2.0930), (30, 2.0423), (60, 2.0003), (120, 1.9799), (1000, 1.9623)):
        assert t_cuantil_975(gl) == pytest.approx(esperado, abs=5e-4)
    with pytest.raises(ValueError):
        t_cuantil_975(0)
