"""
Configurations: the defaults, how a partial configuration is completed and
checked, and the pile type that decides which analysis runs.
"""
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


def test_unknown_choices_fall_back_to_the_default():
    cfg = project.normalize({"options": {"clay_method": "nonsense"},
                             "pile": {"shape": "hexagon"}})
    assert cfg["options"]["clay_method"] == DEFAULT_CONFIG["options"]["clay_method"]
    assert cfg["pile"]["shape"] == DEFAULT_CONFIG["pile"]["shape"]


def test_numbers_are_numbers_and_the_pile_count_is_whole():
    cfg = project.normalize({"group": {"nx": 3.4}, "pile": {"D": "0.6"}})
    assert cfg["group"]["nx"] == 3 and cfg["pile"]["D"] == 0.6


def test_rows_without_a_thickness_are_dropped():
    rows = DEFAULT_CONFIG["soil_profile"] + [{"name": "x", "thickness": None},
                                             {"name": "y", "thickness": 0}]
    cfg = project.normalize({"soil_profile": rows})
    assert cfg["soil_profile"] == DEFAULT_CONFIG["soil_profile"]


def test_an_unknown_pile_type_reads_as_bored():
    assert project.pile_type_of(None) == "bored"
    assert project.pile_type_of("nonsense") == "bored"
    assert project.normalize({"pile_type": "nonsense"})["pile_type"] == "bored"


def test_a_default_title_follows_the_pile_type():
    assert "Rock-socketed" in project.default_config("socket")["project_info"]["title"]
    assert project.default_config("driven")["project_info"]["title"] == \
        project.DEFAULT_TITLES["driven"]


def test_a_bored_pile_is_installed_as_bored():
    cfg = project.normalize({"pile_type": "bored", "pile": {"installation": "driven_high"}})
    assert cfg["pile"]["installation"] == "bored"


def test_a_driven_pile_is_installed_by_driving():
    def installation(value):
        return project.normalize({"pile_type": "driven",
                                  "pile": {"installation": value}})["pile"]["installation"]
    assert project.default_config("driven")["pile"]["installation"] == "driven_high"
    assert installation("driven_low") == "driven_low"
    assert installation("bored") == "driven_high"


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
