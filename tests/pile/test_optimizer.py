"""Tests for the pile optimizer."""

import copy
import math

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
    assert res["best_L"] == required
    assert res["best_L"].is_integer()
    assert all(check["status"] in ("OK", "N/A")
               for check in res["best_results"]["checks"].values())


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


def test_the_default_40_mm_settlement_limit_is_an_optimization_constraint():
    cfg = default_config()
    cfg["loading"]["Q"] = 4000.0
    cfg["seismic"]["enabled"] = False
    res = optimize_length(cfg, L_bounds=(4.0, 30.0))
    assert res["success"]
    assert res["best_L"] > 7.0  # the old 6.52 m optimum settled about 74 mm
    assert res["best_results"]["checks"]["settlement"]["allowable"] == 40.0
    assert res["best_results"]["checks"]["settlement"]["actual"] <= 40.0
    assert all(check["status"] in ("OK", "N/A")
               for check in res["best_results"]["checks"].values())


def test_cost_units_do_not_change_geometry_or_feasibility():
    cfg = default_config()
    options = dict(L_bounds=(5.0, 25.0), D_bounds=(0.4, 1.2), popsize=8,
                   maxiter=20, seed=2, polish=False, atol=1e-5, tol=1e-4)
    units = optimize_cost(cfg, cost_a=1.0, cost_b=0.1, **options)
    thousands = optimize_cost(cfg, cost_a=1000.0, cost_b=100.0, **options)
    assert units["success"] and thousands["success"]
    assert units["best_L"] == thousands["best_L"]
    assert units["best_L"].is_integer()
    assert units["best_D"] == pytest.approx(thousands["best_D"], abs=1e-12)
    assert thousands["best_cost"] == pytest.approx(1000.0 * units["best_cost"])
    for result in (units, thousands):
        assert all(check["status"] in ("OK", "N/A")
                   for check in result["best_results"]["checks"].values())
        assert "converged" in result and result["feasible"] is True


@pytest.mark.parametrize("optimizer", [optimize_length, optimize_cost])
def test_soil_optimizers_refuse_to_silently_optimize_a_socket_as_soil(optimizer):
    with pytest.raises(ValueError, match="rock sockets"):
        optimizer(default_config("socket"))


def test_integer_search_stays_inside_noninteger_bounds():
    cfg = default_config()
    res = optimize_length(cfg, L_bounds=(10.22, 11.9))
    assert res["best_L"] == 11.0
    assert math.ceil(10.22) <= res["best_L"] <= math.floor(11.9)
    with pytest.raises(ValueError, match="no whole-metre"):
        optimize_length(cfg, L_bounds=(10.22, 10.99))


def test_optimizer_checks_independent_boreholes_at_the_same_integer_geometry():
    cfg = default_config()
    cfg["loading"]["Q"] = 4000.0
    cfg["seismic"]["enabled"] = False
    softer = copy.deepcopy(cfg["soil_profile"])
    for layer in softer:
        layer["E"] *= 0.5
    cfg["boreholes"] = [{"name": "BH-A", "soil_profile": cfg["soil_profile"]},
                        {"name": "BH-B", "soil_profile": softer}]
    res = optimize_length(cfg, L_bounds=(4.0, 30.0))
    assert res["success"] and res["best_L"].is_integer()
    assert set(res["best_results"]["boreholes"]) == {"BH-A", "BH-B"}
    for result in res["best_results"]["boreholes"].values():
        assert result["L"] == res["best_L"]
        assert all(check["status"] in ("OK", "N/A") for check in result["checks"].values())
    assert res["best_results"]["checks"]["settlement"]["governing_borehole"] == "BH-B"


def test_failure_to_find_a_feasible_length_is_not_reported_as_success():
    cfg = default_config()
    cfg["loading"]["Q"] = 1e8
    res = optimize_length(cfg, L_bounds=(4.0, 10.0))
    assert res["success"] is False and res["feasible"] is False
    assert res["converged"] is True  # exhaustive search finished; engineering checks failed


@pytest.mark.parametrize("check", [
    {"status": "UNKNOWN", "utilisation": 0.5},
    {"utilisation": 0.5},
    {"status": "OK", "utilisation": -0.5},
    {"status": "OK", "utilisation": math.nan},
    {"status": "OK", "utilisation": True},
    {"status": "OK", "utilisation": "0.5"},
    {"status": "OK"},
    {"status": "OK", "utilisation": 0.5, "actual": math.nan},
    {"status": "OK", "utilisation": 0.5, "allowable": math.nan},
])
def test_invalid_result_checks_fail_closed(check):
    from slipsurface.pile.optimizer import governing_utilisation
    assert math.isinf(governing_utilisation({"checks": {"pile": check}}))


def test_empty_checks_cannot_hide_behind_legacy_capacity_values():
    from slipsurface.pile.optimizer import governing_utilisation
    result = {"utilisation": 0.1, "group": {"utilisation": 0.2}, "checks": {}}
    assert math.isinf(governing_utilisation(result))


def test_missing_settlement_numbers_fail_closed_without_a_type_error():
    from slipsurface.pile.optimizer import governing_utilisation
    result = {"checks": {"settlement": {"status": "OK", "actual": None, "allowable": None}}}
    assert math.isinf(governing_utilisation(result))
