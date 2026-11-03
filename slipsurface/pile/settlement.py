"""
Settlement of a single pile and of a pile group.

Single pile — Vesić (1977), as set out by Das:

    s = s1 + s2 + s3
    s1 = (Qwb + ξ·Qws)·L / (Ap·Ep)              elastic shortening of the pile
    s2 = qwb·D·(1 − νs²)·Iwb / Es,  Iwb = 0.85   settlement from the base load
    s3 = Qws/(p·L)·D·(1 − νs²)·Iws / Es,
         Iws = 2 + 0.35·√(L/D)                   settlement from the shaft load

ξ = 0.5 for friction uniform or parabolic along the shaft, 0.67 for a
triangular distribution. The working load is shared between shaft and base
in the proportion of their ultimate resistances.

Group
    equivalent raft   (Terzaghi & Peck; Tomlinson) the load acts on a raft the
                      size of the group at 2/3 of the pile length and spreads
                      2 : 1 below it; the clay layers consolidate
                      (Cc, Cr, e0, OCR), the others compress with their
                      constrained modulus; the piles' shortening above the
                      raft is added
    Vesić (1969)      sg = s·√(Bg/D)
    Meyerhof (1976)   sg [mm] = 0.96·q·√Bg·I / N60, I = 1 − L/(8·Bg) ≥ 0.5,
                      q = Qg/(Bg·Lg) [kPa], sand only
"""

from __future__ import annotations

import math
from typing import Dict, List

#: The depth below which the added stress is too small to count, as a share of σ'v0
INFLUENCE = 0.10


def single_pile(Qw: float, Qs: float, Qb: float, L: float, D: float, Ap: float,
                perimeter: float, Ep: float, Es_base: float, nu_base: float,
                Es_shaft: float, nu_shaft: float, xi: float = 0.5) -> Dict[str, float]:
    """Vesić's settlement of one pile under the working load Qw [kN]; moduli in MPa."""
    total = Qs + Qb
    share = Qs / total if total > 0 else 1.0
    Qws, Qwb = Qw * share, Qw * (1.0 - share)
    Ep_k, Eb_k, Es_k = 1000.0 * Ep, 1000.0 * max(Es_base, 1e-6), 1000.0 * max(Es_shaft, 1e-6)
    s1 = (Qwb + xi * Qws) * L / (Ap * Ep_k)
    qwb = Qwb / Ap
    s2 = qwb * D * (1.0 - nu_base ** 2) * 0.85 / Eb_k
    Iws = 2.0 + 0.35 * math.sqrt(L / D)
    s3 = Qws / (perimeter * L) * D * (1.0 - nu_shaft ** 2) * Iws / Es_k
    return {"s1": s1, "s2": s2, "s3": s3, "s": s1 + s2 + s3, "Qws": Qws, "Qwb": Qwb,
            "Iws": Iws, "xi": xi}


def constrained_modulus(E: float, nu: float) -> float:
    """M = E·(1 − ν)/((1 + ν)(1 − 2ν)) [same units as E]."""
    nu = min(max(nu, 0.0), 0.49)
    return E * (1.0 - nu) / ((1.0 + nu) * (1.0 - 2.0 * nu))


def layer_compression(layer: dict, sigma0: float, dsigma: float, h: float) -> Dict[str, float]:
    """Compression of one slice under an added stress; a clay with Cc consolidates."""
    if dsigma <= 0 or h <= 0:
        return {"s": 0.0, "kind": "none"}
    if layer["behaviour"] == "cohesive" and layer.get("Cc", 0.0) > 0 and sigma0 > 0:
        e0 = max(layer.get("e0", 0.0), 0.0)
        Cc, Cr = layer["Cc"], max(layer.get("Cr", 0.0), 0.0)
        sp = sigma0 * max(layer.get("OCR", 1.0), 1.0)
        final = sigma0 + dsigma
        if final <= sp:
            strain = Cr * math.log10(final / sigma0)
        else:
            strain = Cr * math.log10(sp / sigma0) + Cc * math.log10(final / sp)
        return {"s": h * strain / (1.0 + e0), "kind": "consolidation"}
    M = 1000.0 * constrained_modulus(max(layer.get("E", 0.0), 1e-6), layer.get("nu", 0.3))
    return {"s": dsigma * h / M, "kind": "elastic"}


def equivalent_raft(profile, Q: float, Bg: float, Lg: float, z_raft: float,
                    spread: float = 2.0, slice_size: float = 0.5) -> Dict[str, object]:
    """Settlement of the equivalent raft at depth z_raft, by slices below it.

    The slices run to the bottom of the profile, or to where the added stress
    falls below a tenth of the effective overburden, whichever is shallower.
    """
    rows: List[dict] = []
    total = consolidation = elastic = 0.0
    bottom = profile.depth
    z_stop = bottom
    for layer, z, h in profile.slices(z_raft, bottom, slice_size):
        depth = z - z_raft
        widen = depth / spread
        dsigma = Q / ((Bg + widen) * (Lg + widen))
        sigma0 = profile.effective_stress(z)
        if sigma0 > 0 and dsigma < INFLUENCE * sigma0:
            z_stop = z - h / 2.0
            break
        part = layer_compression(layer, sigma0, dsigma, h)
        total += part["s"]
        if part["kind"] == "consolidation":
            consolidation += part["s"]
        else:
            elastic += part["s"]
        rows.append({"z": z, "h": h, "layer": layer["name"], "sigma0": sigma0,
                     "dsigma": dsigma, "s": part["s"], "kind": part["kind"]})
    return {"s": total, "consolidation": consolidation, "elastic": elastic,
            "rows": rows, "z_raft": z_raft, "z_stop": z_stop,
            "q": Q / (Bg * Lg), "reached_bottom": z_stop >= bottom - 1e-9}


def vesic_group(s_single: float, Bg: float, D: float) -> float:
    return s_single * math.sqrt(Bg / D)


def meyerhof_group(q: float, Bg: float, L: float, N60: float) -> Dict[str, float]:
    """Meyerhof's SPT rule for a group in sand [m]."""
    I = max(1.0 - L / (8.0 * Bg), 0.5)
    s_mm = 0.96 * q * math.sqrt(Bg) * I / N60
    return {"s": s_mm / 1000.0, "I": I, "N60": N60, "q": q}
