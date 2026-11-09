"""The pile analysis as a whole: hand calculations of simple cases, and the refusals."""
import copy
import math

import pytest

from slipsurface.pile.config import CLAY_METHODS, DEFAULT_CONFIG, PA, TIP_METHODS
from slipsurface.pile.engine import PileAnalysis, analyse
from slipsurface.pile.errors import PileError


def one_layer(behaviour="cohesive", **layer):
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    base = {"name": "Uniform", "thickness": 40.0, "behaviour": behaviour, "gamma": 18.0,
            "gamma_sat": 19.0, "phi": 30.0, "cu": 50.0, "OCR": 1.0, "N60": 0.0, "E": 30.0,
            "nu": 0.3, "Cc": 0.0, "Cr": 0.0, "e0": 0.0}
    base.update(layer)
    cfg["soil_profile"] = [base]
    cfg["groundwater"]["depth"] = 100.0
    cfg["group"].update(nx=1, ny=1)
    cfg["pile"].update(D=0.6, L=15.0, top=0.0)
    cfg["loading"]["Q"] = 500.0
    cfg["seismic"]["enabled"] = False
    return cfg


def test_a_clay_pile_by_hand():
    cfg = one_layer()
    cfg["options"]["clay_method"] = "alpha_kulhawy"
    a = analyse(cfg)
    res = a.results
    alpha = 0.21 + 0.26 * PA / 50.0
    perimeter, area = math.pi * 0.6, math.pi * 0.09
    assert res["Qs"] == pytest.approx(alpha * 50.0 * perimeter * 15.0)
    assert res["Qb"] == pytest.approx(9 * 50.0 * area)
    assert res["W"] == pytest.approx(25.0 * area * 15.0)
    assert res["Q_ult_net"] == pytest.approx(res["Qs"] + res["Qb"] - res["W"])
    assert res["Q_all"] == pytest.approx(res["Q_ult_net"] / 2.5)
    assert res["FS"] == pytest.approx(res["Q_ult_net"] / 500.0)


def test_a_sand_pile_by_hand_without_the_critical_depth():
    cfg = one_layer("granular", phi=30.0)
    cfg["options"].update(critical_depth=False, K_ratio=1.0, delta_ratio=0.75)
    res = analyse(cfg).results
    K = 1 - math.sin(math.radians(30.0))
    tan_d = math.tan(math.radians(22.5))
    expected = K * tan_d * math.pi * 0.6 * 18.0 * 15.0 ** 2 / 2
    assert res["Qs"] == pytest.approx(expected, rel=1e-9)


def test_the_critical_depth_caps_the_sand():
    cfg = one_layer("granular", phi=30.0)
    capped = analyse(cfg).results
    cfg["options"]["critical_depth"] = False
    free = analyse(cfg).results
    assert capped["Qs"] < free["Qs"]
    assert any(w[0] == "warn_critical_depth" for w in capped["warnings"])


def test_the_water_table_lowers_the_capacity_in_sand():
    cfg = one_layer("granular")
    cfg["options"]["critical_depth"] = False
    dry = analyse(cfg).results
    cfg["groundwater"]["depth"] = 0.0
    wet = analyse(cfg).results
    assert wet["Qs"] < dry["Qs"] and wet["Qb"] <= dry["Qb"]
    assert wet["W"] == pytest.approx(math.pi * 0.09 * 15.0 * (25.0 - 9.81))


def test_the_weight_is_subtracted_only_when_asked():
    cfg = one_layer()
    cfg["options"]["subtract_weight"] = False
    res = analyse(cfg).results
    assert res["Q_ult_net"] == pytest.approx(res["Q_ult"])
    assert res["W"] > 0


def test_every_method_combination_is_reported():
    a = analyse(DEFAULT_CONFIG)
    assert len(a.results["combos"]) == len(CLAY_METHODS) * len(TIP_METHODS)
    for clay in CLAY_METHODS:
        for tip in TIP_METHODS:
            combo = a.results["combos"][f"{clay}|{tip}"]
            assert combo["Q_ult"] == pytest.approx(a.results["shaft"]["Qs"][clay]
                                                   + a.results["base"]["methods"][tip]["Qb"])


def test_the_group_takes_the_smaller_of_efficiency_and_block():
    res = analyse(DEFAULT_CONFIG).results
    group = res["group"]
    assert group["Q_ult"] == pytest.approx(min(group["Q_eff"], group["block"]["Q_ult"]))
    assert group["Q_ult_net"] == pytest.approx(group["Q_ult"] - 9 * res["W"])


def test_a_close_group_in_soft_clay_fails_as_a_block():
    cfg = one_layer(cu=20.0)
    cfg["group"].update(nx=5, ny=5, sx=0.9, sy=0.9, efficiency="unity")
    cfg["loading"]["Q"] = 1000.0
    res = analyse(cfg).results
    assert res["group"]["governing"] == "block"
    assert any(w[0] == "warn_spacing" for w in res["warnings"])


