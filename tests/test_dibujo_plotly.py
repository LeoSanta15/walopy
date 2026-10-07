"""Las figuras de Plotly se dibujan, no solo existen como objeto (W-26).

El árbol de KPI de 0.4.0 tenía una ``Figure`` correcta para los tests y salía **en blanco** en el navegador. Aquí hay dos capas:

* **Siempre** (sin navegador): cada traza de cada figura tiene datos finitos que dibujar.
* **Con Chromium** (``WALOPY_DIBUJO=1``; ``make dibujo`` y el job «Dibujo» del CI): se renderiza la figura en un navegador sin interfaz y se compara
  la **zona del gráfico** con la misma figura con las trazas invisibles (``opacity=0``). Medir solo esa zona y contra una base con los mismos ejes y
  cuadrículas es lo que separa «dibujada» de «en blanco»: una captura completa tiene título y ejes aunque no haya datos (el árbol roto ocupa 1,1 %
  de píxeles distintos de blanco en pantalla completa, y 0,00 % de píxeles distintos de la base en la zona del gráfico; los correctos, entre 1,3 % y 66 %).

Si ``WALOPY_DIBUJO=1`` y no hay navegador, los tests **fallan** (no se saltan), para que el CI no pase en silencio. Ruta explícita: ``WALOPY_CHROME``.
"""
from __future__ import annotations

import copy
import glob
import math
import os
import shutil
import subprocess  # noqa: S404
from pathlib import Path

import pytest

import walopy as wl
from walopy import plotting

go = pytest.importorskip("plotly.graph_objects")
np = pytest.importorskip("numpy")

ANCHO, ALTO = 800, 500
MARGEN = {"l": 60, "r": 30, "t": 60, "b": 60}
UMBRAL = 0.002  # fracción mínima de píxeles de la zona del gráfico que cambian al quitar los datos
EXIGIDO = os.environ.get("WALOPY_DIBUJO") == "1"

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


def _ebitda() -> wl.KPINode:
    a = wl.KPINode("Producto A", value=120_000, unit="€")
    b = wl.KPINode("Producto B", value=80_000, unit="€")
    ingresos = wl.KPINode("Ingresos", value=200_000, unit="€", children=[a, b])
    costos = wl.KPINode("Costos de operación", value=100_000, unit="€")
    return wl.KPINode("EBITDA", value=100_000, unit="€", children=[ingresos, costos])


def _contrato(nombre: str):
    from tests.test_contrato_entradas import BASE

    return getattr(wl, nombre)(**copy.deepcopy(BASE[nombre]))


FIGURAS = {
    "kpi_ebitda_treemap": lambda: _ebitda().plot(),
    "kpi_ebitda_sunburst": lambda: _ebitda().plot(kind="sunburst"),
    "kpi_oee_treemap": lambda: wl.oee_kpi_tree(0.9, 0.8, 0.95).plot(),
    "kpi_roi_sunburst": lambda: wl.roi_kpi_tree(50_000.0, 10_000.0, 8.0, 2_000.0, 20_000.0).plot(kind="sunburst"),
    "optimize_servers": lambda: _contrato("optimize_servers").plot(),
    "monte_carlo_gg1": lambda: _contrato("monte_carlo_gg1").plot(),
    "line_balance": lambda: _contrato("line_balance").plot(),
    "break_even": lambda: _contrato("break_even").plot(),
    "break_even_sales": lambda: _contrato("break_even_sales").plot(),
    "sensitivity": lambda: plotting.plot_sensitivity(wl.sensitivity(wl.mm1, "lam", [1.0, 1.5, 2.0, 2.5], mu=3.0), "lam"),
    "queue_distribution": lambda: plotting.plot_queue_distribution(
        wl.queue_length_pmf(2.0, 3.0, n_max=10), wl.sojourn_cdf(2.0, 3.0, n_points=20)
    ),
}


