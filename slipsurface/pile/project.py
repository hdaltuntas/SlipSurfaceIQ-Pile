"""The configuration of an analysis.

The analysis takes one nested configuration dictionary: ``pile``, ``loading``,
``group``, ``groundwater``, ``soil_profile``, ``options``, ``settlement``,
``seismic``, ``criteria``, ``socket``, ``project_info`` and ``pile_type``
(see `config.DEFAULT_CONFIG` for every key and its default).

    default_config(pile_type)   a complete starter configuration
    normalize(cfg)              a partial configuration made complete and
                                checked: missing keys take their default,
                                unknown choices fall back to the default

The pile type decides which analysis runs:

    bored   a bored (cast-in-place) pile, or a group of them, in a layered soil
            profile: axial capacity, group action, settlement, seismic
    driven  the same analysis for a driven pile; its installation (high or low
            displacement) sets the earth pressure along the shaft
    socket  a pile socketed into rock: side shear, base, socket length and
            settlement of the socket
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from .config import (
    BEHAVIOURS,
    CLAY_METHODS,
    DEFAULT_CONFIG,
    EFFICIENCY_METHODS,
    GROUP_SETTLEMENT,
    INSTALLATIONS,
    MODULUS_METHODS,
    OVERBURDEN_FRICTION,
    SHAPES,
    SKIN_DISTRIBUTIONS,
    SOCKET_BASE_DESIGN,
    SOCKET_DESIGN,
    TIP_METHODS,
)

PILE_TYPES = ["bored", "driven", "socket"]

#: How a driven pile can be installed; the first is the default
DRIVEN_INSTALLATIONS = ["driven_high", "driven_low"]

#: The project title a new configuration of each type starts with
DEFAULT_TITLES = {
    "bored": DEFAULT_CONFIG["project_info"]["title"],
    "driven": "Project: Driven pile group in layered ground",
    "socket": "Project: Rock-socketed pile",
}

#: The choices each text input must stay within
_ALLOWED = {
    "shape": SHAPES, "installation": INSTALLATIONS, "efficiency": EFFICIENCY_METHODS,
    "clay_method": CLAY_METHODS, "tip_method": TIP_METHODS, "group_method": GROUP_SETTLEMENT,
    "distribution": SKIN_DISTRIBUTIONS, "modulus_method": MODULUS_METHODS,
    "design": SOCKET_DESIGN, "base_design": SOCKET_BASE_DESIGN,
    "overburden_friction": OVERBURDEN_FRICTION,
}

#: Inputs that are whole numbers
_INTEGERS = {"nx", "ny"}

#: The numbers of a soil layer
SOIL_NUMBERS = ["thickness", "gamma", "gamma_sat", "phi", "cu", "OCR", "N60", "E", "nu",
                "Cc", "Cr", "e0"]


def pile_type_of(value) -> str:
    """The pile type named by `value`; unknown is bored."""
    text = str(value or "")
    return text if text in PILE_TYPES else PILE_TYPES[0]


def default_config(pile_type: str = "bored") -> Dict[str, Any]:
    """A complete starter configuration of the pile type."""
    cfg = normalize({"pile_type": pile_type_of(pile_type)})
    cfg["project_info"]["title"] = DEFAULT_TITLES[cfg["pile_type"]]
    return cfg


def _number(value, default, integer: bool):
    number = float(default if value is None or value == "" else value)
    return int(round(number)) if integer else number


def _text(value, default: str, allowed: Optional[List[str]]) -> str:
    text = str(default if value is None or value == "" else value)
    return text if allowed is None or text in allowed else default


def _value(key: str, value, default):
    if isinstance(default, bool):
        return bool(default if value is None or value == "" else value)
    if isinstance(default, str):
        if key == "analyst":
            return str(value or "")
        return _text(value, default, _ALLOWED.get(key))
    return _number(value, default, key in _INTEGERS)


def _soil_profile(rows) -> List[dict]:
    """Soil layers; rows without a usable thickness are dropped."""
    base = DEFAULT_CONFIG["soil_profile"][0]
    layers = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        try:
            thickness = float(row.get("thickness"))
        except (TypeError, ValueError):
            continue
        if thickness <= 0:
            continue
        layer = {"name": str(row.get("name") or "").strip() or "Layer",
                 "behaviour": _text(row.get("behaviour"), "granular", BEHAVIOURS)}
        for key in SOIL_NUMBERS:
            layer[key] = _number(row.get(key), base[key], False)
        layer["thickness"] = thickness
        layers.append(layer)
    return layers


def normalize(cfg: Optional[dict] = None) -> Dict[str, Any]:
    """A complete, checked configuration from a partial one.

    Every section and key of `config.DEFAULT_CONFIG` is present; a missing or
    empty value takes its default, a choice outside its list falls back to
    the default, and numbers are numbers. Raises ValueError on a value that
    cannot be read as a number.
    """
    cfg = cfg or {}
    out = copy.deepcopy(DEFAULT_CONFIG)
    for section, defaults in DEFAULT_CONFIG.items():
        if not isinstance(defaults, dict):
            continue
        given = cfg.get(section)
        given = given if isinstance(given, dict) else {}
        for key, default in defaults.items():
            out[section][key] = _value(key, given.get(key), default)
    if cfg.get("soil_profile"):
        layer_defaults = DEFAULT_CONFIG["soil_profile"][0]
        out["soil_profile"] = _soil_profile(
            {**layer_defaults, **row} for row in cfg["soil_profile"] if isinstance(row, dict))
    out["pile_type"] = pile_type_of(cfg.get("pile_type"))
    if out["pile_type"] == "bored":
        # the installation follows the type: a bored pile is bored
        out["pile"]["installation"] = "bored"
    elif out["pile"]["installation"] not in DRIVEN_INSTALLATIONS:
        out["pile"]["installation"] = DRIVEN_INSTALLATIONS[0]
    return out
