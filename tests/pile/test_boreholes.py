"""End-to-end checks of separate log analyses and one conservative design."""

import copy
import math

import pytest

from slipsurface import pile
from slipsurface.pile.analysis import envelope_checks


def config():
    cfg = pile.default_config()
    cfg["pile"].update(D=0.8, L=15, top=0)
    cfg["group"].update(nx=1, ny=1)
    cfg["loading"]["Q"] = 300
    cfg["seismic"]["enabled"] = False
    layer = {**cfg["soil_profile"][0], "name": "Sand", "thickness": 40,
             "phi": 25, "E": 150}
    cfg["boreholes"] = [
        {"name": "BH-capacity", "soil_profile": [layer], "groundwater": {"depth": 2}},
        {"name": "BH-settlement", "soil_profile": [{**layer, "phi": 40, "E": 5}],
         "groundwater": {"depth": None}},
    ]
    return cfg


def test_checks_retain_different_governing_logs_and_actual_values():
    cfg = config()
    result = pile.analyse(cfg, with_length=False)
    assert isinstance(result, pile.BoreholeAnalysis)
    assert result.results["checks"]["pile"]["governing_borehole"] == "BH-capacity"
    assert result.results["checks"]["settlement"]["governing_borehole"] == "BH-settlement"
    for key, check in result.results["checks"].items():
        candidates = [a.results["checks"][key] for a in result.analyses.values()]
        assert check["utilisation"] == max(c["utilisation"] for c in candidates)
        original = result.analyses[check["governing_borehole"]].results["checks"][key]
        assert check["actual"] == original["actual"]
        assert check["allowable"] == original["allowable"]
    assert math.isinf(result.analyses["BH-settlement"].profile.zw)
    assert result.analyses["BH-capacity"].profile.zw == 2


def test_a_log_failing_one_check_makes_the_envelope_fail():
    result = pile.analyse(config(), with_length=False)
    assert result.results["checks"]["settlement"]["status"] == "NOT OK"
    assert result.results["status"] == "NOT OK"


def test_reversing_log_order_does_not_change_controlling_checks_or_length():
    cfg = config()
    a = pile.analyse(cfg)
    cfg["boreholes"].reverse()
    b = pile.analyse(cfg)
    assert a.results["checks"] == b.results["checks"]
    assert a.results["required_length"] == b.results["required_length"]
    assert a.results["design_governing_borehole"] == b.results["design_governing_borehole"]


def test_recommended_length_is_integer_and_rechecked_in_every_log():
    cfg = config()
    result = pile.analyse(cfg)
    length = result.results["required_length"]
    assert math.isfinite(length) and length.is_integer()
    cfg["pile"]["L"] = length
    repeated = pile.analyse(cfg, with_length=False)
    assert repeated.results["status"] == "OK"
    assert all(c["status"] in ("OK", "N/A") for a in repeated.analyses.values()
               for c in a.results["checks"].values())
    if length > math.ceil(cfg["criteria"]["L_min"]):
        cfg["pile"]["L"] = length - 1
        assert pile.analyse(cfg, with_length=False).results["status"] == "NOT OK"


def test_shortest_log_bounds_the_shared_search_and_is_never_ignored():
    cfg = config()
    cfg["pile"]["L"] = 8
    cfg["boreholes"][1]["soil_profile"][0]["thickness"] = 10.9
    result = pile.analyse(cfg)
    assert math.isnan(result.results["required_length"])
    assert max(row["L"] for row in result.results["length_curve"]) == 10
    cfg["pile"]["L"] = 11
    with pytest.raises(pile.PileError, match="BH-settlement"):
        pile.analyse(cfg)


def test_spt_logs_flow_to_independent_analysis_and_are_not_mutated():
    holes = [
        {"name": "BH-1", "water_depth": 3,
         "records": [{"depth": 3, "N": 10, "uscs": "SP"},
                     {"depth": 20, "N": 30, "uscs": "SP"}]},
        {"name": "BH-2", "water_depth": 1,
         "records": [{"depth": 3, "N": 10, "uscs": "CL", "cu": 20},
                     {"depth": 20, "N": 20, "uscs": "CL", "cu": 80}]},
    ]
    original = copy.deepcopy(holes)
    investigation = pile.derive_profile(holes)
    cfg = investigation.apply(pile.default_config())
    result = pile.analyse(cfg, with_length=False)
    assert set(result.analyses) == {"BH-1", "BH-2"}
    assert result.analyses["BH-1"].profile.layers[0]["behaviour"] == "granular"
    assert result.analyses["BH-2"].profile.layers[0]["behaviour"] == "cohesive"
    assert holes == original


def test_duplicate_empty_and_geometry_overriding_logs_are_refused():
    for change in ("duplicate", "empty", "geometry"):
        cfg = config()
        if change == "duplicate":
            cfg["boreholes"][1]["name"] = cfg["boreholes"][0]["name"]
        elif change == "empty":
            cfg["boreholes"] = []
        else:
            cfg["boreholes"][0]["socket"] = {"D": 2}
        with pytest.raises(ValueError):
            pile.analyse(cfg)


