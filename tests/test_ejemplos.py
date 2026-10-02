"""Los scripts de examples/ deben ejecutarse sin error."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
EJEMPLOS = sorted((RAIZ / "examples").glob("*.py"))


@pytest.mark.parametrize("script", EJEMPLOS, ids=lambda p: p.name)
def test_el_ejemplo_se_ejecuta(script, tmp_path):
    env = {**os.environ, "MPLBACKEND": "Agg", "PYTHONWARNINGS": "error"}
    r = subprocess.run(  # noqa: S603
        [sys.executable, str(script)], capture_output=True, text=True, timeout=120, cwd=tmp_path, env=env, check=False
    )
    assert r.returncode == 0, r.stderr[-500:]
    assert r.stdout.strip()


def test_hay_ejemplos():
    assert len(EJEMPLOS) >= 5
