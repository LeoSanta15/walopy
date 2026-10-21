"""Objetivos de tasa de llenado (β) y punto de reorden con demanda discreta (0.4.5).

Los oráculos son independientes del código: integración numérica de E[(X − r)⁺] para la normal, y sumas directas de la
función de masa de Poisson / binomial negativa (con ``math.factorial`` y ``math.gamma``, no con ``lgamma`` en logaritmos).
"""
from __future__ import annotations

import math
import random

import pytest

import walopy as wl
from walopy._i18n import columna

SEMILLA = 20261021


def _escenarios(nombre: str, n: int = 80):
    r = random.Random(f"{SEMILLA}-{nombre}")
    return [random.Random(r.random()) for _ in range(n)]


def _faltante_normal(media: float, sigma: float, r: float) -> float:
    """E[(X − r)⁺] con X ~ N(media, σ²), por integración trapezoidal (independiente de la función de pérdida cerrada)."""
    lo, hi, n = r, media + 12 * sigma, 20_000
    h = (hi - lo) / n
    f = lambda x: (x - r) * math.exp(-((x - media) ** 2) / (2 * sigma**2)) / (sigma * math.sqrt(2 * math.pi))  # noqa: E731
    return h * (0.5 * f(lo) + sum(f(lo + i * h) for i in range(1, n)) + 0.5 * f(hi))


# ------------------------------------------------------------------------------------------- tasa de llenado (normal)
def test_rq_con_tasa_de_llenado_alcanza_el_objetivo_segun_integracion_numerica():
    for r in _escenarios("rq"):
        D, K, h, L = r.uniform(5, 200), r.uniform(5, 200), r.uniform(0.1, 3), r.uniform(0.5, 6)
        sd, beta = r.uniform(0.05, 0.5) * D, r.uniform(0.8, 0.999)
        res = wl.rq_policy(D, K, h, L, demand_std=sd, fill_rate=beta)
        sigma = math.sqrt(L) * sd
        faltante = _faltante_normal(D * L, sigma, res.reorder_point)
        assert 1 - faltante / res.order_qty == pytest.approx(beta, abs=1e-5), (D, K, h, L, sd, beta)
        assert res.fill_rate == pytest.approx(beta, abs=1e-9)


def test_rs_con_tasa_de_llenado_alcanza_el_objetivo_segun_integracion_numerica():
    for r in _escenarios("rs"):
        D, K, h, L, R = r.uniform(5, 200), r.uniform(5, 200), r.uniform(0.1, 3), r.uniform(0.5, 6), r.uniform(0.5, 5)
        sd, beta = r.uniform(0.05, 0.5) * D, r.uniform(0.8, 0.999)
        res = wl.rs_policy(D, K, h, L, R, demand_std=sd, fill_rate=beta)
        sigma = math.sqrt(R + L) * sd
        faltante = _faltante_normal(D * (R + L), sigma, res.order_up_to)
        assert 1 - faltante / (D * R) == pytest.approx(beta, abs=1e-5), (D, K, h, L, R, sd, beta)


def test_reorder_point_con_tasa_de_llenado_y_cantidad_de_pedido():
    for r in _escenarios("rop"):
        D, L, sd = r.uniform(5, 200), r.uniform(0.5, 6), r.uniform(1, 40)
        Q, beta = r.uniform(5, 40), r.uniform(0.9, 0.999)   # (1 − β)·Q pequeño frente a σ: el punto de reorden queda positivo
        res = wl.reorder_point(D, L, demand_std=sd, fill_rate=beta, order_qty=Q)
        faltante = _faltante_normal(D * L, math.sqrt(L) * sd, res.reorder_point)
        assert 1 - faltante / Q == pytest.approx(beta, abs=1e-5)
        assert 0 < res.service_level < 1


def test_el_punto_de_reorden_no_baja_de_cero_con_objetivos_muy_holgados():
    # Q muy grande frente a σ: el objetivo se cumpliría con un punto de reorden negativo; se usa 0 y la tasa alcanzada es mayor
    res = wl.reorder_point(10, 2, demand_std=1, fill_rate=0.80, order_qty=500)
    assert res.reorder_point == pytest.approx(0.0, abs=1e-9)
    assert res.fill_rate > 0.80


