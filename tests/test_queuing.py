"""Tests for queuing models."""
from __future__ import annotations

import math
import pytest
import numpy as np

from walopy import littles_law, mm1, mmc, md1, kingman


def test_littles_law_L():
    assert littles_law(lam=5.0, W=0.4) == pytest.approx(2.0)


def test_littles_law_lam():
    assert littles_law(L=2.0, W=0.4) == pytest.approx(5.0)


def test_littles_law_W():
    assert littles_law(L=2.0, lam=5.0) == pytest.approx(0.4)


def test_littles_law_requires_exactly_one_none():
    with pytest.raises(ValueError):
        littles_law(L=2.0, lam=5.0, W=0.4)
    with pytest.raises(ValueError):
        littles_law()


def test_mm1_basic():
    r = mm1(lam=3.0, mu=5.0)
    assert r.rho == pytest.approx(0.6)
    assert r.L   == pytest.approx(0.6 / 0.4)
    assert r.Lq  == pytest.approx(0.6**2 / 0.4)
    assert r.W   == pytest.approx(r.L / 3.0)
    assert r.Wq  == pytest.approx(r.Lq / 3.0)


def test_mm1_unstable():
    with pytest.raises(ValueError, match="unstable"):
        mm1(lam=5.0, mu=4.0)


def test_mmc_equals_mm1_with_c1():
    r1 = mm1(lam=3.0, mu=5.0)
    rc = mmc(lam=3.0, mu=5.0, c=1)
    assert r1.Wq == pytest.approx(rc.Wq, rel=1e-5)


def test_mmc_c2():
    r = mmc(lam=6.0, mu=5.0, c=2)
    assert r.rho == pytest.approx(0.6)
    assert r.Wq >= 0


def test_md1_half_of_mm1():
    r_mm1 = mm1(lam=3.0, mu=5.0)
    r_md1 = md1(lam=3.0, mu=5.0)
    assert r_md1.Lq == pytest.approx(r_mm1.Lq / 2, rel=1e-5)


def test_kingman_reduces_to_mm1_for_exponential():
    r_mm1    = mm1(lam=3.0, mu=5.0)
    r_gg1    = kingman(lam=3.0, mu=5.0, ca2=1.0, cs2=1.0)
    assert r_gg1.Wq == pytest.approx(r_mm1.Wq, rel=1e-5)


def test_kingman_deterministic_service():
    r = kingman(lam=3.0, mu=5.0, ca2=1.0, cs2=0.0)
    r_md1 = md1(lam=3.0, mu=5.0)
    assert r.Wq == pytest.approx(r_md1.Wq, rel=1e-4)
