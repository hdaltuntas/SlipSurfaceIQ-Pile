"""The configuration of an analysis.

The analysis takes one nested configuration dictionary: ``pile``, ``loading``,
``group``, ``groundwater``, ``soil_profile``, ``options``, ``settlement``,
``seismic``, ``criteria``, ``socket``, ``project_info`` and ``pile_type``
(see `config.DEFAULT_CONFIG` for every key and its default).

    default_config(pile_type)   a complete starter configuration
    normalize(cfg)              complete missing keys and validate supplied
                                values; invalid input is never silently replaced

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
import math
from typing import Any, Dict, List, Optional

from .errors import PileError

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


def _invalid(field: str, reason: str):
    raise PileError("err_config", field=field, reason=reason)


def pile_type_of(value) -> str:
    """Resolve an omitted type to bored; reject an unknown supplied type."""
    if value is None:
        return "bored"
    if value not in PILE_TYPES:
        _invalid("pile_type", f"must be one of {', '.join(PILE_TYPES)}")
    return value


def default_config(pile_type: str = "bored") -> Dict[str, Any]:
    """A complete starter configuration of the pile type."""
    cfg = normalize({"pile_type": pile_type_of(pile_type)})
    cfg["project_info"]["title"] = DEFAULT_TITLES[cfg["pile_type"]]
    return cfg


def _number(value, field: str, integer: bool = False):
    if isinstance(value, bool) or value is None:
        _invalid(field, "must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        _invalid(field, "must be a finite number")
    if not math.isfinite(number):
        _invalid(field, "must be finite")
    if integer and not number.is_integer():
        _invalid(field, "must be a whole number")
    return int(number) if integer else number


def _boolean(value, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    _invalid(field, "must be true or false")


def _value(key: str, value, default, field: str):
    if isinstance(default, bool):
        return _boolean(value, field)
    if isinstance(default, str):
        if not isinstance(value, str):
            _invalid(field, "must be text")
        allowed = _ALLOWED.get(key)
        if allowed is not None and value not in allowed:
            _invalid(field, f"must be one of {', '.join(allowed)}")
        return value
    if field == "groundwater.depth" and value is None:
        return None  # explicit dry assumption, never the example water table
    return _number(value, field, key in _INTEGERS)


def _soil_profile(rows, field="soil_profile") -> List[dict]:
    """Keep every supplied layer, or reject it with its exact field name."""
    if not isinstance(rows, (list, tuple)) or not rows:
        _invalid(field, "must contain at least one layer")
    base = DEFAULT_CONFIG["soil_profile"][0]
    layers = []
    for index, row in enumerate(rows):
        path = f"{field}[{index}]"
        if not isinstance(row, dict):
            _invalid(path, "must be a layer object")
        extra = set(row) - set(base)
        if extra:
            _invalid(path, f"unknown field(s): {', '.join(sorted(extra))}")
        if "thickness" not in row:
            _invalid(f"{path}.thickness", "is required")
        behaviour = row.get("behaviour", "granular")
        if behaviour not in BEHAVIOURS:
            _invalid(f"{path}.behaviour", "must be granular or cohesive")
        name = row.get("name", "Layer")
        if not isinstance(name, str) or not name.strip():
            _invalid(f"{path}.name", "must be nonempty text")
        layer = {"name": name.strip(), "behaviour": behaviour}
        for key in SOIL_NUMBERS:
            layer[key] = _number(row.get(key, base[key]), f"{path}.{key}")
        if layer["thickness"] <= 0:
            _invalid(f"{path}.thickness", "must be greater than zero")
        for key in ("N60", "cu", "Cc", "Cr", "e0"):
            if layer[key] < 0:
                _invalid(f"{path}.{key}", "cannot be negative")
        if layer["OCR"] < 1:
            _invalid(f"{path}.OCR", "must be at least 1")
        if layer["Cr"] > layer["Cc"] and layer["Cc"] > 0:
            _invalid(f"{path}.Cr", "cannot exceed Cc")
        layers.append(layer)
    return layers


def _range(out: dict, section: str, key: str, low: float,
           high: Optional[float] = None, *, open_low: bool = False,
           open_high: bool = False) -> None:
    value = out[section][key]
    if value < low or (open_low and value == low) or (high is not None and
            (value > high or (open_high and value == high))):
        bounds = f"{'greater than' if open_low else 'at least'} {low:g}"
        if high is not None:
            bounds += f" and {'less than' if open_high else 'at most'} {high:g}"
        _invalid(f"{section}.{key}", f"must be {bounds}")


def _validate_options(out: dict) -> None:
    """Reject values the old readers silently clamped to another problem."""
    for section, key in (("options", "K_ratio"), ("options", "sladen_C"),
                         ("socket", "aperture"), ("socket", "weak_rock"),
                         ("socket", "min_ratio")):
        _range(out, section, key, 0)
    for section, key in (("options", "delta_ratio"), ("settlement", "raft_fraction"),
                         ("seismic", "tension_sand"), ("seismic", "tension_clay"),
                         ("seismic", "cyclic"), ("socket", "D_blast")):
        _range(out, section, key, 0, 1)
    for section, key in (("seismic", "FS_compression"), ("seismic", "FS_tension"),
                         ("criteria", "FS"), ("socket", "FS_side"),
                         ("socket", "FS_base"), ("options", "zc_ratio"),
                         ("socket", "mi")):
        _range(out, section, key, 1)
    for section, key in (("criteria", "s_allow"), ("criteria", "L_min"),
                         ("criteria", "L_step"), ("settlement", "spread"),
                         ("groundwater", "gamma_water"), ("socket", "Eb_ratio"),
                         ("socket", "spacing"), ("socket", "gamma_c")):
        _range(out, section, key, 0, open_low=True)
    _range(out, "options", "janbu_eta", 60, 105)
    _range(out, "socket", "RQD", 0, 100)
    _range(out, "socket", "GSI", 5, 100)
    if out["groundwater"]["depth"] is not None:
        _range(out, "groundwater", "depth", 0)


# Rock properties may vary by log; geometry, loads and design choices are shared.
BOREHOLE_SOCKET_KEYS = {"rock_depth", "qu", "RQD", "Ei", "modulus_method", "Em", "GSI",
                       "mi", "D_blast", "nu_r", "Eb_ratio", "spacing", "aperture"}


def normalize(cfg: Optional[dict] = None) -> Dict[str, Any]:
    """A complete, checked configuration from a partial one.

    Missing keys use the starter defaults. Supplied invalid enums, nonfinite
    numbers, fractional pile counts, empty profiles and unknown fields raise
    PileError (a ValueError). groundwater.depth=None explicitly assumes dry
    ground. Optional boreholes preserve separate soil/water/rock profiles.
    """
    cfg = {} if cfg is None else cfg
    if not isinstance(cfg, dict):
        _invalid("config", "must be an object")
    extra = set(cfg) - set(DEFAULT_CONFIG) - {"pile_type", "boreholes"}
    if extra:
        _invalid("config", f"unknown field(s): {', '.join(sorted(extra))}")
    out = copy.deepcopy(DEFAULT_CONFIG)
    for section, defaults in DEFAULT_CONFIG.items():
        if not isinstance(defaults, dict):
            continue
        given = cfg.get(section, {})
        if not isinstance(given, dict):
            _invalid(section, "must be an object")
        extra = set(given) - set(defaults)
        if extra:
            _invalid(section, f"unknown field(s): {', '.join(sorted(extra))}")
        for key, default in defaults.items():
            out[section][key] = _value(key, given.get(key, default), default,
                                       f"{section}.{key}")
    out["soil_profile"] = _soil_profile(cfg.get("soil_profile", out["soil_profile"]))
    inferred = "driven" if out["pile"]["installation"] in DRIVEN_INSTALLATIONS else "bored"
    out["pile_type"] = pile_type_of(cfg.get("pile_type", inferred))
    supplied_installation = "installation" in cfg.get("pile", {})
    if out["pile_type"] == "driven" and not supplied_installation:
        out["pile"]["installation"] = "driven_high"
    elif out["pile_type"] == "bored" and out["pile"]["installation"] != "bored":
        _invalid("pile.installation", "must be bored for pile_type=bored")
    elif out["pile_type"] == "driven" and out["pile"]["installation"] == "bored":
        _invalid("pile.installation", "must be driven_high or driven_low for pile_type=driven")
    _validate_options(out)
    if "boreholes" in cfg:
        logs = cfg["boreholes"]
        if not isinstance(logs, (list, tuple)) or not logs:
            _invalid("boreholes", "must contain at least one log")
        out["boreholes"] = []
        seen = set()
        for index, log in enumerate(logs):
            path = f"boreholes[{index}]"
            if not isinstance(log, dict):
                _invalid(path, "must be an object")
            extra = set(log) - {"name", "soil_profile", "groundwater", "socket"}
            if extra:
                _invalid(path, f"unknown field(s): {', '.join(sorted(extra))}")
            name = log.get("name", f"BH-{index + 1}")
            if not isinstance(name, str) or not name.strip() or name.strip() in seen:
                _invalid(f"{path}.name", "must be nonempty and unique")
            name = name.strip()
            seen.add(name)
            if "soil_profile" not in log:
                _invalid(f"{path}.soil_profile", "is required")
            child = {k: copy.deepcopy(v) for k, v in out.items() if k != "boreholes"}
            child["soil_profile"] = _soil_profile(log["soil_profile"], f"{path}.soil_profile")
            for section in ("groundwater", "socket"):
                if section in log:
                    if not isinstance(log[section], dict):
                        _invalid(f"{path}.{section}", "must be an object")
                    if section == "socket" and set(log[section]) - BOREHOLE_SOCKET_KEYS:
                        _invalid(f"{path}.socket", "only log-specific rock properties may vary")
                    child[section].update(log[section])
            try:
                child = normalize(child)
            except PileError as exc:
                _invalid(path, str(exc))
            cleaned = {"name": name, "soil_profile": child["soil_profile"],
                       "groundwater": child["groundwater"]}
            if "socket" in log:
                cleaned["socket"] = {k: child["socket"][k] for k in log["socket"]}
            out["boreholes"].append(cleaned)
    return out