def test_mayor_tasa_de_llenado_exige_mas_stock_de_seguridad():
    previo = -math.inf
    for beta in (0.80, 0.90, 0.95, 0.99, 0.999):
        ss = wl.rq_policy(50, 40, 1, 2, demand_std=10, fill_rate=beta).safety_stock
        assert ss > previo
        previo = ss


def test_la_tasa_de_llenado_informada_con_nivel_de_servicio_sigue_la_formula():
    # CSL = 95 % con σ_DLT = 14,1 y Q = 63,2: tasa de llenado implícita 1 − σ·G(z)/Q
    res = wl.rq_policy(50, 40, 1, 2, demand_std=10, service_level=0.95)
    z, sigma = 1.6448536269514722, math.sqrt(2) * 10
    G = math.exp(-z * z / 2) / math.sqrt(2 * math.pi) - z * (1 - 0.95)
    assert res.fill_rate == pytest.approx(1 - sigma * G / res.order_qty, rel=1e-9)
    assert res.fill_rate > 0.95  # la tasa de llenado suele ser mayor que el nivel por ciclo


def test_sin_variabilidad_la_tasa_de_llenado_es_1_sin_stock_de_seguridad():
    res = wl.rq_policy(50, 40, 1, 2, fill_rate=0.99)
    assert res.safety_stock == 0.0 and res.fill_rate == 1.0


def test_el_nivel_de_servicio_por_defecto_no_cambia():
    # Guarda: sin fill_rate el stock de seguridad es el de siempre, z · σ_DLT
    res = wl.rq_policy(50, 40, 1, 2, demand_std=10, service_level=0.95)
    assert res.safety_stock == pytest.approx(1.6448536269514722 * math.sqrt(2) * 10)
    assert wl.reorder_point(50, 2, demand_std=10).fill_rate is None


def test_errores_de_tasa_de_llenado():
    with pytest.raises(ValueError, match="order_qty"):
        wl.reorder_point(50, 2, demand_std=10, fill_rate=0.95)
    for malo in (0.0, 1.0, 1.5, -0.1):
        with pytest.raises(ValueError, match="fill_rate"):
            wl.rq_policy(50, 40, 1, 2, demand_std=10, fill_rate=malo)
    with pytest.raises(TypeError):
        wl.rs_policy(50, 40, 1, 2, 1, demand_std=10, fill_rate="x")  # type: ignore[arg-type]


def test_el_resultado_muestra_la_tasa_de_llenado():
    res = wl.rq_policy(50, 40, 1, 2, demand_std=10, fill_rate=0.98)
    assert "98.00%" in res.summary()
    assert res.to_frame()[columna(res.to_frame(), "inventory.cabecera.to_frame.tasa_llenado")].iloc[0] == pytest.approx(0.98)


# ------------------------------------------------------------------------------------------- demanda discreta
def _tabla_pmf(mu: float, var: float, K: int) -> list[float]:
    """P(X = k), k = 0..K, por recurrencias (sin ``lgamma``): Poisson si var == mu; binomial negativa si no."""
    if var <= mu * (1 + 1e-12):
        p = [math.exp(-mu)]
        for k in range(K):
            p.append(p[-1] * mu / (k + 1))
        return p
    r, q = mu * mu / (var - mu), mu / var
    p = [q**r]
    for k in range(K):
        p.append(p[-1] * (k + r) / (k + 1) * (1 - q))
    return p


def _cdf(pmf: list[float], s: int) -> float:
    return sum(pmf[: s + 1])


def _faltante_discreto(pmf: list[float], s: int) -> float:
    return sum((k - s) * pk for k, pk in enumerate(pmf) if k > s)


def _llenado(pmf: list[float], s: int, Q: float) -> float:
    return 1 - _faltante_discreto(pmf, s) / Q


def _K(mu: float, var: float) -> int:
    return int(mu + 60 * math.sqrt(var)) + 300


def test_poisson_es_el_menor_entero_con_el_servicio_pedido():
    for r in _escenarios("poisson"):
        mu, svc = r.uniform(0.2, 25), r.uniform(0.5, 0.999)
        res = wl.reorder_point_discrete(demand_rate=mu / 2, lead_time=2, service_level=svc)
        s = int(res.reorder_point)
        pmf = _tabla_pmf(mu, mu, _K(mu, mu))
        assert _cdf(pmf, s) >= svc and (s == 0 or _cdf(pmf, s - 1) < svc), (mu, svc, s)
        assert res.service_level == pytest.approx(_cdf(pmf, s), rel=1e-9)
        assert res.distribution == "Poisson" and res.var_demand_lt == pytest.approx(mu)


