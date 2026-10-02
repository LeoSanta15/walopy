"""Política de idioma (R-03): todo texto que ve la persona usuaria está en español.

Recorre con ``ast`` los mensajes de excepciones, los avisos (``warnings.warn``) y los docstrings de
``src/walopy`` y falla si encuentra palabras que solo existen en inglés. Los identificadores, las claves de
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
PALABRA = re.compile(r"[A-Za-z'-]+")  # los términos con guion (Head-of-Line) cuentan como una palabra
TIPO_NUMPYDOC = re.compile(r"^[\w*,\s]+ : ")  # «x : sequence of float»: el tipo se escribe en inglés por convención
ENCABEZADOS = {"Parameters", "Returns", "Raises", "Examples", "Notes", "See Also", "References", "Yields", "Attributes"}


def _textos(arbol: ast.AST):
    """Genera (línea, texto) de mensajes de excepciones, avisos y docstrings."""
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(nodo, clean=False)
            if doc:
                yield nodo.body[0].lineno, "doc", doc
        elif isinstance(nodo, ast.Raise) and isinstance(nodo.exc, ast.Call):
            for arg in nodo.exc.args:
                yield from ((m.lineno, "mensaje", m.value) for m in ast.walk(arg)
                            if isinstance(m, ast.Constant) and isinstance(m.value, str))
        elif isinstance(nodo, ast.Call):
            f = nodo.func
            nombre = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nombre == "warn" and nodo.args:
                yield from ((m.lineno, "aviso", m.value) for m in ast.walk(nodo.args[0])
                            if isinstance(m, ast.Constant) and isinstance(m.value, str))


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


@pytest.mark.parametrize("ruta", sorted(SRC.glob("*.py")), ids=lambda r: r.name)
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
