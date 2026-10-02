"""La documentación no puede quedar atrás del código: cada símbolo público está documentado (R-13)."""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

import walopy

RAIZ = Path(__file__).resolve().parents[1]
README = (RAIZ / "README.md").read_text(encoding="utf-8")
REFERENCIA = "\n".join(p.read_text(encoding="utf-8") for p in (RAIZ / "docs" / "source" / "referencia").glob("*.rst"))


@pytest.mark.parametrize("nombre", sorted(walopy.__all__))
def test_simbolo_publico_en_la_referencia_sphinx(nombre):
    assert re.search(rf"walopy\.{re.escape(nombre)}\b", REFERENCIA), f"{nombre} no está en docs/source/referencia"


@pytest.mark.parametrize("nombre", sorted(n for n in walopy.__all__ if inspect.isfunction(getattr(walopy, n))))
def test_funcion_publica_en_el_readme(nombre):
    assert re.search(rf"\b{re.escape(nombre)}\b", README), f"{nombre} no aparece en el README"


def test_claude_md_lista_todos_los_modulos():
    claude = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
    modulos = [p.stem for p in (RAIZ / "src" / "walopy").glob("*.py")]
    faltan = [m for m in modulos if f"`{m}.py`" not in claude]
    assert not faltan, f"CLAUDE.md no menciona: {faltan}"
