"""The texts of the program: every placeholder formats."""
import re

from slipsurface.pile.texts import TEXTS, text


def test_no_placeholder_collides_with_the_key_parameter():
    # text(key, **params): a {key} placeholder could not be formatted
    for name, value in TEXTS.items():
        assert "key" not in set(re.findall(r"\{(\w+)", value)), name


def test_an_unknown_key_reads_as_itself():
    assert text("no_such_text") == "no_such_text"
