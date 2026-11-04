"""
Contract tests between the desktop interface and the forms/i18n layers.

These pin the bugs the GUI once shipped with: soil-table edits that never
reached the engine (table name vs values key), duplicate method definitions,
and translation placeholders that collide with t()'s own parameters.
"""
import ast
import re
from pathlib import Path

from slipsurface.pile import forms
from slipsurface.pile.i18n import ENTRIES, TRANSLATIONS, t

UI_DIR = Path(__file__).resolve().parents[2] / "slipsurface" / "ui"


def test_translations_have_identical_keys_in_both_languages():
    assert set(TRANSLATIONS["en"]) == set(TRANSLATIONS["tr"])
    assert set(TRANSLATIONS["en"]) == set(ENTRIES)


def test_no_translation_placeholder_collides_with_t_parameters():
    # t(lang, key, **params): a {lang} or {key} placeholder cannot be formatted
    reserved = {"lang", "key"}
    for name, (en, tr) in ENTRIES.items():
        for text in (en, tr):
            fields = set(re.findall(r"\{(\w+)", text))
            assert not fields & reserved, f"{name}: {fields & reserved}"


def test_ui_language_message_formats_without_collision():
    assert t("en", "ui_language", code="tr") == "Language: tr"
    assert t("tr", "ui_language", code="en") == "Dil: en"


def _table_value_keys():
    # Read the mapping from source so the test needs no Qt import
    tree = ast.parse((UI_DIR / "data_entry.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(tg, ast.Name) and tg.id == "TABLE_VALUE_KEYS" for tg in node.targets):
            return {k.value: v.value for k, v in zip(node.value.keys, node.value.values)}
    raise AssertionError("TABLE_VALUE_KEYS not found in data_entry.py")


def test_dialog_tables_map_to_real_value_keys():
    TABLE_VALUE_KEYS = _table_value_keys()
    defaults = forms.defaults()
    for table, value_key in TABLE_VALUE_KEYS.items():
        assert value_key in defaults, f"{table} -> {value_key} is not a values key"
    for table in ("soil", "study_vars"):
        assert table in TABLE_VALUE_KEYS, f"schema table {table} has no mapping"
        assert table in forms.schema(), f"schema table {table} missing"


def test_edited_soil_rows_reach_the_engine():
    # Regression: the dialog once wrote "soil" while to_config reads "soil_profile"
    values = forms.defaults()
    values["soil_profile"] = [{**values["soil_profile"][0], "name": "Edited", "thickness": 7.5}]
    cfg = forms.to_config(values)
    assert cfg["soil_profile"][0]["name"] == "Edited"
    assert cfg["soil_profile"][0]["thickness"] == 7.5


def test_window_class_has_no_duplicate_methods():
    # Regression: run_analysis / open_interpret were once defined twice
    tree = ast.parse((UI_DIR / "app.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "PileWindow":
            names = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            assert len(names) == len(set(names)), f"duplicate methods: {names}"
            return
    raise AssertionError("PileWindow not found in app.py")
