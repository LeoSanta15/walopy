"""Dimensionamiento de M/M/c+M con K clases (0.4.15): mínimo de servidores que cumple objetivos por clase.

Oráculo independiente de la búsqueda (bisección + crecimiento): barrido completo c = 1, 2, … con ``erlang_a_classes`` y ``erlang_a_classes_service_level``
(el mínimo es el primer c que cumple, ya que los indicadores mejoran con c); la cota inferior rigurosa por servidores ocupados; y la simulación contra lo exacto.
"""
import pytest

import walopy as wl
import walopy.advanced as adv
from walopy import erlang_a_classes, erlang_a_classes_servers, erlang_a_classes_service_level

LAM, MU, TH = [0.5, 1.5], [0.4, 0.25], [0.1, 1 / 3]


def _barrido(lam, mu, th, *, max_ab=None, min_sl=None, t=None, pw=None, c_max=80):
    """Primer c (barrido lineal) que cumple todos los objetivos con el modelo exacto."""
    k = len(lam)
    max_ab = max_ab or [None] * k
    min_sl = min_sl or [None] * k
    for c in range(1, c_max + 1):
        r = erlang_a_classes(lam, mu, th, c)
        ok = all(a is None or x["p_abandon"] <= a for a, x in zip(max_ab, r.classes))
        if ok and any(s is not None for s in min_sl):
            sl = erlang_a_classes_service_level(lam, mu, th, c, t=t)
            ok = all(s is None or v >= s for s, v in zip(min_sl, sl))
        if ok and pw is not None:
            ok = r.p_wait <= pw
        if ok:
            return c
    raise AssertionError("sin solución en el barrido")


@pytest.mark.parametrize("max_ab", [[0.01, 0.05], [0.02, None], [None, 0.03], [0.001, 0.2]])
def test_abandono_dos_clases_mu_distintos_coincide_con_el_barrido(max_ab):
    r = erlang_a_classes_servers(LAM, MU, TH, max_abandon=max_ab, method="exact")
    assert r.method == "exact"
    assert r.servers == _barrido(LAM, MU, TH, max_ab=max_ab)


def test_nivel_de_servicio_y_espera_coinciden_con_el_barrido():
    r = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.05, 0.1], min_service_level=[0.9, 0.7], t=0.5, max_wait_prob=0.6, method="exact")
    assert r.servers == _barrido(LAM, MU, TH, max_ab=[0.05, 0.1], min_sl=[0.9, 0.7], t=0.5, pw=0.6)
    assert r.p_wait <= 0.6 and r.p_wait_target == 0.6
    assert all(cl["ok"] for cl in r.classes)


def test_tres_clases_mu_comun_y_escalar_para_todas():
    lam, th = [0.7, 1.1, 1.6], [0.9, 0.5, 0.25]
    r = erlang_a_classes_servers(lam, 1.0, th, max_abandon=0.08, method="exact")
    assert r.servers == _barrido(lam, [1.0] * 3, th, max_ab=[0.08] * 3)
    assert r.result.servers == r.servers


def test_es_el_minimo_con_un_servidor_menos_incumple():
    r = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.01, 0.05], min_service_level=[None, 0.8], t=0.5, method="exact")
    c = r.servers
    menos = erlang_a_classes(LAM, MU, TH, c - 1)
    sl = erlang_a_classes_service_level(LAM, MU, TH, c - 1, t=0.5)
    assert menos.classes[0]["p_abandon"] > 0.01 or menos.classes[1]["p_abandon"] > 0.05 or sl[1] < 0.8
    assert r.lower_bound <= c


