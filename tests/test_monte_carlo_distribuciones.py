"""Distribuciones no exponenciales en ``monte_carlo_erlang_a`` (0.5.0): llegadas de renovación, servicio y paciencia generales.

Oráculos independientes de la implementación: los momentos de cada familia; el caso exponencial, que debe dar lo de siempre bit a bit y lo de ``erlang_a``;
M/G/1 (Pollaczek-Khinchine, ``mg1``) para el servicio; G/M/1 (la raíz σ = A*(μ(1 − σ))) para las llegadas; la insensibilidad de Erlang B (con paciencia casi nula
el bloqueo no depende de la forma del servicio); y una simulación de eventos escrita aparte, con abandonos como eventos y el generador de ``random``.
"""
import heapq
import math
import random

import numpy as np
import pytest

import walopy as wl
import walopy.advanced as adv
from walopy.advanced import _distribuciones, _llegadas, _muestrear, _unitaria

MU, TH, LAM = 1.0, 0.2, 9.0


def _cerca(est, hw, ref, k=3.0, extra=0.0):
    assert abs(est - ref) <= k * hw + extra, f"{est} ± {hw} vs {ref}"


# --- las familias --------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("familia, cv2", [("exponential", 1.0), ("deterministic", 0.0), ("gamma", 0.25), ("gamma", 1.0), ("gamma", 3.0),
                                          ("hyperexponential", 1.0), ("hyperexponential", 4.0), ("hyperexponential", 9.0)])
def test_media_uno_y_cv2_pedido(familia, cv2):
    x = _unitaria(np.random.default_rng(5), familia, cv2, 1_500_000)
    assert x.min() >= 0.0
    assert x.mean() == pytest.approx(1.0, rel=0.01)
    assert x.var() == pytest.approx(cv2, rel=0.05, abs=1e-12)


@pytest.mark.parametrize("cv2", [0.3, 1.0, 2.0, 4.0, 10.0])
def test_lognormal_media_uno_y_momentos_del_logaritmo(cv2):
    x = _unitaria(np.random.default_rng(9), "lognormal", cv2, 2_000_000)
    s2 = math.log1p(cv2)
    assert x.mean() == pytest.approx(1.0, rel=0.03)
    assert np.log(x).mean() == pytest.approx(-0.5 * s2, abs=0.01)
    assert np.log(x).var() == pytest.approx(s2, rel=0.01)


def test_la_media_la_fija_la_tasa_de_cada_clase():
    clase = np.array([0, 1] * 400_000)
    x = _muestrear(np.random.default_rng(1), [("gamma", 0.5), ("lognormal", 2.0)], clase, [4.0, 0.5], clase.size)
    assert x[clase == 0].mean() == pytest.approx(0.25, rel=0.01)
    assert x[clase == 1].mean() == pytest.approx(2.0, rel=0.03)


# --- el caso exponencial -------------------------------------------------------------------------------------------------------------------------------

ARGS = ([0.5, 1.5], [0.4, 0.25], [0.1, 1 / 3], 6)


def _firma(r):
    return [r.p_wait] + [(x["p_abandon"], x["Wq"], x["service_level"], x["p_abandon_halfwidth"]) for x in r.classes]


def test_exponencial_explicito_da_lo_mismo_que_no_indicarlo_bit_a_bit():
    kw = dict(n_customers=20_000, n_replications=3, t=0.5, seed=11)
    base = _firma(wl.monte_carlo_erlang_a(*ARGS, **kw))
    assert _firma(wl.monte_carlo_erlang_a(*ARGS, **kw, arrivals="exponential", service="exponential", patience="exponential")) == base
    assert _firma(wl.monte_carlo_erlang_a(*ARGS, **kw, arrivals=None, service=[None, "exponential"], patience=("exponential", 1.0))) == base


