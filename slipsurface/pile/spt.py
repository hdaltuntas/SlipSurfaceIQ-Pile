"""
The soil profile from boreholes: SPT blow counts and the tests on their samples.

Each SPT record is one test at one depth, with what the laboratory measured on
its sample. From them this module builds the layers the analysis takes
(`config["soil_profile"]`), and says where every value came from.

    profile = derive_profile(borehole)
    cfg = profile.apply(default_config("bored"))  # soil profile + water table
    result = analyse(cfg)

A list of several boreholes returns an ``SPTInvestigation``. Each log keeps
its own layers and water table; ``investigation.apply(cfg)`` passes all of
them to the analysis so every borehole is checked at the same pile geometry.
Different boreholes are never averaged into an invented soil column.

A borehole::

    {"name": "BH-1",
     "water_depth": 2.5,           # m below the ground surface (optional)
     "energy_ratio": 60,           # hammer energy ratio ER, %   (default 60)
     "borehole_diameter": 100,     # mm                          (default 100)
     "liner": True,                # sampler with its liner      (default True)
     "records": [
         {"depth": 1.5, "N": 7, "uscs": "SM", "fines": 22, "w": 14},
         {"depth": 3.0, "N": 4, "uscs": "CL", "LL": 41, "PL": 21, "w": 31,
          "cu": 38},
         ...]}

A record: ``depth`` (m) and ``N`` (field blow count) are required; the rest is
whatever was measured on the sample:

    uscs        group symbol (SP, SM, CL, CH, ML …)
    fines       % passing 0.075 mm        LL, PL     liquid and plastic limit, %
    w           water content, %          gamma      natural unit weight, kN/m³
    cu          undrained shear strength (UU, unconfined), kPa
    phi         effective friction angle (triaxial, direct shear), degrees
    Cc, Cr, e0  compression and recompression index, initial void ratio
    sigma_p     preconsolidation stress (oedometer), kPa -> OCR
    E           modulus, MPa
    behaviour   "granular" or "cohesive", to override the classification

Corrections
    N60 = N · (ER/60) · CB · CS · CR                         Skempton (1986)
          CR (rod length ≈ depth): 0.75 < 4 m, 0.85 4–6 m, 0.95 6–10 m, 1.0
          CB: 1.00 for 65–115 mm, 1.05 for 150 mm, 1.15 for 200 mm
          CS: 1.0 with the liner, 1.2 without
    (N1)60 = CN · N60, CN = √(pa/σ'v0) ≤ 1.7                  Liao & Whitman (1986)

Behaviour
    cohesive: USCS C…, O…, MH, Pt, or ML / dual symbols with PI ≥ 7; without a
    symbol, fines ≥ 50 % with PI ≥ 7 (or no PI); a measured cu alone also
    makes the sample cohesive. Granular otherwise.

Correlations, used only where the laboratory gave no value
    granular  φ' = √(20·(N1)60) + 20 ≤ 45°                   Hatanaka & Uchida (1996)
              E = k·pa·N60, k = 10 (clean sand), 5 (fines > 12 %)
                                                             Kulhawy & Mayne (1990)
    cohesive  cu = f1·N60, f1 = 6.5 kPa (PI ≤ 15) to 4.4 kPa (PI ≥ 50),
              5.0 kPa without PI                             Stroud (1974)
              φ' from sin φ' = 0.8 − 0.094·ln PI (25° without PI)
                                                             Terzaghi, Peck & Mesri (1996)
              OCR = σ'p/σ'v0, or from cu/σ'v0 = 0.22·OCR^0.8  Ladd (1991), SHANSEP
              Cc = 0.009·(LL − 10)                           Terzaghi & Peck (1967)
              Cr = 0.15·Cc;  e0 = w·Gs, Gs = 2.70 (saturated)
              Eu = 300·cu
    γ         the measured natural unit weight (γsat = γ + 1 above the water
              table, γ = γsat − 1 below it); otherwise a typical value for the
              behaviour and N60
    ν         0.30 granular, 0.40 cohesive

Layers
    Each test stands for the depth range half-way to its neighbours. Adjacent
    ranges join into one layer when they behave alike (granular or cohesive,
    and the same main soil group where symbols are given) and their N60 stays
    within `tolerance` (50 %, at least 5 blows) of the layer's mean. A layer
    thinner than `min_thickness` then joins the neighbour of the same
    behaviour whose N60 is closest; a thin layer between two of the other
    behaviour (a clay lens in sand) is kept. A layer's value of each
    parameter is the mean of its measured values, or else the mean of the
    correlated ones. Repeated tests at the same depth within a borehole may
    be taken together only when their soil classifications are compatible.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union

#: Atmospheric pressure [kPa]
PA = 101.325
GAMMA_W = 9.81
#: Specific gravity of the solids, for e0 from the water content
GS = 2.70

#: Parameters a laboratory may give, in the layer's own key
MEASURED = ("gamma", "phi", "cu", "Cc", "Cr", "e0", "E")

#: Main soil groups of the USCS symbols
GROUP_NAMES = {"G": "Gravel", "S": "Sand", "M": "Silt", "C": "Clay", "O": "Organic soil",
               "P": "Peat"}

USCS_SYMBOLS = {"GW", "GP", "GM", "GC", "SW", "SP", "SM", "SC", "CL", "ML", "CH", "MH",
                "OL", "OH", "PT"}

RECORD_NUMBERS = ("depth", "N", "fines", "LL", "PL", "w", "gamma", "cu", "phi", "Cc", "Cr",
                  "e0", "sigma_p", "E")


# --------------------------------------------------------------------------- #
#  Corrections and correlations
# --------------------------------------------------------------------------- #

def rod_factor(depth: float) -> float:
    """CR, Skempton (1986), taking the rod length as the test depth."""
    if depth < 4.0:
        return 0.75
    if depth < 6.0:
        return 0.85
    if depth < 10.0:
        return 0.95
    return 1.0


def borehole_factor(diameter_mm: float) -> float:
    """CB, Skempton (1986)."""
    if diameter_mm <= 115.0:
        return 1.0
    if diameter_mm <= 150.0:
        return 1.05
    return 1.15


def n60(N: float, depth: float, energy_ratio: float = 60.0, diameter_mm: float = 100.0,
        liner: bool = True) -> float:
    """N60 = N·(ER/60)·CB·CS·CR."""
    cs = 1.0 if liner else 1.2
    return N * energy_ratio / 60.0 * borehole_factor(diameter_mm) * cs * rod_factor(depth)


def overburden_factor(sigma_eff: float) -> float:
    """CN = √(pa/σ'v0) ≤ 1.7, Liao & Whitman (1986)."""
    return min(math.sqrt(PA / max(sigma_eff, 1e-6)), 1.7)


def phi_from_n160(n160: float) -> float:
    """φ' = √(20·(N1)60) + 20 ≤ 45°, Hatanaka & Uchida (1996)."""
    return min(math.sqrt(20.0 * max(n160, 0.0)) + 20.0, 45.0)


def stroud_f1(PI: Optional[float]) -> float:
    """f1 of cu = f1·N60 [kPa], read from Stroud's (1974) chart."""
    if PI is None:
        return 5.0
    if PI <= 15.0:
        return 6.5
    if PI >= 50.0:
        return 4.4
    return 6.5 - (PI - 15.0) * (6.5 - 4.4) / 35.0


def phi_from_pi(PI: Optional[float]) -> float:
    """sin φ' = 0.8 − 0.094·ln PI, Terzaghi, Peck & Mesri (1996); 25° without PI."""
    if PI is None or PI <= 0:
        return 25.0
    return math.degrees(math.asin(min(max(0.8 - 0.094 * math.log(PI), 0.1), 0.9)))


def ocr_from_cu(cu: float, sigma_eff: float) -> float:
    """cu/σ'v0 = 0.22·OCR^0.8 (SHANSEP, Ladd 1991), 1 ≤ OCR ≤ 20."""
    if sigma_eff <= 0:
        return 1.0
    return min(max((cu / (0.22 * sigma_eff)) ** 1.25, 1.0), 20.0)


def typical_unit_weight(behaviour: str, N60: float) -> tuple:
    """(γ, γsat) [kN/m³] typical of the behaviour and the blow count."""
    if behaviour == "granular":
        return (17.0, 19.0) if N60 < 10 else (18.0, 20.0) if N60 < 30 else (19.0, 21.0)
    return (17.0, 18.0) if N60 < 8 else (18.0, 19.0) if N60 < 15 else (19.0, 20.0)


# --------------------------------------------------------------------------- #
#  Classification
# --------------------------------------------------------------------------- #

def plasticity_index(record: dict) -> Optional[float]:
    if record.get("LL") is None or record.get("PL") is None:
        return None
    return max(float(record["LL"]) - float(record["PL"]), 0.0)


def classify(record: dict) -> str:
    """'granular' or 'cohesive', from what the sample tests say."""
    given = record.get("behaviour")
    if given in ("granular", "cohesive"):
        return given
    PI = plasticity_index(record)
    uscs = str(record.get("uscs") or "").upper().replace(" ", "")
    if uscs:
        main = uscs[:2]
        if main.startswith(("C", "O")) or main in ("MH", "PT"):
            return "cohesive"
        if main == "ML":
            return "cohesive" if PI is not None and PI >= 7 else "granular"
        return "granular"
    fines = record.get("fines")
    if fines is not None and float(fines) >= 50.0:
        return "cohesive" if PI is None or PI >= 7 else "granular"
    if PI is not None and fines is None:
        return "cohesive" if PI >= 7 else "granular"
    if record.get("cu") is not None:
        return "cohesive"
    return "granular"


def soil_group(record: dict) -> str:
    """The main group letter of the USCS symbol ('' without one)."""
    return str(record.get("uscs") or "").strip().upper()[:1]


# --------------------------------------------------------------------------- #
#  The derived profile
# --------------------------------------------------------------------------- #

@dataclass
class SPTProfile:
    """The layers derived from the boreholes, and where their values came from."""

    layers: List[dict]                 # in the format of config["soil_profile"]
    water_depth: Optional[float]       # m below the ground surface, if known
    records: List[dict]                # every test, corrected, with its layer number
    sources: List[Dict[str, str]]      # per layer: parameter -> where it came from
    warnings: List[str] = field(default_factory=list)
    name: str = "BH-1"

    def apply(self, cfg: dict) -> dict:
        """A copy using this log, including its explicit dry/groundwater state."""
        out = copy.deepcopy(cfg)
        out["soil_profile"] = copy.deepcopy(self.layers)
        out.setdefault("groundwater", {})["depth"] = self.water_depth
        out.pop("boreholes", None)
        return out

    @property
    def depth(self) -> float:
        return sum(layer["thickness"] for layer in self.layers)


@dataclass
class SPTInvestigation:
    """Independent borehole profiles for a design checked against every log.

    There is deliberately no combined ``layers`` property. A controlling
    borehole is a result of the pile checks, not a soil-parameter average.
    """

    profiles: List[SPTProfile]
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.profiles) < 2:
            raise ValueError("An SPT investigation needs at least two boreholes.")
        names = self.names
        if any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError("Every borehole needs a nonempty name.")
        if len(set(names)) != len(names):
            raise ValueError("Borehole names must be unique.")
        if not self.warnings:
            self.warnings = [f"{profile.name}: {warning}" for profile in self.profiles
                             for warning in profile.warnings]

    @property
    def names(self) -> List[str]:
        return [profile.name for profile in self.profiles]

    def apply(self, cfg: dict) -> dict:
        """Copy a configuration and attach the separate logs for all-log checks."""
        out = copy.deepcopy(cfg)
        out["boreholes"] = [
            {"name": profile.name, "soil_profile": copy.deepcopy(profile.layers),
             "groundwater": {"depth": profile.water_depth}}
            for profile in self.profiles
        ]
        return out