def test_cota_inferior_es_rigurosa_en_todos_los_casos():
    for ab in ([0.01, 0.05], [0.2, 0.3], [0.5, 0.5]):
        r = erlang_a_classes_servers(LAM, MU, TH, max_abandon=ab, method="exact")
        ocupados = sum(lam * (1 - a) / mu for lam, mu, a in zip(LAM, MU, ab))
        assert r.lower_bound == max(1, int(-(-ocupados // 1)))   # techo
        assert r.servers >= r.lower_bound
        # con c < cota el indicador no puede cumplir: con la cota − 1 el ocupado medio ya excede c
        if r.lower_bound > 1:
            menos = erlang_a_classes(LAM, MU, TH, r.lower_bound - 1)
            assert any(x["p_abandon"] > a for x, a in zip(menos.classes, ab))


@pytest.mark.parametrize("ab0", [0.002, 0.004, 0.006, 0.01, 0.02, 0.04, 0.08])
def test_traza_de_evaluaciones_es_coherente(ab0):
    """La traza prueba el tamaño elegido (cumple) y su anterior (incumple) o es la cota: es el mínimo, sin pasarse en la bisección."""
    r = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[ab0, 0.05], method="exact")
    tamanos = dict(r.evaluations)
    assert tamanos[r.servers] is True
    assert (r.servers - 1 in tamanos and tamanos[r.servers - 1] is False) or r.servers == r.lower_bound
    assert len(set(c for c, _ in r.evaluations)) == len(r.evaluations)


@pytest.mark.parametrize("pw", [0.2, 0.5, 0.8])
def test_solo_probabilidad_de_esperar_coincide_con_el_barrido(pw):
    r = erlang_a_classes_servers(LAM, MU, TH, max_wait_prob=pw, method="exact")
    assert r.servers == _barrido(LAM, MU, TH, pw=pw)
    assert r.p_wait <= pw < erlang_a_classes(LAM, MU, TH, r.servers - 1).p_wait


def test_cota_inferior_con_solo_nivel_de_servicio():
    r = erlang_a_classes_servers(LAM, MU, TH, min_service_level=0.9, t=0.5, method="exact")
    # P(abandono) ≤ 1 − nivel: servidores ocupados ≥ Σ λ(1 − 0.1)/μ = 6,525
    assert r.lower_bound == 7 and r.servers >= 7
    assert r.servers == _barrido(LAM, MU, TH, min_sl=[0.9, 0.9], t=0.5)


def test_simulacion_coincide_con_lo_exacto_con_un_servidor_de_margen():
    exacto = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.02, 0.06], method="exact")
    sim = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.02, 0.06], method="simulation", n_customers=60_000, n_replications=6)
    assert sim.method == "simulation"
    assert abs(sim.servers - exacto.servers) <= 1
    cons = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.02, 0.06], method="simulation", n_customers=60_000, n_replications=6, conservative=True)
    assert cons.servers >= sim.servers
    # el conservador exige el extremo adverso: con su c, estimación + semiancho cumple (mismos números aleatorios que la búsqueda)
    r = adv.monte_carlo_erlang_a(LAM, MU, TH, cons.servers, n_customers=60_000, n_replications=6, seed=12345)
    assert all(x["p_abandon"] + x["p_abandon_halfwidth"] <= a for x, a in zip(r.classes, [0.02, 0.06]))
    # y con un servidor menos no cumple (o es la cota inferior)
    if cons.servers > cons.lower_bound:
        r = adv.monte_carlo_erlang_a(LAM, MU, TH, cons.servers - 1, n_customers=60_000, n_replications=6, seed=12345)
        assert any(x["p_abandon"] + x["p_abandon_halfwidth"] > a for x, a in zip(r.classes, [0.02, 0.06]))


def test_conservador_exige_mas_servidores_que_la_estimacion_puntual():
    args = dict(max_abandon=[0.01, 0.05], min_service_level=[None, 0.8], t=1 / 3, n_customers=50_000, n_replications=6, seed=2026)
    punto = erlang_a_classes_servers([5.5, 16.5], MU, TH, **args)
    cons = erlang_a_classes_servers([5.5, 16.5], MU, TH, conservative=True, **args)
    assert cons.servers > punto.servers


def test_simulacion_es_reproducible_con_semilla():
    a = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.02, 0.06], method="simulation", n_customers=20_000, n_replications=4, seed=3)
    b = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.02, 0.06], method="simulation", n_customers=20_000, n_replications=4, seed=3)
    assert a.servers == b.servers and a.evaluations == b.evaluations


