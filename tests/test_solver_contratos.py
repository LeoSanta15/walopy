"""W-30, W-31 y W-32: ``batch_model``, ``compare`` y ``sensitivity`` cumplen lo que documentan.

* W-30: un DataFrame disperso con un parámetro entero (``c``, ``k``…) pasa a ``float64`` por los NaN y el modelo lo rechazaba en todas las filas.
* W-31: ``compare()`` sin resultados devolvía una tabla vacía (la documentación dice ``ValueError``) y, con un resultado de varias filas
  (``wagner_whitin``, ``cpm``…), conservaba solo la primera fila y descartaba el resto en silencio.
* W-32: ``sensitivity`` con un parámetro que el modelo no tiene lanzaba ``TypeError`` y con ``values`` vacío devolvía una tabla vacía
  (la documentación dice ``ValueError`` en ambos casos).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import walopy as wl

ACTIVIDADES = [
    {"name": "A", "duration": 3, "predecessors": []},
    {"name": "B", "duration": 4, "predecessors": ["A"]},
]


# ----------------------------------------------------------------------------------------------- W-30
def test_batch_model_disperso_con_parametro_entero():
    df = pd.DataFrame({"lam": [2.0, 2.0, 2.0], "mu": [5.0, 5.0, 5.0], "c": [2, np.nan, 3]})
    out = wl.batch_model(wl.mmc, df)
    assert out["rho"][0] == pytest.approx(wl.mmc(2.0, 5.0, 2).rho)
    assert out["rho"][2] == pytest.approx(wl.mmc(2.0, 5.0, 3).rho)
    assert pd.isna(out["rho"][1]) and "c" in out["_error"][1]  # sin c no hay modelo: queda como error de esa fila
    assert pd.isna(out["_error"][0]) and pd.isna(out["_error"][2])


def test_batch_model_disperso_con_parametro_flotante_no_cambia():
    # Guarda: valores enteros en una columna flotante con NaN se aceptan también donde se esperaba un float
    df = pd.DataFrame({"lam": [1.0, 2.0, 3.0], "mu": [5.0, np.nan, 5.0]})
    out = wl.batch_model(wl.mm1, df, mu=4.0)
    assert out["rho"].tolist() == pytest.approx([0.2, 0.5, 0.6])


def test_batch_model_entero_sin_nan_sigue_igual():
    # Guarda
    df = pd.DataFrame({"lam": [1, 2, 3], "mu": [5, 5, 5], "c": [1, 2, 3]})
    out = wl.batch_model(wl.mmc, df)
    assert out["c"].tolist() == [1, 2, 3] and "_error" not in out.columns


# ----------------------------------------------------------------------------------------------- W-31
def test_compare_sin_resultados_es_value_error():
    with pytest.raises(ValueError, match="compare"):
        wl.compare()


def test_compare_conserva_los_totales_de_resultados_de_varias_filas():
    demanda = [10, 0, 20, 30]
    a, b = wl.wagner_whitin(demanda, 50, 1), wl.silver_meal(demanda, 50, 1)
    assert len(a.to_frame()) > 1
    tabla = wl.compare(a, b, labels=["WW", "SM"])
    assert tabla["label"].tolist() == ["WW", "SM"]
    assert tabla["total_cost"].tolist() == pytest.approx([a.total_cost, b.total_cost])
    assert tabla["n_orders"].tolist() == [a.n_orders, b.n_orders]


def test_compare_de_proyectos_usa_la_duracion_no_la_primera_actividad():
    tabla = wl.compare(wl.cpm(ACTIVIDADES), wl.pert([{**a, "optimistic": a["duration"], "most_likely": a["duration"], "pessimistic": a["duration"]} for a in ACTIVIDADES]))
    assert tabla["project_duration"].tolist() == [7.0, 7.0]


def test_compare_de_resultados_de_una_fila_no_cambia():
    # Guarda: colas y demás resultados de una fila se muestran con su tabla de siempre
    r1, r2 = wl.mm1(2.0, 5.0), wl.mmc(2.0, 5.0, 2)
    tabla = wl.compare(r1, r2, labels=["M/M/1", "M/M/2"])
    assert list(tabla.columns)[0] == "label"
    assert tabla["c (servidores)"].tolist() == [1, 2]
    assert tabla["Lq (en cola)"].tolist() == pytest.approx([r1.Lq, r2.Lq])


# ----------------------------------------------------------------------------------------------- W-32
def test_sensitivity_con_parametro_inexistente_es_value_error():
    with pytest.raises(ValueError, match="foo"):
        wl.sensitivity(wl.mm1, "foo", [1.0, 2.0], mu=3.0)


def test_sensitivity_con_values_vacio_es_value_error():
    with pytest.raises(ValueError, match="values"):
        wl.sensitivity(wl.mm1, "lam", [], mu=3.0)
    with pytest.raises(ValueError, match="values"):
        wl.sensitivity(wl.mm1, "lam", np.array([]), mu=3.0)


def test_sensitivity_valida_sigue_igual():
    # Guarda: una fila por valor; los inestables quedan solo con el parámetro
    df = wl.sensitivity(wl.mm1, "lam", [1.0, 2.0, 4.0], mu=3.0)
    assert df["lam"].tolist() == [1.0, 2.0, 4.0]
    assert df["rho"].iloc[:2].tolist() == pytest.approx([1 / 3, 2 / 3])
    assert df.drop(columns="lam").iloc[2].isna().all()


def test_sensitivity_admite_modelos_con_kwargs():
    def modelo(**kw):
        return wl.mm1(**kw)

    assert len(wl.sensitivity(modelo, "lam", [1.0, 2.0], mu=3.0)) == 2


# ---------------------------------------------------------------------- propiedades diferenciales (semilla fija)
def _campos(resultado) -> dict[str, float]:
    return {k: v for k, v in vars(resultado).items() if isinstance(v, (int, float, np.floating)) and not k.startswith("_")}


def test_sensitivity_cada_fila_es_el_modelo_evaluado_en_ese_valor():
    import random

    r = random.Random(20261010)
    for _ in range(100):
        mu = r.uniform(1, 10)
        valores = [r.uniform(0.1, 1.4) * mu for _ in range(r.randint(1, 8))]
        df = wl.sensitivity(wl.mm1, "lam", valores, mu=mu)
        assert df["lam"].tolist() == valores
        for v, (_, fila) in zip(valores, df.iterrows()):
            if v < mu:
                assert all(fila[k] == pytest.approx(x, rel=1e-12) for k, x in _campos(wl.mm1(v, mu)).items())
            else:
                assert fila.drop("lam").isna().all()  # inestable: solo queda el parámetro


def test_batch_model_cada_fila_es_el_modelo_y_conserva_indice_y_enteros():
    import random

    r = random.Random(20261011)
    for _ in range(100):
        mu, n = r.uniform(1, 10), r.randint(1, 8)
        lam = [r.uniform(0.1, 1.5) * mu for _ in range(n)]
        servidores = [r.randint(1, 4) for _ in range(n)]
        df = pd.DataFrame({"lam": lam, "c": servidores}, index=[f"i{k}" for k in range(n)])
        out = wl.batch_model(wl.mmc, df, mu=mu)
        assert list(out.index) == list(df.index) and out["c"].tolist() == servidores
        for k, (_, fila) in enumerate(out.iterrows()):
            if lam[k] < servidores[k] * mu:
                esperado = _campos(wl.mmc(lam[k], mu, servidores[k]))
                assert all(fila[nombre] == pytest.approx(x, rel=1e-12) for nombre, x in esperado.items() if nombre in fila.index)
            else:
                assert isinstance(fila["_error"], str)
