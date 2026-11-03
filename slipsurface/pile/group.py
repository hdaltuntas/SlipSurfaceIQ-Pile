"""
Pile groups: the plan of the group, its efficiency, and block failure.

A rectangular group of nx × ny piles at spacings sx and sy. The efficiency η
is the share of n single-pile capacities the group actually develops:

    Converse–Labarre   η = 1 − θ·[(n1 − 1)·n2 + (n2 − 1)·n1] / (90·n1·n2),
                       θ = arctan(D/s) in degrees
    Los Angeles Group  η = 1 − D/(π·s·n1·n2)·[n1(n2 − 1) + n2(n1 − 1)
                           + √2·(n1 − 1)(n2 − 1)]
    Seiler–Keeney      η = 1 − [36·s/(75·s² − 7)]·(n1 + n2 − 2)/(n1 + n2 − 1)
                           + 0.3/(n1 + n2),       s in metres
    Feld               each pile loses 1/16 of its capacity for every pile
                       next to it, straight or diagonal

n1 and n2 are the rows and columns and s the spacing (the mean of the two
where they differ). Block failure takes the group as one deep block the size
of its outline: its shaft is soil on soil and its base carries the unit base
resistance over the whole footprint (Terzaghi & Peck; Das).
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple


def outline(nx: int, ny: int, sx: float, sy: float, D: float) -> Tuple[float, float]:
    """The width and length of the block the group occupies (Bg ≤ Lg)."""
    a = (nx - 1) * sx + D
    b = (ny - 1) * sy + D
    return min(a, b), max(a, b)


def positions(nx: int, ny: int, sx: float, sy: float) -> List[Tuple[float, float]]:
    """Plan coordinates of the piles, centred on the group."""
    x0 = -(nx - 1) * sx / 2.0
    y0 = -(ny - 1) * sy / 2.0
    return [(x0 + i * sx, y0 + j * sy) for j in range(ny) for i in range(nx)]


def converse_labarre(n1: int, n2: int, s: float, D: float) -> float:
    theta = math.degrees(math.atan(D / s))
    return 1.0 - theta * ((n1 - 1) * n2 + (n2 - 1) * n1) / (90.0 * n1 * n2)


def los_angeles(n1: int, n2: int, s: float, D: float) -> float:
    return 1.0 - D / (math.pi * s * n1 * n2) * (
        n1 * (n2 - 1) + n2 * (n1 - 1) + math.sqrt(2.0) * (n1 - 1) * (n2 - 1))


def seiler_keeney(n1: int, n2: int, s: float) -> float:
    if n1 + n2 <= 2:
        return 1.0
    denominator = 75.0 * s * s - 7.0
    if denominator <= 0:                     # below about 0.31 m the formula has no meaning
        return float("nan")
    return (1.0 - 36.0 * s / denominator * (n1 + n2 - 2) / (n1 + n2 - 1)
            + 0.3 / (n1 + n2))


def feld(nx: int, ny: int) -> float:
    """Feld's rule: 1/16 off for every neighbour, averaged over the group."""
    total = 0
    for i in range(nx):
        for j in range(ny):
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if (di or dj) and 0 <= i + di < nx and 0 <= j + dj < ny:
                        total += 1
    return 1.0 - total / (16.0 * nx * ny)


def efficiencies(nx: int, ny: int, sx: float, sy: float, D: float) -> Dict[str, float]:
    """Every efficiency the program knows, each capped at 1."""
    if nx * ny == 1:
        return {key: 1.0 for key in ("converse_labarre", "los_angeles", "seiler_keeney",
                                     "feld", "unity")}
    s = 0.5 * (sx + sy) if nx > 1 and ny > 1 else (sx if nx > 1 else sy)
    out = {
        "converse_labarre": converse_labarre(nx, ny, s, D),
        "los_angeles": los_angeles(nx, ny, s, D),
        "seiler_keeney": seiler_keeney(nx, ny, s),
        "feld": feld(nx, ny),
        "unity": 1.0,
    }
    return {key: (min(max(value, 0.0), 1.0) if math.isfinite(value) else value)
            for key, value in out.items()}


def skempton_nc(Bg: float, Lg: float, depth: float) -> float:
    """Skempton's Nc of a deep rectangle: 5·(1 + 0.2·Bg/Lg)·(1 + 0.2·D/Bg), D/Bg ≤ 2.5."""
    return 5.0 * (1.0 + 0.2 * Bg / Lg) * (1.0 + 0.2 * min(depth / Bg, 2.5))
