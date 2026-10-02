"""``scripts/notas_release.py`` extrae del CHANGELOG el cuerpo del release (se pedía a mano en cada versión)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "notas_release.py"


def _ejecutar(version: str):
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), version], capture_output=True, text=True, check=False
    )


def test_extrae_la_seccion_de_una_version_con_y_sin_v():
    a, b = _ejecutar("0.3.0"), _ejecutar("v0.3.0")
    assert a.returncode == 0 and a.stdout == b.stdout
    assert "Cambios que rompen compatibilidad" in a.stdout
    assert "## [" not in a.stdout, "no mezcla la sección de otra versión"


def test_no_incluye_la_version_anterior():
    assert "NEH flow-shop" not in _ejecutar("0.3.0").stdout


def test_version_inexistente_falla():
    r = _ejecutar("9.9.9")
    assert r.returncode == 1 and "9.9.9" in r.stderr