@pytest.mark.parametrize("spec", [("gamma", 1.0), ("hyperexponential", 1.0)])
def test_familias_con_cv2_uno_son_exponenciales_y_coinciden_con_erlang_a(spec):
    exacto = wl.erlang_a(LAM, MU, TH, 10)
    sl = wl.erlang_a_service_level(LAM, MU, TH, 10, t=0.5)
    for kw in (dict(service=spec), dict(patience=spec), dict(arrivals=spec)):
        r = wl.monte_carlo_erlang_a([LAM], MU, TH, 10, n_customers=150_000, n_replications=8, t=0.5, seed=4, **kw)
        x = r.classes[0]
        _cerca(x["p_abandon"], x["p_abandon_halfwidth"], exacto.params["P(abandono)"], k=2.5)
        _cerca(x["service_level"], x["service_level_halfwidth"], sl, k=2.5)


# --- oráculos clásicos ---------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("servicio, cs2", [("deterministic", 0.0), (("gamma", 0.5), 0.5), (("lognormal", 2.0), 2.0), (("hyperexponential", 4.0), 4.0)])
def test_servicio_general_con_un_servidor_coincide_con_mg1(servicio, cs2):
    r = wl.monte_carlo_erlang_a([0.6], 1.0, 1e-9, 1, n_customers=400_000, n_replications=8, seed=2, service=servicio)
    x = r.classes[0]
    assert x["p_abandon"] == 0.0
    _cerca(x["Wq"], x["wq_halfwidth"], wl.mg1(0.6, 1.0, cs2).Wq, k=3.0)


def _sigma(lst, mu):
    """Raíz de σ = A*(μ(1 − σ)) en (0, 1) por iteración (G/M/1)."""
    s = 0.5
    for _ in range(20_000):
        nuevo = lst(mu * (1.0 - s))
        if abs(nuevo - s) < 1e-14:
            break
        s = nuevo
    return s


@pytest.mark.parametrize("llegadas", ["deterministic", ("gamma", 0.5), ("hyperexponential", 4.0)])
def test_llegadas_generales_con_un_servidor_coinciden_con_gm1(llegadas):
    lam, mu = 0.7, 1.0
    if llegadas == "deterministic":
        lst = lambda s: math.exp(-s / lam)                                   # noqa: E731
    elif llegadas[0] == "gamma":
        k = 1.0 / llegadas[1]
        lst = lambda s: (1.0 + s / (k * lam)) ** (-k)                        # noqa: E731
    else:
        p1 = 0.5 * (1.0 + math.sqrt((llegadas[1] - 1.0) / (llegadas[1] + 1.0)))
        r1, r2 = 2 * p1 * lam, 2 * (1 - p1) * lam
        lst = lambda s: p1 * r1 / (r1 + s) + (1 - p1) * r2 / (r2 + s)        # noqa: E731
    sigma = _sigma(lst, mu)
    r = wl.monte_carlo_erlang_a([lam], mu, 1e-9, 1, n_customers=400_000, n_replications=8, seed=3, arrivals=llegadas)
    x = r.classes[0]
    _cerca(x["Wq"], x["wq_halfwidth"], sigma / (mu * (1.0 - sigma)), k=3.0)


@pytest.mark.parametrize("servicio", ["deterministic", ("gamma", 0.3), ("lognormal", 4.0), ("hyperexponential", 6.0)])
def test_insensibilidad_de_erlang_b_con_paciencia_casi_nula(servicio):
    r = wl.monte_carlo_erlang_a([8.0], 1.0, 1e7, 10, n_customers=300_000, n_replications=8, seed=6, service=servicio)
    x = r.classes[0]
    _cerca(x["p_abandon"], x["p_abandon_halfwidth"], wl.erlang_b(8.0, 1.0, 10), k=3.0)


# --- contra una simulación escrita aparte --------------------------------------------------------------------------------------------------------------

def _muestra(rng, familia, cv2, media):
    if familia == "exponential":
        return rng.expovariate(1.0 / media)
    if familia == "deterministic":
        return media
    if familia == "gamma":
        return rng.gammavariate(1.0 / cv2, media * cv2)
    if familia == "lognormal":
        s2 = math.log(1.0 + cv2)
        return rng.lognormvariate(math.log(media) - s2 / 2.0, math.sqrt(s2))
    raise AssertionError(familia)


