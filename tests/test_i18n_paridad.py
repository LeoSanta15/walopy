"""Paridad entre idiomas del catálogo de mensajes (fase 1+ de la internacionalización).

Los verificadores se prueban con catálogos de prueba; el test sobre los catálogos reales se activa solo cuando el catálogo inglés
deje de estar vacío.
"""
from __future__ import annotations

import json
from pathlib import Path
from string import Formatter

import pytest

RAIZ = Path(__file__).resolve().parents[1]
INVENTARIO = json.loads((RAIZ / "docs" / "auditoria" / "inventario_i18n_base.json").read_text(encoding="utf-8"))
TIPOS_SIN_CLAVE_DE_CATALOGO = {"nombre_arg", "acceso_columna"}  # nombres de argumento y lecturas: no son textos a traducir


def marcadores(plantilla: str) -> set:
    return {campo for _, campo, _, _ in Formatter().parse(plantilla) if campo}


def errores_de_paridad(base: dict, otro: dict, exentas: frozenset = frozenset()) -> list:
    """Claves ausentes o sobrantes, marcadores distintos y traducciones idénticas al texto base (sin traducir)."""
    errores = [f"falta la clave {k}" for k in sorted(set(base) - set(otro))]
    errores += [f"sobra la clave {k}" for k in sorted(set(otro) - set(base))]
    for k in sorted(set(base) & set(otro)):
        if marcadores(base[k]) != marcadores(otro[k]):
            errores.append(f"marcadores distintos en {k}: {sorted(marcadores(base[k]))} ≠ {sorted(marcadores(otro[k]))}")
        elif otro[k] == base[k] and k not in exentas:
            errores.append(f"sin traducir: {k}")
    return errores


# --- los verificadores funcionan (activos desde la fase 0) ------------------------------------------------------------
ES = {"a.error.x": "'{name}' debe ser positivo, se recibió {value!r}.", "a.cli.y": "Muestra la versión."}


def test_paridad_correcta_no_da_errores():
    EN = {"a.error.x": "'{name}' must be positive; got {value!r}.", "a.cli.y": "Shows the version."}
    assert errores_de_paridad(ES, EN) == []


def test_detecta_clave_ausente_y_sobrante():
    EN = {"a.error.x": "'{name}' must be positive; got {value!r}.", "a.otra": "x"}
    e = errores_de_paridad(ES, EN)
    assert "falta la clave a.cli.y" in e and "sobra la clave a.otra" in e


def test_detecta_marcadores_distintos():
    EN = {"a.error.x": "'{name}' must be positive.", "a.cli.y": "Shows the version."}
    assert any("marcadores distintos en a.error.x" in x for x in errores_de_paridad(ES, EN))


def test_detecta_traduccion_sin_hacer_salvo_exentas():
    EN = {"a.error.x": ES["a.error.x"], "a.cli.y": "Shows the version."}
    assert errores_de_paridad(ES, EN) == ["sin traducir: a.error.x"]
    assert errores_de_paridad(ES, EN, exentas=frozenset({"a.error.x"})) == []


# --- catálogos reales -------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def i18n():
    from walopy import _i18n

    return _i18n


def test_el_catalogo_es_contiene_todas_las_claves_del_inventario(i18n):
    esperadas = {e["clave"] for e in INVENTARIO["entradas"] if e["tipo"] not in TIPOS_SIN_CLAVE_DE_CATALOGO}
    assert esperadas - set(i18n.CATALOGOS["es"]) == set()


def test_los_idiomas_tienen_las_mismas_claves_y_marcadores(i18n):
    """Se activa cuando el catálogo inglés deja de estar vacío (fase 2); mientras tanto ``t()`` recurre al español."""
    if not i18n.CATALOGOS["en"]:
        pytest.skip("catálogo en inglés pendiente (fase 2): t() recurre al español")
    exentas = frozenset(getattr(i18n, "EXENTAS_DE_TRADUCCION", ()))
    errores = errores_de_paridad(i18n.CATALOGOS["es"], i18n.CATALOGOS["en"], exentas)
    assert not errores, "\n".join(errores[:20])
