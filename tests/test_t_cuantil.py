"""Cuantil de la t de Student (0.4.10): inversión numérica con la beta incompleta, sin depender de scipy en ejecución.

Las constantes son de scipy.stats.t.ppf (scipy 1.17).
"""
import math

import pytest

from walopy._utils import t_cuantil, t_cuantil_975

# (p, gl, scipy.stats.t.ppf(p, gl))
REFERENCIA = [
    (0.95, 6, 1.9431802805153042),
    (0.995, 10, 3.16927267261695),
    (0.9, 3, 1.637744353696209),
    (0.975, 1, 12.706204736174694),     # Cauchy: tan(π(p − ½))
    (0.975, 2, 4.302652729749462),
    (0.6, 5, 0.2671808657041451),
    (0.975, 6, 2.4469118511449786),
    (0.975, 40, 2.021075390306273),
    (0.9995, 7, 5.407882520861828),
    (0.975, 500, 1.9647198374673676),
    (0.975, 1e5, 1.9599877075346095),
]


@pytest.mark.parametrize("p,gl,esperado", REFERENCIA)
def test_coincide_con_scipy(p, gl, esperado):
    assert t_cuantil(p, gl) == pytest.approx(esperado, rel=1e-9)


def test_simetria_y_mediana():
    assert t_cuantil(0.5, 7) == 0.0
    assert t_cuantil(0.025, 6) == pytest.approx(-t_cuantil(0.975, 6), rel=1e-12)


def test_cauchy_tiene_forma_cerrada():
    for p in (0.55, 0.8, 0.975, 0.999):
        assert t_cuantil(p, 1) == pytest.approx(math.tan(math.pi * (p - 0.5)), rel=1e-9)


def test_grados_de_libertad_no_enteros_son_monotonos():
    v = [t_cuantil(0.975, g) for g in (1.5, 2.5, 3.5, 10.5, 100.5)]
    assert v == sorted(v, reverse=True)


def test_acerca_a_la_tabla_de_t_cuantil_975():
    """La tabla de 4 decimales de ``t_cuantil_975`` y la inversión exacta coinciden salvo el redondeo."""
    for g in range(1, 200):
        assert t_cuantil(0.975, g) == pytest.approx(t_cuantil_975(g), abs=6e-5)


def test_tiende_a_la_normal():
    assert t_cuantil(0.975, 1e7) == pytest.approx(1.959963984540054, rel=1e-6)


@pytest.mark.parametrize("p", [0.0, 1.0, -0.1, 1.5, float("nan")])
def test_p_invalido(p):
    with pytest.raises(ValueError):
        t_cuantil(p, 5)


@pytest.mark.parametrize("gl", [0.0, -1.0, float("nan")])
def test_gl_invalido(gl):
    with pytest.raises(ValueError):
        t_cuantil(0.975, gl)
