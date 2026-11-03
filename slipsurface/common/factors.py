"""
Bearing capacity factors, and the corrections that go with them.

Everything here is a closed-form expression evaluated for one set of numbers:
a friction angle, a shape, an embedment, a load. Nothing knows about soil
layers, the interface or the units of the rest of the program, so each factor
can be checked against its published table on its own.

Factor sets (`bearing_factors`)
    terzaghi   Terzaghi (1943). Nq from the Prandtl-type wedge with a rough
               base, Nc = (Nq − 1)cot φ (5.7 at φ = 0), and Nγ from Bowles's
               fit to Kumbhojkar's (1993) integration of Terzaghi's Kpγ.
               Shape factors only: the method has no depth, inclination,
               base tilt or ground slope factors.
    meyerhof   Meyerhof (1963). Nq = e^(π tan φ)·tan²(45 + φ/2),
               Nc = (Nq − 1)cot φ, Nγ = (Nq − 1)·tan(1.4 φ), with Meyerhof's
               own shape, depth and inclination factors.
    hansen     Brinch Hansen (1970). Nγ = 1.5(Nq − 1)tan φ, with the full set
               of shape, depth, inclination, base tilt and ground slope
               factors, and the additive form at φ = 0.
    vesic      Vesić (1973). Nγ = 2(Nq + 1)tan φ, the same corrections as
               Hansen's with Vesić's own exponents, and the compressibility
               factors of the rigidity index.
    ec7        EN 1997-1 Annex D. Nγ = 2(Nq − 1)tan φ, with the Annex's shape,
               inclination and base inclination factors, and its undrained
               expression (π + 2)·cu.
    skempton   Skempton (1951): the undrained Nc of a cohesive soil as a
               function of B/L and D/B.

Angles are given in degrees at the boundary of this module and turned into
radians inside it; every function returns plain floats.
"""

from __future__ import annotations

import math
from typing import Dict

__all__ = ["bearing_factors", "shape_factors", "depth_factors", "inclination_factors",
           "base_factors", "ground_factors", "compressibility_factors", "skempton_nc",
           "local_shear", "all_factors", "HAS_DEPTH", "HAS_INCLINATION", "HAS_BASE",
           "HAS_GROUND", "NC_PHI0"]

#: Nc at φ = 0: Prandtl's π + 2 for every method but Terzaghi's, which is 5.7
NC_PHI0 = {"terzaghi": 5.7, "meyerhof": 5.14, "hansen": 5.14, "vesic": 5.14,
           "ec7": 5.14, "skempton": 5.14}

#: Which method defines which correction. A method that defines none borrows
#: the nearest set only when the interface asks for it, and says so.
HAS_DEPTH = {"terzaghi": False, "meyerhof": True, "hansen": True, "vesic": True,
             "ec7": False, "skempton": True}
HAS_INCLINATION = {"terzaghi": False, "meyerhof": True, "hansen": True, "vesic": True,
                   "ec7": True, "skempton": False}
HAS_BASE = {"terzaghi": False, "meyerhof": False, "hansen": True, "vesic": True,
            "ec7": True, "skempton": False}
HAS_GROUND = {"terzaghi": False, "meyerhof": False, "hansen": True, "vesic": True,
              "ec7": False, "skempton": False}

#: Below this the friction angle is treated as zero (an undrained analysis)
PHI_ZERO = 1e-6

ONE = {"c": 1.0, "q": 1.0, "g": 1.0}


def _identity(method: str, phi: float) -> Dict[str, float]:
    """The value a correction takes when there is nothing to correct.

    Hansen's undrained expression adds its corrections to the bracket instead
    of multiplying them through, so there the identity of the cohesion
    correction is zero, not one.
    """
    if method == "hansen" and phi <= PHI_ZERO:
        return {"c": 0.0, "q": 1.0, "g": 1.0}
    return dict(ONE)


def _rad(deg: float) -> float:
    return math.radians(float(deg))


def _kp(phi: float) -> float:
    """Rankine's passive coefficient, tan²(45 + φ/2)."""
    return math.tan(_rad(45.0 + phi / 2.0)) ** 2


# --------------------------------------------------------------------------- #
#  Bearing capacity factors
# --------------------------------------------------------------------------- #

