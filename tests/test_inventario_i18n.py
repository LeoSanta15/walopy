"""Catálogo de textos (internacionalización): consistencia entre el código, el catálogo en español y la línea base de la fase 0.

* ``docs/auditoria/inventario_i18n_base.json`` es el inventario **congelado** de los textos que había en ``src/walopy`` antes de migrarlos
  al catálogo (lo generó ``scripts/inventario_i18n.py --src <código anterior>``). No cambia salvo que se decida cambiar un texto.
* Tras la migración, el código solo usa claves ``_t("modulo.tipo.funcion.resumen", ...)``; los textos viven en ``_catalogo_es.py``.
* Las comprobaciones «independientes» no usan el extractor: recorren el código con ``ast`` por su cuenta.
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

from walopy._catalogo_es import ES

RAIZ = Path(__file__).resolve().parents[1]
SRC = RAIZ / "src" / "walopy"
BASE = json.loads((RAIZ / "docs" / "auditoria" / "inventario_i18n_base.json").read_text(encoding="utf-8"))
ENTRADAS = BASE["entradas"]
CLAVE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+){2,3}(_\d+)?$")
RASGOS_ES = re.compile(r"[áéíóúñÁÉÍÓÚÑ¿¡]|\b(debe|deben|para|con|sin|por|valor|tiempo|costo|demanda|tasa|error|lista|número)\b")
CATALOGOS = {"_catalogo_es", "_catalogo_en"}
SIN_CLAVE_DE_CATALOGO = {"nombre_arg", "acceso_columna"}    # nombres de argumentos y lecturas de columnas: no son textos a traducir


def _archivos():
    return [a for a in sorted(SRC.glob("*.py")) if a.stem not in CATALOGOS]


def _arbol(archivo: Path) -> ast.AST:
    return ast.parse(archivo.read_text(encoding="utf-8"))


def _docstrings(arbol: ast.AST) -> set[int]:
    return {
        id(n.body[0].value)
        for n in ast.walk(arbol)
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.body
        and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)
    }


def _marcadores(plantilla: str) -> set[str]:
    return {campo for _, campo, _, _ in Formatter().parse(plantilla) if campo}


def _claves_de_t(archivo: Path):
    """(clave, nombres de argumentos con nombre | None si hay ``**``, línea) de cada llamada ``_t("clave", ...)``."""
    for n in ast.walk(_arbol(archivo)):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_t" and n.args
                and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
            nombres = None if any(k.arg is None for k in n.keywords) else {k.arg for k in n.keywords}
            yield n.args[0].value, nombres, n.lineno


# --- el código no tiene textos fuera del catálogo ---------------------------------------------------------------------------------
def test_no_quedan_textos_visibles_fuera_del_catalogo():
    """El extractor (``scripts/inventario_i18n.py``) no encuentra literales visibles: todo pasa por ``_t()``."""
    r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "inventario_i18n.py")], capture_output=True, text=True, check=False)  # noqa: S603
    assert r.returncode == 0, r.stdout + r.stderr


def test_el_inventario_base_esta_completo():
    sin = [e["es"] for e in ENTRADAS if e["tipo"] == "sin_clasificar"]
    assert not sin, f"clasifica estos textos en scripts/inventario_i18n.py: {sin}"
    assert not BASE["indirectos"], BASE["indirectos"]
    assert BASE["total"] == len(ENTRADAS)


def test_los_argumentos_de_raise_y_warn_son_claves_de_catalogo():
    """Comprobación independiente del extractor: en un ``raise``/``warnings.warn`` solo se admiten claves, nunca prosa literal."""
    sueltos = []
    for archivo in _archivos():
        arbol = _arbol(archivo)
        padres = {id(h): p for p in ast.walk(arbol) for h in ast.iter_child_nodes(p)}
        for n in ast.walk(arbol):
            args = None
            if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call):
                args = n.exc.args
            elif isinstance(n, ast.Call) and getattr(n.func, "attr", getattr(n.func, "id", "")) == "warn" and n.args:
                args = n.args[:1]
            for a in args or ():
                for m in ast.walk(a):
                    if (isinstance(m, ast.Constant) and isinstance(m.value, str) and re.search("[A-Za-z]{3}", m.value)
                            and not CLAVE.match(m.value) and not isinstance(padres.get(id(m)), ast.Subscript)):
                        sueltos.append(f"{archivo.name}:{m.lineno} {m.value[:50]!r}")
    assert not sueltos, "texto literal en un raise/warn (usa _t('clave')):\n" + "\n".join(sueltos)


def test_los_literales_con_rasgos_del_espanol_son_solo_claves_fijas_de_params():
    """Fuera de docstrings y catálogos, un literal en español solo puede ser una clave fija de ``result.params`` (decisión D1)."""
    permitidos = {texto for clave, texto in ES.items() if ".clave_params." in clave}
    sueltos = []
    for archivo in _archivos():
        arbol = _arbol(archivo)
        docs = _docstrings(arbol)
        for n in ast.walk(arbol):
            if (isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and RASGOS_ES.search(n.value)
                    and not CLAVE.match(n.value) and n.value not in permitidos):
                sueltos.append(f"{archivo.name}:{n.lineno} {n.value[:50]!r}")
    assert not sueltos, "\n".join(sueltos)


def test_el_verificador_independiente_detecta_un_texto_literal(tmp_path):
    """Control negativo: la misma lógica señala un mensaje literal en un ``raise``."""
    f = tmp_path / "malo.py"
    f.write_text('def g():\n    raise ValueError("x debe ser positivo")\n', encoding="utf-8")
    assert [m.value for m in ast.walk(_arbol(f)) if isinstance(m, ast.Constant) and RASGOS_ES.search(str(m.value))] == ["x debe ser positivo"]


# --- el catálogo en español es consistente con el código y con la línea base ------------------------------------------------------
# Textos de v0.3.0 corregidos a propósito después (cada uno es un bug de v0.3.0, no un cambio de estilo).
CORREGIDAS_TRAS_V030 = {
    "inventory.error.eoq_quantity_discount.feasible_price_break_found",   # estaba en inglés dentro del catálogo español (R-03)
}


def test_el_catalogo_es_contiene_todas_las_claves_de_la_base_con_su_texto():
    esperadas = {e["clave"]: e["es"] for e in ENTRADAS if e["tipo"] not in SIN_CLAVE_DE_CATALOGO}
    assert {k for k in esperadas if k not in ES} == set()
    cambiadas = [k for k, v in esperadas.items() if ES[k] != v and k not in CORREGIDAS_TRAS_V030]
    assert not cambiadas, f"el texto en español cambió respecto a v0.3.0 (¿intencionado? regenera la base): {cambiadas[:5]}"


# Textos añadidos después de v0.3.0 (no están en la línea base congelada): una clave nueva debe declararse aquí a propósito.
AÑADIDAS_TRAS_V030 = {
    "i18n.error.validar.idioma_no_admitido",
    "solver.error.optimize_servers.sin_servidores_estables_hasta_c_max",   # W-29
    "solver.error.sensitivity.values_no_puede_estar_vacio",   # W-32
    "solver.error.sensitivity.param_no_es_parametro_modelo",
    "solver.error.compare.sin_resultados",   # W-31
    "project.cabecera.to_frame.ht",    # «HT»/«HL» (holgura total/libre): acrónimos españoles que el extractor no veía; ya existían en v0.3.0
    "project.cabecera.to_frame.hl",
}


def test_el_catalogo_no_tiene_claves_que_no_estaban_en_v030():
    """Toda clave del catálogo viene de la línea base (o se declara arriba): detecta etiquetas inventadas por una migración errónea."""
    en_base = {e["clave"] for e in ENTRADAS}
    sobran = sorted(set(ES) - en_base - AÑADIDAS_TRAS_V030)
    assert not sobran, f"claves que no estaban en v0.3.0 (añádelas a AÑADIDAS_TRAS_V030 si son intencionadas): {sobran[:5]}"


def test_las_claves_usadas_en_el_codigo_existen_en_el_catalogo():
    usadas = {c for a in _archivos() for c, _, _ in _claves_de_t(a)}
    usadas |= {c.value for a in _archivos() for c in ast.walk(_arbol(a)) if isinstance(c, ast.Constant) and isinstance(c.value, str) and CLAVE.match(c.value)}
    assert sorted(usadas - set(ES)) == []


def test_no_hay_claves_huerfanas_en_el_catalogo():
    en_codigo = {c.value for a in _archivos() for c in ast.walk(_arbol(a)) if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    huerfanas = [k for k in ES if k not in en_codigo and ".clave_params." not in k]
    assert huerfanas == [], "claves del catálogo que ningún código usa: " + ", ".join(huerfanas[:5])


def test_cada_llamada_a_t_pasa_exactamente_los_marcadores_de_la_plantilla():
    errores = []
    for archivo in _archivos():
        for clave, nombres, linea in _claves_de_t(archivo):
            if clave in ES and nombres is not None and nombres != _marcadores(ES[clave]):
                errores.append(f"{archivo.name}:{linea} {clave}: pasa {sorted(nombres)}, la plantilla pide {sorted(_marcadores(ES[clave]))}")
    assert not errores, "\n".join(errores)


def test_claves_unicas_y_con_formato():
    assert len({e["clave"] for e in ENTRADAS}) == len(ENTRADAS)
    malas = [k for k in ES if not CLAVE.match(k)]
    assert not malas, malas[:5]


@pytest.mark.parametrize("clave", sorted(ES))
def test_cada_plantilla_es_un_formato_valido(clave):
    nombres = _marcadores(ES[clave])
    assert all(n.isidentifier() for n in nombres)
    ES[clave].format(**{n: 1 for n in nombres})   # no lanza: llaves y conversiones bien formadas
