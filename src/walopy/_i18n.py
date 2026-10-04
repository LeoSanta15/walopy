"""Internacionalización: idioma activo, catálogos de textos y la función ``t()``.

Los textos que ve la persona usuaria (mensajes, etiquetas, cabeceras, gráficas, ayuda del CLI) viven en los catálogos
``_catalogo_es.py`` y ``_catalogo_en.py``, con claves ``modulo.tipo.funcion.resumen``. El idioma por defecto es el español.

Orden de prioridad del idioma activo: ``with language("en"):`` (contexto, seguro con hilos y ``asyncio``) →
``set_language("en")`` (global del proceso) → variable de entorno ``WALOPY_LANG`` → español.
"""
from __future__ import annotations

import os
from contextvars import ContextVar, Token
from types import TracebackType
from typing import Any

from ._catalogo_en import EN, EXENTAS_DE_TRADUCCION  # noqa: F401 - se reexporta para los tests de paridad
from ._catalogo_es import ES

IDIOMAS = ("es", "en")
IDIOMA_POR_DEFECTO = "es"
CATALOGOS: dict[str, dict[str, str]] = {"es": ES, "en": EN}

_global: str | None = None
_contexto: ContextVar[str | None] = ContextVar("walopy_idioma", default=None)
_PARAMS_ES = {texto: clave for clave, texto in ES.items() if ".clave_params." in clave}


def _validar(lang: Any) -> str:
    if not isinstance(lang, str) or lang not in IDIOMAS:
        raise ValueError(t("i18n.error.validar.idioma_no_admitido", lang=lang, opciones=", ".join(IDIOMAS)))
    return lang


def _desde_entorno() -> str:
    valor = os.environ.get("WALOPY_LANG", "").strip().lower()[:2]
    return valor if valor in IDIOMAS else IDIOMA_POR_DEFECTO     # un valor desconocido no rompe nada


def get_language() -> str:
    """Devuelve el idioma activo: ``'es'`` (por defecto) o ``'en'``.

    Returns
    -------
    str
        El idioma con el que se muestran los textos: el del contexto ``language()``, si no el de ``set_language()``,
        si no el de la variable de entorno ``WALOPY_LANG`` y, por último, ``'es'``.

    Examples
    --------
    >>> get_language()
    'es'
    """
    return _contexto.get() or _global or _desde_entorno()


def set_language(lang: str) -> None:
    """Fija el idioma de los textos para todo el proceso.

    Parameters
    ----------
    lang : str
        ``'es'`` o ``'en'``.

    Raises
    ------
    ValueError
        Si el idioma no está admitido.

    Examples
    --------
    >>> set_language("es")
    >>> get_language()
    'es'
    """
    global _global
    _global = _validar(lang)


class _Contexto:
    """Administrador de contexto devuelto por :func:`language` (valida al crearse, no al entrar)."""

    def __init__(self, lang: str) -> None:
        self._lang = lang
        self._token: Token | None = None

    def __enter__(self) -> str:
        self._token = _contexto.set(self._lang)
        return self._lang

    def __exit__(self, tipo: type[BaseException] | None, valor: BaseException | None, traza: TracebackType | None) -> None:
        if self._token is not None:
            _contexto.reset(self._token)
            self._token = None


def language(lang: str) -> _Contexto:
    """Cambia el idioma solo dentro de un bloque ``with`` (seguro con hilos y ``asyncio``).

    Parameters
    ----------
    lang : str
        ``'es'`` o ``'en'``.

    Returns
    -------
    contextmanager
        Administrador de contexto; al salir del bloque se restablece el idioma anterior.

    Raises
    ------
    ValueError
        Si el idioma no está admitido.

    Examples
    --------
    >>> with language("es"):
    ...     get_language()
    'es'
    """
    return _Contexto(_validar(lang))


def t(clave: str, /, **datos: Any) -> str:
    """Texto de ``clave`` en el idioma activo, con ``datos`` en sus marcadores (uso interno).

    Si el idioma activo no tiene la clave se usa el español, y si tampoco existe se devuelve la propia clave: la persona usuaria nunca
    recibe un ``KeyError`` por un texto que falta (un test comprueba que todas las claves usadas existen).
    """
    catalogo = CATALOGOS.get(get_language(), ES)
    plantilla = catalogo.get(clave)
    if plantilla is None:
        plantilla = ES.get(clave, clave)
    return plantilla.format(**datos)


def etiqueta_param(clave_es: str) -> str:
    """Etiqueta legible de una clave de ``result.params`` en el idioma activo (uso interno).

    Las claves de ``params`` son fijas (las de siempre, en español) para no romper ``params[...]``; solo lo que se muestra se traduce.
    Una clave desconocida (por ejemplo, de la persona usuaria) se devuelve igual.
    """
    clave = _PARAMS_ES.get(clave_es)
    return t(clave) if clave is not None else clave_es


def columna(tabla: Any, clave: str) -> str:
    """Nombre de la columna (o clave de diccionario) ``clave`` que ``tabla`` realmente tiene (uso interno).

    Las columnas se crean con el idioma activo en ese momento; si el idioma cambió entre crear la tabla y leerla (por ejemplo, un resultado creado
    dentro de ``with language("en")`` y mostrado fuera), se busca la columna en cualquiera de los idiomas en lugar de fallar.
    ``tabla`` es un ``DataFrame`` o un diccionario.
    """
    existentes = getattr(tabla, "columns", tabla)
    actual = t(clave)
    if actual in existentes:
        return actual
    for catalogo in CATALOGOS.values():
        texto = catalogo.get(clave)
        if texto is not None and texto in existentes:
            return texto
    return actual
