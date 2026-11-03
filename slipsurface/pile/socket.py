"""
Piles socketed into rock: the side shear, the base resistance, the socket
length each published correlation needs, and the elastic settlement.

Unit side shear (fs and qu in MPa; qu is the weaker of the rock and the
concrete, since the bond cannot be stronger than either):

    Rosenberg & Journeaux (1976)   fs = 0.375·qu^0.515
    Horvath & Kenney (1979)        fs = 0.21·qu^0.5
    Meigh & Wolski (1979)          fs = 0.22·qu^0.6
    Williams et al. (1980)         fs = 0.44·qu^0.36
    Reynolds & Kaderabek (1980)    fs = 0.30·qu            weak rock
    Gupton & Logan (1984)          fs = 0.20·qu            weak rock
    Rowe & Armitage (1987)         fs = 0.45·qu^0.5
    Carter & Kulhawy (1988)        fs = 0.20·qu^0.5
    Toh et al. (1989)              fs = 0.25·qu            weak rock
    Zhang & Einstein (1998)        fs = 0.40·qu^0.5
    O'Neill & Reese (1999), AASHTO fs = 0.65·αE·pa·(qu/pa)^0.5 ≤ 7.8·pa·(fc/pa)^0.5
    Kulhawy et al. (2005)          fs = 1.0·pa·(qu/pa)^0.5

Unit base resistance (qu of the rock below the base):

    Coates (1967)                  qb = 3·qu
    Rowe & Armitage (1987)         qb = 2.7·qu
    Carter & Kulhawy (1988)        qb = [√s + √(m·√s + s)]·qu   (Hoek–Brown)
    Zhang & Einstein (1998)        qb = 4.83·qu^0.51
    AASHTO / O'Neill & Reese       qb = 2.5·qu
    CFEM (Ladanyi & Roy 1971)      qb = 3·Ksp·d·qu, Ksp = (3 + c/D)/(10·√(1 + 300·δ/c)),
                                   d = 1 + 0.4·Ls/D ≤ 3

Rock mass modulus: Em = Ei·(0.0231·RQD − 1.32) ≥ 0.15·Ei (Gardner 1987), or
Em = Ei·[0.02 + (1 − D/2)/(1 + e^((60 + 15D − GSI)/11))] (Hoek & Diederichs
2006), or entered.

Settlement: the head of the socket by Randolph & Wroth's (1978) closed form
for a compressible pile in an elastic medium, with and without the base, and
by Vesić's three-part expression; the shortening of the pile through the
overburden is added to each.
"""

from __future__ import annotations

import copy
import math
import statistics
from typing import Any, Dict, List

import numpy as np

from .config import (
    DEFAULT_CONFIG,
    MODULUS_METHODS,
    SOCKET_BASE_DESIGN,
    SOCKET_BASE_METHODS,
    SOCKET_DESIGN,
    SOCKET_SIDE_METHODS,
)
from .errors import PileError, message, num
from .settlement import single_pile

#: Atmospheric pressure in MPa
PA_MPA = 0.101325

#: The rules fitted to weak rock only, which the statistics leave out above `weak_rock`
WEAK_ROCK_METHODS = ["reynolds_kaderabek", "gupton_logan", "toh"]

#: The longest socket the length search tries [m]
MAX_SOCKET = 60.0

#: (coefficient, exponent) of the power-law side shear correlations, fs = a·qu^b [MPa]
_POWER = {
    "rosenberg_journeaux": (0.375, 0.515), "horvath_kenney": (0.21, 0.5),
    "meigh_wolski": (0.22, 0.6), "williams": (0.44, 0.36),
    "reynolds_kaderabek": (0.30, 1.0), "gupton_logan": (0.20, 1.0),
    "rowe_armitage": (0.45, 0.5), "carter_kulhawy": (0.20, 0.5), "toh": (0.25, 1.0),
    "zhang_einstein": (0.40, 0.5),
}

