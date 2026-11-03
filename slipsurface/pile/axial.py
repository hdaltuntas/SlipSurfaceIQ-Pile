"""
Unit shaft friction and unit base resistance of a pile, per method.

Every function takes stresses in kPa and angles in degrees and gives a
resistance in kPa. The engine integrates the shaft friction down the pile
slice by slice and takes the base resistance in the layer the tip sits in;
nothing here knows about layers.

Shaft friction
    granular   fs = K·σ'v·tan δ, K = (K/K0)·(1 − sin φ')          (β method)
    cohesive   α methods — API RP 2A (1987), Kulhawy & Phoon (1993),
               Sladen (1992): fs = α·cu
               β method — Burland (1973), Meyerhof (1976):
               fs = (1 − sin φ')·tan φ'·√OCR·σ'v
               λ method — Vijayvergiya & Focht (1972): fs = λ·(σ'v + 2·cu)
    SPT        Meyerhof (1976): fs = 0.02·pa·N60 (large displacement),
               0.01·pa·N60 (otherwise)

Base resistance
    granular   Meyerhof (1976): qb = σ'v·Nq* ≤ 0.5·pa·Nq*·tan φ'
               Vesić (1977):    qb = σ'v·Nq*(Irr)
               Janbu (1976):    qb = σ'v·Nq*(η')
    cohesive   Skempton / Meyerhof: qb = 9·cu; Vesić: Nc*·cu; Janbu: Nc*·cu
    SPT        Meyerhof (1976): qb = 0.4·pa·N60·Lb/D ≤ 4·pa·N60
"""

from __future__ import annotations

import math
from typing import Dict

import numpy as np

from .config import PA

# --------------------------------------------------------------------------- #
#  Tables
# --------------------------------------------------------------------------- #

#: Meyerhof's (1976) bearing capacity factor Nq* for deep foundations, as
#: tabulated by Das (Principles of Foundation Engineering, Table 11.5).
#: Below 20° it is interpolated logarithmically down to Nq* = 1 at φ' = 0.
_MEYERHOF_NQ = {
    0: 1.0, 20: 12.4, 21: 13.8, 22: 15.5, 23: 17.9, 24: 21.4, 25: 26.0, 26: 29.5,
    27: 34.0, 28: 39.7, 29: 46.5, 30: 56.7, 31: 68.2, 32: 81.0, 33: 96.0, 34: 115.0,
    35: 143.0, 36: 168.0, 37: 194.0, 38: 231.0, 39: 276.0, 40: 346.0, 41: 420.0,
    42: 525.0, 43: 650.0, 44: 780.0, 45: 930.0,
}

#: Vijayvergiya & Focht's (1972) λ against the pile's penetration [m]
_LAMBDA = [(0, 0.500), (5, 0.336), (10, 0.245), (15, 0.200), (20, 0.173), (25, 0.150),
           (30, 0.136), (35, 0.132), (40, 0.127), (50, 0.118), (60, 0.113), (70, 0.110),
           (90, 0.110)]

#: K / K0 along the shaft by installation (Das: K0 for bored piles, K0…1.4·K0
#: for a small displacement, K0…1.8·K0 for a large one; the middle is used)
K_RATIO = {"bored": 1.0, "driven_low": 1.2, "driven_high": 1.4}


def meyerhof_nq(phi: float) -> float:
    """Meyerhof's Nq*, interpolated in the table (log-linear)."""
    phi = min(max(float(phi), 0.0), 45.0)
    keys = sorted(_MEYERHOF_NQ)
    xs = np.array(keys, dtype=float)
    ys = np.log(np.array([_MEYERHOF_NQ[k] for k in keys]))
    return float(np.exp(np.interp(phi, xs, ys)))


def lambda_factor(penetration: float) -> float:
    """Vijayvergiya & Focht's λ for a pile that penetrates this deep [m]."""
    xs = np.array([p for p, _ in _LAMBDA], dtype=float)
    ys = np.array([v for _, v in _LAMBDA])
    return float(np.interp(max(penetration, 0.0), xs, ys))


def K0(phi: float) -> float:
    """Jáky's at-rest coefficient of a normally consolidated soil."""
    return 1.0 - math.sin(math.radians(phi))


# --------------------------------------------------------------------------- #
#  Shaft friction
# --------------------------------------------------------------------------- #

def fs_granular(sigma_v: float, phi: float, K: float, delta: float) -> float:
    """K·σ'v·tan δ."""
    return max(K * sigma_v * math.tan(math.radians(delta)), 0.0)


def alpha_api(cu: float, sigma_v: float) -> float:
    """API RP 2A (1987): α = 0.5·ψ^-0.5 for ψ ≤ 1, 0.5·ψ^-0.25 above; ψ = cu/σ'v; α ≤ 1."""
    if cu <= 0:
        return 0.0
    psi = cu / max(sigma_v, 1e-6)
    alpha = 0.5 * psi ** -0.5 if psi <= 1.0 else 0.5 * psi ** -0.25
    return min(alpha, 1.0)


def alpha_kulhawy(cu: float) -> float:
    """Kulhawy & Phoon (1993), drilled shafts: α = 0.21 + 0.26·pa/cu ≤ 1."""
    if cu <= 0:
        return 0.0
    return min(0.21 + 0.26 * PA / cu, 1.0)