@pytest.mark.parametrize("invalid_status", ["OK", "NOT OK"])
def test_invalid_check_cannot_make_an_envelope_safe(invalid_status):
    checks = envelope_checks({
        "A": {"checks": {"pile": {"actual": 1, "allowable": 1,
                                   "status": "OK", "utilisation": 0.5}}},
        "B": {"checks": {"pile": {"actual": math.nan, "allowable": 1,
                                   "status": invalid_status, "utilisation": math.nan}}},
    })
    assert checks["pile"]["governing_borehole"] == "B"
    assert math.isinf(checks["pile"]["utilisation"])
    assert checks["pile"]["status"] == "NOT OK"


def test_boolean_utilisation_is_not_a_valid_engineering_check():
    checks = envelope_checks({"A": {"checks": {
        "pile": {"actual": 3, "allowable": 2.5, "status": "OK", "utilisation": False}}}})
    assert checks["pile"]["status"] == "NOT OK"
    assert math.isinf(checks["pile"]["utilisation"])


def test_a_check_missing_from_one_log_is_not_silently_dropped():
    checks = envelope_checks({
        "A": {"checks": {"pile": {"actual": 1, "allowable": 1,
                                   "status": "OK", "utilisation": 0.5}}},
        "B": {"checks": {}},
    })
    assert checks["pile"]["status"] == "NOT OK"
    assert checks["pile"]["governing_borehole"] == "B"


def test_public_analyse_dispatches_socket_and_preserves_input_values():
    cfg = pile.default_config("socket")
    cfg["socket"].update(D=1.2, Q=1000)
    result = pile.analyse(cfg)
    assert isinstance(result, pile.SocketAnalysis)
    assert result.D == 1.2 and result.Q == 1000
    assert result.results["Ls_design"] == 4


def test_socket_logs_have_one_shared_integer_recommendation():
    cfg = pile.default_config("socket")
    cfg["socket"].update(Ls=0)
    cfg["boreholes"] = [
        {"name": "BH-rock-a", "soil_profile": cfg["soil_profile"],
         "socket": {"qu": 5, "rock_depth": 8}},
        {"name": "BH-rock-b", "soil_profile": cfg["soil_profile"],
         "socket": {"qu": 20, "rock_depth": 12}},
    ]
    result = pile.analyse_socket(cfg)
    length = result.results["total_length_design"]
    assert length.is_integer() and result.results["status"] == "OK"
    assert result.results["required_length"] == length
    assert result.results["length_basis"] == "total_pile"
    assert {a.overburden + a.results["Ls_check"] for a in result.analyses.values()} == {length}
    assert len({a.results["Ls_check"] for a in result.analyses.values()}) == 2
    assert all(c["status"] == "OK" for c in result.results["design_checks"].values())


def test_socket_total_length_is_integer_with_fractional_rock_levels():
    cfg = pile.default_config("socket")
    cfg["socket"].update(Ls=10.22, Q=1000, top=1.1)
    cfg["boreholes"] = [
        {"name": "Rock-A", "soil_profile": cfg["soil_profile"],
         "socket": {"qu": 5, "rock_depth": 8.25}},
        {"name": "Rock-B", "soil_profile": cfg["soil_profile"],
         "socket": {"qu": 20, "rock_depth": 12.5}},
    ]
    result = pile.analyse(cfg)
    expected_checked = 12.5 - 1.1 + 10.22
    assert result.results["L"] == pytest.approx(expected_checked)
    assert result.results["checked_socket_lengths"]["Rock-B"] == pytest.approx(10.22)
    length = result.results["required_length"]
    assert length.is_integer()
    repeated = result.evaluate_length(length)
    assert repeated["status"] == "OK"
    assert result.results["design_socket_lengths"]["Rock-A"] == pytest.approx(length - 7.15)
    assert result.results["design_socket_lengths"]["Rock-B"] == pytest.approx(length - 11.4)
    assert repeated["boreholes"]["Rock-B"]["Ls_check"] == pytest.approx(length - 11.4)


def test_failed_automatic_socket_search_cannot_compare_different_geometries_as_safe():
    cfg = pile.default_config("socket")
    cfg["socket"].update(Ls=0, Q=1e9)
    cfg["boreholes"] = [
        {"name": "Rock-A", "soil_profile": cfg["soil_profile"], "socket": {"qu": 5}},
        {"name": "Rock-B", "soil_profile": cfg["soil_profile"], "socket": {"qu": 20}},
    ]
    result = pile.analyse(cfg)
    assert math.isnan(result.results["required_length"])
    assert result.results["status"] == "NOT OK"
    assert set(result.results["checks"]) == {"shared_design"}
    assert result.results["governing_check"] == "shared_design"
    assert result.results["checked_socket_lengths"] == {}
    assert result.results["design_socket_lengths"] == {}
    assert math.isinf(result.results["utilisation"])


def test_optimizer_requires_the_same_length_to_pass_every_log():
    cfg = config()
    optimum = pile.optimize_length(cfg, L_bounds=(4, 40))
    assert optimum["success"]
    assert optimum["best_L"] == pile.analyse(cfg).results["required_length"]
    assert optimum["best_results"]["status"] == "OK"
