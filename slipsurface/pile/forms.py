"""
Input schema and readers for SlipSurface IQ Pile.

Every input of the program is declared here once: key, bilingual label, unit,
range and default. The browser builds its forms from this schema, and the
server turns the values that come back into the nested configuration
dictionary the analysis core expects. Labels therefore exist in one place
only, and there is no second copy to keep in step.

The flat field keys (``D``, ``water_depth``, ``socket_Ls`` …) are the ones the
interface uses; the nested keys of the configuration (``pile.D``,
``groundwater.depth``, ``socket.Ls`` …) are the ones the engine and the
``.pile`` project files use. `to_config()` and `from_config()` convert
between the two.

A field can declare when it applies — ``when=[("tip_method", ["janbu"])]`` —
and the browser hides it whenever the condition does not hold, so the form
shows the inputs of the method that is actually running and no others.

This module depends on neither HTTP nor the interface, and is tested directly.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .config import (
    BEHAVIOURS,
    CLAY_METHODS,
    DEFAULT_CONFIG,
    EFFICIENCY_METHODS,
    GROUP_SETTLEMENT,
    INSTALLATIONS,
    MODULUS_METHODS,
    SHAPES,
    SKIN_DISTRIBUTIONS,
    SOCKET_BASE_DESIGN,
    SOCKET_DESIGN,
    TIP_METHODS,
)
from .i18n import TRANSLATIONS

#: Name and version written into project files
FILE_FORMAT = "slipsurface-pile"
# Project files saved before the product was renamed still open.
READ_FORMATS = (FILE_FORMAT, "slipsurface-pile")
FILE_VERSION = "0.1"


def _t(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)


# --------------------------------------------------------------------------- #
#  Schema data structures
# --------------------------------------------------------------------------- #

@dataclass
class Field:
    """One input field."""
    key: str
    label: str
    kind: str = "number"                     # number | text | check | select
    default: Any = 0.0
    unit: str = ""
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    decimals: int = 2
    options: List[Dict[str, str]] = field(default_factory=list)
    when: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Only what the browser needs; empty values are left out."""
        keep = ("key", "label", "kind", "default", "decimals")
        return {k: v for k, v in asdict(self).items()
                if k in keep or v not in ("", None, [], 0.0)}


@dataclass
class Group:
    """A titled set of fields."""
    title: str
    fields: List[Field]
    note: str = ""
    when: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"title": self.title, "fields": [f.to_dict() for f in self.fields]}
        if self.note:
            d["note"] = self.note
        if self.when:
            d["when"] = list(self.when)
        return d


def _num(key, label, default, lo=None, hi=None, unit="", dec=2, step=None, when=None):
    return Field(key, label, "number", default, unit, lo, hi, step, dec,
                 when=_when(when))


def _check(key, label, default=False, when=None):
    return Field(key, label, "check", default, when=_when(when))


def _select(key, label, default, options, when=None):
    return Field(key, label, "select", default,
                 options=[{"value": v, "label": t} for v, t in options], when=_when(when))


def _text(key, label, default=""):
    return Field(key, label, "text", default)


def _when(conditions) -> List[Dict[str, Any]]:
    """``[("key", ["a", "b"])]`` as the browser reads it."""
    if not conditions:
        return []
    return [{"key": key, "in": list(values)} for key, values in conditions]


def _choices(lang: str, prefix: str, values: List[str]):
    return [(value, _t(lang, f"{prefix}_{value}")) for value in values]


def design_choices(lang: str) -> list:
    """The design side shear: a statistic, or one correlation by name."""
    return [(key, _t(lang, f"design_{key}") if key in ("mean", "median", "lower", "upper")
             else _t(lang, f"side_{key}")) for key in SOCKET_DESIGN]


def base_design_choices(lang: str) -> list:
    return [(key, _t(lang, f"base_design_{key}") if key in ("none", "min", "mean")
             else _t(lang, f"base_{key}")) for key in SOCKET_BASE_DESIGN]


# --------------------------------------------------------------------------- #
#  Input groups
# --------------------------------------------------------------------------- #

def project_groups(lang: str = "en") -> List[Group]:
    info = DEFAULT_CONFIG["project_info"]
    return [Group(_t(lang, "group_project"), [
        _text("title", _t(lang, "title_label"), info["title"]),
        _text("analyst", _t(lang, "analyst_label"), info["analyst"]),
    ])]


