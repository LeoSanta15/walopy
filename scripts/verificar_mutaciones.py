"""Mutación manual de una línea: comprueba que cada test de regresión FALLA si el bug vuelve.

Para cada mutante copia ``src/`` a un directorio temporal, aplica un reemplazo de una línea que reintroduce el bug
y ejecuta los tests asociados contra esa copia. El mutante debe quedar «muerto» (algún test falla); si «sobrevive»,
el test no protege esa línea. Es un complemento de ``verificar_regresion.py`` (que compara con el tag anterior).

Uso::

    python scripts/verificar_mutaciones.py            # todos los mutantes
    python scripts/verificar_mutaciones.py MU-03 MU-07
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess  # noqa: S404
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# (id, bug, archivo, línea original, línea mutada, selector de pytest)
MUTANTES = [
    ("MU-01", "W-01 NaN pasa la validación", "_utils.py",
     "if not np.isfinite(v) or v <= 0:", "if v <= 0:",
     "tests/test_regresion_validacion.py -k 'cpm_rechaza or mrp_rechaza or weibull_rechaza'"),
    ("MU-02", "W-18 bool aceptado como número", "_utils.py",
     "if isinstance(value, (bool, np.bool_)):", "if False:",
     "tests/test_regresion_validacion.py -k bool"),
    ("MU-03", "W-09 mmc desborda (recurrencia de Erlang-B rota)", "queuing.py",
     "B = a * B / (k + a * B)", "B = a * B / (k + a)",
     "tests/test_mmc_estable.py"),
    ("MU-04", "W-14 actividades duplicadas aceptadas", "project.py",
     "if nm in vistos:", "if False:",
     "tests/test_regresion_validacion.py -k actividades_duplicadas"),
    ("MU-05", "W-16 MRP sin aviso de liberaciones vencidas", "inventory.py",
     "if past_due > 0.0:", "if False:",
     "tests/test_regresion_validacion.py -k mrp_avisa"),
    ("MU-06", "W-19 holguras con -0.0", "project.py",
     "total_float=round(tf, 10) + 0.0,", "total_float=round(tf, 10),",
     "tests/test_cpm_pert.py -k holguras"),
    ("MU-07", "W-12 plot_break_even ignora break_even_sales", "plotting.py",
     'en_ventas = "price_per_unit" not in p', "en_ventas = False",
     "tests/test_plotting.py -k break_even_sales"),
    ("MU-08", "W-21 batch_model no propaga con errors='raise'", "solver.py",
     'if errors == "raise":', "if False:",
     "tests/test_solver.py -k errors_raise"),
    ("MU-09", "W-07 demanda 0 rechazada en ABC", "inventory.py",
     'D   = as_nonneg(_clave(it, i, "demand"), f"items[{i}][\'demand\']")',
     'D   = as_positive(_clave(it, i, "demand"), f"items[{i}][\'demand\']")',
     "tests/test_regresion_validacion.py -k abc_acepta"),
    ("MU-10", "W-02 mttr sin validar", "reliability.py",
     'mttr_v = None if mttr is None else as_nonneg(mttr, "mttr")', "mttr_v = mttr",
     "tests/test_regresion_validacion.py -k 'mtbf_rechaza or sistemas_rechazan_t'"),
    ("MU-11", "W-20 versión desincronizada de los metadatos", "__init__.py",
     '__version__ = "0.4.3"', '__version__ = "0.4.4"',
     "tests/test_version.py"),
    ("MU-12", "H-02 EOQResult.plot() roto (plot_eoq)", "inventory.py",
     "return plot_eoq(self, **kwargs)", 'raise ImportError("plot_eoq")',
     "tests/test_plotting.py -k eoq"),
    ("MU-13", "H-03 árbol ROI con fórmula errónea", "kpi.py",
     "net_profit    = revenue - total_cost", "net_profit    = revenue + total_cost",
     "tests/test_kpi.py"),
    ("MU-14", "W-17 servidores sin cota", "queuing.py",
     'c   = as_int_positive(c, "c", max=MAX_SERVIDORES)', 'c   = as_int_positive(c, "c")',
     "tests/test_mmc_estable.py -k rechaza_demasiados"),
    ("MU-15", "H-07 exchange_curve acepta lista vacía", "inventory.py",
     "    if len(items) == 0:\n        raise ValueError(_t(\"inventory.error.exchange_curve.items_debe_contener_menos_elemento\"))\n\n    parsed: list[dict[str, Any]] = []",
     "    parsed: list[dict[str, Any]] = []",
     "tests/test_exchange_curve.py -k vacios"),
    ("MU-16", "H-07 exchange_curve no acepta números como texto", "inventory.py",
     'D  = as_positive(float(it["demand"]),        f"items[{idx}][\'demand\']")',
     'D  = as_positive(it["demand"] + 0,           f"items[{idx}][\'demand\']")',
     "tests/test_exchange_curve.py -k texto"),
    ("MU-17", "R-07 una gráfica modifica rcParams", "plotting.py",
     "fig, ax = plt.subplots(figsize=figsize or (8, 4))",
     'plt.rcParams["font.size"] = 99; fig, ax = plt.subplots(figsize=figsize or (8, 4))',
     "tests/test_plotting.py -k rcparams"),
    ("MU-18", "W-26 árbol de KPI en blanco (el padre vale menos que la suma de sus hijos)", "plotting.py",
     "values[pos] = max(abs(node.value), children_size, 1e-9)", "values[pos] = max(abs(node.value), 1e-9)",
     "tests/test_kpi_grafica.py -k ningun_padre"),
    ("MU-19", "W-27 wagner_whitin paga preparación en periodos sin demanda", "inventory.py",
     "        if demands_v[i - 1] == 0:\n            # Sin demanda no hay pedido", "        if False:\n            # Sin demanda no hay pedido",
     "tests/test_wagner_whitin_ceros.py"),
    ("MU-20", "W-28 solve_servers/optimize_servers saltan el mínimo estable", "solver.py",
     "    c = max(1, int(lam / mu))\n    while lam / (c * mu) >= 1.0:\n        c += 1\n    return c",
     "    return int(np.ceil(lam / mu)) + 1",
     "tests/test_servidores_minimos.py"),
    ("MU-21", "W-29 optimize_servers no valida c_max", "solver.py",
     'c_max           = as_int_positive(c_max, "c_max", max=MAX_SERVIDORES)', "c_max           = c_max",
     "tests/test_servidores_cmax.py -k optimize_servers"),
    ("MU-22", "W-30 batch_model rechaza enteros en DataFrames dispersos", "solver.py",
     "(k in sparse_int_cols and isinstance", "(False and isinstance",
     "tests/test_solver_contratos.py -k disperso_con_parametro_entero"),
    ("MU-23", "W-31 compare() sin resultados devuelve una tabla vacía", "solver.py",
     "    if len(results) == 0:", "    if False:",
     "tests/test_solver_contratos.py -k sin_resultados"),
    ("MU-24", "W-31 compare descarta las filas de un resultado de varias filas", "solver.py",
     "if tabla is not None and len(tabla) == 1:", "if tabla is not None:",
     "tests/test_solver_contratos.py -k varias_filas or duracion"),
    ("MU-25", "W-32 sensitivity acepta values vacío", "solver.py",
     "    if len(values) == 0:", "    if False:",
     "tests/test_solver_contratos.py -k values_vacio"),
    ("MU-26", "W-32 sensitivity no comprueba el parámetro", "solver.py",
     "if parametros is not None and param not in parametros and", "if False and param not in parametros and",
     "tests/test_solver_contratos.py -k parametro_inexistente"),
]


def ejecutar(mutante: tuple, base: Path) -> str:
    ident, _bug, archivo, viejo, nuevo, selector = mutante
    copia = base / ident / "src"
    shutil.copytree(RAIZ / "src", copia, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    ruta = copia / "walopy" / archivo
    texto = ruta.read_text(encoding="utf-8")
    if texto.count(viejo) < 1:
        return "INVALIDO"
    ruta.write_text(texto.replace(viejo, nuevo, 1), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(copia), "MPLBACKEND": "Agg"}
    orden = [sys.executable, "-m", "pytest", *shlex.split(selector), "-o", "addopts=", "-o", "filterwarnings=",
             "-p", "no:cacheprovider", "-q", "--tb=no", "--timeout=30", "-x"]
    try:
        r = subprocess.run(orden, cwd=RAIZ, env=env, capture_output=True, text=True, timeout=300, check=False)  # noqa: S603
    except subprocess.TimeoutExpired:
        return "MUERTO"
    if r.returncode == 5:
        return "SIN_TESTS"
    return "SOBREVIVE" if r.returncode == 0 else "MUERTO"


def main(ids: list[str]) -> int:
    mutantes = [m for m in MUTANTES if not ids or m[0] in ids]
    problemas = 0
    with tempfile.TemporaryDirectory() as tmp:
        for m in mutantes:
            estado = ejecutar(m, Path(tmp))
            ok = estado == "MUERTO"
            print(f"[{'OK ' if ok else 'MAL'}] {m[0]} {estado:9s} {m[1]}")
            problemas += 0 if ok else 1
    if problemas:
        print(f"\n{problemas} mutante(s) sobreviven o son inválidos: el test no protege esa línea (o la línea cambió).")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
