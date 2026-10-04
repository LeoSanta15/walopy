"""Documentación en inglés (fase 3 de la internacionalización): README.en.md y las traducciones de Sphinx (``docs/source/locale/en``).

* ``README.en.md`` tiene la misma estructura que ``README.md`` (secciones, tablas de contenido, bloques de código) y documenta todo símbolo público.
* Las traducciones de Sphinx cubren todo el texto de la referencia (todos los mensajes tienen traducción y no hay mensajes nuevos sin traducir).
  El registro de cambios (``changelog``) se deja en español a propósito.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

import walopy

RAIZ = Path(__file__).resolve().parents[1]
ES = (RAIZ / "README.md").read_text(encoding="utf-8")
EN = (RAIZ / "README.en.md").read_text(encoding="utf-8")
LOCALE = RAIZ / "docs" / "source" / "locale" / "en" / "LC_MESSAGES"
SIN_TRADUCIR = {"changelog"}      # CHANGELOG.md está en español (convención del repositorio)


def _titulos(texto: str) -> list[str]:
    return re.findall(r"^(#{1,6}) ", texto, re.M)


def _anclas(texto: str) -> set[str]:
    """Anclas de GitHub de los encabezados (minúsculas, sin signos, espacios → guiones)."""
    anclas = set()
    en_codigo = False
    for linea in texto.splitlines():
        if linea.startswith("```"):
            en_codigo = not en_codigo
        m = None if en_codigo else re.match(r"^#{1,6} (.+)$", linea)
        if m:
            t = re.sub(r"[`*]", "", m.group(1)).strip().lower()
            anclas.add(re.sub(r"[^\w\- ]", "", t).replace(" ", "-"))
    return anclas


def test_el_readme_ingles_tiene_la_misma_estructura_que_el_espanol():
    assert _titulos(EN) == _titulos(ES), "los encabezados (niveles y orden) deben coincidir"
    bloques_es = len(re.findall(r"^```python", ES, re.M))
    bloques_en = len(re.findall(r"^```python", EN, re.M))
    assert bloques_en == bloques_es + 1          # el inglés abre con `set_language("en")`


@pytest.mark.parametrize("nombre,texto", [("README.md", ES), ("README.en.md", EN)], ids=["es", "en"])
def test_los_enlaces_de_la_tabla_de_contenidos_apuntan_a_un_encabezado(nombre, texto):
    anclas = _anclas(texto)
    rotos = [a for a in re.findall(r"\]\(#([^)]+)\)", texto) if a not in anclas]
    assert not rotos, f"{nombre}: enlaces internos rotos: {rotos}"


def test_cada_funcion_publica_aparece_en_el_readme_ingles():
    faltan = [n for n in walopy.__all__ if not re.search(rf"\b{re.escape(n)}\b", EN)]
    assert not faltan, f"README.en.md no menciona: {faltan}"


def test_los_dos_readme_se_enlazan_entre_si():
    assert "README.en.md" in ES.split("---")[0]
    assert "README.md" in EN.split("---")[0]


def test_el_readme_ingles_no_tiene_prosa_en_espanol():
    """Fuera de los bloques de código y de los literales entre comillas invertidas, no debe quedar vocabulario español."""
    sin_codigo = re.sub(r"```.*?```", " ", EN, flags=re.S)
    sin_codigo = re.sub(r"`[^`]*`", " ", sin_codigo)
    sin_codigo = re.sub(r"\]\([^)]*\)", "]", sin_codigo)
    espanol = re.compile(
        r"[áéíóúñ¿¡]|\b(el|los|las|con|para|por|debe|deben|valor|tiempo|costo|tasa|demanda|sistema|unidades|pedido|cola|se recibió|versión)\b",
        re.I,
    )
    # la sección de idioma cita a propósito ejemplos en español («Artículo», «Lote por lote») y la línea de enlace al español
    sin_codigo = re.sub(r"^🇪🇸.*$", "", sin_codigo, flags=re.M)
    sin_codigo = re.sub(r"\([^)]*(Artículo|Lote|Producto|tasa)[^)]*\)", "", sin_codigo)
    colados = [f"{m.group()!r}: …{sin_codigo[max(0, m.start() - 30):m.end() + 30]!r}" for m in espanol.finditer(sin_codigo)]
    assert not colados, "\n".join(colados[:10])


# --- Sphinx ---------------------------------------------------------------------------------------------------------------------------


class _Po:
    """Lectura de catálogos .po cerrando los archivos (los avisos son errores en esta suite)."""

    def __init__(self, modulo):
        self._m = modulo

    def read_po(self, ruta: Path):
        with ruta.open("rb") as f:
            return self._m.read_po(f)


@pytest.fixture(scope="module")
def babel_pofile():
    return _Po(pytest.importorskip("babel.messages.pofile", reason="babel no está instalado (viene con Sphinx: extra «docs»)"))


PO = sorted(p for p in LOCALE.rglob("*.po") if p.stem not in SIN_TRADUCIR)


def test_hay_traducciones_de_sphinx():
    assert len(PO) >= 18


@pytest.mark.parametrize("ruta", PO, ids=lambda p: str(p.relative_to(LOCALE)))
def test_todos_los_mensajes_estan_traducidos(ruta, babel_pofile):
    cat = babel_pofile.read_po(ruta)
    sin = [m.id[:60] for m in cat if m.id and (not m.string or m.fuzzy)]
    assert not sin, f"{ruta.name}: mensajes sin traducir o dudosos: {sin[:5]}"


PALABRAS_ES = re.compile(
    r"\b(Funciones|Clases de resultado|Módulo|Si algún|debe|Número|Tasa|Tiempo|Costo|Inventarios|Colas|Confiabilidad|Rendimiento|Solo|Clave)\b"
)


@pytest.mark.parametrize("ruta", PO, ids=lambda p: str(p.relative_to(LOCALE)))
def test_la_traduccion_no_deja_texto_en_espanol(ruta, babel_pofile):
    cat = babel_pofile.read_po(ruta)
    quedan = [m.string[:60] for m in cat if m.id and ">>>" not in m.string and PALABRAS_ES.search(m.string)]
    assert not quedan, f"{ruta.name}: {quedan[:5]}"


def test_las_traducciones_de_sphinx_estan_al_dia(tmp_path, babel_pofile):
    """Si cambia un docstring o una página, hay mensajes nuevos que traducir (``make docs-i18n``)."""
    pytest.importorskip("sphinx")
    destino = tmp_path / "gettext"
    r = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "sphinx", "-b", "gettext", "-D", "language=en", "-q", str(RAIZ / "docs" / "source"), str(destino)],
        capture_output=True, text=True, check=False, timeout=600,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    nuevos = []
    for pot in destino.rglob("*.pot"):
        if pot.stem in SIN_TRADUCIR:
            continue
        rel = pot.relative_to(destino).with_suffix(".po")
        po = LOCALE / rel
        assert po.exists(), f"falta {po.relative_to(RAIZ)}: ejecuta `make docs-i18n`"
        traducidos = {m.id for m in babel_pofile.read_po(po) if m.id}
        nuevos += [f"{rel}: {m.id[:60]!r}" for m in babel_pofile.read_po(pot) if m.id and m.id not in traducidos]
    assert not nuevos, "mensajes nuevos sin traducción (ejecuta `make docs-i18n` y traduce):\n" + "\n".join(nuevos[:10])
