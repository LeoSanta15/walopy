"""mmc debe ser estable para cargas grandes (K-06): contraste con el balance de nacimiento-muerte."""
from __future__ import annotations

import math

import pytest

import walopy as wl


def _nacimiento_muerte(lam: float, mu: float, c: int, n_max: int):
    """Referencia independiente: distribución estacionaria truncada en logaritmos (sin factoriales)."""
    log_p = [0.0]
    for n in range(1, n_max + 1):
        log_p.append(log_p[-1] + math.log(lam) - math.log(mu * min(n, c)))
    m = max(log_p)
    w = [math.exp(x - m) for x in log_p]
    z = sum(w)
    p = [x / z for x in w]
    lq = sum(max(0, n - c) * pn for n, pn in enumerate(p))
    return p[0], lq


@pytest.mark.parametrize("c", [1, 2, 10, 100, 150, 300, 1000])
def test_mmc_coincide_con_nacimiento_muerte(c):
    lam, mu = 0.95 * c, 1.0
    r = wl.mmc(lam, mu, c)
    p0, lq = _nacimiento_muerte(lam, mu, c, n_max=c + 40000)
    assert r.Lq == pytest.approx(lq, rel=1e-6)
    if p0 > 1e-250:
        assert r.params["P0 (idle probability)"] == pytest.approx(p0, rel=1e-6)


def test_mmc_valores_historicos_no_cambian():
    # M/M/4 con λ=8, μ=3: L=3.4235027 (fórmula directa previa y balance de nacimiento-muerte).
    r = wl.mmc(8.0, 3.0, 4)
    assert r.L == pytest.approx(3.4235027, rel=1e-6)
    # M/M/2 con λ=2, μ=3 a mano: a=2/3, ρ=1/3, P0=1/2, Lq = P0·a²·ρ / (2(1-ρ)²) = 1/12.
    r = wl.mmc(2.0, 3.0, 2)
    assert r.params["P0 (idle probability)"] == pytest.approx(0.5, rel=1e-12)
    assert r.Lq == pytest.approx(1.0 / 12.0, rel=1e-12)


def test_mmc_carga_muy_grande_no_desborda():
    r = wl.mmc(145.0, 1.0, 150)
    assert 0.0 <= r.params["C(c,a) Erlang-C"] <= 1.0
    assert math.isfinite(r.Wq) and r.Wq >= 0.0


def test_mmc_pocas_llegadas_con_muchos_servidores():
    r = wl.mmc(1e-3, 1.0, 10_000)
    assert r.Lq == pytest.approx(0.0, abs=1e-12)
    assert r.params["P0 (idle probability)"] == pytest.approx(math.exp(-1e-3), rel=1e-6)


def test_mmc_rechaza_demasiados_servidores():
    with pytest.raises(ValueError, match="no puede superar"):
        wl.mmc(1.0, 1.0, 10**7)
