"""G/G/c (Allen-Cunneen), variabilidad de las salidas y línea serial (0.4.7).

Oráculos independientes: los casos límite exactos (Kingman con un servidor, M/M/c con ca² = cs² = 1, M/D/1) y simulaciones de eventos
discretos escritas aquí (multiservidor con ``heapq``; colas en serie con la recursión de Lindley), no el código de ``walopy``.
"""
from __future__ import annotations

import heapq
import math

import numpy as np
import pytest

import walopy as wl


def _gamma(rng, media: float, cv2: float, n: int) -> np.ndarray:
    return np.full(n, media) if cv2 < 1e-12 else rng.gamma(1 / cv2, media * cv2, n)


def _simular_ggc(lam, mu, c, ca2, cs2, n=250_000, descartar=5_000, seed=1) -> float:
    """Wq medio de una cola G/G/c FIFO por simulación de eventos (servidores en un heap de instantes de liberación)."""
    rng = np.random.default_rng(seed)
    llegadas = np.cumsum(_gamma(rng, 1 / lam, ca2, n))
    servicios = _gamma(rng, 1 / mu, cs2, n)
    libres = [0.0] * c
    esperas = np.empty(n)
    for i in range(n):
        t = heapq.heappop(libres)
        inicio = max(llegadas[i], t)
        esperas[i] = inicio - llegadas[i]
        heapq.heappush(libres, inicio + servicios[i])
    return float(esperas[descartar:].mean())


# --------------------------------------------------------------------------------------------- casos límite exactos
def test_con_un_servidor_ggc_es_kingman():
    for lam, ca2, cs2 in ((0.5, 1.0, 1.0), (0.8, 2.0, 0.5), (0.3, 0.0, 3.0)):
        assert wl.ggc(lam, 1.0, 1, ca2, cs2).Wq == pytest.approx(wl.kingman(lam, 1.0, ca2, cs2).Wq, rel=1e-12)


def test_con_variabilidad_exponencial_ggc_es_mmc():
    for lam, c in ((2.0, 3), (7.5, 10), (0.9, 1)):
        g, m = wl.ggc(lam, 1.0 if c > 1 else 1.0, c, 1.0, 1.0), wl.mmc(lam, 1.0, c)
        assert (g.Wq, g.L, g.Lq, g.W, g.rho) == pytest.approx((m.Wq, m.L, m.Lq, m.W, m.rho), rel=1e-12)


def test_llegadas_de_poisson_y_servicio_determinista_un_servidor_es_md1():
    assert wl.ggc(0.7, 1.0, 1, 1.0, 0.0).Wq == pytest.approx(wl.md1(0.7, 1.0).Wq, rel=1e-12)


def test_ley_de_little_y_relaciones_internas():
    r = wl.ggc(5.0, 2.0, 4, 1.5, 0.7)
    assert r.Lq == pytest.approx(r.lam * r.Wq) and r.L == pytest.approx(r.lam * r.W) and r.W == pytest.approx(r.Wq + 1 / r.mu)


def test_mas_variabilidad_mas_espera_y_mas_servidores_menos_espera():
    assert wl.ggc(2.0, 1.0, 3, 2.0, 2.0).Wq > wl.ggc(2.0, 1.0, 3, 1.0, 1.0).Wq > wl.ggc(2.0, 1.0, 3, 0.2, 0.2).Wq
    assert wl.ggc(3.0, 1.0, 4, 1.0, 0.5).Wq > wl.ggc(3.0, 1.0, 5, 1.0, 0.5).Wq


# --------------------------------------------------------------------------------------------- contra simulación
@pytest.mark.parametrize("lam,mu,c,ca2,cs2", [
    (2.1, 1.0, 3, 1.0, 0.5),    # ρ = 0,70, servicio Erlang-2
    (3.4, 1.0, 4, 0.5, 1.0),    # ρ = 0,85
    (1.4, 1.0, 2, 2.0, 1.0),    # ρ = 0,70, llegadas variables
])
def test_allen_cunneen_coincide_con_la_simulacion_con_error_moderado(lam, mu, c, ca2, cs2):
    simulado = _simular_ggc(lam, mu, c, ca2, cs2)
    aproximado = wl.ggc(lam, mu, c, ca2, cs2).Wq
    assert aproximado == pytest.approx(simulado, rel=0.12), (aproximado, simulado)


