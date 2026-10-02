"""Pruebas de humo de las gráficas (matplotlib con backend Agg y plotly): construyen la figura sin errores."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import pytest  # noqa: E402

import walopy as wl  # noqa: E402
from walopy import plotting  # noqa: E402


@pytest.fixture(autouse=True)
def _cerrar_figuras():
    yield
    plt.close("all")


def _es_figura(obj) -> bool:
    return isinstance(obj, (plt.Figure, go.Figure))


# Resultados con método .plot()
RESULTADOS = {
    "mm1": lambda: wl.mm1(2.0, 3.0),
    "mmc": lambda: wl.mmc(8.0, 3.0, 4),
    "oee": lambda: wl.oee(0.9, 0.8, 0.95),
    "bottleneck": lambda: wl.bottleneck_analysis(["A", "B"], [5.0, 3.0], 2.0),
    "line_balance": lambda: wl.line_balance(["A", "B", "C"], [5.0, 9.0, 4.0], 10.0),
    "break_even": lambda: wl.break_even(1000.0, 10.0, 4.0, actual_units=300.0),
    "break_even_sin_real": lambda: wl.break_even(1000.0, 10.0, 4.0),
    "break_even_sales": lambda: wl.break_even_sales(1000.0, 0.4),
    "break_even_sales_real": lambda: wl.break_even_sales(1000.0, 0.4, actual_revenue=3000.0),
    "eoq": lambda: wl.eoq(1000.0, 50.0, 2.0),
    "optimize_servers": lambda: wl.optimize_servers(4.0, 3.0, cost_per_server=10.0, cost_per_wait=5.0),
    "monte_carlo": lambda: wl.monte_carlo_gg1(2.0, 3.0, 1.0, 1.0, n_customers=2000, seed=1),
    "oee_arbol": lambda: wl.oee_kpi_tree(0.9, 0.9, 0.9),
    "throughput_arbol": lambda: wl.throughput_kpi_tree(80.0, 100.0, 0.05),
    "roi_arbol": lambda: wl.roi_kpi_tree(1000.0, 200.0, 3.0, 100.0, 500.0),
}


@pytest.mark.parametrize("nombre", sorted(RESULTADOS))
def test_plot_de_resultado_devuelve_figura(nombre):
    assert _es_figura(RESULTADOS[nombre]().plot())


def test_break_even_sales_usa_eje_de_ventas():
    fig = wl.break_even_sales(1000.0, 0.4).plot()
    assert fig.layout.xaxis.title.text == "Ventas"


def test_plot_sensitivity():
    df = wl.sensitivity(wl.mm1, "lam", np.linspace(0.5, 2.5, 6), mu=3.0)
    assert _es_figura(plotting.plot_sensitivity(df, "lam", metrics=["Wq", "Lq"]))


def test_plot_queue_distribution():
    pmf = wl.queue_length_pmf(2.0, 3.0, n_max=10)
    cdf = wl.sojourn_cdf(2.0, 3.0, n_points=20)
    assert _es_figura(plotting.plot_queue_distribution(pmf, cdf))


def test_plot_queue_metrics_y_sensibilidad():
    r = wl.mm1(2.0, 3.0)
    assert _es_figura(plotting.plot_queue_metrics(r))
    assert _es_figura(plotting.plot_queue_sensitivity(r))


def test_plot_acepta_titulo_personalizado():
    fig = plotting.plot_break_even(wl.break_even(1000.0, 10.0, 4.0), title="Mi título")
    assert fig.layout.title.text == "Mi título"


def test_plot_no_modifica_rcparams():
    antes = dict(plt.rcParams)
    wl.eoq(1000.0, 50.0, 2.0).plot()
    wl.mm1(2.0, 3.0).plot()
    plt.close("all")
    assert dict(plt.rcParams) == antes