#: How each correlation is written, for the tables and the report
FORMULAS = {
    "rosenberg_journeaux": "0.375·qu^0.515", "horvath_kenney": "0.21·qu^0.5",
    "meigh_wolski": "0.22·qu^0.6", "williams": "0.44·qu^0.36",
    "reynolds_kaderabek": "0.30·qu", "gupton_logan": "0.20·qu",
    "rowe_armitage": "0.45·qu^0.5", "carter_kulhawy": "0.20·qu^0.5", "toh": "0.25·qu",
    "zhang_einstein": "0.40·qu^0.5", "oneill_reese": "0.65·αE·pa·(qu/pa)^0.5",
    "kulhawy_2005": "pa·(qu/pa)^0.5",
    "coates": "3·qu", "base_rowe_armitage": "2.7·qu",
    "base_carter_kulhawy": "[√s + √(m√s + s)]·qu", "base_zhang_einstein": "4.83·qu^0.51",
    "aashto": "2.5·qu", "cfem": "3·Ksp·d·qu",
}

#: O'Neill & Reese's joint modification factor αE against Em/Ei
_ALPHA_E = [(0.0, 0.45), (0.05, 0.45), (0.1, 0.55), (0.3, 0.70), (0.5, 0.80), (1.0, 1.0)]


# --------------------------------------------------------------------------- #
#  Rock mass
# --------------------------------------------------------------------------- #

def modulus_ratio_rqd(RQD: float) -> float:
    """Gardner (1987): Em/Ei = 0.0231·RQD − 1.32, at least 0.15."""
    return min(max(0.0231 * RQD - 1.32, 0.15), 1.0)


def modulus_ratio_gsi(GSI: float, D: float) -> float:
    """Hoek & Diederichs (2006): Em/Ei = 0.02 + (1 − D/2)/(1 + e^((60 + 15D − GSI)/11))."""
    return 0.02 + (1.0 - D / 2.0) / (1.0 + math.exp((60.0 + 15.0 * D - GSI) / 11.0))


def alpha_E(ratio: float) -> float:
    xs = np.array([x for x, _ in _ALPHA_E])
    ys = np.array([y for _, y in _ALPHA_E])
    return float(np.interp(min(max(ratio, 0.0), 1.0), xs, ys))


def hoek_brown(GSI: float, mi: float, D: float) -> Dict[str, float]:
    """The generalised Hoek–Brown constants (Hoek, Carranza-Torres & Corkum 2002)."""
    mb = mi * math.exp((GSI - 100.0) / (28.0 - 14.0 * D))
    s = math.exp((GSI - 100.0) / (9.0 - 3.0 * D))
    a = 0.5 + (math.exp(-GSI / 15.0) - math.exp(-20.0 / 3.0)) / 6.0
    return {"mb": mb, "s": s, "a": a}


# --------------------------------------------------------------------------- #
#  Side shear and base resistance
# --------------------------------------------------------------------------- #

def side_shear(method: str, qu: float, fc: float, alpha: float) -> float:
    """Unit side shear [MPa] of one correlation; qu is already min(rock, concrete)."""
    if method in _POWER:
        a, b = _POWER[method]
        return a * qu ** b
    if method == "oneill_reese":
        fs = 0.65 * alpha * PA_MPA * math.sqrt(qu / PA_MPA)
        return min(fs, 7.8 * PA_MPA * math.sqrt(fc / PA_MPA))
    if method == "kulhawy_2005":
        return PA_MPA * math.sqrt(qu / PA_MPA)
    raise ValueError(f"unknown side shear method: {method}")


def ksp(spacing: float, aperture_mm: float, D: float) -> Dict[str, Any]:
    """The CFEM coefficient Ksp and whether the joints are in its range."""
    c, delta = max(spacing, 1e-6), aperture_mm / 1000.0
    value = (3.0 + c / D) / (10.0 * math.sqrt(1.0 + 300.0 * delta / c))
    valid = 0.05 < c / D < 2.0 and 0.0 <= delta / c < 0.02
    return {"Ksp": value, "valid": valid}


