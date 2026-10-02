"""Comprueba que los tests de regresión de un fix FALLAN contra una versión anterior del código.

Un test de regresión que también pasa sin el fix no protege nada. Este script crea un ``git worktree``
de la referencia indicada (por defecto el último tag), ejecuta los tests *actuales* contra el código
*de esa referencia* y muestra, por cada selector, si falló (detecta el bug), pasó (no lo detecta) o se
quedó colgado (también cuenta como detección).

Uso::

    python scripts/verificar_regresion.py [--ref v0.2.8] [--guardas FRAGMENTO ...] SEL [SEL ...]

``SEL`` es un selector de pytest (``tests/test_x.py::test_y`` o ``tests/test_x.py -k expresion``, entre comillas).
Sale con código 1 si algún test que no sea una guarda (``--guardas``) pasa en la referencia.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess  # noqa: S404
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True  # noqa: S607
    ).stdout.strip()


def ultimo_tag() -> str:
    return _git("describe", "--tags", "--abbrev=0")


_MATCH = re.compile(r",\s*match=(?:r?\"[^\"\\n]*\"|r?'[^'\\n]*'|[A-Za-z_][\\w.]*)")


def copiar_tests_sin_match(destino: Path) -> Path:
    """Copia ``tests/`` quitando ``match=`` de ``pytest.raises``.

    Los mensajes de error cambiaron entre versiones (p. ej. al traducirlos): sin esto, un test fallaría
    en la referencia solo porque el texto de la excepción es distinto, no porque el bug esté presente.
    """
    nuevo = destino / "tests"
    shutil.copytree(RAIZ / "tests", nuevo, ignore=shutil.ignore_patterns("__pycache__"))
    for f in nuevo.glob("*.py"):
        f.write_text(_MATCH.sub("", f.read_text(encoding="utf-8")), encoding="utf-8")
    return nuevo


def _limitar_memoria(megabytes: int):
    """Devuelve una función para ``preexec_fn`` que limita el espacio de direcciones del proceso hijo.

    El código antiguo no tiene cotas de tamaño (ese es el bug): sin límite, ``monte_carlo_gg1(n=10**9)`` llega a
    7,7 GB y el sistema operativo mata el runner del CI. Con el límite falla con ``MemoryError`` (cuenta como detección).
    """
    def aplicar() -> None:
        import resource  # solo POSIX; se importa en el hijo

        limite = megabytes * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limite, limite))

    return aplicar


def ejecutar(selector: str, src_ref: Path, segundos: int, tests: Path, memoria_mb: int) -> tuple[str, list[str], int]:
    """Ejecuta ``selector`` contra ``src_ref``; devuelve (estado, tests que PASAN, tests que fallan).

    Requiere ``pytest-timeout`` (extra ``dev``): un test que no termina en 20 s falla, que cuenta como detección.
    ``estado`` es 'COLGADO' si se agota el tiempo total (cuenta como detección), 'SIN_TESTS' si no recoge
    ningún test y 'OK' en el resto. Se ejecuta *sin* ``-x`` para ver cada test por separado.
    """
    env = {**os.environ, "PYTHONPATH": str(src_ref), "MPLBACKEND": "Agg"}
    orden = [sys.executable, "-m", "pytest", *[a.replace("tests/", f"{tests}/", 1) if a.startswith("tests/") else a
                                              for a in shlex.split(selector)], "-o", "addopts=", "-o", "filterwarnings=",
             "-p", "no:cacheprovider", "-q", "-rA", "--no-header", "--tb=no", "--timeout=20"]
    try:
        r = subprocess.run(orden, cwd=RAIZ, env=env, capture_output=True, text=True, timeout=segundos, check=False,  # noqa: S603
                           preexec_fn=_limitar_memoria(memoria_mb) if memoria_mb and os.name == "posix" else None)
    except subprocess.TimeoutExpired:
        return "COLGADO", [], 0
    if r.returncode == 5:
        return "SIN_TESTS", [], 0
    pasan = [ln[7:].strip() for ln in r.stdout.splitlines() if ln.startswith("PASSED ")]
    fallan = sum(1 for ln in r.stdout.splitlines() if ln.startswith(("FAILED ", "ERROR ")))
    return "OK", pasan, fallan


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("selectores", nargs="*")
    ap.add_argument("--manifiesto", default=None,
                    help="JSON con [{id, titulo, ref, selectores, guardas}] (p. ej. tests/regresiones.json)")
    ap.add_argument("--ref", default=None,
                    help="tag o commit de referencia para los selectores sueltos (por defecto, el último tag); "
                         "en el manifiesto cada entrada trae su propio ``ref``")
    ap.add_argument("--guardas", nargs="*", default=[],
                    help="fragmentos de nodeid de tests que PUEDEN pasar en la referencia (guardas de comportamiento)")
    ap.add_argument("--segundos", type=int, default=60, help="tiempo máximo por selector")
    ap.add_argument("--memoria-mb", type=int, default=4096,
                    help="límite de memoria virtual por selector (0 = sin límite); protege el runner del código sin cotas")
    args = ap.parse_args()

    # (id, ref, selector, guardas)
    tareas: list[tuple[str, str, str, list[str]]] = []
    if args.selectores:
        ref_suelto = args.ref or ultimo_tag()
        tareas += [("", ref_suelto, sel, args.guardas) for sel in args.selectores]
    if args.manifiesto:
        for entrada in json.loads(Path(args.manifiesto).read_text(encoding="utf-8")):
            ref_entrada = args.ref or entrada.get("ref") or ultimo_tag()
            tareas += [(entrada["id"], ref_entrada, sel, entrada.get("guardas", [])) for sel in entrada.get("selectores", [])]

    problemas = 0
    with tempfile.TemporaryDirectory() as tmp:
        raiz_tmp = Path(tmp)
        tests = copiar_tests_sin_match(raiz_tmp)
        arboles: dict[str, Path] = {}
        try:
            for ident, ref, sel, guardas_sel in tareas:
                if ref not in arboles:
                    arboles[ref] = raiz_tmp / f"ref{len(arboles)}"
                    _git("worktree", "add", "--detach", str(arboles[ref]), ref)
                estado, pasan, fallan = ejecutar(sel, arboles[ref] / "src", args.segundos, tests, args.memoria_mb)
                etiqueta = f"{ident} " if ident else ""
                if estado == "SIN_TESTS":
                    print(f"[MAL] {etiqueta}SIN_TESTS  {sel}")
                    problemas += 1
                    continue
                if estado == "COLGADO":
                    print(f"[OK ] {etiqueta}COLGADO ({ref})  {sel}  (el código anterior no termina)")
                    continue
                guardas = [t for t in pasan if any(g in t for g in guardas_sel)]
                sospechosos = [t for t in pasan if t not in guardas]
                marca = "MAL" if sospechosos or fallan == 0 else "OK "
                print(f"[{marca}] {etiqueta}{fallan} fallan, {len(guardas)} guardas, "
                      f"{len(sospechosos)} pasan sin deber en {ref}  {sel}")
                for t in sospechosos:
                    print(f"        pasa en {ref}: {t}")
                problemas += len(sospechosos) + (1 if fallan == 0 else 0)
        finally:
            for arbol in arboles.values():
                _git("worktree", "remove", "--force", str(arbol))
    if problemas:
        print(f"\n{problemas} problema(s): tests que no detectan el bug en su referencia (o selectores vacíos). "
              "Refuerza el test o decláralo guarda con \"guardas\".")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
