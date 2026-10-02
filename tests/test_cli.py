"""Pruebas del CLI (`python -m walopy`)."""
from __future__ import annotations

import subprocess
import sys

import pytest

import walopy
from walopy.__main__ import main


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0
    assert walopy.__version__ in capsys.readouterr().out


def test_sin_argumentos_muestra_ayuda(capsys):
    with pytest.raises(SystemExit) as e:
        main([])
    assert e.value.code == 0
    assert "mm1" in capsys.readouterr().out


@pytest.mark.parametrize("argv,esperado", [
    (["mm1", "--lam", "2", "--mu", "3"], "M/M/1"),
    (["mmc", "--lam", "8", "--mu", "3", "--c", "4"], "M/M/4"),
    (["md1", "--lam", "2", "--mu", "3"], "M/D/1"),
    (["gg1", "--lam", "2", "--mu", "3", "--ca2", "1", "--cs2", "1"], "G/G/1"),
    (["eoq", "--demand", "1000", "--ordering", "50", "--holding", "2"], "223.6"),
])
def test_modelos_imprimen_resultado(argv, esperado, capsys):
    main(argv)
    assert esperado in capsys.readouterr().out


@pytest.mark.parametrize("argv,esperado", [
    (["littles", "--lam", "2", "--W", "3"], "L = 6"),
    (["littles", "--L", "6", "--W", "3"], "lam = 2"),
    (["littles", "--L", "6", "--lam", "2"], "W = 3"),
])
def test_ley_de_little_resuelve_la_variable_faltante(argv, esperado, capsys):
    main(argv)
    assert esperado in capsys.readouterr().out


@pytest.mark.parametrize("argv", [
    ["mm1", "--lam", "5", "--mu", "3"],            # sistema inestable
    ["mm1", "--lam", "nan", "--mu", "3"],          # NaN
    ["mmc", "--lam", "1", "--mu", "1", "--c", "0"],
    ["eoq", "--demand", "-1", "--ordering", "50", "--holding", "2"],
])
def test_entradas_invalidas_salen_con_codigo_1(argv, capsys):
    with pytest.raises(SystemExit) as e:
        main(argv)
    assert e.value.code == 1
    assert capsys.readouterr().err.startswith("Error")


def test_ejecucion_como_modulo():
    r = subprocess.run(
        [sys.executable, "-m", "walopy", "mm1", "--lam", "2", "--mu", "3"],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert r.returncode == 0 and "M/M/1" in r.stdout