def _number(value, label: str, *, minimum: Optional[float] = None,
            maximum: Optional[float] = None, positive: bool = False) -> float:
    """Read a finite number without accepting booleans as measurements."""
    try:
        if isinstance(value, bool):
            raise ValueError
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{label}: a finite number is required") from None
    if not math.isfinite(number):
        raise ValueError(f"{label}: a finite number is required")
    if positive and number <= 0:
        raise ValueError(f"{label}: must be positive")
    if minimum is not None and number < minimum:
        raise ValueError(f"{label}: must be at least {minimum:g}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{label}: must not exceed {maximum:g}")
    return number


def _record(record: dict, name: str) -> dict:
    """Validate a sample before using it in any correction or correlation."""
    if not isinstance(record, dict) or any(record.get(key) in (None, "")
                                          for key in ("depth", "N")):
        raise ValueError(f"{name}: an SPT record needs a depth and a blow count N")
    out = dict(record)
    for key in RECORD_NUMBERS:
        value = out.get(key)
        if value is None or value == "":
            out.pop(key, None)
            continue
        out[key] = _number(value, f"{name}: {key}", minimum=0.0,
                           positive=key in ("depth", "gamma", "cu", "sigma_p", "E"))
    if out.get("fines") is not None and out.get("fines") != "" and out["fines"] > 100:
        raise ValueError(f"{name}: fines must be between 0 and 100 percent")
    if out.get("phi") is not None and out.get("phi") != "" and out["phi"] >= 50:
        raise ValueError(f"{name}: phi must be below 50 degrees")
    if _float(out, "LL") is not None and _float(out, "PL") is not None:
        if out["PL"] > out["LL"]:
            raise ValueError(f"{name}: PL must not exceed LL")
    if _float(out, "Cc") is not None and _float(out, "Cr") is not None:
        if out["Cr"] > out["Cc"]:
            raise ValueError(f"{name}: Cr must not exceed Cc")
    behaviour = out.get("behaviour")
    if behaviour not in (None, "", "granular", "cohesive"):
        raise ValueError(f"{name}: behaviour must be granular or cohesive")
    symbol = str(out.get("uscs") or "").upper().replace(" ", "")
    if symbol and any(part not in USCS_SYMBOLS for part in symbol.split("-")):
        raise ValueError(f"{name}: unknown USCS symbol {symbol!r}")
    out["uscs"] = symbol
    return out


