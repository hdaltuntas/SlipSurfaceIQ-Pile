"""Public summaries retain the checked geometry, governing log and chosen model."""

import copy
import math

import pytest

from slipsurface import pile
from slipsurface.pile import summary


def _envelope(with_length=True):
    cfg = pile.default_config("bored")
    cfg["loading"]["Q"] = 4000.0
    cfg["seismic"]["enabled"] = False
    weaker = copy.deepcopy(cfg["soil_profile"])
    weaker[1]["cu"] = 20.0
    cfg["boreholes"] = [
        {"name": "BH: West", "soil_profile": cfg["soil_profile"]},
        {"name": "BH-East", "soil_profile": weaker},
    ]
    return pile.analyse(cfg, with_length=with_length)


def test_public_summary_routes_socket_and_uses_the_selected_settlement():
    cfg = pile.default_config("socket")
    cfg["socket"].update(base_design="none", modulus_method="direct", Em=100.0)
    analysis = pile.analyse(cfg)
    result = analysis.results
    selected_mm = 1000 * result["settlement"]["s"]
    assert selected_mm != pytest.approx(1000 * result["settlement"]["rw"]["total"])
    headline = summary.headline(analysis)
    assert headline == summary.socket_headline(analysis)
    assert f"s = {selected_mm:.1f} mm" in headline
    assert f"Ls design = {result['Ls_design']:.0f} m" in headline
    assert f"checked Ls = {result['Ls_check']:.2f} m" in headline
    text = summary.results_text(analysis)
    assert text == summary.socket_text(analysis)
    assert f"Recommended whole-metre Ls = {result['Ls_design']:.0f} m" in text
    assert "Continuous capacity-only diagnostic" in text
    assert "Selected settlement" in text
    assert "Minimum socket length" in text


def test_envelope_summary_names_every_log_and_each_controlling_check():
    analysis = _envelope()
    result = analysis.results
    text = summary.results_text(analysis)
    assert "Checked common geometry: D = 0.80 m, L = 20.00 m" in text
    assert "BOREHOLE: BH: West" in text
    assert "BOREHOLE: BH-East" in text
    for check in result["checks"].values():
        assert f"governing borehole: {check['governing_borehole']}" in text
    assert math.isfinite(result["required_length"])
    assert f"Recommended whole-metre L = {result['required_length']:.0f} m" in text
    assert "every active check was re-evaluated in every borehole" in text
    assert "governing borehole:" in summary.headline(analysis)
    # An envelope has no synthetic single-pile Qult field to headline.
    assert "Qult,net" not in summary.headline(analysis)


def test_socket_envelope_summarises_common_total_length_and_each_rock_embedment():
    cfg = pile.default_config("socket")
    cfg["socket"].update(top=0.0, Ls=4.25)
    cfg["boreholes"] = [
        {"name": "BH-Shallow", "soil_profile": cfg["soil_profile"],
         "socket": {"rock_depth": 8.25, "qu": 5.0}},
        {"name": "BH-Deep", "soil_profile": cfg["soil_profile"],
         "socket": {"rock_depth": 12.75, "qu": 20.0}},
    ]
    analysis = pile.analyse(cfg)
    result = analysis.results
    text = summary.results_text(analysis)
    required = result["required_length"]
    assert math.isfinite(required)
    assert "Checked common geometry: D = 1.00 m, L = 17.00 m" in text
    assert "common total head-to-tip pile length" in text
    assert "Ls may be fractional" in text
    assert f"Recommended whole-metre L = {required:.0f} m" in text
    assert "Recommended whole-metre Ls" not in text
    assert "Independent log-only whole-metre Ls" in text
    assert "Log-only Ls (m)" in text
    for name, overburden in (("BH-Shallow", 8.25), ("BH-Deep", 12.75)):
        row = next(line for line in text.splitlines() if line.strip().startswith(name))
        assert row.split() == [name, f"{overburden:.2f}", f"{17 - overburden:.2f}",
                               "17.00", f"{required - overburden:.2f}", f"{required:.0f}"]
    head = summary.headline(analysis)
    assert "checked L = 17.00 m total head-to-tip" in head
    assert f"common Ldesign = {required:.0f} m" in head
    assert "Lsdesign" not in head


def test_failed_socket_auto_sizing_does_not_claim_a_common_checked_geometry():
    cfg = pile.default_config("socket")
    cfg["socket"].update(top=0.0, Ls=0.0, Q=100_000_000.0)
    cfg["boreholes"] = [
        {"name": "BH-Shallow", "soil_profile": cfg["soil_profile"],
         "socket": {"rock_depth": 8.25}},
        {"name": "BH-Deep", "soil_profile": cfg["soil_profile"],
         "socket": {"rock_depth": 12.75}},
    ]
    analysis = pile.analyse(cfg)
    assert analysis.results["checked_socket_lengths"] == {}
    text = summary.results_text(analysis)
    assert "No checked common geometry is available" in text
    assert "No common checked geometry was established" in text
    assert "Each log below is evaluated at the checked common geometry" not in text
    assert "checked common L unavailable" in summary.headline(analysis)
    for name, overburden in (("BH-Shallow", 8.25), ("BH-Deep", 12.75)):
        row = next(line for line in text.splitlines() if line.strip().startswith(name))
        assert row.split() == [name, f"{overburden:.2f}", "—", "—", "—", "—"]


def test_skipping_length_search_is_distinguished_from_no_feasible_length():
    cfg = pile.default_config("bored")
    single = pile.analyse(cfg, with_length=False)
    assert "Length search was not requested" in summary.results_text(single)
    envelope = _envelope(with_length=False)
    text = summary.results_text(envelope)
    assert "Length search was not requested" in text
    assert "No verified common whole-metre length was found" not in text


def test_seismic_group_failure_is_visible_in_the_text_and_headline():
    cfg = pile.default_config("bored")
    cfg["loading"]["Q"] = 100.0
    cfg["seismic"].update(V=24709.080608388136, M_B=0.0, M_L=0.0)
    analysis = pile.analyse(cfg, with_length=False)
    text = summary.results_text(analysis)
    line = next(line for line in text.splitlines() if "Seismic group compression:" in line)
    assert "NOT OK" in line
    assert "NOT OK" in summary.headline(analysis)


def test_dry_profile_text_does_not_print_an_infinite_water_depth():
    cfg = pile.default_config("bored")
    cfg["groundwater"]["depth"] = None
    text = summary.results_text(pile.analyse(cfg, with_length=False))
    assert "dry-ground assumption" in text
    assert "Water table at inf" not in text