def _referencia(lams, mus, ths, c, n, semilla, llegadas, servicio, paciencia, warm):
    """Eventos explícitos (llegada, salida y vencimiento de la paciencia) con colas por clase; devuelve P(abandono) y Wq por clase."""
    rng = random.Random(semilla)
    k = len(lams)
    ev = []
    for j in range(k):
        t0 = _muestra(rng, *llegadas[j], 1.0 / lams[j])
        heapq.heappush(ev, (t0, 0, j, -1))                                  # (instante, tipo: 0 llegada / 1 salida / 2 vence, clase, id)
    colas = [dict() for _ in range(k)]                                      # id → instante de llegada (orden de inserción = orden de llegada)
    libres, nid, vistos = c, 0, 0
    datos = {}
    resumen = [[0, 0, 0.0] for _ in range(k)]                               # llegadas medidas, abandonos, espera total
    while vistos < n:
        t, tipo, j, ident = heapq.heappop(ev)
        if tipo == 0:
            heapq.heappush(ev, (t + _muestra(rng, *llegadas[j], 1.0 / lams[j]), 0, j, -1))
            nid += 1
            i = nid
            medir = i > warm
            if medir:
                resumen[j][0] += 1
            vistos = max(vistos, i)
            if libres > 0:
                libres -= 1
                heapq.heappush(ev, (t + _muestra(rng, *servicio[j], 1.0 / mus[j]), 1, j, -1))
            else:
                colas[j][i] = t
                datos[i] = (j, medir)
                heapq.heappush(ev, (t + _muestra(rng, *paciencia[j], 1.0 / ths[j]), 2, j, i))
        elif tipo == 2:
            if ident in colas[j]:
                t_llega = colas[j].pop(ident)
                if datos[ident][1]:
                    resumen[j][1] += 1
                    resumen[j][2] += t - t_llega
        else:
            for kk in range(k):
                if colas[kk]:
                    ident2 = next(iter(colas[kk]))
                    t_llega = colas[kk].pop(ident2)
                    if datos[ident2][1]:
                        resumen[kk][2] += t - t_llega
                    heapq.heappush(ev, (t + _muestra(rng, *servicio[kk], 1.0 / mus[kk]), 1, kk, -1))
                    break
            else:
                libres += 1
    return [(r[1] / r[0], r[2] / r[0]) for r in resumen]


def test_dos_clases_con_distribuciones_mixtas_coinciden_con_la_simulacion_de_referencia():
    lams, mus, ths, c = [1.2, 3.0], [0.5, 0.8], [0.15, 0.4], 7
    llegadas = [("gamma", 0.5), ("exponential", 1.0)]
    servicio = [("lognormal", 2.0), ("gamma", 0.5)]
    paciencia = [("deterministic", 0.0), ("lognormal", 3.0)]
    r = wl.monte_carlo_erlang_a(lams, mus, ths, c, n_customers=60_000, n_replications=8, seed=21, arrivals=[("gamma", 0.5), None],
                                service=[("lognormal", 2.0), ("gamma", 0.5)], patience=["deterministic", ("lognormal", 3.0)])
    refs = [_referencia(lams, mus, ths, c, 60_000, 1000 + s, llegadas, servicio, paciencia, 6_000) for s in range(8)]
    for j in range(2):
        for idx, clave, hw in ((0, "p_abandon", "p_abandon_halfwidth"), (1, "Wq", "wq_halfwidth")):
            v = np.array([ref[j][idx] for ref in refs])
            hw_ref = 2.365 * v.std(ddof=1) / math.sqrt(len(v))
            x = r.classes[j]
            assert abs(x[clave] - v.mean()) <= 2.0 * math.hypot(x[hw], hw_ref) + 1e-4, (j, clave, x[clave], v.mean())


# --- propiedades ---------------------------------------------------------------------------------------------------------------------------------------

def test_mas_variabilidad_del_servicio_empeora_el_servicio():
    ab = []
    for servicio in ("deterministic", ("gamma", 0.5), None, ("lognormal", 4.0)):
        r = wl.monte_carlo_erlang_a([LAM], MU, TH, 10, n_customers=150_000, n_replications=8, t=0.5, seed=3, service=servicio)
        ab.append((r.classes[0]["p_abandon"], r.classes[0]["service_level"]))
    assert [a for a, _ in ab] == sorted(a for a, _ in ab)
    assert [s for _, s in ab] == sorted((s for _, s in ab), reverse=True)