def _float(record: dict, key: str) -> Optional[float]:
    value = record.get(key)
    if value is None or value == "":
        return None
    return float(value)


def _levels(hole: dict, same_depth: float) -> List[dict]:
    """One log in depth order; compatible repeated tests form one level."""
    tests = []
    er = _number(hole.get("energy_ratio", 60.0), f"{hole['name']}: energy_ratio",
                 positive=True)
    dia = _number(hole.get("borehole_diameter", 100.0),
                  f"{hole['name']}: borehole_diameter", minimum=65.0, maximum=200.0)
    liner = hole.get("liner", True)
    if not isinstance(liner, bool):
        raise ValueError(f"{hole['name']}: liner must be a boolean")
    records = hole.get("records")
    if records is None:
        records = []
    if not isinstance(records, (list, tuple)):
        raise ValueError(f"{hole['name']}: records must be a list of SPT records")
    for i, raw in enumerate(records):
        name = f"{hole['name']} #{i + 1}"
        rec = _record(raw, name)
        depth, N = rec["depth"], rec["N"]
        corrected = n60(N, depth, er, dia, liner)
        if not math.isfinite(corrected):
            raise ValueError(f"{name}: corrected N60 must be finite")
        test = dict(rec, borehole=hole["name"], N60=corrected, PI=plasticity_index(rec),
                    behaviour=classify(rec))
        tests.append(test)
    if not tests:
        raise ValueError("No SPT records were given.")
    tests.sort(key=lambda t: t["depth"])
    levels: List[dict] = []
    for test in tests:
        if levels and test["depth"] - levels[-1]["depth"] <= same_depth:
            levels[-1]["tests"].append(test)
        else:
            levels.append({"depth": test["depth"], "tests": [test]})
    for level in levels:
        kinds = {t["behaviour"] for t in level["tests"]}
        groups = {soil_group(t) for t in level["tests"] if soil_group(t)}
        if len(kinds) > 1 or len(groups) > 1:
            raise ValueError(f"{hole['name']}: conflicting soil classifications near "
                             f"depth {level['depth']:g} m; resolve the log or reduce same_depth")
        level["behaviour"] = level["tests"][0]["behaviour"]
        level["group"] = next(iter(groups), "")
        level["N60"] = sum(t["N60"] for t in level["tests"]) / len(level["tests"])
    return levels


