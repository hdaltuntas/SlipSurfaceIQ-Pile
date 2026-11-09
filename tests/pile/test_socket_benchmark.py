"""Independent limiting-mechanics checks for elastic socket settlement.

Randolph & Wroth (1978), Analysis of Deformation of Vertically Loaded Piles,
J. Geotechnical Engineering Division 104(12), 1465–1488.
https://doi.org/10.1061/AJGEB6.0000729

This is an analytical rigid-pile limiting benchmark, not a field calibration.
It combines the elastic circular-base spring with radial shaft shear.
"""
import math

import pytest

from slipsurface.pile.socket import randolph_wroth


@pytest.mark.parametrize("with_base", [True, False])
def test_rigid_pile_limit_equals_parallel_base_and_shaft_springs(with_base):
    P, L, r, G, nu = 1000.0, 10.0, 0.5, 10000.0, 0.25
    # Uniform ground: influence radius rm = 2.5(1-nu)L = 18.75 m.
    # A rigid shaft has constant displacement, so its shear spring is
    # 2*pi*G*L/log(rm/r); a rigid circular base has Kb=4*G*r/(1-nu).
    shaft_K = 2.0 * math.pi * G * L / math.log(18.75 / 0.5)
    base_K = 4.0 * G * r / (1.0 - nu) if with_base else 0.0
    expected_K = shaft_K + base_K
    result = randolph_wroth(P, L, r, G, G, nu, Ep=1e16, with_base=with_base)
    assert result["K"] == pytest.approx(expected_K, rel=1e-8)
    assert result["w"] == pytest.approx(P / expected_K, rel=1e-8)
    assert result["base_share"] == pytest.approx(base_K / expected_K, abs=1e-8)


def test_slender_stiff_ground_case_has_finite_settlement_and_vanishing_base_share():
    # A slender shaft in very stiff ground has mu*L > 710. Hyperbolic-cosine
    # overflow must not prevent evaluating a valid positive-stiffness model.
    result = randolph_wroth(P=1000.0, L=60.0, r0=0.05, G=80e6,
                            Gb=80e6, nu=0.25, Ep=30e6, with_base=True)
    assert result["mu_L"] > 710.0
    assert math.isfinite(result["w"]) and result["w"] > 0
    assert math.isfinite(result["K"]) and result["K"] > 0
    assert result["base_share"] == 0.0