def alpha_sladen(cu: float, sigma_v: float, C: float) -> float:
    """Sladen (1992): α = C·(σ'v/cu)^0.45 ≤ 1."""
    if cu <= 0:
        return 0.0
    return min(C * (max(sigma_v, 0.0) / cu) ** 0.45, 1.0)


def beta_clay(phi: float, OCR: float) -> float:
    """Burland (1973), Meyerhof (1976): β = (1 − sin φ')·tan φ'·√OCR."""
    phi_r = math.radians(phi)
    return (1.0 - math.sin(phi_r)) * math.tan(phi_r) * math.sqrt(max(OCR, 1.0))


def fs_spt(N60: float, installation: str) -> float:
    """Meyerhof (1976): 0.02·pa·N60 for a large displacement pile, 0.01·pa·N60 otherwise."""
    factor = 0.02 if installation == "driven_high" else 0.01
    return factor * PA * max(N60, 0.0)


# --------------------------------------------------------------------------- #
#  Base resistance
# --------------------------------------------------------------------------- #

def tip_meyerhof(sigma_v: float, phi: float) -> Dict[str, float]:
    """Meyerhof (1976): qb = σ'v·Nq*, limited to ql = 0.5·pa·Nq*·tan φ'."""
    Nq = meyerhof_nq(phi)
    q = sigma_v * Nq
    limit = 0.5 * PA * Nq * math.tan(math.radians(phi))
    return {"qb": min(q, limit), "Nq": Nq, "limit": limit, "limited": q > limit}


def vesic_nq(phi: float, Irr: float) -> float:
    """Vesić's (1977) Nq* of a deep foundation for a reduced rigidity index Irr."""
    p = math.radians(phi)
    s = math.sin(p)
    return (3.0 / (3.0 - s) * math.exp((math.pi / 2.0 - p) * math.tan(p))
            * math.tan(math.pi / 4.0 + p / 2.0) ** 2
            * max(Irr, 1.0) ** (4.0 * s / (3.0 * (1.0 + s))))


def tip_vesic(sigma_v: float, phi: float, E: float, nu: float) -> Dict[str, float]:
    """Vesić (1977) in sand: qb = σ'o·Nσ* = σ'v·Nq*.

    Ir = Es / (2(1 + ν)·σ'v·tan φ'), reduced for the volume change of the
    plastic zone, Irr = Ir / (1 + Ir·Δ), Δ = 0.005·(1 − (φ' − 25)/20)·σ'v/pa.
    E is in MPa.
    """
    tan_phi = math.tan(math.radians(max(phi, 1e-3)))
    sv = max(sigma_v, 1e-3)
    Ir = 1000.0 * E / (2.0 * (1.0 + nu) * sv * tan_phi)
    delta = max(0.005 * (1.0 - (min(max(phi, 25.0), 45.0) - 25.0) / 20.0) * sv / PA, 0.0)
    Irr = Ir / (1.0 + Ir * delta)
    Nq = vesic_nq(phi, Irr)
    return {"qb": sigma_v * Nq, "Nq": Nq, "Ir": Ir, "Irr": Irr, "delta": delta}


def janbu_nq(phi: float, eta: float) -> float:
    """Janbu (1976): Nq* = (tan φ' + √(1 + tan² φ'))²·e^(2η'·tan φ')."""
    t = math.tan(math.radians(phi))
    return (t + math.sqrt(1.0 + t * t)) ** 2 * math.exp(2.0 * math.radians(eta) * t)


def tip_janbu(sigma_v: float, phi: float, eta: float) -> Dict[str, float]:
    Nq = janbu_nq(phi, eta)
    return {"qb": sigma_v * Nq, "Nq": Nq, "eta": eta}


def tip_clay(method: str, cu: float, E: float, eta: float) -> Dict[str, float]:
    """The undrained base resistance of a clay, net of the overburden.

    Meyerhof / Skempton: Nc* = 9. Vesić: Nc* = 4/3·(ln Ir + 1) + π/2 + 1,
    Ir = Es/(3·cu). Janbu at φ = 0: Nc* = 2 + 2η'.
    """
    if method == "vesic":
        Ir = max(1000.0 * E / (3.0 * cu), 1.0) if cu > 0 else 1.0
        Nc = 4.0 / 3.0 * (math.log(Ir) + 1.0) + math.pi / 2.0 + 1.0
        return {"qb": Nc * cu, "Nc": Nc, "Ir": Ir}
    if method == "janbu":
        Nc = 2.0 + 2.0 * math.radians(eta)
        return {"qb": Nc * cu, "Nc": Nc}
    return {"qb": 9.0 * cu, "Nc": 9.0}


def tip_spt(N60: float, embedment: float, D: float) -> Dict[str, float]:
    """Meyerhof (1976): qb = 0.4·pa·N60·Lb/D ≤ 4·pa·N60."""
    q = 0.4 * PA * N60 * max(embedment, 0.0) / D
    limit = 4.0 * PA * N60
    return {"qb": min(q, limit), "limit": limit, "limited": q > limit}