def _intervals(levels: List[dict], bottom: Optional[float]) -> None:
    """Each level stands for the range half-way to its neighbours."""
    for i, level in enumerate(levels):
        level["top"] = 0.0 if i == 0 else (levels[i - 1]["depth"] + level["depth"]) / 2.0
        if i + 1 < len(levels):
            level["bottom"] = (level["depth"] + levels[i + 1]["depth"]) / 2.0
        else:
            half = (level["depth"] - levels[i - 1]["depth"]) / 2.0 if i else 0.75
            level["bottom"] = level["depth"] + max(half, 0.5)
    if bottom is not None:
        deepest = max(t["depth"] for level in levels for t in level["tests"])
        if bottom <= deepest:
            raise ValueError("The profile must reach below the deepest test.")
        levels[-1]["bottom"] = float(bottom)


def _unit_weights(level: dict, zw: Optional[float]) -> tuple:
    measured = [t for t in level["tests"] if _float(t, "gamma") is not None]
    if measured:
        pairs = []
        for test in measured:
            g = test["gamma"]
            below = zw is not None and test["depth"] >= zw
            gammas = (g - 1.0, g) if below else (g, g + 1.0)
            if gammas[0] <= 0 or gammas[1] <= GAMMA_W:
                raise ValueError(f"{test['borehole']}: gamma at {test['depth']:g} m must "
                                 "give positive dry weight and saturated weight above "
                                 "the water unit weight")
            pairs.append(gammas)
        return tuple(sum(pair[i] for pair in pairs) / len(pairs) for i in (0, 1)), "measured"
    return typical_unit_weight(level["behaviour"], level["N60"]), "typical"


