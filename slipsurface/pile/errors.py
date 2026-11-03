"""The one exception the analyses raise for input they cannot work with."""

from __future__ import annotations

from typing import Any, Dict, Tuple


class PileError(ValueError):
    """An input the analysis cannot work with; `key` names the message."""

    def __init__(self, key: str, **params):
        self.key = key
        self.params = params
        from .i18n import TRANSLATIONS
        super().__init__(TRANSLATIONS["en"].get(key, key).format(**params))


def message(key: str, **params) -> Tuple[str, Dict[str, Any]]:
    """A warning as the analyses record it: (translation key, parameters)."""
    return key, params


def num(d: dict, key: str, default: float) -> float:
    """A number from a configuration section; missing or empty gives the default."""
    value = d.get(key, default)
    if value is None or value == "":
        return float(default)
    return float(value)
