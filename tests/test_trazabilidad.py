"""Trazabilidad bug → test de regresión → ficha del catálogo (R-16).

Cada bug corregido figura en ``tests/regresiones.json`` con su identificador ``W-nn``, la versión que
aún lo tenía (``ref``) y los selectores de pytest que lo cubren. Este test comprueba que el manifiesto es
coherente con el catálogo y con los tests. Que esos tests *fallan* en ``ref`` lo comprueba
``scripts/verificar_regresion.py`` (job ``regresion`` del CI).
"""
from __future__ import annotations

import ast
import json
import re
import shlex
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MANIFIESTO = json.loads((RAIZ / "tests" / "regresiones.json").read_text(encoding="utf-8"))
CATALOGO = (RAIZ / "docs" / "referencia" / "BUG_CATALOG.md").read_text(encoding="utf-8")
OPERADORES = {"and", "or", "not"}


def _nombres_de_test(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    return {n.name for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}


def _selectores():
    for entrada in MANIFIESTO:
        for sel in entrada.get("selectores", []):
            yield entrada["id"], sel


def test_identificadores_unicos_y_bien_formados():
    ids = [e["id"] for e in MANIFIESTO]
    assert all(re.fullmatch(r"W-\d{2}", i) for i in ids)
    assert ids == sorted(ids), "el manifiesto va ordenado por identificador"
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize("entrada", MANIFIESTO, ids=lambda e: e["id"])
def test_cada_entrada_tiene_prueba_o_evidencia_y_version_de_referencia(entrada):
    assert entrada["titulo"].strip()
    assert re.fullmatch(r"v\d+\.\d+\.\d+", entrada["ref"]), "``ref`` es el tag que aún tenía el bug"
    assert entrada.get("selectores") or entrada.get("evidencia"), "sin selectores debe explicar la evidencia"


@pytest.mark.parametrize("ident", [e["id"] for e in MANIFIESTO])
def test_cada_bug_tiene_ficha_en_el_catalogo(ident):
    assert re.search(rf"(?m)^\| \*\*{ident}\*\* \|", CATALOGO), f"{ident} no tiene su fila de ficha en docs/referencia/BUG_CATALOG.md"


@pytest.mark.parametrize(("ident", "selector"), list(_selectores()), ids=lambda v: v if isinstance(v, str) else None)
def test_los_selectores_apuntan_a_tests_que_existen(ident, selector):
    """El archivo existe y cada palabra de la expresión ``-k`` aparece en el nombre de algún test."""
    partes = shlex.split(selector)
    archivo = RAIZ / partes[0].split("::")[0]
    assert archivo.is_file(), f"{ident}: {archivo} no existe"
    nombres = _nombres_de_test(archivo)
    if "::" in partes[0]:
        assert partes[0].split("::")[1].split("[")[0] in nombres
    if "-k" in partes:
        palabras = [p for p in re.split(r"[\s()]+", partes[partes.index("-k") + 1]) if p and p not in OPERADORES]
        for palabra in palabras:
            assert any(palabra in n for n in nombres), f"{ident}: «{palabra}» no coincide con ningún test de {archivo.name}"


def test_los_doctests_estan_activos():
    """R-15: los ejemplos de los docstrings se ejecutan en cada ``pytest`` (C-19)."""
    pyproject = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    assert "--doctest-modules" in pyproject