def _stresses(levels: List[dict], zw: Optional[float]) -> None:
    """σ'v0 at each test depth, from the unit weights of the ranges above."""
    for level in levels:
        level["gammas"], level["gamma_source"] = _unit_weights(level, zw)

    def sigma(z: float) -> float:
        total = 0.0
        for lv in levels:
            top, bot = lv["top"], min(lv["bottom"], z)
            if bot <= top:
                break
            g, gs = lv["gammas"]
            if zw is None or bot <= zw:
                total += g * (bot - top)
            elif top >= zw:
                total += gs * (bot - top)
            else:
                total += g * (zw - top) + gs * (bot - zw)
        u = GAMMA_W * max(z - zw, 0.0) if zw is not None else 0.0
        return total - u

    for level in levels:
        level["sigma_eff"] = sigma(level["depth"])
        for t in level["tests"]:
            t["sigma_eff"] = sigma(t["depth"])
            t["N1_60"] = overburden_factor(t["sigma_eff"]) * t["N60"]


def _alike(layer: List[dict], level: dict, rel: float, abs_n: float) -> bool:
    if level["behaviour"] != layer[0]["behaviour"]:
        return False
    groups = {lv["group"] for lv in layer if lv["group"]}
    if level["group"] and groups and level["group"] not in groups:
        return False
    mean = sum(lv["N60"] for lv in layer) / len(layer)
    return abs(level["N60"] - mean) <= max(rel * mean, abs_n)


def _thickness(layer: List[dict]) -> float:
    return layer[-1]["bottom"] - layer[0]["top"]


def _n_mean(layer: List[dict]) -> float:
    return sum(lv["N60"] for lv in layer) / len(layer)


def _merge(levels: List[dict], rel: float, abs_n: float, min_thickness: float) -> List[list]:
    layers: List[List[dict]] = []
    for level in levels:
        if layers and _alike(layers[-1], level, rel, abs_n):
            layers[-1].append(level)
        else:
            layers.append([level])
    changed = True
    while changed and len(layers) > 1:
        changed = False
        thin = sorted((i for i, ly in enumerate(layers) if _thickness(ly) < min_thickness),
                      key=lambda i: _thickness(layers[i]))
        for i in thin:
            kind = layers[i][0]["behaviour"]
            options = [j for j in (i - 1, i + 1)
                       if 0 <= j < len(layers) and layers[j][0]["behaviour"] == kind]
            if not options:
                continue
            j = min(options, key=lambda k: abs(_n_mean(layers[k]) - _n_mean(layers[i])))
            lo, hi = min(i, j), max(i, j)
            layers[lo:hi + 1] = [layers[lo] + layers[hi]]
            changed = True
            break
    # neighbours of the same behaviour and group, alike again after the joins
    i = 0
    while i + 1 < len(layers):
        if all(_alike(layers[i], lv, rel, abs_n) for lv in layers[i + 1]):
            layers[i:i + 2] = [layers[i] + layers[i + 1]]
        else:
            i += 1
    return layers


def _mean(values: List[float]) -> float:
    return sum(values) / len(values)


