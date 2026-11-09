"""Tests for the pile optimizer."""

import pytest

from slipsurface.pile.project import default_config
from slipsurface.pile.optimizer import optimize_length, optimize_cost


def test_optimize_length_finds_safe():
    cfg = default_config()
    res = optimize_length(cfg, L_bounds=(4.0, 30.0), popsize=6, maxiter=12, seed=1)
    assert res["success"] is True
    assert 4.0 <= res["best_L"] <= 30.0
    assert res["nfev"] > 0


def test_optimize_cost_runs():
    cfg = default_config()
    res = optimize_cost(cfg, L_bounds=(5.0, 25.0), D_bounds=(0.4, 1.2),
                        popsize=5, maxiter=10, seed=2)
    assert "best_L" in res and "best_D" in res
    assert res["nfev"] > 0


def test_the_optimizer_uses_the_engines_checks():
    # The seismic compression check counts, as it does for the required length
    from slipsurface.pile.optimizer import governing_utilisation
    res = {"utilisation": 0.5, "group": {"utilisation": 0.6}, "seismic": {"utilisation": 1.4}}
    assert governing_utilisation(res) == 1.4
    assert governing_utilisation({"utilisation": 0.5, "group": {"utilisation": 0.6},
                                  "seismic": None}) == 0.6


def test_the_optimizer_agrees_with_the_required_length():
    from slipsurface.pile.engine import analyse
    cfg = default_config()
    required = analyse(cfg).results["required_length"]
    res = optimize_length(cfg, L_bounds=(4.0, 30.0), popsize=8, maxiter=20, seed=1)
    step = cfg["criteria"]["L_step"]
    assert abs(res["best_L"] - required) <= step


def test_the_optimizer_can_be_cancelled():
    from slipsurface.pile.optimizer import Cancelled
    with pytest.raises(Cancelled):
        optimize_length(default_config(), popsize=5, maxiter=10,
                        is_cancelled=lambda: True)


def test_the_cost_optimizer_reports_progress_and_can_be_cancelled():
    from slipsurface.pile.optimizer import Cancelled, optimize_cost
    with pytest.raises(Cancelled):
        optimize_cost(default_config(), popsize=5, maxiter=10,
                      is_cancelled=lambda: True)
    seen = []
    res = optimize_cost(default_config(), popsize=5, maxiter=4, polish=False,
                        progress=lambda done, total: seen.append((done, total)))
    assert seen and all(total == 4 for _, total in seen)
    assert res["best_cost"] > 0
