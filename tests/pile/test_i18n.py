"""The texts of the program: English only, and every placeholder formats."""
import re

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