def _layer(levels: List[dict], index: int, warnings: List[str]) -> tuple:
    tests = [t for lv in levels for t in lv["tests"]]
    kind = levels[0]["behaviour"]
    thickness = levels[-1]["bottom"] - levels[0]["top"]
    weights = [lv["bottom"] - lv["top"] for lv in levels]
    N60 = sum(lv["N60"] * w for lv, w in zip(levels, weights)) / sum(weights)
    sigma = sum(lv["sigma_eff"] * w for lv, w in zip(levels, weights)) / sum(weights)
    measured = {key: [float(t[key]) for t in tests if _float(t, key) is not None]
                for key in MEASURED}
    PIs = [t["PI"] for t in tests if t["PI"] is not None]
    PI = _mean(PIs) if PIs else None
    src: Dict[str, str] = {}
    layer: Dict[str, Any] = {"behaviour": kind, "thickness": thickness, "N60": N60}
    src["N60"] = f"mean of {len(tests)} test(s), Skempton (1986) corrections"

    def take(key, correlated, how):
        if measured[key]:
            layer[key] = _mean(measured[key])
            src[key] = f"measured, mean of {len(measured[key])}"
        else:
            layer[key] = correlated
            src[key] = how

    g = [lv["gammas"] for lv in levels]
    layer["gamma"] = sum(x[0] * w for x, w in zip(g, weights)) / sum(weights)
    layer["gamma_sat"] = sum(x[1] * w for x, w in zip(g, weights)) / sum(weights)
    kinds = {lv["gamma_source"] for lv in levels}
    src["gamma"] = src["gamma_sat"] = "measured γn" if kinds == {"measured"} else \
        "typical for the soil and N60" if kinds == {"typical"} else "measured and typical"
    measured.pop("gamma")

    if kind == "granular":
        phis = [phi_from_n160(t["N1_60"]) for t in tests]
        take("phi", _mean(phis), "Hatanaka & Uchida (1996) from (N1)60")
        fines = [float(t["fines"]) for t in tests if _float(t, "fines") is not None]
        k = 5.0 if fines and _mean(fines) > 12.0 else 10.0
        take("E", k * PA * N60 / 1000.0, f"Kulhawy & Mayne (1990), E = {k:g}·pa·N60")
        layer.update(cu=0.0, OCR=1.0, Cc=0.0, Cr=0.0, e0=0.0, nu=0.30)
        src["nu"] = "typical (0.30)"
    else:
        take("cu", stroud_f1(PI) * N60, f"Stroud (1974), f1 = {stroud_f1(PI):.1f} kPa")
        if not measured["cu"] and layer["cu"] < 5.0:
            warnings.append(f"Layer {index}: correlated cu {layer['cu']:.1f} kPa raised "
                            "to 5 kPa (low SPT resistance; measure the strength).")
            layer["cu"] = 5.0
            src["cu"] += ", raised to the 5 kPa floor"
        take("phi", phi_from_pi(PI), "Terzaghi, Peck & Mesri (1996) from PI"
             if PI is not None else "typical (25°), no PI")
        sp = [float(t["sigma_p"]) for t in tests if _float(t, "sigma_p") is not None]
        if sp:
            layer["OCR"] = max(_mean(sp) / max(sigma, 1e-6), 1.0)
            src["OCR"] = f"σ'p / σ'v0, mean of {len(sp)} oedometer test(s)"
        else:
            layer["OCR"] = ocr_from_cu(layer["cu"], sigma)
            src["OCR"] = "SHANSEP (Ladd 1991) from cu/σ'v0"
        LLs = [float(t["LL"]) for t in tests if _float(t, "LL") is not None]
        take("Cc", max(0.009 * (_mean(LLs) - 10.0), 0.0) if LLs else 0.0,
             "Terzaghi & Peck (1967) from LL" if LLs else "none (no LL): no consolidation")
        take("Cr", 0.15 * layer["Cc"], "0.15·Cc")
        ws = [float(t["w"]) for t in tests if _float(t, "w") is not None]
        take("e0", _mean(ws) / 100.0 * GS if ws else 0.0,
             f"w·Gs, Gs = {GS}" if ws else "none (no w)")
        take("E", 0.3 * layer["cu"], "Eu = 300·cu")
        layer["nu"] = 0.40
        src["nu"] = "typical (0.40)"
    if layer["E"] <= 0:
        warnings.append(f"Layer {index}: E raised to 1 MPa (N60 near zero).")
        layer["E"] = 1.0
        src["E"] += ", raised to 1 MPa"

    groups = sorted({str(t.get("uscs")).upper() for t in tests if t.get("uscs")})
    main = levels[0]["group"]
    noun = GROUP_NAMES.get(main, "Cohesive soil" if kind == "cohesive" else "Granular soil")
    layer["name"] = f"{noun} ({', '.join(groups)})" if groups else noun
    for key in ("thickness", "N60", "gamma", "gamma_sat", "phi", "cu", "OCR", "E",
                "Cc", "Cr", "e0"):
        layer[key] = float(layer[key])
        if not math.isfinite(layer[key]):
            raise ValueError(f"Layer {index}: derived {key} must be finite")
    ordered = {k: layer[k] for k in ("name", "thickness", "behaviour", "gamma", "gamma_sat",
                                     "phi", "cu", "OCR", "N60", "E", "nu", "Cc", "Cr", "e0")}
    return ordered, src