def test_paciencia_determinista_casi_no_abandona_con_la_misma_media():
    r = wl.monte_carlo_erlang_a([LAM], MU, TH, 10, n_customers=150_000, n_replications=8, seed=3, patience="deterministic")
    assert r.classes[0]["p_abandon"] < 0.005 < wl.erlang_a(LAM, MU, TH, 10).params["P(abandono)"]


# --- las llegadas de renovación ------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("especs", [[("gamma", 0.5), ("hyperexponential", 4.0)], [("deterministic", 0.0), ("exponential", 1.0)]])
def test_llegadas_ordenadas_con_la_mezcla_y_los_intervalos_de_cada_clase(especs):
    lams = [2.0, 0.5]
    llegada, clase = _llegadas(np.random.default_rng(3), lams, especs, 400_000)
    assert llegada.shape == clase.shape == (400_000,)
    assert np.all(np.diff(llegada) >= 0)
    assert np.mean(clase == 1) == pytest.approx(0.5 / 2.5, rel=0.03)
    for k, (lam_k, (_familia, cv2)) in enumerate(zip(lams, especs)):
        intervalos = np.diff(llegada[clase == k])
        assert intervalos.mean() == pytest.approx(1.0 / lam_k, rel=0.02)
        assert (intervalos.var() * lam_k ** 2) == pytest.approx(cv2, rel=0.08, abs=1e-9)


def test_llegadas_cuando_una_clase_necesita_mas_horizonte(monkeypatch):
    """Si la clase rápida se queda sin llegadas antes de la n-ésima de la mezcla, se amplía el horizonte y no se pierden llegadas de esa clase."""
    llamadas = []

    def falsa(rng, familia, cv2, n):
        llamadas.append(n)
        return np.full(n, 2.0 if len(llamadas) % 2 == 1 else 0.25)       # clase 0 lenta (cada 2), clase 1 rápida (cada 0.25)

    monkeypatch.setattr(adv, "_unitaria", falsa)
    llegada, clase = _llegadas(np.random.default_rng(0), [1.0, 1.0], [("gamma", 1.0), ("gamma", 1.0)], 300)
    assert len(llamadas) > 2                                              # hubo al menos una ampliación
    for k, paso in ((0, 2.0), (1, 0.25)):
        assert np.sum(clase == k) == int(llegada[-1] / paso + 1e-9)       # todas las llegadas de la clase hasta la última de la mezcla
    assert llegada.shape == (300,) and np.all(np.diff(llegada) >= 0)


def test_llegadas_con_cv2_extremo():
    llegada, clase = _llegadas(np.random.default_rng(8), [1.0, 1.0], [("lognormal", 1000.0), ("exponential", 1.0)], 2_000)
    assert llegada.shape == (2_000,) and np.all(np.diff(llegada) >= 0)
    assert set(np.unique(clase)) == {0, 1}


def test_llegadas_simultaneas_respetan_la_prioridad_de_clase():
    llegada, clase = _llegadas(np.random.default_rng(0), [1.0, 1.0], [("deterministic", 0.0), ("deterministic", 0.0)], 10)
    assert list(clase) == [0, 1] * 5 and np.all(np.diff(llegada) >= 0)


# --- validación y presentación ----------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("malo, exc", [
    ("poisson", ValueError), ("Gamma", ValueError), (("gamma",), ValueError), (("gamma", None), ValueError), ("gamma", ValueError), (("gamma", 0.0), ValueError),
    (("gamma", -1.0), ValueError), (("gamma", float("nan")), ValueError), (("gamma", float("inf")), ValueError), (("gamma", "a"), ValueError), (("gamma", True), TypeError),
    (("lognormal", 2e4), ValueError), (("hyperexponential", 0.5), ValueError), (("exponential", 2.0), ValueError), (("deterministic", 1.0), ValueError),
    (5, TypeError), (2.5, TypeError), (True, TypeError), (b"gamma", TypeError), ({"gamma": 1.0}, TypeError),
    (["exponential"], ValueError), (["exponential"] * 3, ValueError), ([("gamma", 1.0), 7], TypeError), ([["gamma", 1.0], "exponential"], TypeError),
])
@pytest.mark.parametrize("argumento", ["arrivals", "service", "patience"])
def test_validacion_de_distribuciones(argumento, malo, exc):
    with pytest.raises(exc):
        wl.monte_carlo_erlang_a([0.5, 1.5], 1.0, 0.3, 4, n_customers=1000, n_replications=2, seed=1, **{argumento: malo})


