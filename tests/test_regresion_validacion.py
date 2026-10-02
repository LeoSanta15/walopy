"""Regresiones de la auditoría 2026-10 (hallazgos K-xx / N-xx): validación de entradas y casos borde."""
from __future__ import annotations

import pytest

import walopy as wl

NAN, INF = float("nan"), float("inf")
NO_FINITOS_O_NEGATIVOS = [NAN, INF, -INF, -1.0]


# ─── K-01: NaN/inf/negativos deben rechazarse (la comparación con NaN es siempre falsa) ──────────

@pytest.mark.parametrize("malo", NO_FINITOS_O_NEGATIVOS)
def test_cpm_rechaza_duracion_no_valida(malo):
    with pytest.raises(ValueError, match="duration"):
        wl.cpm([{"name": "A", "duration": malo, "predecessors": []}])


@pytest.mark.parametrize("malo", [NAN, INF, -INF])
def test_pert_rechaza_estimaciones_no_finitas(malo):
    with pytest.raises(ValueError):
        wl.pert([{"name": "A", "optimistic": malo, "most_likely": 2, "pessimistic": 3, "predecessors": []}])


@pytest.mark.parametrize("malo", NO_FINITOS_O_NEGATIVOS)
@pytest.mark.parametrize("campo", ["t", "mttr"])
def test_mtbf_rechaza_t_y_mttr_no_validos(malo, campo):
    with pytest.raises(ValueError, match=campo):
        wl.mtbf_analysis(0.01, **{campo: malo})


@pytest.mark.parametrize("malo", NO_FINITOS_O_NEGATIVOS)
@pytest.mark.parametrize("fn", ["series_system", "parallel_system"])
@pytest.mark.parametrize("campo", ["t", "mttr"])
def test_sistemas_rechazan_t_y_mttr_no_validos(fn, malo, campo):
    with pytest.raises(ValueError, match=campo):
        getattr(wl, fn)([0.01, 0.02], **{campo: malo})


@pytest.mark.parametrize("malo", NO_FINITOS_O_NEGATIVOS)
@pytest.mark.parametrize("campo", ["t", "mttr"])
def test_koon_rechaza_t_y_mttr_no_validos(malo, campo):
    with pytest.raises(ValueError, match=campo):
        wl.koon_system(3, 2, 0.01, **{campo: malo})


def test_confiabilidad_nunca_supera_uno():
    assert wl.mtbf_analysis(0.01, t=0.0).R_t == pytest.approx(1.0)
    assert 0.0 <= wl.mtbf_analysis(0.01, t=50.0, mttr=2.0).availability <= 1.0


@pytest.mark.parametrize("malo", [NAN, INF, -INF, -1.0])
def test_mrp_rechaza_existencia_inicial_no_valida(malo):
    with pytest.raises(ValueError, match="initial_on_hand"):
        wl.mrp([10, 20, 30], initial_on_hand=malo)


@pytest.mark.parametrize("malo", [NAN, INF])
def test_weibull_rechaza_tiempos_no_finitos(malo):
    with pytest.raises(ValueError, match="failure_times"):
        wl.weibull_analysis([malo, 1.0, 2.0])


# ─── K-08 / N-07: listas vacías y bool ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("fn", ["series_system", "parallel_system"])
def test_sistemas_rechazan_lista_vacia(fn):
    with pytest.raises(ValueError, match="failure_rates"):
        getattr(wl, fn)([])


def test_koon_valida_n_y_k_enteros():
    with pytest.raises(TypeError):
        wl.koon_system(3.5, 2, 0.01)
    with pytest.raises(TypeError):
        wl.koon_system(3, True, 0.01)


def test_bool_no_se_acepta_como_entero():
    with pytest.raises(TypeError):
        wl.mmc(2.0, 3.0, True)


def test_bool_no_se_acepta_como_numero():
    with pytest.raises(TypeError):
        wl.mm1(True, 3.0)


# ─── K-05: Weibull con datos degenerados ───────────────────────────────────────────────────────

@pytest.mark.parametrize("metodo", ["MLE", "RRY"])
def test_weibull_datos_constantes_lanza_error_claro(metodo):
    with pytest.raises(ValueError, match="iguales"):
        wl.weibull_analysis([5.0, 5.0, 5.0, 5.0], method=metodo)


def test_weibull_casi_constante_avisa_de_cota():
    with pytest.warns(UserWarning, match="cota"):
        r = wl.weibull_analysis([5.0, 5.0, 5.0, 5.0000001])
    assert r.shape == pytest.approx(100.0)


def test_weibull_n_dos_funciona_sin_aviso(recwarn):
    r = wl.weibull_analysis([5.0, 9.0])
    assert r.n == 2 and r.shape > 0
    assert not [w for w in recwarn if issubclass(w.category, UserWarning)]


# ─── N-04: nombres de actividad duplicados ─────────────────────────────────────────────────────

@pytest.mark.parametrize("fn,extra", [
    ("cpm", {"duration": 1}),
    ("pert", {"optimistic": 1, "most_likely": 2, "pessimistic": 3}),
])
def test_actividades_duplicadas_se_rechazan(fn, extra):
    acts = [{"name": "A", "predecessors": [], **extra}, {"name": "A", "predecessors": [], **extra}]
    with pytest.raises(ValueError, match="duplicado"):
        getattr(wl, fn)(acts)


