"""Tests for the pile optimizer."""

import pytest

from slipsurface.pile.forms import defaults, to_config
from slipsurface.pile.optimizer import optimize_length, optimize_cost


def test_optimize_length_finds_safe():
    cfg = to_config(defaults())
    res = optimize_length(cfg, L_bounds=(4.0, 30.0), popsize=6, maxiter=12, seed=1)
    assert res["success"] is True
    assert 4.0 <= res["best_L"] <= 30.0
    assert res["nfev"] > 0


def test_optimize_cost_runs():
    cfg = to_config(defaults())
    res = optimize_cost(cfg, L_bounds=(5.0, 25.0), D_bounds=(0.4, 1.2),
                        popsize=5, maxiter=10, seed=2)
    assert "best_L" in res and "best_D" in res
    assert res["nfev"] > 0