def _nq_prandtl(phi: float) -> float:
    """Reissner's Nq = e^(π tan φ)·tan²(45 + φ/2) — every method but Terzaghi's."""
    p = _rad(phi)
    return math.exp(math.pi * math.tan(p)) * _kp(phi)


def _nq_terzaghi(phi: float) -> float:
    """Terzaghi's Nq: the wedge below a rough base, a = e^((3π/2 − φ)tan φ)."""
    p = _rad(phi)
    a = math.exp((1.5 * math.pi - p) * math.tan(p))
    return a / (2.0 * math.cos(_rad(45.0 + phi / 2.0)) ** 2)


def bearing_factors(phi: float, method: str = "vesic") -> Dict[str, float]:
    """Nc, Nq and Nγ of one factor set, for a friction angle in degrees."""
    phi = float(phi)
    if phi < 0:
        raise ValueError("the friction angle cannot be negative")
    p = _rad(phi)
    nq = _nq_terzaghi(phi) if method == "terzaghi" else _nq_prandtl(phi)
    if phi <= PHI_ZERO:
        nq = 1.0
        nc = NC_PHI0.get(method, 5.14)
    else:
        nc = (nq - 1.0) / math.tan(p)

    if phi <= PHI_ZERO:
        ngamma = 0.0
    elif method == "terzaghi":
        # Bowles's fit to Kumbhojkar's (1993) integration of Terzaghi's Kpγ
        ngamma = 2.0 * (nq + 1.0) * math.tan(p) / (1.0 + 0.4 * math.sin(4.0 * p))
    elif method == "meyerhof":
        ngamma = (nq - 1.0) * math.tan(1.4 * p)
    elif method == "hansen":
        ngamma = 1.5 * (nq - 1.0) * math.tan(p)
    elif method == "vesic":
        ngamma = 2.0 * (nq + 1.0) * math.tan(p)
    elif method == "ec7":
        ngamma = 2.0 * (nq - 1.0) * math.tan(p)
    elif method == "skempton":
        ngamma = 0.0                      # an undrained method: φ = 0
    else:
        raise ValueError(f"unknown method: {method}")
    return {"Nc": nc, "Nq": nq, "Ngamma": ngamma}


def skempton_nc(B: float, L: float, Df: float) -> float:
    """Skempton's (1951) undrained Nc: 5(1 + 0.2 B/L)(1 + 0.2 D/B) ≤ 7.5(1 + 0.2 B/L)."""
    B = max(float(B), 1e-9)
    ratio = min(max(B / max(float(L), B), 0.0), 1.0)
    shape = 1.0 + 0.2 * ratio
    return min(5.0 * shape * (1.0 + 0.2 * max(float(Df), 0.0) / B), 7.5 * shape)


def local_shear(c: float, phi: float) -> tuple:
    """Terzaghi's local-shear reduction: c* = 2c/3, φ* = arctan(2 tan φ / 3)."""
    return 2.0 * float(c) / 3.0, math.degrees(math.atan(2.0 * math.tan(_rad(phi)) / 3.0))


# --------------------------------------------------------------------------- #
#  Shape
# --------------------------------------------------------------------------- #

def shape_factors(method: str, B: float, L: float, phi: float,
                  N: Dict[str, float], shape: str = "rectangle") -> Dict[str, float]:
    """sc, sq and sγ. B and L are the effective dimensions, B ≤ L."""
    if shape == "strip":
        return dict(ONE)
    ratio = min(max(float(B) / max(float(L), 1e-9), 0.0), 1.0)
    if shape == "circle":
        ratio = 1.0

    if method == "terzaghi":
        # 1.3 and 0.8 for a square, 1.3 and 0.6 for a circle, interpolated
        # linearly with B/L for a rectangle; the surcharge term is unchanged.
        if shape == "circle":
            return {"c": 1.3, "q": 1.0, "g": 0.6}
        return {"c": 1.0 + 0.3 * ratio, "q": 1.0, "g": 1.0 - 0.2 * ratio}

    if method == "meyerhof":
        kp = _kp(phi)
        sc = 1.0 + 0.2 * kp * ratio
        sq = 1.0 + 0.1 * kp * ratio if phi >= 10.0 else 1.0
        return {"c": sc, "q": sq, "g": sq}

    if method in ("hansen", "vesic"):
        if phi <= PHI_ZERO:
            # Hansen's additive sc' = 0.2 B/L; the same number multiplied
            # through Nc = 5.14 for Vesić, whose form stays multiplicative.
            return {"c": 1.0 + 0.2 * ratio, "q": 1.0, "g": 1.0}
        sc = 1.0 + (N["Nq"] / N["Nc"]) * ratio
        sq = 1.0 + ratio * math.tan(_rad(phi))
        return {"c": sc, "q": sq, "g": max(1.0 - 0.4 * ratio, 0.6)}

    if method == "ec7":
        if phi <= PHI_ZERO:
            return {"c": 1.0 + 0.2 * ratio, "q": 1.0, "g": 1.0}
        sq = 1.0 + ratio * math.sin(_rad(phi))
        sg = 1.0 - 0.3 * ratio
        sc = (sq * N["Nq"] - 1.0) / (N["Nq"] - 1.0)
        return {"c": sc, "q": sq, "g": sg}

    if method == "skempton":
        return dict(ONE)                  # the shape is already inside Skempton's Nc
    raise ValueError(f"unknown method: {method}")