def test_the_required_length_is_the_first_that_passes():
    cfg = one_layer()
    cfg["loading"]["Q"] = 800.0
    a = analyse(cfg)
    L = a.results["required_length"]
    assert math.isfinite(L) and float(L).is_integer()
    curve = {round(p["L"], 6): p for p in a.results["length_curve"]}
    assert curve[round(L, 6)]["utilisation"] <= 1.0
    previous = curve[round(L - 1.0, 6)]
    assert max(previous["utilisation"], previous["utilisation_group"],
               previous["utilisation_settlement"], previous["utilisation_seismic"]) > 1.0
    trial = copy.deepcopy(cfg)
    trial["pile"]["L"] = L
    checks = PileAnalysis(trial).run(with_length=False)["checks"]
    assert all(check["status"] in {"OK", "N/A"} for check in checks.values())


def test_required_length_includes_the_settlement_limit():
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["loading"]["Q"] = 4000.0
    cfg["seismic"]["enabled"] = False
    # The previous capacity-only answer was 6.5 m, settling 74.2 mm against
    # the default 40 mm limit. Its ceiling (7 m) also fails settlement.
    cfg["pile"]["L"] = 6.5
    a = analyse(cfg)
    assert a.results["checks"]["pile"]["status"] == "OK"
    assert a.results["checks"]["group"]["status"] == "OK"
    assert a.results["checks"]["settlement"]["status"] == "NOT OK"
    assert a.results["checks"]["settlement"]["actual"] == pytest.approx(74.21135233407199)
    assert a.results["required_length"] == 9
    cfg["pile"]["L"] = a.results["required_length"]
    safe = analyse(cfg, with_length=False).results
    assert all(check["status"] in {"OK", "N/A"} for check in safe["checks"].values())
    assert safe["checks"]["settlement"]["utilisation"] == pytest.approx(
        safe["checks"]["settlement"]["actual"] / 40.0)


def test_integer_length_is_rechecked_when_rounding_enters_a_weak_layer():
    cfg = one_layer("granular", phi=36.0, E=50.0, N60=40.0)
    sand = cfg["soil_profile"][0]
    clay = {**sand, "name": "Weak clay", "behaviour": "cohesive", "phi": 20.0,
            "cu": 5.0, "E": 10.0, "N60": 0.0}
    cfg["soil_profile"] = [
        {**sand, "thickness": 10.8}, {**clay, "thickness": 1.2},
        {**sand, "thickness": 28.0},
    ]
    cfg["pile"]["L"] = 10.22
    cfg["criteria"]["L_min"] = 10.22
    cfg["loading"]["Q"] = 800.0
    a = analyse(cfg)
    assert a.results["L"] == 10.22  # an entered fractional length is preserved
    assert all(check["status"] == "OK" for check in a.results["checks"].values())
    curve = {point["L"]: point for point in a.results["length_curve"]}
    assert curve[11]["utilisation"] > 1.0
    assert a.results["required_length"] == 12  # ceil(10.22) is not a safe design
    cfg["pile"]["L"] = 12
    assert all(check["status"] == "OK" for check in
               analyse(cfg, with_length=False).results["checks"].values())


def test_no_integer_recommendation_extends_past_the_investigated_profile():
    cfg = one_layer(thickness=10.8)
    cfg["pile"]["L"] = 10.22
    cfg["criteria"]["L_min"] = 10.22
    cfg["loading"]["Q"] = 10.0
    result = analyse(cfg).results
    assert result["checks"]["pile"]["status"] == "OK"
    assert result["length_curve"] == []
    assert math.isnan(result["required_length"])


def test_no_length_is_reported_as_such():
    cfg = one_layer(cu=5.0)
    cfg["loading"]["Q"] = 50_000.0
    res = analyse(cfg).results
    assert math.isnan(res["required_length"])
    assert any(w[0] == "warn_no_length" for w in res["warnings"])


def test_a_group_settles_more_than_one_pile():
    st = analyse(DEFAULT_CONFIG).results["settlement"]
    assert st["vesic"] > st["single"]["s"]
    assert st["raft"]["total"] == pytest.approx(st["raft"]["s"] + st["raft"]["shortening"])
    assert st["raft"]["consolidation"] > 0 and st["raft"]["elastic"] > 0
    assert st["meyerhof"] is not None


def test_a_weaker_layer_under_the_tip_is_flagged():
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["pile"]["L"] = 12.5                    # tip at 14.0 m, stiff clay from 15 m
    res = analyse(cfg).results
    assert any(w[0] == "warn_weak_below" for w in res["warnings"])