def test_auto_usa_exacto_cuando_aplica_y_simula_cuando_no():
    r = erlang_a_classes_servers(LAM, MU, TH, max_abandon=0.05)
    assert r.method == "exact"
    cuatro = erlang_a_classes_servers([0.5, 0.5, 0.5, 0.5], 1.0, [0.2] * 4, max_abandon=0.2, n_customers=20_000, n_replications=4)
    assert cuatro.method == "simulation"
    tres_distintos = erlang_a_classes_servers([0.5, 0.5, 0.5], [1.0, 0.8, 0.5], [0.2] * 3, max_abandon=0.2, n_customers=20_000, n_replications=4)
    assert tres_distintos.method == "simulation"


def test_auto_cae_a_simulacion_si_el_exacto_supera_su_cota(monkeypatch):
    monkeypatch.setattr(adv, "MAX_COSTE_CLASES", 10)
    monkeypatch.setattr(adv, "MAX_ELEMENTOS_PRIORIDAD", 10)
    r = erlang_a_classes_servers(LAM, MU, TH, max_abandon=0.05, n_customers=20_000, n_replications=4)
    assert r.method == "simulation"
    with pytest.raises(ValueError):
        erlang_a_classes_servers(LAM, MU, TH, max_abandon=0.05, method="exact")


def test_salida_to_frame_y_summary():
    r = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.01, None], min_service_level=[None, 0.8], t=0.5, max_wait_prob=0.7, method="exact")
    df = r.to_frame()
    assert len(df) == 2 and list(df.iloc[:, 0]) == [0, 1]
    assert df.iloc[0, 1] == 0.01 and df.iloc[1, 1] is None or df.iloc[1, 1] != df.iloc[1, 1]
    texto = str(r)
    assert str(r.servers) in texto and "P(esperar)" in texto and "exact" in texto


def test_en_ingles():
    wl.set_language("en")
    try:
        r = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.01, 0.05], method="exact")
        assert "Minimum staffing" in r.summary()
        assert "Max. abandonment" in list(r.to_frame().columns)
        with pytest.raises(ValueError, match="Give at least one target"):
            erlang_a_classes_servers(LAM, MU, TH)
        with pytest.raises(ValueError, match="'method' must be"):
            erlang_a_classes_servers(LAM, MU, TH, max_abandon=0.05, method="x")
    finally:
        wl.set_language("es")


@pytest.mark.parametrize("kw, exc", [
    (dict(), ValueError),                                                          # sin objetivo
    (dict(max_abandon=0.0), ValueError), (dict(max_abandon=1.0), ValueError), (dict(max_abandon=-0.1), ValueError),
    (dict(max_abandon=[0.1]), ValueError), (dict(max_abandon=[0.1, 0.1, 0.1]), ValueError),
    (dict(max_abandon="a"), TypeError), (dict(max_abandon=True), TypeError), (dict(max_abandon=[0.1, "x"]), TypeError),
    (dict(max_wait_prob=0.0), ValueError), (dict(max_wait_prob=1.5), ValueError),
    (dict(min_service_level=0.9), ValueError),                                     # falta t
    (dict(min_service_level=0.9, t=-1.0), ValueError),
    (dict(max_abandon=0.1, method="otro"), ValueError),
    (dict(max_abandon=0.1, c_max=0), ValueError), (dict(max_abandon=0.1, c_max=1.5), TypeError),
])
def test_validacion(kw, exc):
    with pytest.raises(exc):
        erlang_a_classes_servers(LAM, MU, TH, **kw)


def test_inalcanzable_con_c_max_pequeno():
    with pytest.raises(ValueError, match="c_max"):
        erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.001, 0.001], c_max=3, method="exact")


def test_objetivo_trivial_devuelve_la_cota_inferior():
    r = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.99, 0.99], method="exact")
    assert r.servers == r.lower_bound
    assert r.evaluations == [(r.lower_bound, True)]


def test_dos_clases_bien_servidas_con_mas_servidores_no_cumplen_al_reves():
    # si endurece el objetivo de una clase, la dotación no puede disminuir
    laxo = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.05, 0.1], method="exact").servers
    duro = erlang_a_classes_servers(LAM, MU, TH, max_abandon=[0.005, 0.1], method="exact").servers
    assert duro >= laxo
