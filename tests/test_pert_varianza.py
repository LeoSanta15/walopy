"""W-34: con varias rutas críticas empatadas, ``pert`` sumaba las varianzas de **todas** las actividades críticas.

La varianza del proyecto en PERT es la de una ruta (la convención, con empates, es la de mayor varianza). Con 5 rutas
idénticas de 3 actividades, σ salía 3,23 en lugar de 1,44 (√5 veces mayor). Además ``pert`` avisa cuando hay rutas casi
críticas, porque entonces la probabilidad PERT (una sola ruta) es optimista.
"""
from __future__ import annotations

import warnings

import pytest

import walopy as wl


def _rutas_paralelas(n_rutas: int = 5) -> list[dict]:
    acts = []
    for p in range(n_rutas):
        previa: list[str] = []
        for j in range(3):
            nombre = f"P{p}A{j}"
            acts.append({"name": nombre, "optimistic": 4, "most_likely": 5, "pessimistic": 9, "predecessors": previa})
            previa = [nombre]
    acts.append({"name": "FIN", "optimistic": 1, "most_likely": 1, "pessimistic": 1, "predecessors": [f"P{p}A2" for p in range(n_rutas)]})
    return acts


def _pert(acts):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return wl.pert(acts)


def test_rutas_empatadas_usan_la_varianza_de_una_ruta():
    r = _pert(_rutas_paralelas())
    assert r.project_variance == pytest.approx(3 * (5 / 6) ** 2)  # antes 15 · (5/6)² = 10,42
    assert len(r.critical_path) == 16  # el conjunto de actividades críticas no cambia


def test_con_empate_se_elige_la_ruta_de_mayor_varianza():
    acts = [
        {"name": "A", "optimistic": 2, "most_likely": 5, "pessimistic": 8, "predecessors": []},   # var 1
        {"name": "B", "optimistic": 4, "most_likely": 5, "pessimistic": 6, "predecessors": []},   # var 1/9
        {"name": "C", "optimistic": 1, "most_likely": 1, "pessimistic": 1, "predecessors": ["A", "B"]},
    ]
    assert _pert(acts).project_variance == pytest.approx(1.0)  # antes 1 + 1/9


def test_una_sola_ruta_critica_no_cambia():
    # Guarda: sin empates la varianza es la de la ruta crítica, como siempre
    acts = [
        {"name": "A", "optimistic": 2, "most_likely": 4, "pessimistic": 6, "predecessors": []},
        {"name": "B", "optimistic": 1, "most_likely": 1, "pessimistic": 1, "predecessors": []},
        {"name": "C", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": ["A", "B"]},
    ]
    r = wl.pert(acts)
    assert r.project_variance == pytest.approx((4 / 6) ** 2 + (2 / 6) ** 2)


def test_avisa_si_hay_rutas_casi_criticas():
    with pytest.warns(UserWarning) as avisos:
        wl.pert(_rutas_paralelas())
    assert "P1A0" in str(avisos[0].message)


def test_no_avisa_si_las_demas_rutas_tienen_holgura_amplia():
    acts = [
        {"name": "Larga", "optimistic": 20, "most_likely": 22, "pessimistic": 24, "predecessors": []},
        {"name": "Corta", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": []},
        {"name": "Fin", "optimistic": 1, "most_likely": 1, "pessimistic": 1, "predecessors": ["Larga", "Corta"]},
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        wl.pert(acts)