def pile_groups(lang: str = "en") -> List[Group]:
    p = DEFAULT_CONFIG["pile"]
    g = DEFAULT_CONFIG["group"]
    w = DEFAULT_CONFIG["groundwater"]
    return [
        Group(_t(lang, "group_pile"), [
            _select("shape", _t(lang, "shape_label"), p["shape"],
                    _choices(lang, "shape", SHAPES)),
            _num("D", _t(lang, "D_label"), p["D"], 0.1, 5, "m", 2, 0.05),
            _num("L", _t(lang, "L_label"), p["L"], 0.5, 200, "m", 2, 0.5),
            _num("top", _t(lang, "top_label"), p["top"], 0, 50, "m", 2, 0.1),
            _select("installation", _t(lang, "installation_label"), p["installation"],
                    _choices(lang, "installation", INSTALLATIONS)),
            _num("gamma_p", _t(lang, "gamma_p_label"), p["gamma_p"], 1, 100, "kN/m³", 1, 0.5),
            _num("Ep", _t(lang, "Ep_label"), p["Ep"], 100, 300000, "MPa", 0, 1000),
        ], note=_t(lang, "pile_note")),
        Group(_t(lang, "group_loading"), [
            _num("Q", _t(lang, "Q_label"), DEFAULT_CONFIG["loading"]["Q"], 1, 1e7, "kN", 1, 100),
        ], note=_t(lang, "loading_note")),
        Group(_t(lang, "group_group"), [
            _num("nx", _t(lang, "nx_label"), g["nx"], 1, 50, "", 0, 1),
            _num("ny", _t(lang, "ny_label"), g["ny"], 1, 50, "", 0, 1),
            _num("sx", _t(lang, "sx_label"), g["sx"], 0.1, 50, "m", 2, 0.1),
            _num("sy", _t(lang, "sy_label"), g["sy"], 0.1, 50, "m", 2, 0.1),
            _select("efficiency", _t(lang, "efficiency_label"), g["efficiency"],
                    _choices(lang, "eff", EFFICIENCY_METHODS)),
            _check("block", _t(lang, "block_label"), g["block"]),
        ], note=_t(lang, "group_note")),
        Group(_t(lang, "group_water"), [
            _num("water_depth", _t(lang, "water_depth_label"), w["depth"], 0, 500, "m", 2, 0.1),
            _num("gamma_water", _t(lang, "gamma_w_label"), w["gamma_water"], 9, 11,
                 "kN/m³", 2, 0.01),
        ]),
    ]


def option_groups(lang: str = "en") -> List[Group]:
    o = DEFAULT_CONFIG["options"]
    s = DEFAULT_CONFIG["settlement"]
    c = DEFAULT_CONFIG["criteria"]
    return [
        Group(_t(lang, "group_methods"), [
            _select("clay_method", _t(lang, "clay_method_label"), o["clay_method"],
                    _choices(lang, "method", CLAY_METHODS)),
            _num("sladen_C", _t(lang, "sladen_C_label"), o["sladen_C"], 0, 1, "", 2, 0.05,
                 when=[("clay_method", ["alpha_sladen"])]),
            _select("tip_method", _t(lang, "tip_method_label"), o["tip_method"],
                    _choices(lang, "method", TIP_METHODS)),
            _num("janbu_eta", _t(lang, "janbu_eta_label"), o["janbu_eta"], 60, 105, "°", 0, 5,
                 when=[("tip_method", ["janbu"])]),
            _num("K_ratio", _t(lang, "K_ratio_label"), o["K_ratio"], 0, 3, "", 2, 0.05),
            _num("delta_ratio", _t(lang, "delta_ratio_label"), o["delta_ratio"], 0, 1, "", 2,
                 0.05),
            _check("critical_depth", _t(lang, "critical_depth_label"), o["critical_depth"]),
            _num("zc_ratio", _t(lang, "zc_ratio_label"), o["zc_ratio"], 1, 50, "", 1, 1,
                 when=[("critical_depth", [True])]),
            _check("spt_method", _t(lang, "spt_method_label"), o["spt_method"]),
        ], note=_t(lang, "methods_note")),
        Group(_t(lang, "group_weight"), [
            _check("subtract_weight", _t(lang, "subtract_weight_label"), o["subtract_weight"]),
            _check("buoyant_weight", _t(lang, "buoyant_weight_label"), o["buoyant_weight"]),
        ], note=_t(lang, "weight_note")),
        Group(_t(lang, "group_settlement"), [
            _select("group_method", _t(lang, "group_method_label"), s["group_method"],
                    _choices(lang, "gs", GROUP_SETTLEMENT)),
            _num("raft_fraction", _t(lang, "raft_fraction_label"), s["raft_fraction"], 0, 1,
                 "", 3, 0.05),
            _num("spread", _t(lang, "spread_label"), s["spread"], 0.5, 10, "", 1, 0.5),
            _select("distribution", _t(lang, "distribution_label"), s["distribution"],
                    _choices(lang, "distribution", SKIN_DISTRIBUTIONS)),
        ], note=_t(lang, "settlement_note")),
        seismic_group(lang),
        Group(_t(lang, "group_criteria"), [
            _num("FS", _t(lang, "FS_label"), c["FS"], 1, 10, "", 2, 0.1),
            _num("s_allow", _t(lang, "s_allow_label"), c["s_allow"], 1, 500, "mm", 1, 5),
            _num("L_min", _t(lang, "L_min_label"), c["L_min"], 0.5, 100, "m", 2, 0.5),
            _num("L_step", _t(lang, "L_step_label"), c["L_step"], 0.05, 5, "m", 2, 0.05),
        ], note=_t(lang, "criteria_note")),
    ]