@pytest.mark.parametrize("section, key, value, error", [
    ("pile", "D", 0.0, "err_dimensions"),
    ("pile", "L", 100.0, "err_tip_below"),
    ("pile", "top", -1.0, "err_top"),
    ("loading", "Q", 0.0, "err_load"),
    ("group", "sx", 0.3, "err_group_spacing"),
    ("group", "nx", 0, "err_group_count"),
])
def test_impossible_inputs_are_refused(section, key, value, error):
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg[section][key] = value
    with pytest.raises(PileError) as caught:
        PileAnalysis(cfg)
    assert caught.value.key == error


def test_a_clay_without_cu_is_refused():
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["soil_profile"][1]["cu"] = 0.0
    with pytest.raises(PileError) as caught:
        PileAnalysis(cfg)
    assert caught.value.key == "err_cu"


def test_a_run_without_the_length_search_leaves_it_out():
    res = PileAnalysis(DEFAULT_CONFIG).run(with_length=False)
    assert res["length_curve"] == [] and math.isnan(res["required_length"])


# --------------------------------------------------------------------------- #
#  The seismic load case
# --------------------------------------------------------------------------- #

def seismic_case(**seismic):
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["seismic"].update({"enabled": True, **seismic})
    return cfg


def test_the_cap_shares_the_seismic_load_by_hand():
    a = PileAnalysis(seismic_case(V=9000.0, M_B=10000.0, M_L=4000.0))
    loads = a.pile_loads()
    sxx = syy = 6 * 2.4 ** 2                   # a 3 × 3 group at 2.4 m
    for p in loads:
        assert p["P"] == pytest.approx(1000.0 + 10000.0 * p["x"] / sxx
                                       + 4000.0 * p["y"] / syy)
    assert sum(p["P"] for p in loads) == pytest.approx(9000.0)
    assert sum(p["P"] * p["x"] for p in loads) == pytest.approx(10000.0)
    assert sum(p["P"] * p["y"] for p in loads) == pytest.approx(4000.0)


@pytest.mark.parametrize("nx, ny, moment, axis", [
    (1, 3, "M_B", "B"), (3, 1, "M_L", "L"),
    (1, 1, "M_B", "B"), (1, 1, "M_L", "L"),
])
def test_a_seismic_moment_without_an_axial_lever_arm_is_rejected(nx, ny, moment, axis):
    cfg = seismic_case(V=300.0, M_B=0.0, M_L=0.0)
    cfg["group"].update(nx=nx, ny=ny)
    cfg["seismic"][moment] = 100000.0
    with pytest.raises(PileError) as caught:
        PileAnalysis(cfg)
    assert caught.value.key == "err_seismic_moment"
    assert caught.value.params["axis"] == axis
    cfg["seismic"]["enabled"] = False
    assert analyse(cfg, with_length=False).results["seismic"] is None


def test_seismic_group_compression_cannot_pass_on_individual_capacities_alone():
    cfg = seismic_case(V=24709.080608388136, M_B=0.0, M_L=0.0)
    cfg["loading"]["Q"] = 100.0
    res = analyse(cfg, with_length=False).results
    assert res["checks"]["group"]["status"] == "OK"  # static case
    assert res["checks"]["seismic_compression"]["status"] == "OK"
    group = res["seismic"]["group_compression"]
    assert group["Q_all"] == pytest.approx(20651.716278608223)
    assert group["utilisation"] == pytest.approx(1.1964662052801236)
    assert res["checks"]["seismic_group_compression"]["status"] == "NOT OK"
    assert res["seismic"]["utilisation"] == pytest.approx(group["utilisation"])


def test_the_uplift_capacity_by_hand():
    cfg = one_layer("granular", phi=30.0)
    cfg["options"]["critical_depth"] = False
    cfg["seismic"].update(enabled=True, V=-300.0, M_B=0.0, M_L=0.0, tension_sand=0.75,
                          cyclic=0.8, FS_tension=2.0)
    res = analyse(cfg).results
    t = res["seismic"]["tension"]
    assert t["Qs"] == pytest.approx(0.75 * 0.8 * res["Qs"])
    assert t["W"] == pytest.approx(res["W"])
    assert t["T_all"] == pytest.approx(t["Qs"] / 2.0 + t["W"])
    assert t["T"] == pytest.approx(300.0)
    assert t["FS"] == pytest.approx(t["Qs"] / (300.0 - t["W"]))
    assert res["checks"]["seismic_tension"]["status"] == "OK"
    assert res["seismic"]["group"] is None       # a single pile has no block
    assert res["seismic"]["group_compression"] is None


def test_clay_keeps_its_whole_shaft_friction_in_tension():
    cfg = one_layer()
    cfg["seismic"].update(enabled=True, V=-100.0, M_B=0.0, tension_clay=1.0, cyclic=1.0)
    res = analyse(cfg).results
    assert res["seismic"]["tension"]["Qs"] == pytest.approx(res["Qs"])


