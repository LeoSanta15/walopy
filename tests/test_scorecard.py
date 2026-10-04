"""La media del SCORECARD se recalcula desde su propia tabla (una cifra no se da por buena sin recalcularla)."""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TEXTO = (RAIZ / "docs" / "retrospectiva" / "SCORECARD.md").read_text(encoding="utf-8")
NOTAS = [int(m.group(1)) for m in re.finditer(r"(?m)^\| \d{1,2} \| [^|]+ \| ([0-5]) \|", TEXTO)]


def test_hay_14_dimensiones_con_nota_entre_0_y_5():
    assert len(NOTAS) == 14


def test_la_media_declarada_coincide_con_la_tabla():
    m = re.search(r"Media aritmética: (\d),(\d{2})\*\* \((\d+) / (\d+);", TEXTO)
    assert m, "falta la línea «**Media aritmética: X,XX** (suma / 14; …)»"
    declarada = float(f"{m.group(1)}.{m.group(2)}")
    assert int(m.group(3)) == sum(NOTAS) and int(m.group(4)) == len(NOTAS)
    assert declarada == round(sum(NOTAS) / len(NOTAS), 2)


def test_el_recuento_por_notas_declarado_es_correcto():
    m = re.search(r"(\w+) dimensiones en 4 y (\w+) en 3", TEXTO)
    assert m
    palabras = {"diez": 10, "cuatro": 4}
    assert NOTAS.count(4) == palabras[m.group(1)] and NOTAS.count(3) == palabras[m.group(2)]