def seismic_group(lang: str = "en") -> Group:
    e = DEFAULT_CONFIG["seismic"]
    on = [("seismic_enabled", [True])]
    return Group(_t(lang, "group_seismic"), [
        _check("seismic_enabled", _t(lang, "seismic_enabled_label"), e["enabled"]),
        _num("V_E", _t(lang, "V_E_label"), e["V"], -1e7, 1e7, "kN", 1, 100, when=on),
        _num("M_B", _t(lang, "M_B_label"), e["M_B"], -1e8, 1e8, "kN·m", 1, 100, when=on),
        _num("M_L", _t(lang, "M_L_label"), e["M_L"], -1e8, 1e8, "kN·m", 1, 100, when=on),
        _num("tension_sand", _t(lang, "tension_sand_label"), e["tension_sand"], 0, 1, "", 2,
             0.05, when=on),
        _num("tension_clay", _t(lang, "tension_clay_label"), e["tension_clay"], 0, 1, "", 2,
             0.05, when=on),
        _num("cyclic", _t(lang, "cyclic_label"), e["cyclic"], 0, 1, "", 2, 0.05, when=on),
        _num("FS_E_c", _t(lang, "FS_E_c_label"), e["FS_compression"], 1, 10, "", 2, 0.1,
             when=on),
        _num("FS_E_t", _t(lang, "FS_E_t_label"), e["FS_tension"], 1, 10, "", 2, 0.1,
             when=on),
    ], note=_t(lang, "seismic_note"))