def test_especificaciones_validas_y_normalizacion():
    assert _distribuciones(None, "service", 2) == [("exponential", 1.0)] * 2
    assert _distribuciones("deterministic", "service", 2) == [("deterministic", 0.0)] * 2
    assert _distribuciones(("gamma", 2), "service", 3) == [("gamma", 2.0)] * 3
    assert _distribuciones(["exponential", ("lognormal", 4.0)], "service", 2) == [("exponential", 1.0), ("lognormal", 4.0)]
    assert _distribuciones((None, ("gamma", 0.5)), "service", 2) == [("exponential", 1.0), ("gamma", 0.5)]
    assert _distribuciones(np.array([None, "deterministic"], dtype=object), "service", 2) == [("exponential", 1.0), ("deterministic", 0.0)]


def test_resultado_guarda_las_distribuciones_y_el_resumen_las_muestra():
    r = wl.monte_carlo_erlang_a([0.5, 1.5], 1.0, 0.3, 4, n_customers=5_000, n_replications=2, seed=1, service=[("lognormal", 2.0), "deterministic"], patience=("gamma", 0.5))
    assert r.service == [("lognormal", 2.0), ("deterministic", 0.0)]
    assert r.patience == [("gamma", 0.5)] * 2 and r.arrivals == [("exponential", 1.0)] * 2
    texto = str(r)
    assert "G/G/4+G" in texto and "servicio [lognormal(CV²=2), deterministic]" in texto and "paciencia gamma(CV²=0.5)" in texto and "llegadas exponential" in texto
    clasico = str(wl.monte_carlo_erlang_a([0.5, 1.5], 1.0, 0.3, 4, n_customers=5_000, n_replications=2, seed=1))
    assert "M/M/4+M" in clasico and "Distribuciones" not in clasico


def test_resumen_en_ingles():
    wl.set_language("en")
    try:
        r = wl.monte_carlo_erlang_a([1.0], 1.0, 0.3, 2, n_customers=3_000, n_replications=2, seed=1, service=("lognormal", 2.0))
        assert "G/G/2+G simulation" in str(r) and "Distributions (with mean" in str(r)
        with pytest.raises(ValueError, match="does not exist"):
            wl.monte_carlo_erlang_a([1.0], 1.0, 0.3, 2, n_customers=3_000, n_replications=2, service="otra")
    finally:
        wl.set_language("es")


# --- dotación con distribuciones generales -----------------------------------------------------------------------------------------------------------

def test_dotacion_con_distribuciones_generales_siempre_simula():
    args = ([4.0, 12.0], 1.0, [0.1, 0.3])
    kw = dict(max_abandon=0.03, n_customers=40_000, n_replications=6)
    exacto = wl.erlang_a_classes_servers(*args, **kw)
    assert exacto.method == "exact"
    det = wl.erlang_a_classes_servers(*args, **kw, service="deterministic")
    hip = wl.erlang_a_classes_servers(*args, **kw, service=("hyperexponential", 6.0))
    assert det.method == hip.method == "simulation"
    assert det.servers < exacto.servers < hip.servers
    with pytest.raises(ValueError, match="exponenciales"):
        wl.erlang_a_classes_servers(*args, **kw, service="deterministic", method="exact")
    with pytest.raises(ValueError):
        wl.erlang_a_classes_servers(*args, **kw, patience="nada")
    pac = wl.erlang_a_classes_servers(*args, **kw, patience="deterministic")
    assert pac.method == "simulation" and pac.servers < exacto.servers
