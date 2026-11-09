"""
Configurations: the defaults, how a partial configuration is completed and
checked, and the pile type that decides which analysis runs.
"""
import math

import pytest

from slipsurface.pile import project
from slipsurface.pile.config import DEFAULT_CONFIG


def test_the_default_configuration_is_the_documented_one():
    cfg = project.default_config("bored")
    for section in DEFAULT_CONFIG:
        if section != "pile_type":
            assert cfg[section] == DEFAULT_CONFIG[section], section
    assert cfg["pile_type"] == "bored"


def test_a_file_missing_entries_keeps_the_defaults():
    cfg = project.normalize({"pile": {"D": 1.5}})
    assert cfg["pile"]["D"] == 1.5
    assert cfg["pile"]["L"] == DEFAULT_CONFIG["pile"]["L"]
    assert cfg["soil_profile"] == DEFAULT_CONFIG["soil_profile"]


@pytest.mark.parametrize("cfg, field", [
    ({"options": {"clay_method": "nonsense"}}, "options.clay_method"),
    ({"pile": {"shape": "hexagon"}}, "pile.shape"),
    ({"options": {"tip_methd": "vesic"}}, "tip_methd"),
])
def test_unknown_choices_and_misspelled_fields_are_refused(cfg, field):
    with pytest.raises(ValueError, match=field):
        project.normalize(cfg)


def test_numbers_are_numbers_and_the_pile_count_is_whole():
    cfg = project.normalize({"group": {"nx": 3.0}, "pile": {"D": "0.6"}})
    assert cfg["group"]["nx"] == 3 and cfg["pile"]["D"] == 0.6
    with pytest.raises(ValueError, match="whole number"):
        project.normalize({"group": {"nx": 3.4}})


@pytest.mark.parametrize("row", [{"name": "x"}, {"thickness": None}, {"thickness": 0},
                                 {"thickness": -1}, {"thickness": math.nan}])
def test_invalid_layers_are_refused_instead_of_deleted(row):
    with pytest.raises(ValueError, match="thickness"):
        project.normalize({"soil_profile": DEFAULT_CONFIG["soil_profile"] + [row]})


def test_an_omitted_type_defaults_but_an_unknown_type_is_refused():
    assert project.pile_type_of(None) == "bored"
    with pytest.raises(ValueError, match="pile_type"):
        project.pile_type_of("nonsense")
    with pytest.raises(ValueError, match="pile_type"):
        project.normalize({"pile_type": "nonsense"})


def test_a_default_title_follows_the_pile_type():
    assert "Rock-socketed" in project.default_config("socket")["project_info"]["title"]
    assert project.default_config("driven")["project_info"]["title"] == \
        project.DEFAULT_TITLES["driven"]


def test_a_bored_pile_is_installed_as_bored():
    with pytest.raises(ValueError, match="installation"):
        project.normalize({"pile_type": "bored", "pile": {"installation": "driven_high"}})


def test_a_driven_pile_is_installed_by_driving():
    def installation(value):
        return project.normalize({"pile_type": "driven",
                                  "pile": {"installation": value}})["pile"]["installation"]
    assert project.default_config("driven")["pile"]["installation"] == "driven_high"
    assert installation("driven_low") == "driven_low"
    with pytest.raises(ValueError, match="installation"):
        installation("bored")


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, None, True, ""])
def test_nonfinite_or_missing_supplied_numbers_are_refused(value):
    with pytest.raises(ValueError, match="pile.D"):
        project.normalize({"pile": {"D": value}})


def test_empty_profiles_do_not_become_the_example_geology():
    with pytest.raises(ValueError, match="at least one layer"):
        project.normalize({"soil_profile": []})


def test_boolean_text_is_parsed_explicitly_and_unrecognised_values_fail():
    assert project.normalize({"seismic": {"enabled": "false"}})["seismic"]["enabled"] is False
    assert project.normalize({"seismic": {"enabled": "TRUE"}})["seismic"]["enabled"] is True
    with pytest.raises(ValueError, match="true or false"):
        project.normalize({"seismic": {"enabled": "sometimes"}})


def test_explicitly_dry_profile_is_not_replaced_with_default_water():
    assert project.normalize({"groundwater": {"depth": None}})["groundwater"]["depth"] is None


def test_normalisation_is_idempotent_and_preserves_driven_installation():
    cfg = project.default_config("driven")
    assert project.normalize(cfg) == cfg


def test_driven_and_bored_give_different_capacities():
    from slipsurface.pile.engine import analyse
    bored = analyse(project.default_config("bored")).results
    driven = analyse(project.default_config("driven")).results
    assert driven["Qs"] > bored["Qs"]          # K/K0 1.4 against 1.0 in the sand


def test_reports_are_always_pdf(tmp_path):
    from slipsurface.pile import report
    from slipsurface.pile.socket import analyse_socket
    socket = analyse_socket(project.default_config("socket"))
    report.export_report(str(tmp_path / "r"), None, socket=socket)
    assert (tmp_path / "r.pdf").read_bytes()[:5] == b"%PDF-"
    report.export_report(str(tmp_path / "s.html"), None, socket=socket)
    assert (tmp_path / "s.html.pdf").read_bytes()[:5] == b"%PDF-"