def socket_groups(lang: str = "en") -> List[Group]:
    s = DEFAULT_CONFIG["socket"]
    return [
        Group(_t(lang, "group_socket"), [
            _num("socket_D", _t(lang, "socket_D_label"), s["D"], 0.1, 6, "m", 2, 0.05),
            _num("socket_Ls", _t(lang, "socket_Ls_label"), s["Ls"], 0, 60, "m", 2, 0.25),
            _num("socket_top", _t(lang, "socket_top_label"), s["top"], 0, 50, "m", 2, 0.1),
            _num("rock_depth", _t(lang, "rock_depth_label"), s["rock_depth"], 0, 200, "m", 2,
                 0.5),
            _num("socket_Q", _t(lang, "socket_Q_label"), s["Q"], 1, 1e7, "kN", 1, 100),
        ], note=_t(lang, "socket_note")),
        Group(_t(lang, "group_rock"), [
            _num("qu", _t(lang, "qu_label"), s["qu"], 0.1, 400, "MPa", 1, 1),
            _select("modulus_method", _t(lang, "modulus_method_label"), s["modulus_method"],
                    _choices(lang, "modulus", MODULUS_METHODS)),
            _num("Ei", _t(lang, "Ei_label"), s["Ei"], 10, 200000, "MPa", 0, 500,
                 when=[("modulus_method", ["rqd", "gsi"])]),
            _num("RQD", _t(lang, "RQD_label"), s["RQD"], 0, 100, "%", 0, 5,
                 when=[("modulus_method", ["rqd"])]),
            _num("Em", _t(lang, "Em_label"), s["Em"], 10, 200000, "MPa", 0, 500,
                 when=[("modulus_method", ["direct"])]),
            _num("GSI", _t(lang, "GSI_label"), s["GSI"], 5, 100, "", 0, 5),
            _num("mi", _t(lang, "mi_label"), s["mi"], 1, 40, "", 1, 1),
            _num("D_blast", _t(lang, "D_blast_label"), s["D_blast"], 0, 1, "", 2, 0.1),
            _num("nu_r", _t(lang, "nu_r_label"), s["nu_r"], 0, 0.49, "", 2, 0.01),
            _num("Eb_ratio", _t(lang, "Eb_ratio_label"), s["Eb_ratio"], 0.01, 10, "", 2, 0.1),
            _num("spacing", _t(lang, "spacing_label"), s["spacing"], 0.01, 10, "m", 2, 0.1),
            _num("aperture", _t(lang, "aperture_label"), s["aperture"], 0, 50, "mm", 1, 0.5),
        ], note=_t(lang, "rock_note")),
        Group(_t(lang, "group_concrete"), [
            _num("fc", _t(lang, "fc_label"), s["fc"], 5, 150, "MPa", 1, 5),
            _num("Ec", _t(lang, "Ec_label"), s["Ec"], 1000, 100000, "MPa", 0, 1000),
            _num("gamma_c", _t(lang, "gamma_c_label"), s["gamma_c"], 1, 100, "kN/m³", 1, 0.5),
        ]),
        Group(_t(lang, "group_socket_design"), [
            _select("design", _t(lang, "design_label"), s["design"], design_choices(lang)),
            _select("base_design", _t(lang, "base_design_label"), s["base_design"],
                    base_design_choices(lang)),
            _num("FS_side", _t(lang, "FS_side_label"), s["FS_side"], 1, 10, "", 2, 0.1),
            _num("FS_base", _t(lang, "FS_base_label"), s["FS_base"], 1, 10, "", 2, 0.1),
            _num("min_ratio", _t(lang, "min_ratio_label"), s["min_ratio"], 0, 10, "", 2, 0.25),
            _num("weak_rock", _t(lang, "weak_rock_label"), s["weak_rock"], 0, 100, "MPa", 1,
                 0.5),
        ], note=_t(lang, "socket_design_note")),
    ]


def study_groups(lang: str = "en") -> List[Group]:
    from .study import METHODS as SAMPLING
    return [Group(_t(lang, "group_study"), [
        _select("study_method", _t(lang, "study_method"), "lhs",
                [(m, _t(lang, f"sampling_{m}")) for m in SAMPLING]),
        _num("study_n", _t(lang, "study_n"), 200, 3, 100000, "", 0, 50),
        _num("study_seed", _t(lang, "study_seed"), 0, 0, 10 ** 6, "", 0, 1),
    ], note=_t(lang, "study_note"))]


# --------------------------------------------------------------------------- #
#  Tables: soil layers, study variables
# --------------------------------------------------------------------------- #

SOIL_NUMBERS = ["thickness", "gamma", "gamma_sat", "phi", "cu", "OCR", "N60", "E", "nu",
                "Cc", "Cr", "e0"]

#: Columns that mean nothing in a granular layer, which the table greys out
CLAY_ONLY = ["cu", "OCR", "Cc", "Cr", "e0"]

#: Columns that mean nothing in a cohesive layer
SAND_ONLY = ["N60"]


def soil_columns(lang: str = "en") -> List[dict]:
    """Columns of the soil profile table."""
    def number(key):
        return {"key": key, "label": _t(lang, f"col_{key}"), "kind": "number"}

    return ([{"key": "name", "label": _t(lang, "col_name"), "kind": "text"},
             number("thickness"),
             {"key": "behaviour", "label": _t(lang, "col_behaviour"), "kind": "select",
              "options": [{"value": v, "label": _t(lang, f"behaviour_{v}")}
                          for v in BEHAVIOURS]}]
            + [number(key) for key in SOIL_NUMBERS[1:]])