def test_binomial_negativa_es_el_menor_entero_con_el_servicio_pedido():
    for r in _escenarios("nbin"):
        mu, razon, svc = r.uniform(0.3, 20), r.uniform(1.3, 8), r.uniform(0.5, 0.999)
        var = mu * razon
        res = wl.reorder_point_discrete(demand_rate=mu / 3, lead_time=3, demand_std=math.sqrt(var / 3), service_level=svc)
        s = int(res.reorder_point)
        pmf = _tabla_pmf(mu, var, _K(mu, var))
        assert _cdf(pmf, s) >= svc and (s == 0 or _cdf(pmf, s - 1) < svc), (mu, var, svc, s)
        assert res.distribution == "binomial negativa"


def test_tasa_de_llenado_discreta_es_la_menor_que_cumple_el_objetivo():
    for r in _escenarios("llenado_discreto"):
        mu, razon = r.uniform(0.5, 15), r.choice([1.0, r.uniform(1.3, 6)])
        var, Q, beta = mu * razon, r.uniform(2, 60), r.uniform(0.8, 0.999)
        sd = None if razon == 1.0 else math.sqrt(var / 2)
        res = wl.reorder_point_discrete(mu / 2, 2, demand_std=sd, fill_rate=beta, order_qty=Q)
        pmf = _tabla_pmf(mu, var, _K(mu, var))
        s = int(res.reorder_point)
        assert _llenado(pmf, s, Q) >= beta - 1e-9 and (s == 0 or _llenado(pmf, s - 1, Q) < beta + 1e-9), (mu, var, Q, beta, s)
        assert res.fill_rate == pytest.approx(_llenado(pmf, s, Q), abs=1e-7)


def test_con_media_grande_coincide_con_la_aproximacion_normal():
    discreto = wl.reorder_point_discrete(demand_rate=200, lead_time=2, service_level=0.95)  # Poisson, media 400
    normal = wl.reorder_point(demand_rate=200, lead_time=2, demand_std=math.sqrt(200), service_level=0.95)
    assert abs(discreto.reorder_point - normal.reorder_point) <= 2


def test_binomial_negativa_tiende_a_poisson_si_la_varianza_se_acerca_a_la_media():
    poisson = wl.reorder_point_discrete(demand_rate=2, lead_time=3, service_level=0.97)
    casi = wl.reorder_point_discrete(demand_rate=2, lead_time=3, demand_std=math.sqrt(2.0 * 1.0001), service_level=0.97)
    assert poisson.reorder_point == casi.reorder_point


def test_mayor_dispersion_exige_mas_stock():
    previo = 0.0
    for razon in (1.0, 2.0, 4.0, 8.0):
        sd = None if razon == 1.0 else math.sqrt(razon * 0.5)
        s = wl.reorder_point_discrete(0.5, 4, demand_std=sd, service_level=0.95).reorder_point
        assert s >= previo
        previo = s


def test_errores_de_demanda_discreta():
    with pytest.raises(ValueError, match="subdispers|varianza|variance"):
        wl.reorder_point_discrete(2.0, 3.0, demand_std=0.5)  # varianza 1,5 < media 6
    with pytest.raises(ValueError, match="reorder_point"):
        wl.reorder_point_discrete(1e6, 1.0)  # media demasiado grande
    with pytest.raises(ValueError, match="order_qty"):
        wl.reorder_point_discrete(1.0, 1.0, fill_rate=0.9)
    with pytest.raises(ValueError):
        wl.reorder_point_discrete(1.0, 1.0, service_level=1.0)
    with pytest.raises(ValueError):
        wl.reorder_point_discrete(-1.0, 1.0)


def test_resultado_discreto_summary_y_tabla():
    res = wl.reorder_point_discrete(0.5, 4, demand_std=1.5, fill_rate=0.98, order_qty=10)
    assert "binomial negativa" in res.summary() and "Tasa de llenado" in res.summary()
    assert len(res.to_frame()) == 1