# --------------------------------------------------------------------------------------------- variabilidad de salidas
def test_ecuacion_de_enlace_casos_limite():
    assert wl.departure_cv2(1e-6, 1.0, 1, 3.0, 0.2) == pytest.approx(3.0, abs=1e-4)      # sin carga: salidas = llegadas
    assert wl.departure_cv2(0.999999, 1.0, 1, 3.0, 0.2) == pytest.approx(0.2, abs=1e-4)  # saturada: salidas = servicio
    assert wl.departure_cv2(0.8, 1.0, 1, 1.0, 1.0) == pytest.approx(1.0)                 # M/M/1: Burke, salidas de Poisson
    assert wl.departure_cv2(2.1, 1.0, 3, 1.0, 1.0) == pytest.approx(1.0)                 # M/M/c también
    assert wl.departure_cv2(0.8, 1.0, 1, 2.0, 0.5) == pytest.approx(0.8**2 * 0.5 + (1 - 0.8**2) * 2.0)   # Hopp-Spearman


def test_la_variabilidad_de_salida_coincide_con_la_simulada_en_un_servidor():
    lam, mu, ca2, cs2, n = 0.8, 1.0, 2.0, 0.5, 400_000
    rng = np.random.default_rng(5)
    llegadas = np.cumsum(_gamma(rng, 1 / lam, ca2, n))
    servicios = _gamma(rng, 1 / mu, cs2, n)
    salidas = np.empty(n)
    previa = 0.0
    for i in range(n):
        previa = max(llegadas[i], previa) + servicios[i]
        salidas[i] = previa
    intervalos = np.diff(salidas[5_000:])
    cd2_simulado = float(intervalos.var() / intervalos.mean() ** 2)
    # es una aproximación: aquí la simulación da ≈ 0,96 frente a 1,04 (≈ 8 %); se exige el mismo orden de magnitud y el sentido correcto
    assert wl.departure_cv2(lam, mu, 1, ca2, cs2) == pytest.approx(cd2_simulado, rel=0.12)
    assert min(cs2, ca2) < cd2_simulado < max(cs2, ca2)


def _cd2_simulado_multiservidor(lam, mu, c, ca2, cs2, n=400_000, seed=3) -> float:
    rng = np.random.default_rng(seed)
    llegadas = np.cumsum(_gamma(rng, 1 / lam, ca2, n))
    servicios = _gamma(rng, 1 / mu, cs2, n)
    libres = [0.0] * c
    salidas = np.empty(n)
    for i in range(n):
        inicio = max(llegadas[i], heapq.heappop(libres))
        salidas[i] = inicio + servicios[i]
        heapq.heappush(libres, salidas[i])
    salidas.sort()                       # con varios servidores las salidas no salen en el orden de llegada
    intervalos = np.diff(salidas[5_000:])
    return float(intervalos.var() / intervalos.mean() ** 2)


@pytest.mark.parametrize("lam,mu,c,ca2,cs2", [(2.1, 1.0, 3, 1.0, 0.5), (2.8, 1.0, 4, 1.0, 2.0)])
def test_la_ecuacion_de_enlace_multiservidor_coincide_con_la_simulacion_y_necesita_la_raiz_de_c(lam, mu, c, ca2, cs2):
    rho = lam / (c * mu)
    formula = 1 + (1 - rho**2) * (ca2 - 1) + rho**2 * (cs2 - 1) / math.sqrt(c)          # escrita aquí, a mano (Whitt)
    sin_raiz = 1 + (1 - rho**2) * (ca2 - 1) + rho**2 * (cs2 - 1)                         # la variante de un servidor, que no vale con c > 1
    simulado = _cd2_simulado_multiservidor(lam, mu, c, ca2, cs2)
    assert wl.departure_cv2(lam, mu, c, ca2, cs2) == pytest.approx(formula, rel=1e-12)
    assert formula == pytest.approx(simulado, rel=0.08)
    assert abs(formula - simulado) < abs(sin_raiz - simulado)