def study_columns(lang: str = "en") -> List[dict]:
    """Columns of the study variable table."""
    from .study import DISTRIBUTIONS
    return [
        {"key": "path", "label": _t(lang, "col_param"), "kind": "select", "options": []},
        {"key": "mode", "label": _t(lang, "col_mode"), "kind": "select",
         "options": [{"value": "range", "label": _t(lang, "mode_range")},
                     {"value": "dist", "label": _t(lang, "mode_dist")}]},
        {"key": "min", "label": _t(lang, "col_min"), "kind": "number"},
        {"key": "max", "label": _t(lang, "col_max"), "kind": "number"},
        {"key": "dist", "label": _t(lang, "col_dist"), "kind": "select",
         "options": [{"value": d, "label": _t(lang, f"dist_{d}")} for d in DISTRIBUTIONS]},
        {"key": "mean", "label": _t(lang, "col_mean"), "kind": "number"},
        {"key": "cov", "label": _t(lang, "col_cov"), "kind": "number"},
        {"key": "n_points", "label": _t(lang, "col_points"), "kind": "number"},
    ]


def default_soil_rows() -> List[dict]:
    return [dict(layer) for layer in DEFAULT_CONFIG["soil_profile"]]


# --------------------------------------------------------------------------- #
#  Schema collector
# --------------------------------------------------------------------------- #

#: The parts of the schema made of groups of fields
PARTS = ("project", "pile", "options", "socket", "study")


def schema(lang: str = "en") -> dict:
    """The whole schema the browser builds its forms from, in one language."""
    return {
        "project": {"groups": [g.to_dict() for g in project_groups(lang)]},
        "pile": {"groups": [g.to_dict() for g in pile_groups(lang)]},
        "options": {"groups": [g.to_dict() for g in option_groups(lang)]},
        "socket": {"groups": [g.to_dict() for g in socket_groups(lang)]},
        "study": {"groups": [g.to_dict() for g in study_groups(lang)]},
        "soil": {"columns": soil_columns(lang), "rows": default_soil_rows(),
                 "note": _t(lang, "soil_note"), "clay_only": list(CLAY_ONLY),
                 "sand_only": list(SAND_ONLY)},
        "study_vars": {"columns": study_columns(lang)},
    }


def _all_groups(lang: str = "en") -> List[Group]:
    return (project_groups(lang) + pile_groups(lang) + option_groups(lang)
            + socket_groups(lang) + study_groups(lang))


def defaults(lang: str = "en") -> Dict[str, Any]:
    """Default values of every field, as one flat dictionary."""
    values: Dict[str, Any] = {}
    for group in _all_groups(lang):
        for f in group.fields:
            values[f.key] = f.default
    values["soil_profile"] = default_soil_rows()
    values["study_variables"] = []
    return values


# --------------------------------------------------------------------------- #
#  Readers: flat values <-> configuration dictionary
# --------------------------------------------------------------------------- #

def _f(values: dict, key: str, default: float = 0.0) -> float:
    """A numeric field; missing or empty falls back to the default."""
    v = values.get(key, default)
    if v is None or v == "":
        return float(default)
    return float(v)


def _b(values: dict, key: str, default: bool = False) -> bool:
    v = values.get(key, default)
    return bool(default if v is None or v == "" else v)


def _s(values: dict, key: str, default: str = "", allowed: Optional[List[str]] = None) -> str:
    v = values.get(key, default)
    text = str(default if v is None or v == "" else v)
    return text if allowed is None or text in allowed else default


def read_soil_profile(values: dict) -> List[dict]:
    """Soil layers from the table; rows without a usable thickness are dropped."""
    base = DEFAULT_CONFIG["soil_profile"][0]
    layers = []
    for row in values.get("soil_profile") or []:
        try:
            thickness = float(row.get("thickness"))
        except (TypeError, ValueError):
            continue
        if thickness <= 0:
            continue
        layer = {"name": str(row.get("name") or "").strip() or "Layer",
                 "behaviour": _s(row, "behaviour", "granular", BEHAVIOURS)}
        for key in SOIL_NUMBERS:
            layer[key] = _f(row, key, base[key])
        layer["thickness"] = thickness
        layers.append(layer)
    return layers


#: Flat names of the seismic inputs that would otherwise clash with others
SEISMIC_KEYS = {"enabled": "seismic_enabled", "V": "V_E", "FS_compression": "FS_E_c",
                "FS_tension": "FS_E_t"}

