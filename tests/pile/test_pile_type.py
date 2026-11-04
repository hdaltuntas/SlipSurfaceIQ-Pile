"""
The pile type is chosen first and decides the inputs and the outputs: these
pin that it survives a save, that the schema shows each type its own inputs,
and that a nested project file is read in full by the command line.
"""
import json

from slipsurface.pile import forms


def test_the_pile_type_round_trips_through_a_project_file():
    for pile_type in forms.PILE_TYPES:
        values = {**forms.defaults(), "pile_type": pile_type}
        saved = json.loads(json.dumps(forms.project_file(values)))
        assert saved["pile_type"] == pile_type
        assert forms.from_config(saved)["pile_type"] == pile_type


def test_old_and_unknown_pile_types_read_as_bored():
    assert forms.pile_type_of("soil") == "bored"
    assert forms.pile_type_of(None) == "bored"
    assert forms.pile_type_of("nonsense") == "bored"
    assert forms.from_config({"pile_type": "soil"})["pile_type"] == "bored"


def test_a_bored_pile_is_installed_as_bored():
    cfg = forms.to_config({**forms.defaults(), "installation": "driven_high"})
    assert cfg["pile"]["installation"] == "bored"


def _visible_fields(pile_type):
    schema = forms.schema()
    keys = set()
    for part in forms.PARTS:
        if pile_type not in forms.PART_TYPES.get(part, [pile_type]):
            continue
        for group in schema[part]["groups"]:
            if any(c["key"] == "pile_type" and pile_type not in c["in"]
                   for c in group.get("when", [])):
                continue
            keys.update(f["key"] for f in group["fields"])
    return keys


def test_each_pile_type_sees_only_its_own_inputs():
    bored, socket = _visible_fields("bored"), _visible_fields("socket")
    assert {"D", "L", "Q", "nx", "clay_method", "study_n"} <= bored
    assert not {"socket_D", "qu", "fc"} & bored
    assert {"socket_D", "socket_Ls", "rock_depth", "qu", "fc", "design"} <= socket
    assert not {"D", "L", "Q", "nx", "clay_method", "study_n"} & socket
    # site data applies to both
    assert {"water_depth", "title"} <= bored & socket
    assert forms.PART_TYPES["soil"] == ["bored", "driven"]


def test_zero_lower_bounds_reach_the_interface():
    fields = {f["key"]: f for g in forms.schema()["pile"]["groups"] for f in g["fields"]}
    assert fields["top"]["min"] == 0
    assert fields["D"]["unit"] == "m"


def test_the_command_line_reads_every_section_of_a_nested_file(tmp_path):
    import main
    data = forms.project_file(forms.defaults())
    data["pile"]["D"] = 1.5
    data["loading"]["Q"] = 1234.0
    path = tmp_path / "p.pile.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    cfg = main._load_config(str(path))
    assert cfg["pile"]["D"] == 1.5
    assert cfg["loading"]["Q"] == 1234.0


def test_a_default_title_follows_the_pile_type_but_a_users_title_stays():
    assert "Rock-socketed" in forms.default_title("socket")
    assert forms.default_title("socket", forms.DEFAULT_TITLES["bored"]) == \
        forms.DEFAULT_TITLES["socket"]
    assert forms.default_title("socket", "Bridge pier P3") == "Bridge pier P3"


def test_reports_are_always_pdf(tmp_path):
    from slipsurface.pile import report
    from slipsurface.pile.socket import analyse_socket
    socket = analyse_socket(forms.to_config({**forms.defaults(), "pile_type": "socket"}))
    report.export_report(str(tmp_path / "r"), None, "en", socket=socket)
    assert (tmp_path / "r.pdf").read_bytes()[:5] == b"%PDF-"
    report.export_report(str(tmp_path / "s.html"), None, "en", socket=socket)
    assert (tmp_path / "s.html.pdf").read_bytes()[:5] == b"%PDF-"
    assert not hasattr(report, "export_html")


def test_a_driven_pile_has_the_soil_inputs_and_its_installation():
    driven, bored = _visible_fields("driven"), _visible_fields("bored")
    assert driven >= {"D", "L", "Q", "nx", "clay_method", "study_n"}
    fields = {f["key"]: f for g in forms.schema()["pile"]["groups"] for f in g["fields"]}
    assert fields["installation"]["when"] == [{"key": "pile_type", "in": ["driven"]}]
    assert {o["value"] for o in fields["installation"]["options"]} == \
        {"driven_low", "driven_high"}


def test_a_driven_pile_is_installed_by_driving():
    cfg = forms.to_config({**forms.defaults(), "pile_type": "driven"})
    assert cfg["pile"]["installation"] == "driven_high"
    cfg = forms.to_config({**forms.defaults(), "pile_type": "driven",
                           "installation": "driven_low"})
    assert cfg["pile"]["installation"] == "driven_low"
    cfg = forms.to_config({**forms.defaults(), "pile_type": "driven", "installation": "bored"})
    assert cfg["pile"]["installation"] == "driven_high"


def test_older_files_installed_by_driving_open_as_driven():
    assert forms.from_config({"pile": {"installation": "driven_low"}})["pile_type"] == "driven"
    old = {"pile_type": "soil", "pile": {"installation": "driven_high"}}
    assert forms.from_config(old)["pile_type"] == "driven"
    # a file that names its type keeps it
    assert forms.from_config({"pile_type": "bored",
                              "pile": {"installation": "bored"}})["pile_type"] == "bored"


def test_driven_and_bored_give_different_capacities():
    from slipsurface.pile.engine import analyse
    bored = analyse(forms.to_config({**forms.defaults(), "pile_type": "bored"})).results
    driven = analyse(forms.to_config({**forms.defaults(), "pile_type": "driven"})).results
    assert driven["Qs"] > bored["Qs"]          # K/K0 1.4 against 1.0 in the sand
