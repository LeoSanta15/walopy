"""Complejidad real de los algoritmos (N-03): equivalencia con referencias independientes y tiempos acotados."""
from __future__ import annotations

import itertools
import math
import random
import time

import pytest

import walopy as wl


def _cmax(seq, T):
    """Makespan de una permutación (recursión estándar del flow-shop)."""
    m = len(T[0])
    C = [0.0] * m
    for j in seq:
        for k in range(m):
            C[k] = max(C[k], C[k - 1] if k else 0.0) + T[j][k]
    return C[-1]


def _neh_referencia(T):
    """NEH sin aceleración: recalcula el makespan completo por cada posición (O(n³m))."""
    n = len(T)
    orden = sorted(range(n), key=lambda i: -sum(T[i]))
    seq = [orden[0]]
    for job in orden[1:]:
        mejor, pos_mejor = math.inf, 0
        for pos in range(len(seq) + 1):
            c = _cmax(seq[:pos] + [job] + seq[pos:], T)
            if c < mejor:
                mejor, pos_mejor = c, pos
        seq = seq[:pos_mejor] + [job] + seq[pos_mejor:]
    return seq, _cmax(seq, T)


@pytest.mark.parametrize("semilla", range(150))
def test_neh_acelerado_coincide_con_la_version_directa(semilla):
    r = random.Random(semilla)
    n, m = r.randint(1, 12), r.randint(1, 6)
    entero = semilla % 2 == 0
    T = [[float(r.randint(1, 30)) if entero else r.uniform(0.5, 30.0) for _ in range(m)] for _ in range(n)]
    res = wl.neh_flowshop(T, names=[str(i) for i in range(n)])
    seq_ref, cmax_ref = _neh_referencia(T)
    secuencia = [int(x) for x in res.sequence]
    assert sorted(secuencia) == list(range(n))
    assert res.makespan == pytest.approx(_cmax(secuencia, T), rel=1e-12)
    if entero:
        # Con datos enteros los empates son exactos: debe darse la misma permutación y makespan.
        assert secuencia == seq_ref
        assert res.makespan == pytest.approx(cmax_ref, rel=1e-12)
    else:
        # Con decimales un empate exacto puede resolverse distinto por redondeo y la heurística
        # diverge: se exige la misma calidad (diferencia pequeña), no la misma permutación.
        assert abs(res.makespan - cmax_ref) <= 0.1 * cmax_ref


def test_neh_no_se_aleja_del_optimo_en_casos_pequenos():
    huecos = []
    for semilla in range(40):
        r = random.Random(1000 + semilla)
        n, m = r.randint(3, 7), r.randint(2, 5)
        T = [[float(r.randint(1, 20)) for _ in range(m)] for _ in range(n)]
        optimo = min(_cmax(p, T) for p in itertools.permutations(range(n)))
        huecos.append((wl.neh_flowshop(T).makespan - optimo) / optimo)
    assert min(huecos) >= -1e-12 and max(huecos) < 0.15  # NEH es heurística: cota empírica conocida


def test_neh_n200_m10_es_rapido():
    r = random.Random(0)
    T = [[float(r.randint(1, 50)) for _ in range(10)] for _ in range(200)]
    t0 = time.perf_counter()
    wl.neh_flowshop(T)
    assert time.perf_counter() - t0 < 2.0  # antes 5,3 s (O(n³m))


def _ww_fuerza_bruta(d, S, h):
    """Óptimo por enumeración, independiente de la programación dinámica.

    Un pedido solo se coloca en un periodo con demanda positiva (no hay nada que cubrir en uno nulo) y el primero
    de ellos debe tener pedido. Un horizonte sin demanda cuesta 0.
    """
    positivos = [t for t, x in enumerate(d) if x > 0]
    if not positivos:
        return 0.0
    n = len(d)
    mejor = math.inf
    for mascara in range(1 << (len(positivos) - 1)):
        inicios = [positivos[0]] + [positivos[i + 1] for i in range(len(positivos) - 1) if mascara >> i & 1]
        costo = 0.0
        for si, a in enumerate(inicios):
            fin = inicios[si + 1] if si + 1 < len(inicios) else n
            costo += S + sum(h * d[j] * (j - a) for j in range(a, fin))
        mejor = min(mejor, costo)
    return mejor


@pytest.mark.parametrize("semilla", range(100))
def test_wagner_whitin_coincide_con_fuerza_bruta(semilla):
    r = random.Random(semilla)
    n = r.randint(2, 9)
    d = [r.choice([0, 0, r.randint(1, 40)]) for _ in range(n)]  # ceros en cualquier posición (W-27)
    S, h = r.randint(10, 100), r.choice([0.5, 1, 2])
    assert wl.wagner_whitin(d, S, h).total_cost == pytest.approx(_ww_fuerza_bruta(d, S, h), abs=1e-9)


def test_wagner_whitin_n1000_es_rapido():
    r = random.Random(0)
    d = [r.randint(1, 50) for _ in range(1000)]
    t0 = time.perf_counter()
    wl.wagner_whitin(d, 100, 1)
    assert time.perf_counter() - t0 < 2.0  # antes 10,2 s (O(n³))
