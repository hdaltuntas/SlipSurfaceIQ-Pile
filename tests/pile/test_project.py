"""
Configurations and project files: the defaults, how a partial or older file is
completed and checked, and the pile type that decides which analysis runs.
"""
import json

from slipsurface.pile import project
from slipsurface.pile.config import DEFAULT_CONFIG


def test_the_default_configuration_is_the_documented_one():
    cfg = project.default_config("bored")
    for section in DEFAULT_CONFIG:
        if section != "pile_type":
            assert cfg[section] == DEFAULT_CONFIG[section], section
    assert cfg["pile_type"] == "bored"


def test_a_project_file_round_trips(tmp_path):
    cfg = project.default_config()
    cfg["pile"].update(D=1.2, shape="square")
    cfg["group"]["nx"] = 4
    cfg["options"].update(clay_method="beta", tip_method="janbu", critical_depth=False)
    cfg["socket"].update(Ls=5.5, design="carter_kulhawy", base_design="none")
    path = tmp_path / "p.pile.json"
    project.save_config(cfg, path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["format"] == project.FILE_FORMAT
    assert project.load_config(path) == cfg


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


def test_the_pile_type_round_trips_through_a_project_file(tmp_path):
    for pile_type in project.PILE_TYPES:
        path = tmp_path / f"{pile_type}.pile.json"
        project.save_config(project.default_config(pile_type), path)
        assert project.load_config(path)["pile_type"] == pile_type


def test_old_and_unknown_pile_types_read_as_bored():
    assert project.pile_type_of("soil") == "bored"
    assert project.pile_type_of(None) == "bored"
    assert project.pile_type_of("nonsense") == "bored"
    assert project.normalize({"pile_type": "soil"})["pile_type"] == "bored"


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


def test_older_files_installed_by_driving_open_as_driven():
    assert project.normalize({"pile": {"installation": "driven_low"}})["pile_type"] == "driven"
    old = {"pile_type": "soil", "pile": {"installation": "driven_high"}}
    assert project.normalize(old)["pile_type"] == "driven"
    # a file that names its type keeps it
    assert project.normalize({"pile_type": "bored",
                              "pile": {"installation": "bored"}})["pile_type"] == "bored"


def test_an_older_file_with_a_study_block_still_opens(tmp_path):
    path = tmp_path / "old.pile.json"
    path.write_text(json.dumps({"pile": {"L": 12}, "study": {"n": 3}}), encoding="utf-8")
    cfg = project.load_config(path)
    assert cfg["pile"]["L"] == 12 and "study" not in cfg


def test_driven_and_bored_give_different_capacities():
    from slipsurface.pile.engine import analyse
    bored = analyse(project.default_config("bored")).results
    driven = analyse(project.default_config("driven")).results
    assert driven["Qs"] > bored["Qs"]          # K/K0 1.4 against 1.0 in the sand


def test_reports_are_always_pdf(tmp_path):
    from slipsurface.pile import report
    from slipsurface.pile.socket import analyse_socket
    socket = analyse_socket(project.default_config("socket"))
    report.export_report(str(tmp_path / "r"), None, "en", socket=socket)
    assert (tmp_path / "r.pdf").read_bytes()[:5] == b"%PDF-"
    report.export_report(str(tmp_path / "s.html"), None, "en", socket=socket)
    assert (tmp_path / "s.html.pdf").read_bytes()[:5] == b"%PDF-"