# --------------------------------------------------------------------------- #
#  Depth
# --------------------------------------------------------------------------- #

def depth_factors(method: str, B: float, Df: float, phi: float) -> Dict[str, float]:
    """dc, dq and dγ. Terzaghi's and Skempton's methods carry no depth factor;
    EN 1997-1 Annex D gives none either, and borrows Hansen's when asked."""
    if method in ("terzaghi", "skempton"):
        return dict(ONE)
    B = max(float(B), 1e-9)
    Df = max(float(Df), 0.0)

    if method == "meyerhof":
        root_kp = math.sqrt(_kp(phi))
        dc = 1.0 + 0.2 * root_kp * Df / B
        dq = 1.0 + 0.1 * root_kp * Df / B if phi >= 10.0 else 1.0
        return {"c": dc, "q": dq, "g": dq}

    # Hansen's factors, which Vesić keeps and EN 1997-1 borrows
    k = Df / B if Df <= B else math.atan(Df / B)
    p = _rad(phi)
    if phi <= PHI_ZERO:
        return {"c": 1.0 + 0.4 * k, "q": 1.0, "g": 1.0}
    dq = 1.0 + 2.0 * math.tan(p) * (1.0 - math.sin(p)) ** 2 * k
    return {"c": 1.0 + 0.4 * k, "q": dq, "g": 1.0}


# --------------------------------------------------------------------------- #
#  Load inclination
# --------------------------------------------------------------------------- #

def _m_exponent(B: float, L: float, Hb: float, Hl: float) -> float:
    """Vesić's exponent m for a horizontal load of any direction in plan."""
    ratio = max(float(B), 1e-9) / max(float(L), 1e-9)
    mB = (2.0 + ratio) / (1.0 + ratio)
    mL = (2.0 + 1.0 / ratio) / (1.0 + 1.0 / ratio)
    h2 = Hb ** 2 + Hl ** 2
    if h2 <= 0:
        return mB
    return mB * Hb ** 2 / h2 + mL * Hl ** 2 / h2


