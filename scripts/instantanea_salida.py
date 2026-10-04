"""Instantánea de TODO lo que la persona usuaria ve de walopy, para demostrar que una refactorización no cambia la salida.

Captura, de forma determinista:

* resultados válidos de las funciones públicas (``str()``, tablas de ``to_frame()``, campos, claves de ``params``, números);
* mensajes de las excepciones ante las entradas inválidas del test de contrato;
* avisos (``warnings``) de escenarios conocidos;
* textos de las gráficas (matplotlib y plotly);
* la salida de cada bloque de código del README y de ``docs/source/*.md``;
* la ayuda y la salida del CLI.

Uso::

    python scripts/instantanea_salida.py --escribir tests/golden/salida_es.json     # genera la referencia
    python scripts/instantanea_salida.py --comprobar tests/golden/salida_es.json    # falla si algo difiere
    python scripts/instantanea_salida.py --comprobar ref.json --idioma en           # (fase 2) en otro idioma

El idioma se fija con la variable de entorno ``WALOPY_LANG`` (si el código ya la soporta); sin ella, el defecto.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import difflib
import importlib.util
import io
import json
import os
import re
import subprocess  # noqa: S404
import sys
import tempfile
import traceback
import warnings
from contextlib import redirect_stdout
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import walopy as wl  # noqa: E402


def _cargar_contrato():
    ruta = RAIZ / "tests" / "test_contrato_entradas.py"
    spec = importlib.util.spec_from_file_location("contrato_para_instantanea", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _redondear_flotantes(texto: str) -> str:
    """Los números impresos con muchos decimales difieren en la última cifra según la versión de numpy: se fijan a 9 cifras."""
    return re.sub(r"-?\d+\.\d{9,}(?:e[+-]?\d+)?", lambda m: f"{float(m.group()):.9g}", texto)


def _repr_estable(valor) -> str:
    """repr independiente de la versión de numpy (np.float64(1.0) en numpy 2, 1.0 en numpy 1)."""
    if isinstance(valor, (list, tuple, np.ndarray)):
        return "[" + ", ".join(_repr_estable(v) for v in valor) + "]"
    if isinstance(valor, np.generic):
        return repr(valor.item())
    return repr(valor)


def _mensaje_de_excepcion(exc: BaseException) -> str:
    """Solo se conserva el mensaje si lo escribió walopy (línea ``raise``); los de Python cambian entre versiones."""
    ultimo = traceback.extract_tb(exc.__traceback__)[-1] if exc.__traceback__ else None
    if ultimo is not None and "walopy" in ultimo.filename and (ultimo.line or "").lstrip().startswith("raise"):
        return f"{type(exc).__name__}: {exc}"
    return f"{type(exc).__name__}: <mensaje de Python>"


def describir(obj, profundidad: int = 0):
    """Representación determinista y completa (números exactos incluidos) de un resultado."""
    if profundidad > 5:
        return f"<{type(obj).__name__}>"
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return f"{float(obj):.9g}"      # 9 cifras significativas: estable entre versiones de numpy/pandas
    if isinstance(obj, pd.DataFrame):
        return {"__df__": True, "columnas": [str(c) for c in obj.columns], "indice": [str(i) for i in obj.index],
                "csv": obj.to_csv(float_format="%.9g")}
    if isinstance(obj, pd.Series):
        return {"__serie__": True, "nombre": str(obj.name), "indice": [str(i) for i in obj.index], "valores": [describir(v, profundidad + 1) for v in obj.tolist()]}
    if isinstance(obj, np.ndarray):
        return [describir(v, profundidad + 1) for v in obj.tolist()]
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {"__clase__": type(obj).__name__, **{f.name: describir(getattr(obj, f.name), profundidad + 1) for f in dataclasses.fields(obj)}}
    if isinstance(obj, dict):
        return {"__dict__": [[describir(k, profundidad + 1), describir(v, profundidad + 1)] for k, v in obj.items()]}
    if isinstance(obj, (list, tuple)):
        return [describir(v, profundidad + 1) for v in obj]
    if callable(obj):
        return f"<callable {getattr(obj, '__name__', type(obj).__name__)}>"
    return f"<{type(obj).__name__}> {obj!s}"[:200]


CLAVES_PLOTLY_CON_TEXTO = {"text", "name", "hovertemplate", "hovertext", "ticktext", "title", "labels", "parents", "ids", "label",
                           "legendgroup", "x", "y"}


def _textos_plotly(valor, ruta: str = "", clave: str = "") -> list:
    """Cadenas de las claves con texto visible (se ignoran plantillas de estilo y colores, que cambian con la versión de plotly)."""
    salida = []
    if isinstance(valor, dict):
        for k, v in valor.items():
            if k == "template":
                continue
            salida += _textos_plotly(v, f"{ruta}.{k}", k)
    elif isinstance(valor, (list, tuple, np.ndarray)):          # plotly 5.0 devuelve ndarray en lugar de lista
        for i, v in enumerate(valor.tolist() if isinstance(valor, np.ndarray) else valor):
            salida += _textos_plotly(v, f"{ruta}[{i}]", clave)
    elif isinstance(valor, str) and clave in CLAVES_PLOTLY_CON_TEXTO:
        salida.append(f"{ruta}={valor}")
    return salida


def textos_de_figura(fig) -> list:
    """Todos los textos visibles de una figura de matplotlib o plotly."""
    if hasattr(fig, "to_dict") and not hasattr(fig, "axes"):
        return _textos_plotly(fig.to_dict())
    if not hasattr(fig, "texts") and hasattr(fig, "figure"):
        fig = fig.figure                # algunas gráficas devuelven un Axes
    textos = [f"suptitle={fig._suptitle.get_text()}" if fig._suptitle else "suptitle="]
    textos += [f"fig.text={t.get_text()}" for t in fig.texts]
    for i, ax in enumerate(fig.axes):
        textos += [f"ax{i}.title={ax.get_title()}", f"ax{i}.xlabel={ax.get_xlabel()}", f"ax{i}.ylabel={ax.get_ylabel()}"]
        textos += [f"ax{i}.text={t.get_text()}" for t in ax.texts]
        leg = ax.get_legend()
        if leg is not None:
            textos += [f"ax{i}.legend={t.get_text()}" for t in leg.get_texts()]
        textos += [f"ax{i}.etiqueta_linea={ln.get_label()}" for ln in ax.get_lines() if not ln.get_label().startswith("_")]
    return textos


def _grafica(resultado):
    import matplotlib.pyplot as plt

    if not hasattr(resultado, "plot") or isinstance(resultado, pd.DataFrame):   # DataFrame.plot es de pandas, no de walopy
        return None
    try:
        fig = resultado.plot()
        textos = textos_de_figura(fig)
    except Exception as e:  # noqa: BLE001
        textos = [f"EXCEPCION {type(e).__name__}: {e}"]
    plt.close("all")
    return textos


NOMBRES_NUEVOS = {"set_language", "get_language", "language"}   # API de 0.4.0: v0.3.0 no la tenía, no hay salida de referencia


def capturar_funciones(contrato) -> dict:
    salida: dict = {}
    for nombre in sorted(set(contrato.BASE) - NOMBRES_NUEVOS):
        fn = getattr(wl, nombre)
        with warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter("always")
            resultado = fn(**copy.deepcopy(contrato.BASE[nombre]))
        entrada: dict = {"resultado": describir(resultado), "avisos": [f"{a.category.__name__}: {a.message}" for a in avisos if a.category is UserWarning]}
        if hasattr(resultado, "__str__") and not isinstance(resultado, (pd.DataFrame, float, int)):
            entrada["str"] = str(resultado)
        for met in ("summary", "to_frame", "curve_to_frame"):
            if hasattr(resultado, met):
                try:
                    entrada[met] = describir(getattr(resultado, met)())
                except Exception as e:  # noqa: BLE001
                    entrada[met] = f"EXCEPCION {type(e).__name__}: {e}"
        entrada["grafica"] = _grafica(resultado)
        salida[nombre] = entrada
    return salida


def capturar_errores(contrato) -> dict:
    salida: dict = {}
    for nombre in sorted(set(contrato.BASE) - NOMBRES_NUEVOS):
        fn = getattr(wl, nombre)
        base = contrato.BASE[nombre]
        params = __import__("inspect").signature(fn).parameters
        longitudes = [len(v) for v in base.values() if isinstance(v, (list, tuple, np.ndarray))]
        for arg, valor in base.items():
            defecto = params[arg].default if arg in params else __import__("inspect").Parameter.empty
            n_par = longitudes.count(len(valor)) if isinstance(valor, (list, tuple, np.ndarray)) else 0
            for malo in contrato._candidatos(arg, valor, defecto, n_par):
                kw = copy.deepcopy(base)
                kw[arg] = malo
                estado, res = contrato._llamar(fn, kw)
                if estado == "exc":
                    salida[f"{nombre}({arg}={_repr_estable(malo)})"] = _mensaje_de_excepcion(res)
                else:
                    salida[f"{nombre}({arg}={_repr_estable(malo)})"] = f"<{estado}>"
    return salida


def capturar_escenarios() -> dict:
    """Avisos y casos especiales que el test de contrato no recorre."""
    salida: dict = {}

    def con_avisos(clave, f):
        with warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter("always")
            try:
                r = f()
                salida[clave] = {"resultado": describir(r), "str": str(r), "avisos": [f"{a.category.__name__}: {a.message}" for a in avisos if a.category is UserWarning]}
            except Exception as e:  # noqa: BLE001
                salida[clave] = {"excepcion": _mensaje_de_excepcion(e), "avisos": [f"{a.category.__name__}: {a.message}" for a in avisos if a.category is UserWarning]}

    con_avisos("mrp_vencidas", lambda: wl.mrp([10, 20], lead_time=5))
    con_avisos("weibull_cota", lambda: wl.weibull_analysis([5, 5, 5, 5.0000001]))
    con_avisos("weibull_constante", lambda: wl.weibull_analysis([5, 5, 5, 5]))
    con_avisos("mm1_inestable", lambda: wl.mm1(5.0, 3.0))
    con_avisos("compare", lambda: wl.compare(wl.mm1(2.0, 3.0), wl.mmc(2.0, 3.0, 2)))
    con_avisos("compare_etiquetas", lambda: wl.compare(wl.mm1(2.0, 3.0), wl.mmc(2.0, 3.0, 2), labels=["a", "b"]))
    con_avisos("sensitivity", lambda: wl.sensitivity(wl.mm1, "lam", np.linspace(0.5, 2.5, 5), mu=3.0))
    con_avisos("sensitivity_gg1", lambda: wl.sensitivity(wl.kingman, "lam", [1.0, 2.0], mu=3.0, ca2=1.0, cs2=1.0))
    escenarios = pd.DataFrame({"lam": [1.0, 6.0, 2.0], "mu": [5.0, 5.0, 5.0]})
    con_avisos("batch_model", lambda: wl.batch_model(wl.mm1, escenarios))
    con_avisos("batch_model_raise", lambda: wl.batch_model(wl.mm1, escenarios, errors="raise"))
    con_avisos("batch_model_errors_invalido", lambda: wl.batch_model(wl.mm1, escenarios, errors="x"))
    con_avisos("solve_servers", lambda: wl.solve_servers("Wq", 0.5, lam=4.0, mu=3.0))
    con_avisos("abc_cero", lambda: wl.abc_analysis([{"name": "a", "demand": 0, "unit_value": 1}, {"name": "b", "demand": 5, "unit_value": 2}]))
    con_avisos("abc_todo_cero", lambda: wl.abc_analysis([{"name": "a", "demand": 0, "unit_value": 1}]))
    con_avisos("abc_sin_nombre", lambda: wl.abc_analysis([{"demand": 3, "unit_value": 1}, {"demand": 5, "unit_value": 2}]))
    con_avisos("cpm_duplicado", lambda: wl.cpm([{"name": "A", "duration": 1, "predecessors": []}, {"name": "A", "duration": 2, "predecessors": []}]))
    con_avisos("cpm_ciclo", lambda: wl.cpm([{"name": "A", "duration": 1, "predecessors": ["B"]}, {"name": "B", "duration": 2, "predecessors": ["A"]}]))
    con_avisos("exchange_vacio", lambda: wl.exchange_curve([], target_orders=5.0))
    con_avisos("exchange_texto", lambda: wl.exchange_curve([{"demand": "1000", "ordering_cost": "50", "holding_cost": "2"}], target_orders=5.0))
    con_avisos("mrp_item_name", lambda: wl.mrp([10.0, 20.0, 30.0], initial_on_hand=5.0, lead_time=1))
    con_avisos("eoq_multi_sin_nombres", lambda: wl.eoq_multi([1000.0, 500.0], [50.0, 30.0], [2.0, 1.0]))
    con_avisos("neh", lambda: wl.neh_flowshop([[3.0, 2.0], [1.0, 4.0], [2.0, 1.0]]))
    con_avisos("johnson", lambda: wl.johnson_flowshop([3.0, 1.0, 2.0], [2.0, 4.0, 1.0]))
    con_avisos("kpi_roi", lambda: wl.roi_kpi_tree(1000.0, 200.0, 3.0, 100.0, 500.0))
    con_avisos("kpi_roi_moneda", lambda: wl.roi_kpi_tree(1000.0, 200.0, 3.0, 100.0, 500.0, currency="USD"))
    return salida


API_NUEVA = re.compile(r"\b(set_language|get_language|language)\(")   # no existía en v0.3.0: sus ejemplos no tienen salida de referencia


def capturar_readme() -> dict:
    salida: dict = {}
    archivos = [RAIZ / "README.md", *sorted((RAIZ / "docs" / "source").glob("*.md"))]
    patron = re.compile(r"```python\n(.*?)```", re.S)
    cwd = Path.cwd()
    for archivo in archivos:
        espacio: dict = {}
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                for i, bloque in enumerate(patron.findall(archivo.read_text(encoding="utf-8")), 1):
                    if API_NUEVA.search(bloque):
                        continue
                    buf = io.StringIO()
                    try:
                        with warnings.catch_warnings(), redirect_stdout(buf):
                            warnings.simplefilter("ignore")
                            exec(compile(bloque, f"{archivo.name}[{i}]", "exec"), espacio)  # noqa: S102
                        salida[f"{archivo.name}[{i}]"] = _redondear_flotantes(buf.getvalue())
                    except Exception as e:  # noqa: BLE001
                        salida[f"{archivo.name}[{i}]"] = f"EXCEPCION {type(e).__name__}: {e}"
            finally:
                os.chdir(cwd)
        import matplotlib.pyplot as plt

        plt.close("all")
    return salida


def capturar_cli() -> dict:
    salida: dict = {}
    llamadas = [["--help"], ["--version"], [], ["mm1", "--help"], ["mmc", "--help"], ["md1", "--help"], ["gg1", "--help"], ["littles", "--help"], ["eoq", "--help"],
                ["mm1", "--lam", "2", "--mu", "3"], ["mmc", "--lam", "8", "--mu", "3", "--c", "4"], ["md1", "--lam", "2", "--mu", "3"],
                ["gg1", "--lam", "2", "--mu", "3", "--ca2", "1", "--cs2", "1"], ["eoq", "--demand", "1000", "--ordering", "50", "--holding", "2"],
                ["littles", "--lam", "2", "--W", "3"], ["littles", "--L", "6", "--lam", "2"], ["littles", "--L", "1"],
                ["mm1", "--lam", "5", "--mu", "3"], ["mm1", "--lam", "nan", "--mu", "3"], ["mmc", "--lam", "1", "--mu", "1", "--c", "0"],
                ["eoq", "--demand", "-1", "--ordering", "50", "--holding", "2"]]
    env = {k: v for k, v in os.environ.items() if k != "COLUMNS"}
    env["COLUMNS"] = "100"
    env["PYTHONPATH"] = str(RAIZ / "src")
    for argv in llamadas:
        r = subprocess.run([sys.executable, "-m", "walopy", *argv], capture_output=True, text=True, env=env, check=False, timeout=60)  # noqa: S603
        norm = lambda t: t.replace("optional arguments:", "options:")  # noqa: E731 - argparse cambió el título en Python 3.10
        salida[" ".join(argv) or "(sin argumentos)"] = {"codigo": r.returncode, "stdout": _redondear_flotantes(norm(r.stdout)), "stderr": norm(r.stderr)}
    return salida


def capturar() -> dict:
    contrato = _cargar_contrato()
    return {
        "version_formato": 1,
        "funciones": capturar_funciones(contrato),
        "errores": capturar_errores(contrato),
        "escenarios": capturar_escenarios(),
        "readme": capturar_readme(),
        "cli": capturar_cli(),
    }


def _aplanar(valor, ruta: str = "") -> dict:
    if isinstance(valor, dict):
        plano = {}
        for k, v in valor.items():
            plano.update(_aplanar(v, f"{ruta}/{k}"))
        return plano
    if isinstance(valor, list):
        plano = {}
        for i, v in enumerate(valor):
            plano.update(_aplanar(v, f"{ruta}[{i}]"))
        return plano
    return {ruta: valor}


def diferencias(esperado: dict, actual: dict, maximo: int = 25) -> list:
    a, b = _aplanar(esperado), _aplanar(actual)
    difs = []
    for k in sorted(set(a) | set(b)):
        if a.get(k, "<ausente>") != b.get(k, "<ausente>"):
            va, vb = a.get(k, "<ausente>"), b.get(k, "<ausente>")
            if isinstance(va, str) and isinstance(vb, str) and "\n" in va + vb:
                detalle = "\n".join(list(difflib.unified_diff(va.splitlines(), vb.splitlines(), "esperado", "actual", lineterm="", n=0))[:6])
            else:
                detalle = f"{va!r} ≠ {vb!r}"
            difs.append(f"{k}: {detalle}")
    return difs[:maximo] if maximo else difs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--escribir", metavar="RUTA")
    g.add_argument("--comprobar", metavar="RUTA")
    ap.add_argument("--idioma", default=None, help="fija WALOPY_LANG para la captura (fase 2)")
    args = ap.parse_args()
    if args.idioma:
        os.environ["WALOPY_LANG"] = args.idioma
    datos = capturar()
    if args.escribir:
        ruta = Path(args.escribir)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        total = sum(len(v) for k, v in datos.items() if isinstance(v, dict))
        print(f"instantánea escrita en {ruta} ({total} entradas, {ruta.stat().st_size // 1024} KiB)")
        return 0
    esperado = json.loads(Path(args.comprobar).read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(datos, ensure_ascii=False, sort_keys=True))
    difs = diferencias(esperado, actual)
    if difs:
        print(f"La salida cambió ({len(difs)} diferencias mostradas):")
        print("\n".join(difs))
        return 1
    print("La salida es idéntica a la instantánea.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
