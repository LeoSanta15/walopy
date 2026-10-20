"""Avisos de validez (0.4.4): el modelo se usa fuera del rango en que su resultado es fiable.

* ``newsvendor`` con demanda normal y CV > 0,5: la normal asigna probabilidad apreciable a demanda negativa.
* ``monte_carlo_gg1``: el semiancho al 95 % de Wq (medias de 20 lotes) supera el 10 %; una réplica puede engañar.
* ``pert``: ver ``test_pert_varianza.py``.
"""
from __future__ import annotations

import warnings

import pytest

import walopy as wl


def test_newsvendor_avisa_con_cv_alto():
    with pytest.warns(UserWarning) as avisos:
        wl.newsvendor(20.0, 20.0, 10.0, 4.0)
    assert "15.9%" in str(avisos[0].message) or "15,9" in str(avisos[0].message)  # P(D < 0) del modelo


def test_newsvendor_no_avisa_con_cv_moderado():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        wl.newsvendor(100.0, 30.0, 10.0, 4.0)
        wl.newsvendor(100.0, 50.0, 10.0, 4.0)  # CV = 0,5 justo en el límite


def test_simulacion_avisa_si_la_estimacion_es_imprecisa():
    with pytest.warns(UserWarning) as avisos:
        wl.monte_carlo_gg1(0.95, 1.0, 1.0, 1.0, n_customers=20_000, seed=1)
    assert "n_customers" in str(avisos[0].message)


def test_simulacion_no_avisa_si_la_estimacion_es_precisa():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        wl.monte_carlo_gg1(2.0, 3.0, 1.0, 1.0, n_customers=50_000, seed=1)


def test_el_aviso_no_cambia_el_resultado():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        a = wl.monte_carlo_gg1(0.95, 1.0, 1.0, 1.0, n_customers=5_000, seed=3)
        b = wl.newsvendor(20.0, 20.0, 10.0, 4.0)
    assert a.Wq_mean > 0 and b.optimal_qty > 0