def inclination_factors(method: str, V: float, Hb: float, Hl: float, B: float, L: float,
                        area: float, c: float, phi: float,
                        N: Dict[str, float]) -> Dict[str, float]:
    """ic, iq and iγ for a resultant inclined by the horizontal load.

    `area` is the effective area A', `c` the cohesion (c' drained, cu
    undrained) and V the vertical load. Terzaghi's and Skempton's methods
    carry no inclination factor.
    """
    if method in ("terzaghi", "skempton"):
        return _identity(method, phi)
    H = math.hypot(float(Hb), float(Hl))
    V = float(V)
    if H <= 0 or V <= 0:
        return _identity(method, phi)
    p = _rad(phi)
    undrained = phi <= PHI_ZERO

    if method == "meyerhof":
        alpha = math.degrees(math.atan2(H, V))
        ic = iq = max(1.0 - alpha / 90.0, 0.0) ** 2
        ig = 1.0 if undrained else max(1.0 - alpha / max(phi, 1e-9), 0.0) ** 2
        return {"c": ic, "q": iq, "g": ig}

    # The denominator V + A'·ca·cot φ of Hansen, Vesić and EN 1997-1
    cot = 0.0 if undrained else 1.0 / math.tan(p)
    denom = V + float(area) * float(c) * cot

    if method == "hansen":
        if undrained:
            # the additive form: ic' is subtracted from the bracket
            ratio = min(H / max(float(area) * float(c), 1e-9), 1.0)
            return {"c": 0.5 - 0.5 * math.sqrt(max(1.0 - ratio, 0.0)), "q": 1.0, "g": 1.0}
        iq = max(1.0 - 0.5 * H / denom, 0.0) ** 5
        ig = max(1.0 - 0.7 * H / denom, 0.0) ** 5
        ic = iq - (1.0 - iq) / (N["Nq"] - 1.0)
        return {"c": ic, "q": iq, "g": ig}

    m = _m_exponent(B, L, Hb, Hl)
    if method == "vesic":
        if undrained:
            ic = 1.0 - m * H / (max(float(area) * float(c), 1e-9) * N["Nc"])
            return {"c": max(ic, 0.0), "q": 1.0, "g": 1.0}
        iq = max(1.0 - H / denom, 0.0) ** m
        ig = max(1.0 - H / denom, 0.0) ** (m + 1.0)
        ic = iq - (1.0 - iq) / (N["Nq"] - 1.0)
        return {"c": max(ic, 0.0), "q": iq, "g": ig}

    if method == "ec7":
        if undrained:
            ratio = min(H / max(float(area) * float(c), 1e-9), 1.0)
            return {"c": 0.5 * (1.0 + math.sqrt(max(1.0 - ratio, 0.0))), "q": 1.0, "g": 1.0}
        iq = max(1.0 - H / denom, 0.0) ** m
        ig = max(1.0 - H / denom, 0.0) ** (m + 1.0)
        ic = (iq * N["Nq"] - 1.0) / (N["Nq"] - 1.0)
        return {"c": max(ic, 0.0), "q": iq, "g": ig}
    raise ValueError(f"unknown method: {method}")


# --------------------------------------------------------------------------- #
#  Base tilt and ground slope
# --------------------------------------------------------------------------- #

def base_factors(method: str, eta: float, phi: float, N: Dict[str, float]) -> Dict[str, float]:
    """bc, bq and bγ for a base tilted by η degrees from the horizontal."""
    if method in ("terzaghi", "meyerhof", "skempton") or abs(eta) < 1e-9:
        return _identity(method, phi)
    e = _rad(abs(eta))
    p = _rad(phi)
    undrained = phi <= PHI_ZERO

    if method == "hansen":
        if undrained:                      # additive: bc' is subtracted
            return {"c": abs(eta) / 147.0, "q": 1.0, "g": 1.0}
        return {"c": 1.0 - abs(eta) / 147.0,
                "q": math.exp(-2.0 * e * math.tan(p)),
                "g": math.exp(-2.7 * e * math.tan(p))}

    # Vesić and EN 1997-1 share bq = bγ = (1 − η tan φ)²
    bq = max(1.0 - e * math.tan(p), 0.0) ** 2
    if undrained:
        return {"c": 1.0 - 2.0 * e / (math.pi + 2.0), "q": 1.0, "g": 1.0}
    if method == "vesic":
        bc = bq - (1.0 - bq) / (N["Nc"] * math.tan(p))
    elif method == "ec7":
        bc = (bq * N["Nq"] - 1.0) / (N["Nq"] - 1.0)
    else:
        raise ValueError(f"unknown method: {method}")
    return {"c": bc, "q": bq, "g": bq}


def ground_factors(method: str, beta: float, phi: float,
                   N: Dict[str, float]) -> Dict[str, float]:
    """gc, gq and gγ for ground sloping away at β degrees.

    Only Hansen's and Vesić's methods define them; EN 1997-1 borrows Vesić's
    when the interface asks for it.
    """
    if method in ("terzaghi", "meyerhof", "skempton") or abs(beta) < 1e-9:
        return _identity(method, phi)
    b = _rad(abs(beta))
    p = _rad(phi)
    undrained = phi <= PHI_ZERO

    if method == "hansen":
        if undrained:                      # additive: gc' is subtracted
            return {"c": abs(beta) / 147.0, "q": 1.0, "g": 1.0}
        gq = max(1.0 - 0.5 * math.tan(b), 0.0) ** 5
        return {"c": 1.0 - abs(beta) / 147.0, "q": gq, "g": gq}

    gq = max(1.0 - math.tan(b), 0.0) ** 2
    if undrained:
        return {"c": 1.0 - 2.0 * b / (math.pi + 2.0), "q": 1.0, "g": 1.0}
    gc = gq - (1.0 - gq) / (N["Nc"] * math.tan(p))
    return {"c": gc, "q": gq, "g": gq}


