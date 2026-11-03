"""Unit shaft friction and base resistance against their expressions, by hand."""
import math

import pytest

from slipsurface.pile import axial
from slipsurface.pile.config import PA


def test_meyerhof_nq_reads_the_table_and_interpolates_between_rows():
    assert axial.meyerhof_nq(30.0) == pytest.approx(56.7)
    assert axial.meyerhof_nq(36.0) == pytest.approx(168.0)
    between = axial.meyerhof_nq(30.5)
    assert 56.7 < between < 68.2
    assert axial.meyerhof_nq(0.0) == pytest.approx(1.0)
    assert axial.meyerhof_nq(60.0) == pytest.approx(930.0)      # held at the last row


def test_the_api_alpha_changes_branch_at_psi_one():
    assert axial.alpha_api(50.0, 100.0) == pytest.approx(0.5 * 0.5 ** -0.5)
    assert axial.alpha_api(200.0, 100.0) == pytest.approx(0.5 * 2.0 ** -0.25)
    assert axial.alpha_api(10.0, 200.0) == 1.0                  # capped
    assert axial.alpha_api(0.0, 100.0) == 0.0


def test_kulhawy_and_sladen_alpha():
    assert axial.alpha_kulhawy(100.0) == pytest.approx(0.21 + 0.26 * PA / 100.0)
    assert axial.alpha_kulhawy(20.0) == 1.0
    assert axial.alpha_sladen(100.0, 150.0, 0.4) == pytest.approx(0.4 * 1.5 ** 0.45)


def test_the_beta_of_a_clay():
    phi = math.radians(25.0)
    expected = (1 - math.sin(phi)) * math.tan(phi) * math.sqrt(4.0)
    assert axial.beta_clay(25.0, 4.0) == pytest.approx(expected)


def test_lambda_follows_the_penetration():
    assert axial.lambda_factor(0.0) == pytest.approx(0.5)
    assert axial.lambda_factor(20.0) == pytest.approx(0.173)
    assert axial.lambda_factor(12.5) == pytest.approx(0.5 * (0.245 + 0.200))
    assert axial.lambda_factor(200.0) == pytest.approx(0.110)


def test_sand_shaft_friction_is_k_sigma_tan_delta():
    got = axial.fs_granular(100.0, 30.0, 0.5, 22.5)
    assert got == pytest.approx(0.5 * 100.0 * math.tan(math.radians(22.5)))


def test_meyerhof_base_is_limited():
    shallow = axial.tip_meyerhof(20.0, 30.0)
    assert shallow["qb"] == pytest.approx(20.0 * 56.7) and not shallow["limited"]
    deep = axial.tip_meyerhof(500.0, 30.0)
    assert deep["limited"]
    assert deep["qb"] == pytest.approx(0.5 * PA * 56.7 * math.tan(math.radians(30.0)))


def test_vesic_nq_without_rigidity_and_the_reduced_index():
    phi = 30.0
    p = math.radians(phi)
    base = 3 / (3 - math.sin(p)) * math.exp((math.pi / 2 - p) * math.tan(p)) * \
        math.tan(math.pi / 4 + p / 2) ** 2
    assert axial.vesic_nq(phi, 1.0) == pytest.approx(base)
    got = axial.tip_vesic(100.0, 35.0, 50.0, 0.3)
    Ir = 50_000.0 / (2 * 1.3 * 100.0 * math.tan(math.radians(35.0)))
    delta = 0.005 * (1 - 10.0 / 20.0) * 100.0 / PA
    assert got["Ir"] == pytest.approx(Ir)
    assert got["Irr"] == pytest.approx(Ir / (1 + Ir * delta))
    assert got["qb"] == pytest.approx(100.0 * got["Nq"])


def test_janbu_nq_and_its_undrained_limit():
    t = math.tan(math.radians(30.0))
    expected = (t + math.sqrt(1 + t * t)) ** 2 * math.exp(2 * math.radians(90.0) * t)
    assert axial.janbu_nq(30.0, 90.0) == pytest.approx(expected)
    # φ → 0: Nc* = (Nq* − 1)·cot φ tends to 2 + 2η'
    small = 1e-4
    nc = (axial.janbu_nq(small, 90.0) - 1) / math.tan(math.radians(small))
    assert nc == pytest.approx(2 + math.pi, rel=1e-3)
    assert axial.tip_clay("janbu", 50.0, 20.0, 90.0)["Nc"] == pytest.approx(2 + math.pi)


def test_clay_base_by_method():
    assert axial.tip_clay("meyerhof", 80.0, 20.0, 90.0)["qb"] == pytest.approx(720.0)
    vesic = axial.tip_clay("vesic", 80.0, 24.0, 90.0)
    Ir = 24_000.0 / (3 * 80.0)
    assert vesic["Nc"] == pytest.approx(4 / 3 * (math.log(Ir) + 1) + math.pi / 2 + 1)


def test_spt_rules():
    assert axial.fs_spt(20.0, "driven_high") == pytest.approx(0.02 * PA * 20)
    assert axial.fs_spt(20.0, "bored") == pytest.approx(0.01 * PA * 20)
    got = axial.tip_spt(30.0, 2.0, 0.5)
    assert got["qb"] == pytest.approx(0.4 * PA * 30 * 4.0)
    assert axial.tip_spt(30.0, 50.0, 0.5)["qb"] == pytest.approx(4 * PA * 30)