# --------------------------------------------------------------------------------------------- línea serial
def test_linea_serial_exponencial_coincide_con_jackson():
    nombres, mu, servers, lam = ["A", "B", "C"], [1.5, 1.2, 2.0], [1, 2, 1], 0.9
    linea = wl.serial_line(nombres, mu, lam=lam, servers=servers)
    red = wl.jackson_network(nombres, mu, [lam, 0.0, 0.0], [[0, 1, 0], [0, 0, 1], [0, 0, 0]], servers=servers)
    assert linea.cycle_time == pytest.approx(red.W_system, rel=1e-12)
    assert linea.wip == pytest.approx(red.L_system, rel=1e-12)
    assert all(s.cd2 == pytest.approx(1.0) for s in linea.stations)


def test_linea_serial_contra_simulacion_de_colas_en_serie():
    lam, mus, cs2s, ca2 = 0.7, [1.0, 0.9, 1.1], [0.5, 2.0, 1.0], 1.0
    n = 300_000
    rng = np.random.default_rng(11)
    llegada = np.cumsum(_gamma(rng, 1 / lam, ca2, n))
    t_entrada = llegada.copy()
    for mu, cs2 in zip(mus, cs2s):
        servicio = _gamma(rng, 1 / mu, cs2, n)
        salida = np.empty(n)
        previa = 0.0
        for i in range(n):
            previa = max(t_entrada[i], previa) + servicio[i]
            salida[i] = previa
        t_entrada = salida
    ciclo_simulado = float((t_entrada - llegada)[5_000:].mean())
    r = wl.serial_line(["A", "B", "C"], mus, lam=lam, ca2=ca2, cs2=cs2s)
    assert r.cycle_time == pytest.approx(ciclo_simulado, rel=0.10), (r.cycle_time, ciclo_simulado)


def test_linea_serial_cuello_de_botella_little_y_encadenamiento():
    r = wl.serial_line(["Corte", "Soldadura"], mu=[1.0, 0.8], lam=0.6, cs2=[0.5, 2.0])
    assert r.bottleneck == "Soldadura"
    assert r.wip == pytest.approx(r.lam * r.cycle_time) == pytest.approx(sum(s.L for s in r.stations))
    assert r.stations[1].ca2 == pytest.approx(r.stations[0].cd2)           # las salidas de una estación son las llegadas de la siguiente
    assert r.ca2_out == pytest.approx(r.stations[-1].cd2)
    assert len(r.to_frame()) == 2 and "Cuello de botella" in r.summary()


def test_mas_variabilidad_en_cualquier_estacion_alarga_el_ciclo():
    base = wl.serial_line(["A", "B"], [1.0, 1.0], lam=0.7, cs2=[1.0, 1.0]).cycle_time
    assert wl.serial_line(["A", "B"], [1.0, 1.0], lam=0.7, cs2=[3.0, 1.0]).cycle_time > base
    assert wl.serial_line(["A", "B"], [1.0, 1.0], lam=0.7, cs2=[1.0, 3.0]).cycle_time > base


# --------------------------------------------------------------------------------------------- errores
def test_errores():
    with pytest.raises(ValueError, match="inestable|Unstable"):
        wl.ggc(3.0, 1.0, 3, 1.0, 1.0)
    with pytest.raises(ValueError):
        wl.departure_cv2(3.0, 1.0, 3, 1.0, 1.0)
    with pytest.raises(ValueError) as e:
        wl.serial_line(["A", "B"], [1.0, 0.5], lam=0.6)
    assert "'B'" in str(e.value)
    with pytest.raises(ValueError, match="longitud"):
        wl.serial_line(["A", "B"], [1.0], lam=0.5)
    with pytest.raises(ValueError):
        wl.serial_line(["A", "B"], [1.0, 1.0], lam=0.5, cs2=[1.0])
    with pytest.raises(TypeError):
        wl.ggc("x", 1.0, 2, 1.0, 1.0)  # type: ignore[arg-type]
    assert math.isfinite(wl.ggc(0.1, 1.0, 1, 0.0, 0.0).Wq)