# --------------------------------------------------------------------------- #
#  Compressibility (Vesić 1973)
# --------------------------------------------------------------------------- #

def compressibility_factors(B: float, L: float, phi: float, c: float, q: float,
                            G: float, N: Dict[str, float]) -> Dict[str, float]:
    """Vesić's Fc, Fq and Fγ from the rigidity index Ir = G/(c + q·tan φ).

    Below the critical rigidity index the soil punches rather than shears
    along a full failure surface, and the capacity is reduced. `q` is the
    effective overburden at about B/2 below the base and `G` the shear
    modulus, both in the same units as `c`.
    """
    if G <= 0:
        return dict(ONE)
    p = _rad(phi)
    ratio = min(max(float(B) / max(float(L), 1e-9), 0.0), 1.0)
    denom = float(c) + float(q) * math.tan(p)
    if denom <= 0:
        return dict(ONE)
    ir = float(G) / denom
    ir_crit = 0.5 * math.exp((3.30 - 0.45 * ratio) / math.tan(_rad(45.0 - phi / 2.0)))
    if ir >= ir_crit:
        return dict(ONE)

    exponent = ((-4.4 + 0.6 * ratio) * math.tan(p)
                + (3.07 * math.sin(p) * math.log10(2.0 * ir)) / (1.0 + math.sin(p)))
    fq = math.exp(exponent)
    fq = min(max(fq, 0.0), 1.0)
    if phi <= PHI_ZERO:
        fc = min(0.32 + 0.12 * ratio + 0.60 * math.log10(ir), 1.0)
    else:
        fc = fq - (1.0 - fq) / (N["Nq"] * math.tan(p))
    return {"c": min(max(fc, 0.0), 1.0), "q": fq, "g": fq,
            "Ir": ir, "Ir_crit": ir_crit}


# --------------------------------------------------------------------------- #
#  Everything at once
# --------------------------------------------------------------------------- #

def all_factors(method: str, *, B: float, L: float, Df: float, phi: float, c: float,
                V: float = 0.0, Hb: float = 0.0, Hl: float = 0.0, area: float = 0.0,
                eta: float = 0.0, beta: float = 0.0, shape: str = "rectangle",
                G: float = 0.0, q_mid: float = 0.0,
                use_shape: bool = True, use_depth: bool = True,
                use_inclination: bool = True, use_base: bool = True,
                use_ground: bool = True, use_compressibility: bool = False) -> Dict[str, Dict]:
    """Every factor of one method, gathered for the capacity equation.

    The returned dictionary holds the bearing capacity factors under ``N`` and
    each correction under its own name (``shape``, ``depth``, ``inclination``,
    ``base``, ``ground``, ``compressibility``), each a mapping
    ``{"c": …, "q": …, "g": …}``. A correction switched off, or one the method
    does not define, is the identity.
    """
    N = bearing_factors(phi, method)
    if method == "skempton":
        N = {"Nc": skempton_nc(B, L, Df), "Nq": 1.0, "Ngamma": 0.0}
    out = {"N": N}
    out["shape"] = (shape_factors(method, B, L, phi, N, shape) if use_shape else dict(ONE))
    out["depth"] = (depth_factors(method, B, Df, phi) if use_depth else dict(ONE))
    out["inclination"] = (inclination_factors(method, V, Hb, Hl, B, L, area, c, phi, N)
                          if use_inclination else _identity(method, phi))
    out["base"] = (base_factors(method, eta, phi, N) if use_base
                   else _identity(method, phi))
    out["ground"] = (ground_factors(method, beta, phi, N) if use_ground
                     else _identity(method, phi))
    out["compressibility"] = (compressibility_factors(B, L, phi, c, q_mid, G, N)
                              if use_compressibility else dict(ONE))
    return out