def base_resistance(method: str, qu: float, hb: Dict[str, float], D: float, Ls: float,
                    spacing: float, aperture: float) -> Dict[str, Any]:
    """Unit base resistance [MPa] of one method."""
    if method == "coates":
        return {"qb": 3.0 * qu}
    if method == "rowe_armitage":
        return {"qb": 2.7 * qu}
    if method == "carter_kulhawy":
        s, m = hb["s"], hb["mb"]
        return {"qb": (math.sqrt(s) + math.sqrt(m * math.sqrt(s) + s)) * qu}
    if method == "zhang_einstein":
        return {"qb": 4.83 * qu ** 0.51}
    if method == "aashto":
        return {"qb": 2.5 * qu}
    if method == "cfem":
        k = ksp(spacing, aperture, D)
        depth = min(1.0 + 0.4 * Ls / D, 3.0)
        return {"qb": 3.0 * k["Ksp"] * depth * qu, "Ksp": k["Ksp"], "d": depth,
                "valid": k["valid"]}
    raise ValueError(f"unknown base method: {method}")


# --------------------------------------------------------------------------- #
#  Elastic settlement
# --------------------------------------------------------------------------- #

def randolph_wroth(P: float, L: float, r0: float, G: float, Gb: float, nu: float,
                   Ep: float, with_base: bool = True, rho: float = 1.0,
                   eta: float = 1.0) -> Dict[str, float]:
    """Head settlement of a compressible pile in an elastic medium [m].

    Pt/(G·r0·wt) = [4η/((1 − ν)ξ) + (2πρ/ζ)·(tanh μL/μL)·(L/r0)]
                   / [1 + (1/(πλ))·(4η/((1 − ν)ξ))·(tanh μL/μL)·(L/r0)]
    ξ = G/Gb, λ = Ep/G, ζ = ln(rm/r0), rm = {0.25 + ξ[2.5ρ(1 − ν) − 0.25]}·L,
    μL = √(2/(ζλ))·(L/r0). G, Gb and Ep in kPa, P in kN.
    """
    L = max(L, 1e-3)
    xi = G / Gb if with_base else 1.0
    lam = Ep / G
    # The solution is meant for a shaft several radii long; for a stub the
    # radius of influence would fall inside the pile, so it is kept at 2·r0.
    rm = max((0.25 + xi * (2.5 * rho * (1.0 - nu) - 0.25)) * L, 2.0 * r0)
    zeta = math.log(rm / r0)
    mu_L = math.sqrt(2.0 / (zeta * lam)) * (L / r0)
    t = math.tanh(mu_L) / mu_L
    base = 4.0 * eta / ((1.0 - nu) * xi) if with_base else 0.0
    shaft = 2.0 * math.pi * rho / zeta * t * (L / r0)
    stiffness = G * r0 * (base + shaft) / (1.0 + base * t * (L / r0) / (math.pi * lam))
    base_share = base / (math.cosh(mu_L) * (base + shaft)) if with_base else 0.0
    return {"w": P / stiffness, "K": stiffness, "base_share": base_share, "zeta": zeta,
            "mu_L": mu_L, "lambda": lam, "rm": rm}


# --------------------------------------------------------------------------- #
#  The analysis
# --------------------------------------------------------------------------- #

