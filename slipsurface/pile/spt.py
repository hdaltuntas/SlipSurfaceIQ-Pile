"""
The soil profile from boreholes: SPT blow counts and the tests on their samples.

Each SPT record is one test at one depth, with what the laboratory measured on
its sample. From them this module builds the layers the analysis takes
(`config["soil_profile"]`), and says where every value came from.

    profile = derive_profile(borehole)            # or a list of boreholes
    cfg = profile.apply(default_config("bored"))  # soil profile + water table
    result = analyse(cfg)

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
    correlated ones. Tests at the same depth in several boreholes are taken
    together.
"""

from __future__ import annotations

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

    def apply(self, cfg: dict) -> dict:
        """A copy of the configuration with this soil profile (and water table)."""
        import copy
        out = copy.deepcopy(cfg)
        out["soil_profile"] = copy.deepcopy(self.layers)
        if self.water_depth is not None:
            out.setdefault("groundwater", {})["depth"] = self.water_depth
        return out

    @property
    def depth(self) -> float:
        return sum(layer["thickness"] for layer in self.layers)


def _float(record: dict, key: str) -> Optional[float]:
    value = record.get(key)
    if value is None or value == "":
        return None
    return float(value)


def _levels(boreholes: Sequence[dict], same_depth: float) -> List[dict]:
    """The tests in depth order; tests at the same depth form one level."""
    tests = []
    for b, hole in enumerate(boreholes):
        er = float(hole.get("energy_ratio", 60.0))
        dia = float(hole.get("borehole_diameter", 100.0))
        liner = bool(hole.get("liner", True))
        for i, rec in enumerate(hole.get("records") or []):
            name = f"{hole.get('name') or f'BH-{b + 1}'} #{i + 1}"
            try:
                depth, N = float(rec["depth"]), float(rec["N"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"{name}: an SPT record needs a depth and a blow count N")
            if depth <= 0 or N < 0:
                raise ValueError(f"{name}: the depth must be positive and N not negative")
            test = dict(rec, borehole=hole.get("name") or f"BH-{b + 1}", depth=depth, N=N,
                        N60=n60(N, depth, er, dia, liner), PI=plasticity_index(rec),
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
        kinds = [t["behaviour"] for t in level["tests"]]
        level["behaviour"] = max(set(kinds), key=kinds.count)
        groups = [soil_group(t) for t in level["tests"] if soil_group(t)]
        level["group"] = max(set(groups), key=groups.count) if groups else ""
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
        if bottom <= levels[-1]["depth"]:
            raise ValueError("The profile must reach below the deepest test.")
        levels[-1]["bottom"] = float(bottom)


def _unit_weights(level: dict, zw: Optional[float]) -> tuple:
    measured = [t["gamma"] for t in level["tests"] if _float(t, "gamma") is not None]
    if measured:
        g = sum(float(x) for x in measured) / len(measured)
        below = zw is not None and level["depth"] >= zw
        return ((g - 1.0, g) if below else (g, g + 1.0)), "measured"
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
            t["sigma_eff"] = level["sigma_eff"]
            t["N1_60"] = overburden_factor(level["sigma_eff"]) * t["N60"]


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
    layer: Dict[str, Any] = {"behaviour": kind, "thickness": round(thickness, 3),
                             "N60": round(N60, 1)}
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
        if layer["cu"] < 5.0:
            warnings.append(f"Layer {index}: cu {layer['cu']:.1f} kPa raised to 5 kPa "
                            "(N60 near zero; test the strength).")
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
    for key in ("gamma", "gamma_sat", "phi", "cu", "OCR", "E", "Cc", "Cr", "e0"):
        layer[key] = round(float(layer[key]), 4)
    ordered = {k: layer[k] for k in ("name", "thickness", "behaviour", "gamma", "gamma_sat",
                                     "phi", "cu", "OCR", "N60", "E", "nu", "Cc", "Cr", "e0")}
    return ordered, src


def derive_profile(boreholes: Union[dict, Sequence[dict]], water_depth: Optional[float] = None,
                   bottom: Optional[float] = None, tolerance: float = 0.5,
                   min_n_difference: float = 5.0, min_thickness: float = 1.0,
                   same_depth: float = 0.25) -> SPTProfile:
    """The soil layers from one borehole or several (taken together).

    water_depth   the water table, m (default: the shallowest a borehole gives)
    bottom        the depth the profile reaches (default: half a test spacing
                  below the deepest test)
    tolerance, min_n_difference
                  how far a test's N60 may stray from a layer's mean and still
                  join it: 50 %, but at least 5 blows
    min_thickness thinner layers join a neighbour of the same behaviour, m
    same_depth    tests closer than this, in any borehole, form one level, m
    """
    holes = [boreholes] if isinstance(boreholes, dict) else list(boreholes)
    if water_depth is None:
        given = [float(h["water_depth"]) for h in holes if h.get("water_depth") is not None]
        water_depth = min(given) if given else None
    levels = _levels(holes, same_depth)
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
    return SPTProfile(layers, water_depth, records, sources, warnings)
