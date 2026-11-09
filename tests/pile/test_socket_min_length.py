"""Socket geometry, serviceability and whole-metre design recommendations."""
import math

import pytest

from slipsurface.pile.config import DEFAULT_CONFIG, MIN_SOCKET_RATIO
from slipsurface.pile.project import default_config
from slipsurface.pile.socket import analyse_socket


def _socket(**socket):
    cfg = default_config("socket")
    cfg["socket"].update(socket)
    return analyse_socket(cfg).results


def test_the_minimum_is_three_diameters_by_default():
    assert MIN_SOCKET_RATIO == 3.0
    assert DEFAULT_CONFIG["socket"]["min_ratio"] == 3.0
    res = _socket()
    assert res["Ls_min"] == pytest.approx(3.0 * res["D"])
    assert res["Ls_design"] >= res["Ls_min"] - 1e-9


def test_a_tiny_load_still_needs_three_diameters():
    res = _socket(Q=10.0, D=1.2)
    assert res["Ls_min"] == pytest.approx(3.6)
    assert res["Ls_design"] == 4.0
    assert all(c["status"] == "OK" for c in res["design_checks"].values())


def test_an_old_ratio_below_three_is_raised_with_a_warning():
    cfg = default_config("socket")
    cfg["socket"]["min_ratio"] = 1.0
    analysis = analyse_socket(cfg)
    assert analysis.results["Ls_min"] == pytest.approx(3.0 * analysis.results["D"])
    assert any(key == "warn_socket_min_ratio" for key, _ in analysis.results["warnings"])


def test_a_larger_ratio_is_kept():
    res = _socket(min_ratio=4.0)
    assert res["Ls_min"] == pytest.approx(4.0 * res["D"])
    assert not any(key == "warn_socket_min_ratio" for key, _ in res["warnings"])


def test_a_short_socket_cannot_pass_overall_even_when_capacity_is_ample():
    res = _socket(Q=10.0, D=1.2, Ls=0.2)
    assert res["checks"]["capacity"]["status"] == "OK"
    assert res["checks"]["min_length"]["status"] == "NOT OK"
    assert res["check"]["status"] == "NOT OK"
    assert res["Ls_design"] == 4.0


def test_safe_fractional_entered_socket_is_not_warned_as_short_due_to_rounding():
    res = _socket(Q=10.0, D=1.2, Ls=3.6)
    assert res["Ls_check"] == 3.6
    assert res["Ls_design"] == 4.0
    assert res["check"]["status"] == "OK"
    assert not any(key == "warn_socket_short" for key, _ in res["warnings"])


@pytest.mark.parametrize("continuous, recommended", [(10.22, 11.0), (10.0, 10.0)])
def test_capacity_requirement_is_rechecked_at_whole_metres(continuous, recommended):
    # Horvath–Kenney: fs = 0.21 sqrt(qu) MPa. With no base and no weight,
    # Qall = pi D L fs / FS. Choose a load needing 10.22 m by this hand formula.
    cfg = default_config("socket")
    cfg["socket"].update(D=1.0, Ls=0.0, top=0.0, rock_depth=0.0,
                         design="horvath_kenney", base_design="none",
                         Q=math.pi * 0.21 * math.sqrt(20.0) * 1000.0 * continuous / 2.5)
    cfg["options"]["subtract_weight"] = False
    res = analyse_socket(cfg).results
    assert res["Ls_req_continuous"] == pytest.approx(continuous, abs=1e-3)
    assert res["Ls_design"] == recommended
    assert res["Ls_check"] == recommended
    assert all(c["status"] == "OK" for c in res["checks"].values())


def test_serviceability_can_require_more_than_the_rounded_capacity_length():
    cfg = default_config("socket")
    cfg["socket"].update(Ls=0.0, rock_depth=0.0, top=0.0, base_design="none",
                         modulus_method="direct", Em=100.0)
    cfg["criteria"]["s_allow"] = 10.0
    analysis = analyse_socket(cfg)
    res = analysis.results
    capacity_length = math.ceil(max(res["Ls_req_continuous"], res["Ls_min"]))
    early = analysis.check_length(capacity_length)
    assert early["checks"]["capacity"]["status"] == "OK"
    assert early["checks"]["settlement"]["status"] == "NOT OK"
    assert res["Ls_design"] > capacity_length
    assert res["Ls_design"].is_integer()
    assert res["settlement"]["method"] == "rw_side"
    assert res["check"]["status"] == "OK"
    assert analysis.check_length(res["Ls_design"] - 1)["checks"]["settlement"]["status"] == "NOT OK"