class SocketAnalysis:
    """A pile socketed into rock. Build it, then call `run()`."""

    def __init__(self, config: Dict[str, Any]):
        self.config = copy.deepcopy(config)
        self.warnings: List = []
        self._read()
        self.results: Dict[str, Any] = {}

    def _read(self) -> None:
        s = {**DEFAULT_CONFIG["socket"], **(self.config.get("socket") or {})}
        w = {**DEFAULT_CONFIG["groundwater"], **(self.config.get("groundwater") or {})}
        o = {**DEFAULT_CONFIG["options"], **(self.config.get("options") or {})}
        self.D = num(s, "D", 1.0)
        self.Ls = num(s, "Ls", 0.0)
        self.top = num(s, "top", 0.0)
        self.rock_depth = num(s, "rock_depth", 0.0)
        self.Q = num(s, "Q", 0.0)
        self.qu = num(s, "qu", 0.0)
        self.RQD = min(max(num(s, "RQD", 100.0), 0.0), 100.0)
        self.Ei = num(s, "Ei", 0.0)
        self.modulus_method = (s.get("modulus_method") if s.get("modulus_method")
                               in MODULUS_METHODS else "rqd")
        self.Em_entered = num(s, "Em", 0.0)
        self.GSI = min(max(num(s, "GSI", 60.0), 5.0), 100.0)
        self.mi = max(num(s, "mi", 10.0), 1.0)
        self.D_blast = min(max(num(s, "D_blast", 0.0), 0.0), 1.0)
        self.nu = num(s, "nu_r", 0.25)
        self.Eb_ratio = max(num(s, "Eb_ratio", 1.0), 0.01)
        self.spacing = num(s, "spacing", 0.6)
        self.aperture = max(num(s, "aperture", 0.0), 0.0)
        self.fc = num(s, "fc", 30.0)
        self.Ec = num(s, "Ec", 30000.0)
        self.gamma_c = num(s, "gamma_c", 25.0)
        self.design = s.get("design") if s.get("design") in SOCKET_DESIGN else "mean"
        self.base_design = (s.get("base_design") if s.get("base_design") in SOCKET_BASE_DESIGN
                            else "min")
        self.FS_side = max(num(s, "FS_side", 2.5), 1.0)
        self.FS_base = max(num(s, "FS_base", 3.0), 1.0)
        self.min_ratio = max(num(s, "min_ratio", 1.0), 0.0)
        self.weak_rock = max(num(s, "weak_rock", 5.0), 0.0)
        self.zw = max(num(w, "depth", 0.0), 0.0)
        self.gw = num(w, "gamma_water", 9.81)
        self.buoyant = bool(o.get("buoyant_weight", True))
        self.subtract_weight = bool(o.get("subtract_weight", True))

        if self.D <= 0:
            raise PileError("err_socket_D")
        if self.Ls < 0:
            raise PileError("err_socket_Ls")
        if self.top < 0 or self.rock_depth < self.top:
            raise PileError("err_socket_rock_depth")
        if self.Q <= 0:
            raise PileError("err_socket_load")
        if self.qu <= 0 or self.fc <= 0:
            raise PileError("err_socket_qu")
        if self.Ec <= 0 or (self.modulus_method == "direct" and self.Em_entered <= 0) or \
                (self.modulus_method != "direct" and self.Ei <= 0):
            raise PileError("err_socket_modulus")
        if not 0.0 <= self.nu < 0.5:
            raise PileError("err_socket_nu")

    # ------------------------------------------------------------------ geometry
    @property
    def area(self) -> float:
        return math.pi * self.D ** 2 / 4.0

    @property
    def perimeter(self) -> float:
        return math.pi * self.D

    @property
    def overburden(self) -> float:
        """The length of pile above the rock surface."""
        return self.rock_depth - self.top

    def weight(self, Ls: float) -> float:
        """The weight of the whole pile with a socket this long, buoyant under water."""
        z1, z2 = self.top, self.rock_depth + Ls
        dry = max(min(z2, self.zw) - z1, 0.0)
        wet = max(z2 - max(z1, self.zw), 0.0)
        g_wet = self.gamma_c - (self.gw if self.buoyant else 0.0)
        return self.area * (self.gamma_c * dry + g_wet * wet)

    # ------------------------------------------------------------------ pieces
    def _modulus(self) -> Dict[str, float]:
        if self.modulus_method == "direct":
            Em = self.Em_entered
            ratio = Em / self.Ei if self.Ei > 0 else 1.0
        elif self.modulus_method == "gsi":
            ratio = modulus_ratio_gsi(self.GSI, self.D_blast)
            Em = self.Ei * ratio
        else:
            ratio = modulus_ratio_rqd(self.RQD)
            Em = self.Ei * ratio
        return {"Em": Em, "ratio": min(ratio, 1.0), "alpha_E": alpha_E(ratio)}

    def _base_design(self, Ls: float) -> float:
        """The design unit base resistance [kPa] for a socket this long."""
        if self.base_design == "none":
            return 0.0
        hb = hoek_brown(self.GSI, self.mi, self.D_blast)
        values = {key: 1000.0 * base_resistance(key, self.qu, hb, self.D, Ls, self.spacing,
                                                self.aperture)["qb"]
                  for key in SOCKET_BASE_METHODS}
        if self.base_design == "min":
            return min(values.values())
        if self.base_design == "mean":
            return statistics.fmean(values.values())
        return values[self.base_design]

    def capacity(self, Ls: float, fs: float) -> Dict[str, float]:
        """Ultimate and allowable capacity of a socket this long [kN]; fs, qb in kPa."""
        qb = self._base_design(Ls)
        Qs = self.perimeter * Ls * fs
        Qb = self.area * qb
        W = self.weight(Ls) if self.subtract_weight else 0.0
        Q_all = Qs / self.FS_side + Qb / self.FS_base - W
        Q_ult = Qs + Qb
        return {"Qs": Qs, "Qb": Qb, "qb": qb, "W": self.weight(Ls), "W_used": W,
                "Q_ult": Q_ult, "Q_ult_net": Q_ult - W, "Q_all": Q_all,
                "FS": (Q_ult - W) / self.Q, "utilisation": self.Q / Q_all if Q_all > 0
                else float("inf")}

    def required_length(self, fs: float, tolerance: float = 1e-3) -> float:
        """The shortest socket whose allowable capacity carries the load, by bisection."""
        if fs <= 0:
            return float("nan")
        if self.capacity(0.0, fs)["Q_all"] >= self.Q:
            return 0.0
        hi = MAX_SOCKET
        if self.capacity(hi, fs)["Q_all"] < self.Q:
            return float("nan")
        lo = 0.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if self.capacity(mid, fs)["Q_all"] >= self.Q:
                hi = mid
            else:
                lo = mid
            if hi - lo < tolerance:
                break
        return hi

    def settlement(self, Ls: float, fs: float) -> Dict[str, Any]:
        """The head settlement of the pile with a socket this long [m]."""
        Em = self.results["modulus"]["Em"]
        G = 1000.0 * Em / (2.0 * (1.0 + self.nu))
        Gb = G * self.Eb_ratio
        Ep = 1000.0 * self.Ec
        r0 = self.D / 2.0
        shortening = self.Q * self.overburden / (self.area * Ep)
        rw = randolph_wroth(self.Q, Ls, r0, G, Gb, self.nu, Ep, with_base=True)
        side = randolph_wroth(self.Q, Ls, r0, G, Gb, self.nu, Ep, with_base=False)
        cap = self.capacity(Ls, fs)
        vesic = single_pile(self.Q, cap["Qs"], cap["Qb"], max(Ls, 1e-3), self.D, self.area,
                            self.perimeter, self.Ec, Em * self.Eb_ratio, self.nu, Em, self.nu)
        return {
            "Ls": Ls, "shortening": shortening,
            "rw": {**rw, "total": rw["w"] + shortening},
            "rw_side": {**side, "total": side["w"] + shortening},
            "vesic": {**vesic, "total": vesic["s"] + shortening},
        }

    # ------------------------------------------------------------------ the run
    def run(self) -> Dict[str, Any]:
        modulus = self._modulus()
        self.results = {"modulus": modulus}
        qu_side = min(self.qu, self.fc)
        if self.fc < self.qu:
            self.warnings.append(message("warn_socket_concrete", fc=self.fc, qu=self.qu))

        side: Dict[str, dict] = {}
        for key in SOCKET_SIDE_METHODS:
            fs = 1000.0 * side_shear(key, qu_side, self.fc, modulus["alpha_E"])
            in_range = not (key in WEAK_ROCK_METHODS and self.qu > self.weak_rock)
            side[key] = {"fs": fs, "in_range": in_range, "formula": FORMULAS[key]}

        hb = hoek_brown(self.GSI, self.mi, self.D_blast)
        base: Dict[str, dict] = {}
        for key in SOCKET_BASE_METHODS:
            got = base_resistance(key, self.qu, hb, self.D, self.Ls, self.spacing,
                                  self.aperture)
            base[key] = {**got, "qb": 1000.0 * got["qb"],
                         "formula": FORMULAS.get(f"base_{key}", FORMULAS.get(key, ""))}
        if not base["cfem"].get("valid", True) and self.base_design in ("cfem", "mean", "min"):
            self.warnings.append(message("warn_socket_ksp"))
        self.results["base"] = base

        usable = [entry["fs"] for entry in side.values() if entry["in_range"]]
        if any(not entry["in_range"] for entry in side.values()):
            self.warnings.append(message("warn_socket_weak", qu=self.qu, limit=self.weak_rock))
        stats = {"mean": statistics.fmean(usable), "median": statistics.median(usable),
                 "lower": min(usable), "upper": max(usable), "n": len(usable)}
        if self.design in stats:
            fs_design = stats[self.design]
        else:
            fs_design = side[self.design]["fs"]
            if not side[self.design]["in_range"]:
                self.warnings.append(message("warn_socket_design_weak"))

        for key, entry in side.items():
            entry["Ls_req"] = self.required_length(entry["fs"])
            entry["Q_all"] = self.capacity(self.Ls, entry["fs"])["Q_all"]
        Ls_req = self.required_length(fs_design)
        minimum = self.min_ratio * self.D
        Ls_design = max(Ls_req, minimum) if math.isfinite(Ls_req) else float("nan")
        lengths = [entry["Ls_req"] for entry in side.values()
                   if entry["in_range"] and math.isfinite(entry["Ls_req"])]
        if not math.isfinite(Ls_req):
            self.warnings.append(message("warn_socket_no_length", hi=MAX_SOCKET))

        Ls_check = self.Ls if self.Ls > 0 else (Ls_design if math.isfinite(Ls_design) else 0.0)
        check = self.capacity(Ls_check, fs_design)
        check["status"] = "OK" if check["utilisation"] <= 1.0 + 1e-9 else "NOT OK"
        if self.Ls > 0 and math.isfinite(Ls_design) and self.Ls + 1e-9 < Ls_design:
            self.warnings.append(message("warn_socket_short", Ls=self.Ls, need=Ls_design))
        if check["qb"] > 1000.0 * self.fc:
            self.warnings.append(message("warn_socket_base_concrete",
                                         qb=check["qb"] / 1000.0, fc=self.fc))
        settle = self.settlement(max(Ls_check, 0.05), fs_design)

        self.results.update({
            "D": self.D, "A": self.area, "perimeter": self.perimeter, "Q": self.Q,
            "top": self.top, "rock_depth": self.rock_depth, "overburden": self.overburden,
            "Ls": self.Ls, "Ls_check": Ls_check, "qu": self.qu, "qu_side": qu_side,
            "hoek_brown": hb, "side": side, "stats": stats, "design": self.design,
            "fs_design": fs_design, "qb_design": check["qb"],
            "base_design": self.base_design,
            "Ls_req": Ls_req, "Ls_min": minimum, "Ls_design": Ls_design,
            "Ls_spread": (min(lengths), max(lengths)) if lengths else (float("nan"),) * 2,
            "check": check, "settlement": settle, "warnings": self.warnings,
        })
        return self.results

    def settlement_curve(self, lengths) -> List[dict]:
        """Head settlement against socket length, for the design chart."""
        out = []
        for Ls in lengths:
            got = self.settlement(max(float(Ls), 0.05), self.results["fs_design"])
            out.append({"Ls": float(Ls), "rw": got["rw"]["total"],
                        "rw_side": got["rw_side"]["total"], "vesic": got["vesic"]["total"],
                        "base_share": got["rw"]["base_share"]})
        return out


def analyse_socket(config: Dict[str, Any]) -> SocketAnalysis:
    analysis = SocketAnalysis(config)
    analysis.run()
    return analysis