def test_actividad_sin_nombre_o_duracion_da_error_claro():
    with pytest.raises(ValueError, match="name"):
        wl.cpm([{"duration": 1}])
    with pytest.raises(ValueError, match="duration"):
        wl.cpm([{"name": "A", "predecessors": []}])
    with pytest.raises(TypeError):
        wl.cpm("A")


# ─── N-05: MRP con liberaciones vencidas ───────────────────────────────────────────────────────

def test_mrp_avisa_de_liberaciones_vencidas():
    with pytest.warns(UserWarning, match="antes del periodo 1"):
        r = wl.mrp([10, 20], lead_time=5)
    assert r.past_due_releases == pytest.approx(30.0)
    assert r.planned_releases == [0.0, 0.0]


def test_mrp_sin_vencidas_no_avisa(recwarn):
    r = wl.mrp([0, 0, 10, 20], lead_time=1)
    assert r.past_due_releases == 0.0
    assert not [w for w in recwarn if issubclass(w.category, UserWarning)]


def test_mrp_entradas_mal_formadas():
    with pytest.raises(ValueError):
        wl.mrp([])
    with pytest.raises(TypeError):
        wl.mrp(5)
    with pytest.raises(ValueError, match="lead_time"):
        wl.mrp([1, 2], lead_time=True)
    with pytest.raises(ValueError, match="periods"):
        wl.mrp([1, 2], periods=[1])


# ─── K-03 / K-04: ABC/XYZ con items mal formados o con demanda 0 ───────────────────────────────

def test_abc_items_mal_formados_dan_errores_claros():
    with pytest.raises(ValueError, match="unit_value"):
        wl.abc_analysis([{"name": "a", "demand": 5}])
    with pytest.raises(TypeError):
        wl.abc_analysis("abc")
    with pytest.raises(TypeError):
        wl.abc_analysis([1, 2])
    with pytest.raises(ValueError, match="demand"):
        wl.abc_analysis([{"name": "a", "unit_value": 1}])


def test_abc_acepta_articulos_sin_demanda_como_clase_c():
    items = [
        {"name": "a", "demand": 100, "unit_value": 10},
        {"name": "muerto", "demand": 0, "unit_value": 10},
    ]
    r = wl.abc_analysis(items)
    por_nombre = {e["name"]: e["class"] for e in r.items}
    assert por_nombre["muerto"] == "C"
    assert por_nombre["a"] == "A"


def test_abc_todas_las_demandas_cero_da_error_claro():
    with pytest.raises(ValueError, match="cero"):
        wl.abc_analysis([{"name": "a", "demand": 0, "unit_value": 1}])


def test_xyz_rechaza_cv_nan_y_negativo():
    with pytest.raises(ValueError):
        wl.xyz_analysis([{"name": "a", "cv": NAN}])
    with pytest.raises(ValueError):
        wl.xyz_analysis([{"name": "a", "cv": -0.3}])
    with pytest.raises(ValueError, match="demand_std"):
        wl.xyz_analysis([{"name": "a"}])


def test_abc_xyz_con_nombres_repetidos_empareja_por_posicion():
    items = [
        {"name": "x", "demand": 1000, "unit_value": 10, "cv": 0.1},   # A, X
        {"name": "x", "demand": 1, "unit_value": 1, "cv": 2.0},       # C, Z
    ]
    r = wl.abc_xyz(items)
    assert sorted(e["combined_class"] for e in r.items) == ["AX", "CZ"]


# ─── K-07: eoq_multi_constrained con restricciones inválidas (antes: bloqueo o ZeroDivisionError) ──

@pytest.mark.parametrize("presupuesto", [0.0, -1.0, NAN, INF, -INF])
def test_eoq_restringido_rechaza_presupuesto_no_valido(presupuesto):
    with pytest.raises(ValueError, match="budget"):
        wl.eoq_multi_constrained([1000, 500], [50, 30], [2, 1], budget=presupuesto, budget_unit_costs=[10, 5])


def test_eoq_restringido_costos_de_presupuesto_no_validos():
    with pytest.raises(ValueError, match="budget_unit_costs"):
        wl.eoq_multi_constrained([1000, 500], [50, 30], [2, 1], budget=5000, budget_unit_costs=[NAN, 5])
    with pytest.raises(ValueError, match="budget_unit_costs"):
        wl.eoq_multi_constrained([1000, 500], [50, 30], [2, 1], budget=5000, budget_unit_costs=[INF, 5])


def test_eoq_restringido_restriccion_personalizada_mal_formada():
    with pytest.raises(ValueError, match="constraints"):
        wl.eoq_multi_constrained([1000], [50], [2], constraints=[{"name": "x"}])


def test_eoq_restringido_valido_sigue_funcionando():
    r = wl.eoq_multi_constrained([1000, 500], [50, 30], [2, 1], budget=3000, budget_unit_costs=[10, 5])
    assert r.total_cost >= r.unconstrained_total_cost
