"""Los ejemplos de código de la documentación son tests: todo bloque ```python debe ejecutarse sin error.

Los bloques de un archivo comparten el espacio de nombres (se ejecutan en orden, como los lee una persona).
"""
from __future__ import annotations

import io
import re
import warnings
from contextlib import redirect_stdout
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVOS = [RAIZ / "README.md", *sorted((RAIZ / "docs" / "source").glob("*.md"))]
PATRON = re.compile(r"```python\n(.*?)```", re.S)


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.name)
def test_los_bloques_de_codigo_se_ejecutan(archivo, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # algunos ejemplos guardan archivos (.png, .html)
    texto = archivo.read_text(encoding="utf-8")
    bloques = PATRON.findall(texto)
    espacio: dict = {}
    fallos = []
    for i, bloque in enumerate(bloques, 1):
        linea = texto[: texto.index(bloque)].count("\n") + 1
        try:
            with warnings.catch_warnings(), redirect_stdout(io.StringIO()):
                warnings.simplefilter("ignore")
                exec(compile(bloque, f"{archivo.name}[bloque {i}]", "exec"), espacio)  # noqa: S102
        except Exception as e:  # noqa: BLE001
            fallos.append(f"bloque {i} (línea ~{linea}): {type(e).__name__}: {str(e)[:100]}")
    assert not fallos, f"{archivo.name}:\n" + "\n".join(fallos)


def test_hay_bloques_en_el_readme():
    assert len(PATRON.findall((RAIZ / "README.md").read_text(encoding="utf-8"))) >= 50
