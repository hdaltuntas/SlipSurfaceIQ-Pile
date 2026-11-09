"""The soil profile from SPT records and the tests on their samples."""
import math

import pytest

from slipsurface import pile
from slipsurface.pile import spt
from slipsurface.pile.engine import LAYER_NUMBERS


def hole(*records, **extra):
    return {"name": "BH-1", "water_depth": 2.0, **extra, "records": list(records)}


def sand(depth, N, **more):
    return {"depth": depth, "N": N, "uscs": "SP", "fines": 4, **more}


def clay(depth, N, **more):
    return {"depth": depth, "N": N, "uscs": "CL", "LL": 40, "PL": 20, **more}


# --------------------------------------------------------------- corrections

def test_n60_takes_skemptons_corrections():
    # ER 45 %, 3 m of rods (CR 0.75), standard borehole and sampler
    assert spt.n60(20, 3.0, energy_ratio=45) == pytest.approx(20 * 0.75 * 0.75)
    # ER 60 %, 12 m (CR 1.0), 150 mm borehole (CB 1.05), no liner (CS 1.2)
    assert spt.n60(20, 12.0, 60, 150, liner=False) == pytest.approx(20 * 1.05 * 1.2)
    assert [spt.rod_factor(z) for z in (2, 5, 8, 15)] == [0.75, 0.85, 0.95, 1.0]


def test_the_overburden_correction_is_capped_at_1_7():
    assert spt.overburden_factor(spt.PA) == pytest.approx(1.0)
    assert spt.overburden_factor(10.0) == 1.7
    assert spt.overburden_factor(4 * spt.PA) == pytest.approx(0.5)


def test_the_correlations_give_their_published_values():
    assert spt.phi_from_n160(20) == pytest.approx(40.0)          # √400 + 20
    assert spt.phi_from_n160(200) == 45.0                        # capped
    assert spt.stroud_f1(10) == 6.5 and spt.stroud_f1(60) == 4.4
    assert spt.stroud_f1(32.5) == pytest.approx(5.45)
    assert spt.stroud_f1(None) == 5.0
    sin = 0.8 - 0.094 * math.log(20)
    assert spt.phi_from_pi(20) == pytest.approx(math.degrees(math.asin(sin)))
    assert spt.ocr_from_cu(0.22 * 100, 100) == pytest.approx(1.0)


# ------------------------------------------------------------ classification

@pytest.mark.parametrize("record, behaviour", [
    ({"uscs": "CL"}, "cohesive"), ({"uscs": "CH"}, "cohesive"), ({"uscs": "MH"}, "cohesive"),
    ({"uscs": "SM"}, "granular"), ({"uscs": "GW"}, "granular"), ({"uscs": "SC"}, "granular"),
    ({"uscs": "ML", "LL": 30, "PL": 26}, "granular"),
    ({"uscs": "ML", "LL": 40, "PL": 28}, "cohesive"),
    ({"fines": 70}, "cohesive"), ({"fines": 70, "LL": 25, "PL": 22}, "granular"),
    ({"fines": 20}, "granular"), ({"cu": 40}, "cohesive"), ({}, "granular"),
    ({"uscs": "CL", "behaviour": "granular"}, "granular"),
])
def test_the_behaviour_follows_the_sample_tests(record, behaviour):
    assert spt.classify(record) == behaviour


# --------------------------------------------------------------------- layers

def test_alike_tests_form_one_layer_and_a_change_of_behaviour_splits():
    prof = spt.derive_profile(hole(sand(1.5, 10), sand(3.0, 12), sand(4.5, 11),
                                   clay(6.0, 6), clay(7.5, 7), clay(9.0, 6)))
    assert [layer["behaviour"] for layer in prof.layers] == ["granular", "cohesive"]
    assert [layer["thickness"] for layer in prof.layers] == [5.25, 4.5]
    assert prof.depth == pytest.approx(9.75)        # half a spacing below the last test
    assert [r["layer"] for r in prof.records] == [1, 1, 1, 2, 2, 2]


def test_a_jump_in_the_blow_count_starts_a_new_layer():
    prof = spt.derive_profile(hole(sand(1.5, 8), sand(3.0, 9), sand(4.5, 10),
                                   sand(6.0, 40), sand(7.5, 42), sand(9.0, 45)))
    assert len(prof.layers) == 2
    assert prof.layers[1]["N60"] > 2 * prof.layers[0]["N60"]


def test_a_different_soil_group_starts_a_new_layer():
    gravel = [{"depth": z, "N": 12, "uscs": "GW"} for z in (6.0, 7.5, 9.0)]
    prof = spt.derive_profile(hole(sand(1.5, 12), sand(3.0, 12), sand(4.5, 12), *gravel))
    assert [layer["name"] for layer in prof.layers] == ["Sand (SP)", "Gravel (GW)"]


def test_a_thin_layer_joins_its_alike_neighbour():
    # 1 m spacing: the one dense test is a 1 m range of its own
    records = [sand(z, N) for z, N in ((1, 10), (2, 11), (3, 30), (4, 12), (5, 11))]
    assert len(spt.derive_profile(hole(*records), min_thickness=0.5).layers) == 3
    # thinner than 1.5 m: it joins the neighbour whose N60 is closer (12, 11 below)
    prof = spt.derive_profile(hole(*records), min_thickness=1.5)
    assert len(prof.layers) == 2
    assert [r["layer"] for r in prof.records] == [1, 1, 2, 2, 2]


def test_a_thin_clay_lens_in_sand_is_kept():
    records = [sand(1, 15), sand(2, 15), clay(3, 4), sand(4, 15), sand(5, 15)]
    prof = spt.derive_profile(hole(*records), min_thickness=1.5)
    assert [layer["behaviour"] for layer in prof.layers] == \
        ["granular", "cohesive", "granular"]


