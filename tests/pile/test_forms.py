"""
The input schema and its readers, which the interface and the project files
both depend on.
"""
from slipsurface.pile import forms
from slipsurface.pile.config import DEFAULT_CONFIG
from slipsurface.pile.i18n import TRANSLATIONS


def test_every_default_value_has_a_field():
    values = forms.defaults()
    assert values["D"] == DEFAULT_CONFIG["pile"]["D"]
    assert values["Q"] == DEFAULT_CONFIG["loading"]["Q"]
    assert values["socket_D"] == DEFAULT_CONFIG["socket"]["D"]
    assert values["socket_Q"] == DEFAULT_CONFIG["socket"]["Q"]
    assert values["soil_profile"] == DEFAULT_CONFIG["soil_profile"]


def test_the_defaults_turn_back_into_the_default_configuration():
    cfg = forms.to_config(forms.defaults())
    for section in ("pile", "loading", "group", "groundwater", "options", "settlement",
                    "criteria", "socket"):
        assert cfg[section] == DEFAULT_CONFIG[section], section


def test_a_project_file_round_trips():
    values = forms.defaults()
    values.update(D=1.2, shape="square", nx=4, clay_method="beta", tip_method="janbu",
                  socket_Ls=5.5, design="carter_kulhawy", base_design="none",
                  critical_depth=False)
    values["study_variables"] = [{"path": "loading.Q", "mode": "range", "min": 1, "max": 2}]
    back = forms.from_config(forms.project_file(values))
    for key, value in values.items():
        assert back[key] == value, key


def test_a_file_missing_entries_keeps_the_defaults():
    back = forms.from_config({"pile": {"D": 1.5}})
    assert back["D"] == 1.5
    assert back["L"] == DEFAULT_CONFIG["pile"]["L"]


def test_unknown_choices_fall_back_to_the_default():
    cfg = forms.to_config({**forms.defaults(), "clay_method": "nonsense", "shape": "hexagon"})
    assert cfg["options"]["clay_method"] == DEFAULT_CONFIG["options"]["clay_method"]
    assert cfg["pile"]["shape"] == DEFAULT_CONFIG["pile"]["shape"]


def test_the_pile_count_is_a_whole_number():
    cfg = forms.to_config({**forms.defaults(), "nx": 3.4})
    assert cfg["group"]["nx"] == 3


def test_rows_without_a_thickness_are_dropped():
    values = forms.defaults()
    values["soil_profile"] = values["soil_profile"] + [{"name": "x", "thickness": None}]
    assert len(forms.read_soil_profile(values)) == len(DEFAULT_CONFIG["soil_profile"])


def test_every_label_exists_in_both_languages():
    for lang in ("en", "tr"):
        schema = forms.schema(lang)
        for part in forms.PARTS:
            for group in schema[part]["groups"]:
                assert group["title"] and group["title"] not in TRANSLATIONS[lang]
                for field in group["fields"]:
                    assert field["label"] and not field["label"].endswith("_label"), \
                        field["key"]
                    for option in field.get("options", []):
                        assert "_" not in option["label"] or " " in option["label"], option
        for column in schema["soil"]["columns"]:
            assert not column["label"].startswith("col_")


def test_every_condition_names_a_field_that_exists():
    keys = set(forms.defaults())
    schema = forms.schema()
    for part in forms.PARTS:
        for group in schema[part]["groups"]:
            for item in [group] + group["fields"]:
                for condition in item.get("when", []):
                    assert condition["key"] in keys, condition


def test_the_study_may_vary_every_layer_and_the_load():
    choices = forms.variable_choices(forms.defaults())
    paths = {choice["value"] for choice in choices}
    assert "loading.Q" in paths and "pile.L" in paths and "group.sx" in paths
    assert "soil_profile.1.cu" in paths
    assert all(isinstance(choice["base"], float) for choice in choices)


def test_a_single_pile_offers_no_spacing():
    values = {**forms.defaults(), "nx": 1, "ny": 1}
    paths = {choice["value"] for choice in forms.variable_choices(values)}
    assert "group.sx" not in paths and "group.sy" not in paths
