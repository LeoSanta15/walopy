"""Los árboles de KPI se dibujan (W-26).

Con ``branchvalues="total"`` Plotly exige que el valor de cada padre sea **al menos** la suma de los de sus hijos; si no, la figura sale en blanco en el
navegador. Un KPI casi nunca es la suma de sus hijos (EBITDA = Ingresos − Costos; OEE = A × P × Q), así que ``plot_kpi_tree`` usa como tamaño del
rectángulo ``max(valor, suma de los tamaños de los hijos)`` y rotula el valor real del nodo. Estos tests comprueban esa condición sobre la figura
(el objeto ``Figure`` no se renderiza aquí).
"""
from __future__ import annotations

import pytest

import walopy as wl

pytest.importorskip("plotly")


def _ebitda() -> wl.KPINode:
    a = wl.KPINode("Producto A", value=120_000, unit="€")
    b = wl.KPINode("Producto B", value=80_000, unit="€")
    ingresos = wl.KPINode("Ingresos", value=200_000, unit="€", children=[a, b])
    costos = wl.KPINode("Costos de operación", value=100_000, unit="€")
    return wl.KPINode("EBITDA", value=100_000, unit="€", children=[ingresos, costos])


def _suma_exacta() -> wl.KPINode:
    return wl.KPINode("Total", value=300.0, children=[wl.KPINode("A", value=100.0), wl.KPINode("B", value=200.0)])


ARBOLES = {
    "ebitda": _ebitda,
    "oee": lambda: wl.oee_kpi_tree(0.9, 0.8, 0.95),
    "throughput": lambda: wl.throughput_kpi_tree(750.0, 1000.0, 0.05),
    "roi": lambda: wl.roi_kpi_tree(50_000.0, 10_000.0, 8.0, 2_000.0, 20_000.0),
    "suma_exacta": _suma_exacta,
    "una_hoja": lambda: wl.KPINode("Solo", value=5.0),
    "con_cero": lambda: wl.KPINode("R", value=0.0, children=[wl.KPINode("H", value=0.0)]),
    "negativo": lambda: wl.KPINode("R", value=-10.0, children=[wl.KPINode("H1", value=-30.0), wl.KPINode("H2", value=5.0)]),
}


def _violaciones(traza) -> list[str]:
    """Padres cuyo valor es menor que la suma de sus hijos (lo que deja a Plotly con la figura en blanco)."""
    valor = dict(zip(traza.ids, traza.values))
    suma: dict[str, float] = {}
    for id_, padre in zip(traza.ids, traza.parents):
        if padre:
            suma[padre] = suma.get(padre, 0.0) + valor[id_]
    return [f"{p}: {valor[p]:g} < {s:g}" for p, s in suma.items() if valor[p] < s * (1 - 1e-12)]


@pytest.mark.parametrize("kind", ["treemap", "sunburst"])
@pytest.mark.parametrize("nombre", sorted(ARBOLES))
def test_ningun_padre_vale_menos_que_la_suma_de_sus_hijos(nombre, kind):
    fig = ARBOLES[nombre]().plot(kind=kind)
    traza = fig.data[0]
    assert traza.branchvalues == "total"
    assert not _violaciones(traza), f"{nombre} ({kind}) se dibujaría en blanco: {_violaciones(traza)}"
    assert all(v > 0 for v in traza.values)


@pytest.mark.parametrize("kind", ["treemap", "sunburst"])
def test_el_rotulo_es_el_valor_real_del_nodo_no_el_tamano(kind):
    fig = _ebitda().plot(kind=kind)
    traza = fig.data[0]
    rotulos = dict(zip(traza.labels, traza.text))
    assert rotulos["EBITDA"] == "100,000"                    # no 300 000, que es el tamaño del rectángulo
    assert rotulos["Ingresos"] == "200,000" and rotulos["Producto A"] == "120,000"
    assert "%{text}" in traza.texttemplate


def test_un_arbol_valido_conserva_los_tamanos_de_siempre():
    """Si el padre ya es la suma (o mayor), nada cambia: tamaño = valor del nodo."""
    traza = _suma_exacta().plot().data[0]
    assert dict(zip(traza.labels, traza.values)) == {"Total": 300.0, "A": 100.0, "B": 200.0}
    mayor = wl.KPINode("P", value=500.0, children=[wl.KPINode("H", value=100.0)])
    assert dict(zip(mayor.plot().data[0].labels, mayor.plot().data[0].values)) == {"P": 500.0, "H": 100.0}


def test_el_texto_emergente_sigue_mostrando_el_valor_y_la_formula():
    raiz = wl.KPINode("EBITDA", value=100_000, unit="€", formula="Ingresos − Costos", children=[wl.KPINode("X", value=1.0)])
    hover = raiz.plot().data[0].customdata[0]
    assert "100000" in hover and "Ingresos − Costos" in hover and "€" in hover