def test_tests_at_the_same_depth_in_several_boreholes_are_taken_together():
    a = hole(sand(1.5, 10), sand(3.0, 12))
    b = {"name": "BH-2", "water_depth": 1.0, "records": [sand(1.5, 14), sand(3.1, 10)]}
    prof = spt.derive_profile([a, b])
    assert prof.water_depth == 1.0                       # the shallowest
    assert len(prof.records) == 4 and len(prof.layers) == 1
    assert {r["borehole"] for r in prof.records} == {"BH-1", "BH-2"}


# ------------------------------------------------------------- the parameters

def test_measured_values_take_precedence_over_the_correlations():
    prof = spt.derive_profile(hole(clay(3.0, 4, cu=30), clay(4.5, 5, cu=50), clay(6.0, 6)))
    layer, src = prof.layers[0], prof.sources[0]
    assert layer["cu"] == pytest.approx(40.0) and src["cu"] == "measured, mean of 2"
    assert src["phi"].startswith("Terzaghi, Peck & Mesri")


def test_without_lab_values_the_correlations_fill_in():
    prof = spt.derive_profile(hole(clay(3.0, 8, w=30), clay(4.5, 8, w=30)),
                              water_depth=0.0)
    layer, src = prof.layers[0], prof.sources[0]
    N60 = layer["N60"]
    assert layer["cu"] == pytest.approx(spt.stroud_f1(20) * N60, rel=0.01)  # N60 rounded
    assert src["cu"].startswith("Stroud (1974)")
    assert layer["Cc"] == pytest.approx(0.009 * 30) and layer["Cr"] == pytest.approx(0.15 * 0.27)
    assert layer["e0"] == pytest.approx(0.30 * 2.70)
    assert layer["E"] == pytest.approx(0.3 * layer["cu"], rel=1e-3)
    sand_layer = spt.derive_profile(hole(sand(3.0, 20), sand(4.5, 20))).layers[0]
    assert sand_layer["E"] == pytest.approx(10 * spt.PA * sand_layer["N60"] / 1000, rel=0.01)


def test_the_ocr_comes_from_the_oedometer_when_there_is_one():
    prof = spt.derive_profile(hole(clay(4.0, 6, sigma_p=150, gamma=18)), water_depth=10.0)
    record = prof.records[0]
    assert prof.layers[0]["OCR"] == pytest.approx(150 / record["sigma_eff"], rel=0.05)
    assert prof.sources[0]["OCR"].startswith("σ'p / σ'v0")


def test_a_measured_unit_weight_is_used_above_and_below_the_water_table():
    above = spt.derive_profile(hole(sand(1.0, 10, gamma=18.0)), water_depth=5.0).layers[0]
    below = spt.derive_profile(hole(sand(6.0, 10, gamma=20.0)), water_depth=5.0).layers[0]
    assert (above["gamma"], above["gamma_sat"]) == (18.0, 19.0)
    assert (below["gamma"], below["gamma_sat"]) == (19.0, 20.0)


def test_a_clay_with_almost_no_blows_gets_a_floor_and_a_warning():
    prof = spt.derive_profile(hole(clay(3.0, 0), clay(4.5, 0)))
    assert prof.layers[0]["cu"] == 5.0
    assert any("5 kPa" in w for w in prof.warnings)


def test_bad_records_are_refused():
    with pytest.raises(ValueError, match="depth and a blow count"):
        spt.derive_profile(hole({"depth": 3.0}))
    with pytest.raises(ValueError, match="No SPT records"):
        spt.derive_profile(hole())
    with pytest.raises(ValueError, match="below the deepest test"):
        spt.derive_profile(hole(sand(3.0, 10)), bottom=2.0)


# ----------------------------------------------------------------- end to end

def borehole():
    return hole(sand(1.5, 6, fines=25), clay(3.0, 3, cu=30, w=32), clay(4.5, 4, w=34),
                clay(6.0, 5, cu=40), sand(7.5, 18), sand(9.0, 22), sand(10.5, 26),
                {"depth": 12.0, "N": 45, "uscs": "GW"}, {"depth": 13.5, "N": 50, "uscs": "GW"},
                {"depth": 15.0, "N": 50, "uscs": "GW"}, energy_ratio=45)


def test_the_layers_are_what_the_analysis_takes():
    prof = spt.derive_profile(borehole())
    for layer in prof.layers:
        assert set(LAYER_NUMBERS) <= set(layer) and {"name", "behaviour"} <= set(layer)
    cfg = prof.apply(pile.default_config("bored"))
    assert cfg["groundwater"]["depth"] == 2.0 and cfg["soil_profile"] == prof.layers
    cfg["pile"].update(D=0.8, L=12.0)
    result = pile.analyse(cfg)
    assert result.results["FS"] > 0
    assert pile.analyse(prof.apply(pile.default_config("driven")) | {
        "pile": {**cfg["pile"], "installation": "driven_high"}}).results["FS"] > 0


def test_the_report_shows_where_each_value_came_from(tmp_path):
    from slipsurface.pile import report
    prof = spt.derive_profile(borehole())
    cfg = prof.apply(pile.default_config("bored"))
    cfg["pile"].update(D=0.8, L=12.0)
    result = pile.analyse(cfg)
    html = report.build_html(result, {}, img_src=lambda k: k, spt=prof)
    assert "Soil profile from the boreholes" in html
    assert "Hatanaka &amp; Uchida (1996)" in html and "measured, mean of 2" in html
    out = tmp_path / "r.pdf"
    report.export_report(str(out), result, spt=prof)
    assert out.read_bytes()[:5] == b"%PDF-"
