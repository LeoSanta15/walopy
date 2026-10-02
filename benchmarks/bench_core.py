"""Benchmarks reproducibles de las operaciones críticas de walopy (semillas fijas).

Uso:  python benchmarks/bench_core.py            # tabla en texto
      python benchmarks/bench_core.py --markdown # tabla en Markdown (para docs/source/rendimiento.md)
"""
from __future__ import annotations

import argparse
import platform
import random
import statistics
import time
from functools import partial

import walopy as wl


def _entrada_neh(n: int, m: int):
    r = random.Random(0)
    return [[float(r.randint(1, 50)) for _ in range(m)] for _ in range(n)]


def _demandas(n: int):
    r = random.Random(0)
    return [r.randint(1, 50) for _ in range(n)]


def _actividades(n: int):
    r = random.Random(0)
    return [
        {"name": f"T{i}", "duration": r.randint(1, 9),
         "predecessors": [f"T{j}" for j in range(max(0, i - 4), i) if r.random() < 0.5]}
        for i in range(n)
    ]


def _tiempos_falla(n: int):
    r = random.Random(0)
    return [r.weibullvariate(100, 1.5) for _ in range(n)]


def _items(n: int):
    r = random.Random(0)
    return [{"name": f"i{i}", "demand": r.randint(10, 1000), "unit_value": r.random() * 10 + 1,
             "cv": r.random()} for i in range(n)]


CASOS = [
    ("neh_flowshop n=100, m=10", partial(wl.neh_flowshop, _entrada_neh(100, 10))),
    ("neh_flowshop n=200, m=10", partial(wl.neh_flowshop, _entrada_neh(200, 10))),
    ("wagner_whitin n=1000", partial(wl.wagner_whitin, _demandas(1000), 100, 1)),
    ("wagner_whitin n=2000", partial(wl.wagner_whitin, _demandas(2000), 100, 1)),
    ("mmc c=1000 (ρ=0.95)", partial(wl.mmc, 950.0, 1.0, 1000)),
    ("monte_carlo_gg1 n=1e6", partial(wl.monte_carlo_gg1, 2.0, 3.0, 1.0, 1.0, n_customers=10**6, seed=1)),
    ("abc_xyz n=2000", partial(wl.abc_xyz, _items(2000))),
    ("cpm n=1000", partial(wl.cpm, _actividades(1000))),
    ("weibull_analysis n=5000 (MLE)", partial(wl.weibull_analysis, _tiempos_falla(5000))),
]


def medir(fn, repeticiones: int = 3) -> float:
    tiempos = []
    for _ in range(repeticiones):
        t0 = time.perf_counter()
        fn()
        tiempos.append(time.perf_counter() - t0)
    return statistics.median(tiempos)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()
    filas = [(nombre, medir(fn)) for nombre, fn in CASOS]
    entorno = f"Python {platform.python_version()}, {platform.machine()}, walopy {wl.__version__}"
    if args.markdown:
        print("| Operación | Mediana de 3 ejecuciones (s) |\n|---|---|")
        for nombre, t in filas:
            print(f"| {nombre} | {t:.3f} |")
        print(f"\nEntorno de referencia: {entorno}.")
    else:
        print(entorno)
        for nombre, t in filas:
            print(f"{nombre:36s} {t:8.3f} s")


if __name__ == "__main__":
    main()
