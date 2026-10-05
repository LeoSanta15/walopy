"""La salida que ve la persona usuaria no cambia al refactorizar (internacionalización, fase 1).

``tests/golden/salida_es.json`` se generó con ``python scripts/instantanea_salida.py --escribir`` sobre el código de v0.3.0, ANTES de
mover los textos a un catálogo. Cubre resultados, tablas, mensajes de error, avisos, gráficas, README y CLI, con el idioma por defecto.
Si cambia a propósito un texto en español, regenera la instantánea y revisa el diff como parte del PR.

Excepción deliberada (W-26): la ``grafica`` de ``oee_kpi_tree``, ``throughput_kpi_tree`` y ``roi_kpi_tree`` se actualizó a mano en la instantánea: ahora
rotula el valor real de cada nodo en ``text`` (los árboles salían en blanco en el navegador, ver ``tests/test_kpi_grafica.py``).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GOLDEN = RAIZ / "tests" / "golden" / "salida_es.json"


def test_la_salida_en_espanol_es_identica_a_la_instantanea():
    env = {k: v for k, v in os.environ.items() if k != "WALOPY_LANG"}   # el idioma por defecto, sin importar el entorno
    env["MPLBACKEND"] = "Agg"
    r = subprocess.run(  # noqa: S603
        [sys.executable, str(RAIZ / "scripts" / "instantanea_salida.py"), "--comprobar", str(GOLDEN)],
        capture_output=True, text=True, env=env, check=False, timeout=600,
    )
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1000:]


def test_la_instantanea_no_esta_vacia_ni_contiene_excepciones_inesperadas():
    datos = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert len(datos["funciones"]) >= 67 and len(datos["errores"]) > 900 and len(datos["readme"]) >= 60
    assert "EXCEPCION" not in GOLDEN.read_text(encoding="utf-8")