#: Flat key <- (section, key) of the configuration, for everything but the tables
_MAP = [("title", "project_info", "title"), ("analyst", "project_info", "analyst")] + \
    [(k, "pile", k) for k in DEFAULT_CONFIG["pile"]] + \
    [("Q", "loading", "Q")] + \
    [(k, "group", k) for k in DEFAULT_CONFIG["group"]] + \
    [("water_depth", "groundwater", "depth"), ("gamma_water", "groundwater", "gamma_water")] + \
    [(k, "options", k) for k in DEFAULT_CONFIG["options"]] + \
    [(k, "settlement", k) for k in DEFAULT_CONFIG["settlement"]] + \
    [(k, "criteria", k) for k in DEFAULT_CONFIG["criteria"]] + \
    [({"D": "socket_D", "Ls": "socket_Ls", "top": "socket_top", "Q": "socket_Q"}.get(k, k),
      "socket", k) for k in DEFAULT_CONFIG["socket"]] + \
    [(SEISMIC_KEYS.get(k, k), "seismic", k) for k in DEFAULT_CONFIG["seismic"]]

#: The choice lists each select field must stay within
_ALLOWED = {
    "shape": SHAPES, "installation": INSTALLATIONS, "efficiency": EFFICIENCY_METHODS,
    "clay_method": CLAY_METHODS, "tip_method": TIP_METHODS, "group_method": GROUP_SETTLEMENT,
    "distribution": SKIN_DISTRIBUTIONS, "modulus_method": MODULUS_METHODS,
    "design": SOCKET_DESIGN, "base_design": SOCKET_BASE_DESIGN,
}

#: Fields that are whole numbers
_INTEGERS = {"nx", "ny"}


def to_config(values: dict) -> Dict[str, Any]:
    """The nested configuration the analysis core takes, from flat values."""
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    for flat, section, key in _MAP:
        default = DEFAULT_CONFIG[section][key]
        if isinstance(default, bool):
            cfg[section][key] = _b(values, flat, default)
        elif isinstance(default, str):
            if flat == "analyst":
                cfg[section][key] = str(values.get(flat) or "")
            else:
                cfg[section][key] = _s(values, flat, default, _ALLOWED.get(flat))
        elif flat in _INTEGERS:
            cfg[section][key] = int(round(_f(values, flat, default)))
        else:
            cfg[section][key] = _f(values, flat, default)
    cfg["soil_profile"] = read_soil_profile(values)
    return cfg


def from_config(cfg: dict, base: Optional[dict] = None) -> Dict[str, Any]:
    """Flat values from a nested configuration — reads a `.pile` project file.

    Whatever the file does not carry keeps its default.
    """
    values = dict(base) if base is not None else defaults()
    for flat, section, key in _MAP:
        if key in (cfg.get(section) or {}):
            values[flat] = cfg[section][key]
    if cfg.get("soil_profile"):
        layer_defaults = DEFAULT_CONFIG["soil_profile"][0]
        values["soil_profile"] = [{**layer_defaults, **layer} for layer in cfg["soil_profile"]
                                  if isinstance(layer, dict)]
    study = cfg.get("study") or {}
    for src, dst in (("method", "study_method"), ("n", "study_n"), ("seed", "study_seed")):
        if src in study:
            values[dst] = study[src]
    if "variables" in study:
        values["study_variables"] = [dict(spec) for spec in study["variables"]]
    return values


def study_spec(values: dict) -> Dict[str, Any]:
    """The study block of a project file: options plus the variable table."""
    from .study import METHODS as SAMPLING
    return {
        "method": _s(values, "study_method", "lhs", SAMPLING),
        "n": int(_f(values, "study_n", 200)),
        "seed": int(_f(values, "study_seed", 0)),
        "variables": [dict(spec) for spec in values.get("study_variables") or []],
    }


def project_file(values: dict) -> Dict[str, Any]:
    """What `Save` writes: the configuration plus the study definition."""
    cfg = to_config(values)
    return {"format": FILE_FORMAT, "version": FILE_VERSION, **cfg, "study": study_spec(values)}


def study_variables(values: dict):
    """The study variables as `study.StudyVariable` objects."""
    from .study import StudyVariable
    return [StudyVariable.from_dict(spec) for spec in values.get("study_variables") or []]


def variable_choices(values: dict, lang: str = "en") -> List[dict]:
    """Every input a study may vary, with a readable label and its project value."""
    from .study import available_variables, get_value, pretty_label
    cfg = to_config(values)
    L = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    out = []
    for path, _ in available_variables(cfg):
        try:
            base = float(get_value(cfg, path))
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        out.append({"value": path, "label": pretty_label(cfg, path, L), "base": base})
    return out

