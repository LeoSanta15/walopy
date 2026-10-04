"""Política de idioma (R-03): el texto que ve la persona usuaria por defecto (catálogo ``es`` y docstrings) está en español.

Recorre con ``ast`` los mensajes de excepciones, los avisos (``warnings.warn``) y los docstrings de
``src/walopy`` y los valores del catálogo en español, y falla si encuentra palabras que solo existen en inglés. Los mensajes del
código son claves de catálogo (``modulo.tipo.funcion.resumen``): se omiten aquí y se comprueban sus textos en ``_catalogo_es.py``.
El catálogo en inglés (``_catalogo_en.py``) está en inglés a propósito y queda fuera. Los identificadores, las claves de
datos, los encabezados de sección de numpydoc (``Parameters``, ``Returns``…) y las líneas de tipo
(``x : sequence of float``) quedan fuera a propósito.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import walopy

SRC = Path(walopy.__file__).resolve().parent  # el paquete importado (así `verificar_regresion.py` puede apuntarlo a un tag)

# Palabras que no existen en español y delatan texto en inglés (en minúsculas, palabra completa).
INGLES = frozenset(
    "the of and with for is are must should cannot from which when this that these those been being have has than then "
    "there their its".split()
)
CODIGO = re.compile(r"``.*?``")
CLAVE_CATALOGO = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+){2,3}(_\d+)?$")
PALABRA = re.compile(r"[A-Za-z'-]+")  # los términos con guion (Head-of-Line) cuentan como una palabra
TIPO_NUMPYDOC = re.compile(r"^[\w*,\s]+ : ")  # «x : sequence of float»: el tipo se escribe en inglés por convención
ENCABEZADOS = {"Parameters", "Returns", "Raises", "Examples", "Notes", "See Also", "References", "Yields", "Attributes"}


def _es_texto(m: ast.AST) -> bool:
    """Constante de texto que no es una clave de catálogo (las claves se resuelven al español en ``_catalogo_es.py``)."""
    return isinstance(m, ast.Constant) and isinstance(m.value, str) and not CLAVE_CATALOGO.match(m.value)


def _textos(arbol: ast.AST):
    """Genera (línea, texto) de mensajes de excepciones, avisos y docstrings."""
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(nodo, clean=False)
            if doc:
                yield nodo.body[0].lineno, "doc", doc
        elif isinstance(nodo, ast.Raise) and isinstance(nodo.exc, ast.Call):
            for arg in nodo.exc.args:
                yield from ((m.lineno, "mensaje", m.value) for m in ast.walk(arg) if _es_texto(m))
        elif isinstance(nodo, ast.Call):
            f = nodo.func
            nombre = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nombre == "warn" and nodo.args:
                yield from ((m.lineno, "aviso", m.value) for m in ast.walk(nodo.args[0]) if _es_texto(m))


def _prosa(texto: str, tipo: str) -> list[str]:
    """Líneas de prosa del texto (sin ejemplos ``>>>``, encabezados numpydoc ni líneas de código)."""
    if tipo != "doc":
        return [texto]
    prosa = []
    en_ejemplo = False
    for linea in texto.splitlines():
        s = linea.strip()
        if s.startswith(">>>") or s.startswith("..."):
            en_ejemplo = True
            continue
        if not s:
            en_ejemplo = False
            continue
        if en_ejemplo or s in ENCABEZADOS or set(s) <= {"-", "="} or TIPO_NUMPYDOC.match(s):
            continue
        prosa.append(s)
    return prosa


def encontrar_ingles(ruta: Path) -> list[str]:
    hallazgos = []
    for linea, tipo, texto in _textos(ast.parse(ruta.read_text(encoding="utf-8"))):
        for prosa in _prosa(texto, tipo):
            sin_codigo = CODIGO.sub(" ", prosa)
            palabras = {p.lower() for p in PALABRA.findall(sin_codigo)} & INGLES
            if palabras:
                hallazgos.append(f"{ruta.name}:{linea} ({tipo}) {sorted(palabras)} → {prosa[:70]!r}")
    return hallazgos


def encontrar_ingles_en_catalogo(catalogo: dict[str, str]) -> list[str]:
    """Valores del catálogo con palabras que solo existen en inglés (se ignoran los marcadores ``{...}`` y el código entre ``` ``).``"""
    hallazgos = []
    for clave, texto in catalogo.items():
        sin_codigo = re.sub(r"\{[^{}]*\}", " ", CODIGO.sub(" ", texto))
        palabras = {p.lower() for p in PALABRA.findall(sin_codigo)} & INGLES
        if palabras:
            hallazgos.append(f"{clave} {sorted(palabras)} → {texto[:70]!r}")
    return hallazgos


def test_el_catalogo_en_espanol_no_tiene_ingles():
    from walopy._catalogo_es import ES

    hallazgos = encontrar_ingles_en_catalogo(ES)
    assert not hallazgos, "Texto en inglés en el catálogo español:\n" + "\n".join(hallazgos)


ESPANOL = re.compile(
    r"[áéíóúñÁÉÍÓÚÑ¿¡]|\b(de|la|el|los|las|con|para|por|sin|debe|deben|valor|tiempo|costo|tasa|demanda|modelo|sistema|unidades|pedido"
    r"|artículo|estación|cola|se recibió)\b",
    re.IGNORECASE,
)


def encontrar_espanol_en_catalogo(catalogo: dict[str, str]) -> list[str]:
    """Valores del catálogo inglés con vocabulario español (sin marcadores ``{...}`` ni código entre comillas invertidas)."""
    hallazgos = []
    for clave, texto in catalogo.items():
        sin_codigo = re.sub(r"\{[^{}]*\}", " ", CODIGO.sub(" ", texto))
        m = ESPANOL.search(sin_codigo)
        if m:
            hallazgos.append(f"{clave} [{m.group()}] → {texto[:70]!r}")
    return hallazgos


def test_el_catalogo_en_ingles_no_tiene_espanol():
    from walopy._catalogo_en import EN

    hallazgos = encontrar_espanol_en_catalogo(EN)
    assert not hallazgos, "Texto en español en el catálogo inglés:\n" + "\n".join(hallazgos)


def test_el_detector_de_catalogo_encuentra_espanol():
    assert encontrar_espanol_en_catalogo({"a.error.x": "x debe ser positivo", "a.error.y": "x must be positive"}) == [
        "a.error.x [debe] → 'x debe ser positivo'"
    ]


def test_el_detector_de_catalogo_encuentra_ingles():
    assert encontrar_ingles_en_catalogo({"a.error.x": "x must be positive", "a.error.y": "x debe ser positivo"}) == [
        "a.error.x ['must'] → 'x must be positive'"
    ]


@pytest.mark.parametrize("ruta", [r for r in sorted(SRC.glob("*.py")) if r.name != "_catalogo_en.py"], ids=lambda r: r.name)
def test_textos_visibles_en_espanol(ruta):
    hallazgos = encontrar_ingles(ruta)
    assert not hallazgos, "Texto en inglés visible para la persona usuaria:\n" + "\n".join(hallazgos)


def test_el_detector_encuentra_ingles(tmp_path):
    """Control negativo: el detector debe señalar mensajes, avisos y docstrings en inglés."""
    f = tmp_path / "malo.py"
    f.write_text(
        'import warnings\n'
        'def g(x):\n'
        '    """Compute the value of x."""\n'
        '    if x < 0:\n'
        '        raise ValueError("x must be positive")\n'
        '    warnings.warn("this is not finite")\n',
        encoding="utf-8",
    )
    tipos = {h.split("(")[1].split(")")[0] for h in encontrar_ingles(f)}
    assert tipos == {"doc", "mensaje", "aviso"}


def test_el_detector_no_marca_espanol(tmp_path):
    f = tmp_path / "bueno.py"
    f.write_text(
        'def g(x):\n'
        '    """Calcula el valor de x.\n\n    Parameters\n    ----------\n    x : float\n        Valor positivo.\n    """\n'
        '    raise ValueError("x debe ser positivo")\n',
        encoding="utf-8",
    )
    assert encontrar_ingles(f) == []
