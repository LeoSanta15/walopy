"""Lo que ve la persona usuaria en inglés: ningún texto en español se cuela y los números no cambian con el idioma (fase 2).

Se ejecuta lo mismo que la instantánea de la fase 1 (funciones, errores del contrato y escenarios) con ``language("en")`` y se busca
vocabulario español con un detector independiente del catálogo. La salida en español ya la fija ``tests/test_salida_identica.py``.
"""
from __future__ import annotations

import copy
import importlib.util
import os
import re
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest

import walopy as wl

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("instantanea_salida", RAIZ / "scripts" / "instantanea_salida.py")
instantanea = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(instantanea)

ESPANOL = re.compile(
    r"[áéíóúñÁÉÍÓÚÑ¿¡]|\b(de|la|el|los|las|con|para|por|sin|debe|deben|valor|tiempo|costo|tasa|demanda|modelo|sistema|unidades|pedido"
    r"|artículo|estación|cola|se recibió)\b",
    re.IGNORECASE,
)
MENSAJE_AJENO = "<mensaje de Python>"      # la instantánea sustituye los mensajes que no escribió walopy


def _textos(valor, ruta=""):
    """(ruta, texto) de todo lo que se muestra; ``resultado`` se omite: incluye las claves fijas de ``params`` (decisión D1)."""
    if isinstance(valor, dict):
        for k, v in valor.items():
            if k != "resultado":
                yield from _textos(v, f"{ruta}/{k}")
    elif isinstance(valor, list):
        for i, v in enumerate(valor):
            yield from _textos(v, f"{ruta}[{i}]")
    elif isinstance(valor, str):
        yield ruta, valor


@pytest.fixture(scope="module")
def salida_en():
    contrato = instantanea._cargar_contrato()
    with wl.language("en"):
        return {
            "funciones": instantanea.capturar_funciones(contrato),
            "errores": instantanea.capturar_errores(contrato),
            "escenarios": instantanea.capturar_escenarios(),
        }


@pytest.mark.parametrize("parte", ["funciones", "errores", "escenarios"])
def test_en_ingles_no_hay_texto_en_espanol(salida_en, parte):
    colados = []
    for ruta, texto in _textos(salida_en[parte], f"/{parte}"):
        limpio = texto.replace(MENSAJE_AJENO, "")
        m = ESPANOL.search(limpio)
        if m:
            colados.append(f"{ruta[:70]} [{m.group()}] {texto[:80]!r}")
    assert not colados, "texto en español con el idioma en inglés:\n" + "\n".join(colados[:20])


def test_el_detector_encuentra_espanol():
    """Control negativo del detector."""
    assert ESPANOL.search("Costo total") and ESPANOL.search("debe ser positivo") and ESPANOL.search("Estación")
    assert not ESPANOL.search("Total cost: must be positive; Station") and not ESPANOL.search("ABC\\XYZ   X     Y     Z   Total")


def test_en_ingles_los_errores_siguen_siendo_los_mismos_tipos_y_hay_tantos_como_en_espanol(salida_en):
    contrato = instantanea._cargar_contrato()
    es = instantanea.capturar_errores(contrato)
    assert set(es) == set(salida_en["errores"])
    cambian_de_tipo = [k for k in es if es[k].split(":")[0] != salida_en["errores"][k].split(":")[0]]
    assert not cambian_de_tipo, cambian_de_tipo[:5]


def test_el_idioma_no_cambia_ningun_numero():
    """Las tablas de cada función son iguales en ambos idiomas salvo los nombres de columna y de textos."""
    contrato = instantanea._cargar_contrato()
    distintos = []
    for nombre in sorted(set(contrato.BASE) - instantanea.NOMBRES_NUEVOS):
        resultados = {}
        for lang in ("es", "en"):
            with wl.language(lang), warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r = getattr(wl, nombre)(**copy.deepcopy(contrato.BASE[nombre]))
            if hasattr(r, "to_frame"):
                df = r.to_frame()
                resultados[lang] = (df.shape, df.select_dtypes(include=[np.number]).to_numpy(), str(r).count("\n"))
        if "es" in resultados:
            (fa, na, la), (fb, nb, lb) = resultados["es"], resultados["en"]
            if fa != fb or la != lb or not np.array_equal(na, nb, equal_nan=True):
                distintos.append(nombre)
    assert not distintos, f"el idioma cambia la forma o los números de: {distintos}"


def test_la_cli_en_ingles(monkeypatch):
    env = {**os.environ, "WALOPY_LANG": "en", "PYTHONPATH": str(RAIZ / "src"), "COLUMNS": "100"}
    ayuda = subprocess.run([sys.executable, "-m", "walopy", "--help"], capture_output=True, text=True, env=env, check=False, timeout=60)  # noqa: S603
    assert ayuda.returncode == 0 and "Queueing theory" in ayuda.stdout and not ESPANOL.search(re.sub(r"usage:.*", "", ayuda.stdout))
    r = subprocess.run([sys.executable, "-m", "walopy", "mm1", "--lam", "5", "--mu", "3"], capture_output=True, text=True, env=env, check=False, timeout=60)  # noqa: S603
    assert r.returncode != 0 and "Unstable system" in r.stderr
    ok = subprocess.run([sys.executable, "-m", "walopy", "mm1", "--lam", "2", "--mu", "3"], capture_output=True, text=True, env=env, check=False, timeout=60)  # noqa: S603
    assert ok.returncode == 0 and "arrival rate" in ok.stdout and not ESPANOL.search(ok.stdout)