def _derive_one(hole: dict, water_depth: Optional[float], bottom: Optional[float],
                tolerance: float, min_n_difference: float, min_thickness: float,
                same_depth: float) -> SPTProfile:
    levels = _levels(hole, same_depth)
    _intervals(levels, bottom)
    _stresses(levels, water_depth)
    groups = _merge(levels, tolerance, min_n_difference, min_thickness)
    warnings: List[str] = []
    if water_depth is None:
        warnings.append("No water table was given: none is assumed.")
    layers, sources, records = [], [], []
    for index, group in enumerate(groups, start=1):
        layer, src = _layer(group, index, warnings)
        layers.append(layer)
        sources.append(src)
        for lv in group:
            for t in lv["tests"]:
                records.append({"borehole": t["borehole"], "depth": t["depth"], "N": t["N"],
                                "N60": round(t["N60"], 1), "N1_60": round(t["N1_60"], 1),
                                "sigma_eff": round(t["sigma_eff"], 1),
                                "uscs": t.get("uscs") or "", "behaviour": t["behaviour"],
                                "layer": index})
    return SPTProfile(layers, water_depth, records, sources, warnings, name=hole["name"])


def derive_profile(boreholes: Union[dict, Sequence[dict]], water_depth: Optional[float] = None,
                   bottom: Optional[float] = None, tolerance: float = 0.5,
                   min_n_difference: float = 5.0, min_thickness: float = 1.0,
                   same_depth: float = 0.25) -> Union[SPTProfile, SPTInvestigation]:
    """Derive one profile per borehole without pooling different logs.

    One dictionary or a one-item list returns ``SPTProfile``. Several logs
    return ``SPTInvestigation``; apply it to a configuration to check all logs
    at the same pile geometry and let the unfavorable checks govern.

    water_depth   optional override for a single borehole; for multiple logs
                  put each water table in its own borehole dictionary.
                  A missing water table means explicitly dry, with a warning.
    bottom        depth reached by each profile (default: half a test spacing
                  below that log's deepest test)
    tolerance, min_n_difference
                  within-log N60 tolerances for joining adjacent levels
    min_thickness thinner layers join a neighbor of the same behavior, m
    same_depth    compatible tests this close within one log form a level, m
    """
    if isinstance(boreholes, dict):
        holes = [boreholes]
    elif isinstance(boreholes, (list, tuple)):
        holes = list(boreholes)
    else:
        raise ValueError("Boreholes must be one dictionary or a list of dictionaries.")
    if not holes:
        raise ValueError("No SPT records were given.")
    if len(holes) > 1 and water_depth is not None:
        raise ValueError("For multiple boreholes, set water_depth separately on each log.")
    if water_depth is not None:
        water_depth = _number(water_depth, "water_depth", minimum=0.0)
    if bottom is not None:
        bottom = _number(bottom, "bottom", positive=True)
    options = {"tolerance": tolerance, "min_n_difference": min_n_difference,
               "min_thickness": min_thickness, "same_depth": same_depth}
    options = {key: _number(value, key, minimum=0.0) for key, value in options.items()}
    prepared = []
    names = set()
    for index, raw in enumerate(holes, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Borehole {index}: a dictionary is required")
        name = raw.get("name", f"BH-{index}")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Borehole {index}: a nonempty name is required")
        name = name.strip()
        if name in names:
            raise ValueError(f"Borehole names must be unique: {name!r}")
        names.add(name)
        own_water = raw.get("water_depth")
        if own_water is not None:
            own_water = _number(own_water, f"{name}: water_depth", minimum=0.0)
        if water_depth is not None:
            own_water = water_depth
        prepared.append((dict(raw, name=name), own_water))
    profiles = [_derive_one(hole, own_water, bottom, **options)
                for hole, own_water in prepared]
    return profiles[0] if len(profiles) == 1 else SPTInvestigation(profiles)