def _arreglos(traza) -> list:
    """Matrices que la traza dibuja: ``x``/``y`` (barras, líneas) o ``values`` (árboles)."""
    return [getattr(traza, k) for k in ("x", "y", "values") if getattr(traza, k, None) is not None]


@pytest.mark.parametrize("nombre", sorted(FIGURAS))
def test_cada_traza_tiene_datos_finitos_que_dibujar(nombre):
    fig = FIGURAS[nombre]()
    assert len(fig.data) > 0, nombre
    for i, traza in enumerate(fig.data):
        valores = [float(v) for a in _arreglos(traza) for v in a if isinstance(v, (int, float, np.integer, np.floating))]
        assert any(math.isfinite(v) for v in valores), f"{nombre}: la traza {i} ({traza.type}) no tiene valores finitos"


# ---------------------------------------------------------------------------------------------- navegador
def _chrome() -> str | None:
    if os.environ.get("WALOPY_CHROME"):
        return os.environ["WALOPY_CHROME"]
    for cmd in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        ruta = shutil.which(cmd)
        if ruta:
            return ruta
    candidatos = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return candidatos[-1] if candidatos else None


@pytest.fixture(scope="module")
def navegador() -> str:
    if not EXIGIDO:
        pytest.skip("renderizado en navegador: ejecuta con WALOPY_DIBUJO=1 (make dibujo)")
    ruta = _chrome()
    assert ruta, "WALOPY_DIBUJO=1 pero no hay Chromium/Chrome (define WALOPY_CHROME)"
    return ruta


def _preparar(fig):
    f = go.Figure(fig)
    f.update_layout(
        width=ANCHO, height=ALTO, margin=MARGEN, showlegend=False, title=None, paper_bgcolor="white", plot_bgcolor="white"
    )
    return f


def _invisible(fig):
    f = go.Figure(fig)
    for traza in f.data:
        traza.opacity = 0
    return f


def _renderizar(chrome: str, fig, carpeta: Path) -> np.ndarray:
    import matplotlib.image as mpimg

    html, png = carpeta / "figura.html", carpeta / "figura.png"
    png.unlink(missing_ok=True)
    fig.write_html(str(html), include_plotlyjs=True, full_html=True, config={"displayModeBar": False, "staticPlot": True})
    orden = [
        chrome, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", f"--window-size={ANCHO},{ALTO}",
        "--virtual-time-budget=4000", f"--screenshot={png}", html.as_uri(),
    ]
    subprocess.run(orden, capture_output=True, timeout=120, check=True)  # noqa: S603
    return np.asarray(mpimg.imread(str(png)))[..., :3]


def _fraccion_dibujada(chrome: str, fig, carpeta: Path) -> float:
    con = _renderizar(chrome, _preparar(fig), carpeta)
    sin = _renderizar(chrome, _preparar(_invisible(fig)), carpeta)
    zona = (slice(MARGEN["t"], ALTO - MARGEN["b"]), slice(MARGEN["l"], ANCHO - MARGEN["r"]))
    return float((np.abs(con[zona] - sin[zona]).max(axis=2) > 0.1).mean())


@pytest.mark.parametrize("nombre", sorted(FIGURAS))
def test_la_figura_se_dibuja_en_el_navegador(nombre, navegador, tmp_path):
    fraccion = _fraccion_dibujada(navegador, FIGURAS[nombre](), tmp_path)
    assert fraccion > UMBRAL, f"{nombre}: la zona del gráfico solo cambia un {fraccion:.4%} respecto de la figura sin datos (¿en blanco?)"


def test_el_detector_ve_en_blanco_el_arbol_de_kpi_de_0_4_0(navegador, tmp_path):
    """Control: con un padre menor que la suma de sus hijos (el defecto W-26) Plotly no dibuja y la medida tiene que quedar bajo el umbral."""
    fig = go.Figure(_ebitda().plot())
    valores = list(fig.data[0].values)
    valores[0] = 1e-9  # raíz menor que la suma de sus hijos
    fig.data[0].values = valores
    assert _fraccion_dibujada(navegador, fig, tmp_path) <= UMBRAL
