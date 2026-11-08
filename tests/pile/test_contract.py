"""
Contract tests between the forms and i18n layers and the engine.

These pin bugs once shipped: soil rows that never reached the engine (table
name vs values key) and translation placeholders that collide with t()'s own
parameters.
"""
import re

from slipsurface.pile import forms
from slipsurface.pile.i18n import ENTRIES, TRANSLATIONS


def test_the_texts_are_english_only():
    assert list(TRANSLATIONS) == ["en"]
    assert set(TRANSLATIONS["en"]) == set(ENTRIES)


def test_no_translation_placeholder_collides_with_t_parameters():
    # t(lang, key, **params): a {lang} or {key} placeholder cannot be formatted
    reserved = {"lang", "key"}
    for name, text in ENTRIES.items():
        fields = set(re.findall(r"\{(\w+)", text))
        assert not fields & reserved, f"{name}: {fields & reserved}"


def test_edited_soil_rows_reach_the_engine():
    # Regression: the dialog once wrote "soil" while to_config reads "soil_profile"
    values = forms.defaults()
    values["soil_profile"] = [{**values["soil_profile"][0], "name": "Edited", "thickness": 7.5}]
    cfg = forms.to_config(values)
    assert cfg["soil_profile"][0]["name"] == "Edited"
    assert cfg["soil_profile"][0]["thickness"] == 7.5