def test_a_large_moment_pulls_the_outer_piles_and_can_fail_them():
    res = analyse(seismic_case(V=8000.0, M_B=16000.0)).results
    t = res["seismic"]["tension"]
    assert t["n"] == 3 and t["T"] == pytest.approx(16000.0 * 2.4 / 34.56 - 8000.0 / 9)
    assert any(w[0] == "warn_seismic_tension" for w in res["warnings"])
    failing = analyse(seismic_case(V=2000.0, M_B=200000.0)).results
    assert failing["checks"]["seismic_tension"]["status"] == "NOT OK"


def test_no_tension_means_no_uplift_check():
    res = analyse(seismic_case(V=9000.0, M_B=0.0, M_L=0.0)).results
    assert res["seismic"]["tension"]["T"] == 0.0
    assert res["checks"]["seismic_tension"]["status"] == "N/A"


def test_a_lifted_group_is_checked_as_a_block():
    res = analyse(seismic_case(V=-3000.0, M_B=0.0)).results
    g = res["seismic"]["group"]
    assert g is not None and g["T"] == pytest.approx(3000.0)
    assert g["T_all"] == pytest.approx(g["Qs"] / 2.0 + g["W"])
    assert "seismic_group_tension" in res["checks"]
    assert res["checks"]["seismic_group_compression"]["status"] == "N/A"


def test_the_seismic_checks_lengthen_the_pile_when_they_govern():
    calm = analyse(seismic_case(enabled=False)).results["required_length"]
    shaken = analyse(seismic_case(V=8000.0, M_B=30000.0)).results
    assert shaken["required_length"] > calm
    curve = {round(p["L"], 6): p for p in shaken["length_curve"]}
    assert curve[round(shaken["required_length"], 6)]["utilisation_seismic"] <= 1.0


def test_the_earthquake_off_leaves_no_trace():
    res = analyse(seismic_case(enabled=False)).results
    assert res["seismic"] is None
    assert not any(key.startswith("seismic") for key in res["checks"])


def test_the_raft_load_spreads_two_to_one_on_each_side():
    # Tomlinson's 2 : 1 — at depth z below the raft the load acts on (Bg + z)(Lg + z)
    from slipsurface.pile.settlement import raft_widening
    assert raft_widening(4.0, 2.0) == pytest.approx(4.0)
    st = analyse(DEFAULT_CONFIG).results["settlement"]
    raft = st["raft"]
    row = raft["rows"][-1]
    z = row["z"] - raft["z_raft"]
    q = DEFAULT_CONFIG["loading"]["Q"]
    assert row["dsigma"] == pytest.approx(q / ((st["Bg"] + z) * (st["Lg"] + z)))


def test_a_tip_on_a_layer_boundary_is_flagged():
    # the default tip is 1.5 m (< 2·D) into the dense sand
    res = analyse(DEFAULT_CONFIG).results
    assert any(w[0] == "warn_tip_embedment" for w in res["warnings"])
    deeper = {**DEFAULT_CONFIG, "pile": {**DEFAULT_CONFIG["pile"], "L": 24.0}}
    assert not any(w[0] == "warn_tip_embedment"
                   for w in analyse(deeper).results["warnings"])


def test_repeated_runs_do_not_accumulate_trial_or_previous_warnings():
    a = PileAnalysis(DEFAULT_CONFIG)
    first = a.run(with_length=False)
    warnings = copy.deepcopy(first["warnings"])
    second = a.run(with_length=True)
    assert second["warnings"] == warnings
    assert first["warnings"] == warnings


def test_no_water_table_means_dry_stresses_and_full_pile_weight():
    cfg = one_layer("granular")
    cfg["groundwater"]["depth"] = None
    a = PileAnalysis(cfg)
    res = a.run(with_length=False)
    assert math.isinf(a.profile.zw)
    assert a.profile.effective_stress(15.0) == pytest.approx(18.0 * 15.0)
    assert res["W"] == pytest.approx(25.0 * math.pi * 0.6 ** 2 / 4.0 * 15.0)


def test_the_soil_constructor_refuses_a_socket_configuration():
    cfg = {**DEFAULT_CONFIG, "pile_type": "socket"}
    with pytest.raises(PileError) as caught:
        PileAnalysis(cfg)
    assert caught.value.key == "err_pile_type"


def test_the_soil_constructor_cannot_silently_ignore_boreholes():
    cfg = one_layer()
    cfg["boreholes"] = [{"name": "BH-1", "soil_profile": cfg["soil_profile"]}]
    with pytest.raises(PileError) as caught:
        PileAnalysis(cfg)
    assert caught.value.key == "err_config"
    assert caught.value.params["field"] == "boreholes"
