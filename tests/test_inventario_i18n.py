"""Inventario de texto visible (fase 0 de la internacionalización).

El inventario (``docs/auditoria/inventario_i18n.json``) lo genera ``scripts/inventario_i18n.py`` recorriendo el código con ``ast``.
Estos tests garantizan que no se queda atrás del código mientras se prepara la migración y que su cobertura se comprueba
con un método **independiente** del extractor (cualquier cadena con rasgos del español debe figurar en él).
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from string import Formatter

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SRC = RAIZ / "src" / "walopy"
INVENTARIO = json.loads((RAIZ / "docs" / "auditoria" / "inventario_i18n.json").read_text(encoding="utf-8"))
RASGOS_ES = re.compile(r"[áéíóúñÁÉÍÓÚÑ¿¡]|\b(debe|deben|para|con|sin|por|valor|tiempo|costo|demanda|tasa|error|lista|número)\b")
FORMATO_CLAVE = re.compile(r"^[a-z0-9]+\.[a-z_]+\.[a-z0-9_]+\.[a-z0-9_]+$")


def cadenas_con_rasgos_del_espanol() -> list[tuple[str, int, str]]:
    """Cadenas literales (fuera de docstrings) con tildes, ñ o palabras españolas, sin usar el extractor."""
    encontradas = []
    for archivo in sorted(SRC.glob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        docs = {
            id(n.body[0].value)
            for n in ast.walk(arbol)
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)
        }
        for n in ast.walk(arbol):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and RASGOS_ES.search(n.value):
                encontradas.append((archivo.stem, n.lineno, n.value))
    return encontradas


def ausentes_del_inventario(entradas: list[dict]) -> list[tuple[str, int, str]]:
    union = "\n".join(e["es"] for e in entradas).replace("{{", "{").replace("}}", "}")
    ausentes = []
    for modulo, linea, texto in cadenas_con_rasgos_del_espanol():
        fragmento = re.sub(r"\{[^{}]*\}", "", texto).strip()
        if fragmento and fragmento not in union:
            ausentes.append((modulo, linea, texto[:60]))
    return ausentes


def test_el_inventario_esta_al_dia():
    """Falla si hay textos nuevos, cambiados o eliminados en ``src/`` sin regenerar el inventario."""
    r = subprocess.run(  # noqa: S603
        [sys.executable, str(RAIZ / "scripts" / "inventario_i18n.py"), "--comprobar"], capture_output=True, text=True, check=False
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_no_hay_textos_sin_clasificar_ni_mensajes_indirectos():
    sin = [e["es"] for e in INVENTARIO["entradas"] if e["tipo"] == "sin_clasificar"]
    assert not sin, f"clasifica estos textos en scripts/inventario_i18n.py: {sin}"
    assert not INVENTARIO["indirectos"], INVENTARIO["indirectos"]


def test_cobertura_independiente_del_extractor():
    assert ausentes_del_inventario(INVENTARIO["entradas"]) == []


def test_el_verificador_independiente_detecta_un_texto_ausente():
    """Control negativo: sin la entrada de un mensaje real, la comprobación independiente debe señalarlo."""
    sin_una = [e for e in INVENTARIO["entradas"] if e["clave"] != "utils.error.as_positive.numero_finito_positivo_recibio"]
    if len(sin_una) == len(INVENTARIO["entradas"]):  # la clave cambió: busca otra de _utils
        objetivo = next(e for e in INVENTARIO["entradas"] if e["modulo"] == "_utils" and e["tipo"] == "error")
        sin_una = [e for e in INVENTARIO["entradas"] if e is not objetivo]
    assert len(ausentes_del_inventario(sin_una)) >= 1


def test_claves_unicas_y_con_formato():
    claves = [e["clave"] for e in INVENTARIO["entradas"]]
    assert len(claves) == len(set(claves))
    malas = [c for c in claves if not FORMATO_CLAVE.match(re.sub(r"_\d+$", "", c))]
    assert not malas, malas[:5]


@pytest.mark.parametrize("entrada", INVENTARIO["entradas"], ids=lambda e: e["clave"])
def test_cada_plantilla_es_un_formato_valido_con_sus_marcadores(entrada):
    nombres = {campo for _, campo, _, _ in Formatter().parse(entrada["es"]) if campo}
    assert nombres == {m["nombre"] for m in entrada["marcadores"]}
    assert all(n.isidentifier() for n in nombres)
    entrada["es"].format(**{n: 1 for n in nombres})  # no lanza: llaves y conversiones bien formadas