def test_no_socket_is_recommended_when_overburden_shortening_alone_fails():
    cfg = default_config("socket")
    cfg["socket"]["Ls"] = 0.0
    cfg["criteria"]["s_allow"] = 1.0
    res = analyse_socket(cfg).results
    assert res["settlement"]["shortening"] * 1000.0 > 1.0
    assert math.isnan(res["Ls_design"])
    assert res["design_check"] is None
    assert res["check"]["status"] == "NOT OK"


def test_dry_socket_pile_weight_uses_concrete_unit_weight_along_whole_length():
    cfg = default_config("socket")
    cfg["groundwater"]["depth"] = None
    analysis = analyse_socket(cfg)
    assert analysis.weight(4.0) == pytest.approx(math.pi / 4.0 * 15.0 * 25.0)


def test_socket_run_is_repeatable_without_duplicating_or_mutating_warnings():
    analysis = analyse_socket(default_config("socket"))
    previous = analysis.results
    warnings = list(previous["warnings"])
    repeated = analysis.run()
    assert repeated["warnings"] == warnings
    assert previous["warnings"] == warnings
    assert previous["warnings"] is not repeated["warnings"]
    assert repeated["checks"] == previous["checks"]


def test_automatic_socket_method_capacities_use_the_checked_common_length():
    cfg = default_config("socket")
    cfg["socket"]["Ls"] = 0.0
    analysis = analyse_socket(cfg)
    length = analysis.results["Ls_check"]
    assert length > 0
    for row in analysis.results["side"].values():
        assert row["Ls_check"] == length
        assert row["Q_all"] == pytest.approx(analysis.capacity(length, row["fs"])["Q_all"])


def test_positive_base_modulus_ratio_below_one_percent_is_preserved():
    cfg = default_config("socket")
    cfg["socket"]["Eb_ratio"] = 0.005
    analysis = analyse_socket(cfg)
    assert analysis.Eb_ratio == 0.005


def test_multiple_logs_without_a_feasible_shared_socket_never_report_ok():
    cfg = default_config("socket")
    cfg["socket"]["Ls"] = 0.0
    cfg["criteria"]["s_allow"] = 1.0  # overburden shortening already exceeds this
    cfg["boreholes"] = [
        {"name": "BH-A", "soil_profile": cfg["soil_profile"], "socket": {"qu": 5.0}},
        {"name": "BH-B", "soil_profile": cfg["soil_profile"], "socket": {"qu": 20.0}},
    ]
    result = analyse_socket(cfg).results
    assert result["status"] == "NOT OK"
    assert math.isnan(result["total_length_design"])
    assert result["checks"]["shared_design"]["status"] == "NOT OK"
    assert math.isinf(result["utilisation"])


def test_cfem_capacity_peak_before_the_search_limit_is_not_missed():
    # CFEM's increasing base term caps at 5D; beyond that, the self-weight of
    # this large dry shaft grows faster than its allowable side resistance.
    # A 60 m endpoint failure therefore does not rule out a shorter socket.
    cfg = default_config("socket")
    cfg["socket"].update(D=3.1, Ls=0.0, top=0.0, rock_depth=0.0, Q=170.0,
                         qu=0.05, design="horvath_kenney", base_design="cfem",
                         modulus_method="direct", Em=10.0)
    cfg["groundwater"]["depth"] = None
    analysis = analyse_socket(cfg)
    result = analysis.results
    assert analysis.check_length(60.0)["checks"]["capacity"]["status"] == "NOT OK"
    assert 10.0 < result["Ls_req_continuous"] < 11.0
    assert result["Ls_design"] == 11.0
    assert result["check"]["status"] == "OK"
    assert analysis.check_length(10.0)["checks"]["capacity"]["status"] == "NOT OK"
