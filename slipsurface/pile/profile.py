"""
The layered soil column: where each layer is, and the stresses in it.

The layers run from the ground surface down; the last one is taken as
continuing below the profile wherever a stress is asked for deeper than it
reaches. Stresses are the in-situ vertical total stress σv0, the hydrostatic
pore pressure u0 below the water table, and the effective stress σ'v0.
"""

from __future__ import annotations

from typing import List, Tuple


class Profile:
    """The layered soil column and its in-situ stresses."""

    def __init__(self, layers: List[dict], water_depth: float, gamma_w: float):
        self.layers = layers
        self.zw = water_depth
        self.gw = gamma_w
        top = 0.0
        for layer in layers:
            layer["top"] = top
            layer["bottom"] = top + layer["thickness"]
            top = layer["bottom"]
        self.depth = top

    def layer_at(self, z: float) -> dict:
        """The layer containing depth z; the last one continues below the profile."""
        for layer in self.layers:
            if z < layer["bottom"] - 1e-12:
                return layer
        return self.layers[-1]

    def total_stress(self, z: float) -> float:
        """σv0 at depth z."""
        z = max(float(z), 0.0)
        sigma = 0.0
        for i, layer in enumerate(self.layers):
            top = layer["top"]
            bottom = layer["bottom"] if i < len(self.layers) - 1 else float("inf")
            if z <= top:
                break
            seg = min(z, bottom)
            dry = max(min(seg, self.zw) - top, 0.0)
            wet = max(seg - max(top, self.zw), 0.0)
            sigma += layer["gamma"] * dry + layer["gamma_sat"] * wet
        return sigma

    def pore_pressure(self, z: float) -> float:
        return self.gw * max(float(z) - self.zw, 0.0)

    def effective_stress(self, z: float) -> float:
        return self.total_stress(z) - self.pore_pressure(z)

    def segments(self, z1: float, z2: float) -> List[Tuple[dict, float, float]]:
        """The (layer, top, bottom) pieces the depth range z1…z2 is made of."""
        out = []
        for i, layer in enumerate(self.layers):
            top = layer["top"]
            bottom = layer["bottom"] if i < len(self.layers) - 1 else max(z2, layer["bottom"])
            lo, hi = max(z1, top), min(z2, bottom)
            if hi - lo > 1e-9:
                out.append((layer, lo, hi))
        return out

    def slices(self, z1: float, z2: float, size: float = 0.25) -> List[Tuple[dict, float, float]]:
        """The range z1…z2 cut into thin slices that never straddle a layer
        boundary: (layer, mid-depth, thickness) each, for the integrals along
        the shaft and below the group."""
        out = []
        for layer, lo, hi in self.segments(z1, z2):
            n = max(int(round((hi - lo) / size)), 1)
            h = (hi - lo) / n
            for k in range(n):
                out.append((layer, lo + (k + 0.5) * h, h))
        return out

    def average(self, key: str, z1: float, z2: float, behaviour: str = "") -> float:
        """A layer property averaged over z1…z2 by thickness; only over the
        layers of one behaviour if one is named. nan when nothing is there."""
        total = value = 0.0
        for layer, lo, hi in self.segments(z1, z2):
            if behaviour and layer["behaviour"] != behaviour:
                continue
            total += hi - lo
            value += (hi - lo) * layer[key]
        return value / total if total > 0 else float("nan")
