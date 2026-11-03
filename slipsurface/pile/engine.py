"""
The axial analysis of a pile, and of a group of them, in a layered profile.

Given the pile (shape, size, head depth, length, installation, material), the
load on the group, the layout of the group, the groundwater level and the soil
layers, `PileAnalysis.run()` works out

    * the in-situ stresses σv0, u0 and σ'v0 down the shaft and at the tip,
      with Meyerhof's critical depth in sand if asked for
    * the shaft friction by every method — the clay methods side by side, the
      granular layers by K·σ'v·tan δ — and the base resistance by Meyerhof,
      Vesić and Janbu, and Meyerhof's SPT rule where blow counts are given
    * the pile's weight, buoyant below the water table, taken off the ultimate
      capacity: Qult,net = Qs + Qb − W, Qall = Qult,net / FS
    * the group efficiency by every method, block failure, and the capacity of
      the group
    * the settlement of one pile (Vesić) and of the group (equivalent raft,
      Vesić's √(Bg/D) rule, Meyerhof's SPT rule)
    * under the seismic load combination, the load on every pile of a rigid
      cap, the compression check of the most loaded pile, and the uplift of
      the piles in tension — shaft friction in tension plus the pile's weight —
      and of the whole block when the group as a whole is lifted
    * the shortest pile that satisfies the single-pile and the group check,
      and the seismic checks when the earthquake is on

Input problems are raised as `PileError`, which carries a translation key, so
the interface can say what is wrong in the user's language.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List

from . import axial
from . import group as grp
from . import settlement as stl
from .config import (
    BEHAVIOURS,
    CLAY_METHODS,
    DEFAULT_CONFIG,
    EFFICIENCY_METHODS,
    GROUP_SETTLEMENT,
    INSTALLATIONS,
    SHAPES,
    SKIN_DISTRIBUTIONS,
    TIP_METHODS,
)
from .errors import PileError, message, num
from .profile import Profile

#: Thickness of the slices the shaft friction is integrated over [m]
SLICE = 0.25

#: Depth below the tip in which a weaker layer is looked for, in diameters
BELOW_TIP = 3.0

#: The spacing below which a group is closer than the usual minimum, in diameters
MIN_SPACING = 2.5

#: Layer properties that are numbers, with their defaults
LAYER_NUMBERS = {"thickness": 0.0, "gamma": 18.0, "gamma_sat": 19.0, "phi": 0.0, "cu": 0.0,
                 "OCR": 1.0, "N60": 0.0, "E": 10.0, "nu": 0.3, "Cc": 0.0, "Cr": 0.0,
                 "e0": 0.0}


class PileAnalysis:
    """Axial capacity and settlement of one pile and its group. Build it, then `run()`."""

    def __init__(self, config: Dict[str, Any]):
        self.config = copy.deepcopy(config)
        self.warnings: List = []
        self._read()
        self.results: Dict[str, Any] = {}

    # ------------------------------------------------------------------ input
    def _read(self) -> None:
        cfg, base = self.config, DEFAULT_CONFIG
        p = {**base["pile"], **(cfg.get("pile") or {})}
        load = {**base["loading"], **(cfg.get("loading") or {})}
        g = {**base["group"], **(cfg.get("group") or {})}
        w = {**base["groundwater"], **(cfg.get("groundwater") or {})}
        o = {**base["options"], **(cfg.get("options") or {})}
        s = {**base["settlement"], **(cfg.get("settlement") or {})}
        e = {**base["seismic"], **(cfg.get("seismic") or {})}
        c = {**base["criteria"], **(cfg.get("criteria") or {})}

        self.shape = p["shape"] if p.get("shape") in SHAPES else "circular"
        self.D = num(p, "D", 0.0)
        self.L = num(p, "L", 0.0)
        self.top = num(p, "top", 0.0)
        self.installation = (p["installation"] if p.get("installation") in INSTALLATIONS
                             else "bored")
        self.gamma_p = num(p, "gamma_p", 25.0)
        self.Ep = num(p, "Ep", 30000.0)
        if self.D <= 0 or self.L <= 0:
            raise PileError("err_dimensions")
        if self.top < 0:
            raise PileError("err_top")
        if self.Ep <= 0 or self.gamma_p <= 0:
            raise PileError("err_material")

        self.Q = num(load, "Q", 0.0)
        if self.Q <= 0:
            raise PileError("err_load")

        self.nx = int(round(num(g, "nx", 1)))
        self.ny = int(round(num(g, "ny", 1)))
        self.sx = num(g, "sx", 3.0 * self.D)
        self.sy = num(g, "sy", 3.0 * self.D)
        if self.nx < 1 or self.ny < 1:
            raise PileError("err_group_count")
        if (self.nx > 1 and self.sx < self.D) or (self.ny > 1 and self.sy < self.D):
            raise PileError("err_group_spacing")
        self.efficiency_method = (g["efficiency"] if g.get("efficiency") in EFFICIENCY_METHODS
                                  else "converse_labarre")
        self.use_block = bool(g.get("block", True))

        o_def = base["options"]
        self.clay_method = o["clay_method"] if o.get("clay_method") in CLAY_METHODS \
            else o_def["clay_method"]
        self.tip_method = o["tip_method"] if o.get("tip_method") in TIP_METHODS \
            else o_def["tip_method"]
        ratio = num(o, "K_ratio", 0.0)
        self.K_ratio = ratio if ratio > 0 else axial.K_RATIO[self.installation]
        self.delta_ratio = min(max(num(o, "delta_ratio", 0.75), 0.0), 1.0)
        self.critical_depth = bool(o.get("critical_depth", True))
        self.zc_ratio = max(num(o, "zc_ratio", 15.0), 1.0)
        self.janbu_eta = min(max(num(o, "janbu_eta", 90.0), 60.0), 105.0)
        C = num(o, "sladen_C", 0.0)
        self.sladen_C = C if C > 0 else (0.4 if self.installation == "bored" else 0.5)
        self.subtract_weight = bool(o.get("subtract_weight", True))
        self.buoyant_weight = bool(o.get("buoyant_weight", True))
        self.spt_on = bool(o.get("spt_method", True))

        self.group_settlement = (s["group_method"] if s.get("group_method") in GROUP_SETTLEMENT
                                 else "raft")
        self.raft_fraction = min(max(num(s, "raft_fraction", 2.0 / 3.0), 0.0), 1.0)
        self.spread = max(num(s, "spread", 2.0), 0.1)
        self.distribution = (s["distribution"] if s.get("distribution") in SKIN_DISTRIBUTIONS
                             else "uniform")

        self.seismic_on = bool(e.get("enabled", False))
        self.V_E = num(e, "V", 0.0)
        self.M_B = num(e, "M_B", 0.0)
        self.M_L = num(e, "M_L", 0.0)
        self.tension_sand = min(max(num(e, "tension_sand", 0.75), 0.0), 1.0)
        self.tension_clay = min(max(num(e, "tension_clay", 1.0), 0.0), 1.0)
        self.cyclic = min(max(num(e, "cyclic", 1.0), 0.0), 1.0)
        self.FS_E_c = max(num(e, "FS_compression", 1.5), 1.0)
        self.FS_E_t = max(num(e, "FS_tension", 2.0), 1.0)

        self.FS = max(num(c, "FS", 2.5), 1.0)
        self.s_allow = max(num(c, "s_allow", 25.0), 0.1)
        self.L_min = max(num(c, "L_min", 4.0), 0.5)
        self.L_step = max(num(c, "L_step", 0.25), 0.05)

        gamma_w = num(w, "gamma_water", 9.81)
        self.gamma_w = gamma_w
        layers = []
        for raw in cfg.get("soil_profile") or []:
            layer = {**base["soil_profile"][0], **raw}
            values = {key: num(layer, key, default) for key, default in LAYER_NUMBERS.items()}
            if values["thickness"] <= 0:
                continue
            name = str(layer.get("name") or "Layer").strip() or "Layer"
            behaviour = layer.get("behaviour") if layer.get("behaviour") in BEHAVIOURS \
                else "granular"
            if values["gamma"] <= 0 or values["gamma_sat"] <= gamma_w:
                raise PileError("err_gamma", name=name)
            if not 0.0 <= values["phi"] < 50.0:
                raise PileError("err_phi", name=name)
            if not 0.0 <= values["nu"] < 0.5:
                raise PileError("err_nu", name=name)
            if behaviour == "cohesive" and values["cu"] <= 0:
                raise PileError("err_cu", name=name)
            if behaviour == "granular" and values["phi"] <= 0:
                raise PileError("err_granular_phi", name=name)
            if values["E"] <= 0:
                raise PileError("err_E", name=name)
            values.update(name=name, behaviour=behaviour)
            values["OCR"] = max(values["OCR"], 1.0)
            for key in ("cu", "N60", "Cc", "Cr", "e0"):
                values[key] = max(values[key], 0.0)
            layers.append(values)
        if not layers:
            raise PileError("err_no_layers")
        self.profile = Profile(layers, max(num(w, "depth", 0.0), 0.0), gamma_w)
        if self.top + self.L > self.profile.depth + 1e-9:
            raise PileError("err_tip_below", depth=self.profile.depth,
                            tip=self.top + self.L)

    # ------------------------------------------------------------------ geometry
    @property
    def area(self) -> float:
        return math.pi * self.D ** 2 / 4.0 if self.shape == "circular" else self.D ** 2

    @property
    def perimeter(self) -> float:
        return math.pi * self.D if self.shape == "circular" else 4.0 * self.D

    @property
    def n(self) -> int:
        return self.nx * self.ny

    @property
    def zc(self) -> float:
        """Meyerhof's critical depth below the ground surface."""
        return self.zc_ratio * self.D

    def _sigma_sand(self, z: float) -> float:
        """σ'v as the sand sees it: held constant below the critical depth."""
        if self.critical_depth:
            z = min(z, self.zc)
        return self.profile.effective_stress(z)

    def weight(self, L: float) -> float:
        """The weight of a pile this long, buoyant below the water table if asked."""
        z1, z2 = self.top, self.top + L
        zw = self.profile.zw
        dry = max(min(z2, zw) - z1, 0.0)
        wet = max(z2 - max(z1, zw), 0.0)
        wet_gamma = self.gamma_p - (self.gamma_w if self.buoyant_weight else 0.0)
        return self.area * (self.gamma_p * dry + wet_gamma * wet)

    # ------------------------------------------------------------------ shaft
    def _unit_clay(self, method: str, layer: dict, sv: float, penetration: float) -> float:
        cu = layer["cu"]
        if method == "alpha_api":
            return axial.alpha_api(cu, sv) * cu
        if method == "alpha_kulhawy":
            return axial.alpha_kulhawy(cu) * cu
        if method == "alpha_sladen":
            return axial.alpha_sladen(cu, sv, self.sladen_C) * cu
        if method == "beta":
            return axial.beta_clay(layer["phi"], layer["OCR"]) * sv
        return axial.lambda_factor(penetration) * (sv + 2.0 * cu)

    def _unit_sand(self, layer: dict, z: float) -> float:
        K = self.K_ratio * axial.K0(layer["phi"])
        return axial.fs_granular(self._sigma_sand(z), layer["phi"], K,
                                 self.delta_ratio * layer["phi"])

    def shaft(self, L: float) -> Dict[str, Any]:
        """Shaft friction of a pile this long, by every method, slice by slice."""
        z_tip = self.top + L
        slices = []
        totals = {method: 0.0 for method in CLAY_METHODS}
        spt_total, spt_ok = 0.0, self.spt_on
        cohesive = False
        for layer, z, h in self.profile.slices(self.top, z_tip, SLICE):
            sv = self.profile.effective_stress(z)
            row = {"z": z, "h": h, "layer": layer["name"], "behaviour": layer["behaviour"],
                   "sv": sv}
            if layer["behaviour"] == "cohesive":
                cohesive = True
                for method in CLAY_METHODS:
                    row[method] = self._unit_clay(method, layer, sv, z_tip)
                row["spt"] = row[self.clay_method]
            else:
                value = self._unit_sand(layer, z)
                row["sv_used"] = self._sigma_sand(z)
                for method in CLAY_METHODS:
                    row[method] = value
                if layer["N60"] > 0:
                    row["spt"] = axial.fs_spt(layer["N60"], self.installation)
                else:
                    spt_ok = False
                    row["spt"] = float("nan")
            for method in CLAY_METHODS:
                totals[method] += row[method] * self.perimeter * h
            if math.isfinite(row["spt"]):
                spt_total += row["spt"] * self.perimeter * h
            slices.append(row)
        return {"slices": slices, "Qs": totals, "Qs_spt": spt_total if spt_ok else float("nan"),
                "cohesive": cohesive}

    # ------------------------------------------------------------------ base
    def base(self, L: float) -> Dict[str, Any]:
        """Unit base resistance and base capacity by every method."""
        z_tip = self.top + L
        layer = self.profile.layer_at(z_tip)
        out: Dict[str, Any] = {"layer": layer["name"], "behaviour": layer["behaviour"],
                               "z": z_tip, "sv": self.profile.effective_stress(z_tip)}
        methods: Dict[str, dict] = {}
        if layer["behaviour"] == "cohesive":
            for method in TIP_METHODS:
                got = axial.tip_clay(method, layer["cu"], layer["E"], self.janbu_eta)
                methods[method] = {**got, "Qb": got["qb"] * self.area}
        else:
            sv = self._sigma_sand(z_tip)
            out["sv_used"] = sv
            phi = layer["phi"]
            got = {"meyerhof": axial.tip_meyerhof(sv, phi),
                   "vesic": axial.tip_vesic(sv, phi, layer["E"], layer["nu"]),
                   "janbu": axial.tip_janbu(sv, phi, self.janbu_eta)}
            for method in TIP_METHODS:
                methods[method] = {**got[method], "Qb": got[method]["qb"] * self.area}
        out["methods"] = methods
        spt = float("nan")
        if self.spt_on:
            if layer["behaviour"] == "cohesive":
                spt = methods[self.tip_method]["qb"]
            elif layer["N60"] > 0:
                embedment = z_tip - max(layer["top"], self.top)
                spt = axial.tip_spt(layer["N60"], embedment, self.D)["qb"]
        out["qb_spt"] = spt
        out["Qb_spt"] = spt * self.area if math.isfinite(spt) else float("nan")
        return out

    # ------------------------------------------------------------------ group
    def block(self, L: float, shaft: dict, base: dict) -> Dict[str, Any]:
        """Block failure of the group: soil-on-soil shaft plus the footprint's base."""
        Bg, Lg = grp.outline(self.nx, self.ny, self.sx, self.sy, self.D)
        perimeter = 2.0 * (Bg + Lg)
        side = 0.0
        for row in shaft["slices"]:
            layer = self.profile.layer_at(row["z"])
            if layer["behaviour"] == "cohesive":
                fs = layer["cu"]
            else:
                fs = axial.K0(layer["phi"]) * row["sv"] * math.tan(math.radians(layer["phi"]))
            side += fs * perimeter * row["h"]
        z_tip = self.top + L
        tip_layer = self.profile.layer_at(z_tip)
        if tip_layer["behaviour"] == "cohesive":
            Nc = grp.skempton_nc(Bg, Lg, z_tip)
            qb = Nc * tip_layer["cu"]
        else:
            Nc = float("nan")
            qb = base["methods"][self.tip_method]["qb"]
        return {"Bg": Bg, "Lg": Lg, "perimeter": perimeter, "Qs": side, "qb": qb,
                "Nc": Nc, "Qb": qb * Bg * Lg, "Q_ult": side + qb * Bg * Lg}

    # ------------------------------------------------------------------ seismic
    def pile_loads(self) -> List[Dict[str, float]]:
        """The seismic load on every pile of a rigid cap.

        P = V/n + M_B·x/Σx² + M_L·y/Σy², x along B and y along L measured from
        the centre of the group; positive in compression.
        """
        points = grp.positions(self.nx, self.ny, self.sx, self.sy)
        sxx = sum(x * x for x, _ in points)
        syy = sum(y * y for _, y in points)
        out = []
        for x, y in points:
            P = self.V_E / self.n
            if sxx > 0:
                P += self.M_B * x / sxx
            if syy > 0:
                P += self.M_L * y / syy
            out.append({"x": x, "y": y, "P": P})
        return out

    def uplift(self, L: float, shaft: dict) -> Dict[str, float]:
        """Uplift capacity of one pile: the shaft friction in tension and the weight.

        Qs,t = Σ λt·ζ·fs·p·Δz, λt the tension / compression ratio of the layer
        (sand, clay), ζ the cyclic reduction; W the pile's weight, buoyant below
        the water table. Tall = Qs,t / FSt + W.
        """
        Qs_t = 0.0
        for row in shaft["slices"]:
            ratio = self.tension_clay if row["behaviour"] == "cohesive" else self.tension_sand
            Qs_t += row[self.clay_method] * ratio * self.cyclic * self.perimeter * row["h"]
        W = self.weight(L)
        return {"Qs": Qs_t, "W": W, "T_ult": Qs_t + W, "T_all": Qs_t / self.FS_E_t + W}

    def block_uplift(self, L: float, shaft: dict) -> Dict[str, float]:
        """Uplift of the whole group as one block: the soil-on-soil shear round its
        outline, reduced for cyclic loading, and the effective weight of the soil
        and the piles inside it."""
        Bg, Lg = grp.outline(self.nx, self.ny, self.sx, self.sy, self.D)
        perimeter = 2.0 * (Bg + Lg)
        side = 0.0
        for row in shaft["slices"]:
            layer = self.profile.layer_at(row["z"])
            if layer["behaviour"] == "cohesive":
                fs = layer["cu"]
            else:
                fs = axial.K0(layer["phi"]) * row["sv"] * math.tan(math.radians(layer["phi"]))
            side += fs * self.cyclic * perimeter * row["h"]
        z_tip = self.top + L
        soil = self.profile.effective_stress(z_tip) - self.profile.effective_stress(self.top)
        W = Bg * Lg * soil + self.n * (self.weight(L) - self.area * soil)
        return {"Bg": Bg, "Lg": Lg, "Qs": side, "W": W, "T_ult": side + W,
                "T_all": side / self.FS_E_t + W}

    def seismic(self, L: float, shaft: dict, Q_net: float) -> Dict[str, Any]:
        """The seismic checks for a pile of length L."""
        loads = self.pile_loads()
        P_max = max(p["P"] for p in loads)
        P_min = min(p["P"] for p in loads)
        Q_all = Q_net / self.FS_E_c
        compression = {
            "P": P_max, "Q_all": Q_all, "allowable": self.FS_E_c,
            "FS": Q_net / P_max if P_max > 0 else float("inf"),
            "utilisation": P_max / Q_all if P_max > 0 and Q_all > 0
            else (0.0 if P_max <= 0 else float("inf")),
        }
        up = self.uplift(L, shaft)
        T = max(-P_min, 0.0)
        pull = T - up["W"]
        tension = {
            **up, "T": T, "n": sum(1 for p in loads if p["P"] < 0), "allowable": self.FS_E_t,
            "FS": up["Qs"] / pull if pull > 0 else float("inf"),
            "utilisation": T / up["T_all"] if up["T_all"] > 0 else float("inf"),
        }
        group = None
        if self.V_E < 0 and self.n > 1:
            b = self.block_uplift(L, shaft)
            T_g = -self.V_E
            pull_g = T_g - b["W"]
            group = {**b, "T": T_g, "allowable": self.FS_E_t,
                     "FS": b["Qs"] / pull_g if pull_g > 0 else float("inf"),
                     "utilisation": T_g / b["T_all"] if b["T_all"] > 0 else float("inf")}
        worst = max(compression["utilisation"], tension["utilisation"],
                    group["utilisation"] if group else 0.0)
        return {"loads": loads, "P_max": P_max, "P_min": P_min, "compression": compression,
                "tension": tension, "group": group, "utilisation": worst}

    # ------------------------------------------------------------------ one length
    def evaluate(self, L: float) -> Dict[str, Any]:
        """Everything the capacity checks need, for a pile of length L."""
        shaft = self.shaft(L)
        base = self.base(L)
        W = self.weight(L)
        W_used = W if self.subtract_weight else 0.0
        Qs = shaft["Qs"][self.clay_method]
        Qb = base["methods"][self.tip_method]["Qb"]
        Q_ult = Qs + Qb
        Q_net = Q_ult - W_used
        Q_all = Q_net / self.FS
        Qp = self.Q / self.n

        combos = {}
        for clay in CLAY_METHODS:
            for tip in TIP_METHODS:
                total = shaft["Qs"][clay] + base["methods"][tip]["Qb"]
                combos[f"{clay}|{tip}"] = {"Qs": shaft["Qs"][clay],
                                           "Qb": base["methods"][tip]["Qb"],
                                           "Q_ult": total, "Q_ult_net": total - W_used}

        eta = grp.efficiencies(self.nx, self.ny, self.sx, self.sy, self.D)
        chosen = eta[self.efficiency_method]
        if not math.isfinite(chosen):
            chosen = eta["converse_labarre"]
        Q_eff = chosen * self.n * Q_ult
        block = self.block(L, shaft, base) if (self.use_block and self.n > 1) else None
        if block is not None and block["Q_ult"] < Q_eff:
            Qg_ult, governing = block["Q_ult"], "block"
        else:
            Qg_ult, governing = Q_eff, "efficiency"
        Qg_net = Qg_ult - self.n * W_used
        Qg_all = Qg_net / self.FS
        seismic = self.seismic(L, shaft, Q_net) if self.seismic_on else None
        return {
            "seismic": seismic,
            "L": L, "z_tip": self.top + L, "shaft": shaft, "base": base,
            "W": W, "W_used": W_used, "Qs": Qs, "Qb": Qb, "Q_ult": Q_ult,
            "Q_ult_net": Q_net, "Q_all": Q_all, "Q_pile": Qp,
            "FS": Q_net / Qp if Qp > 0 else float("inf"),
            "utilisation": Qp / Q_all if Q_all > 0 else float("inf"),
            "combos": combos,
            "group": {"eta": eta, "eta_used": chosen, "Q_eff": Q_eff, "block": block,
                      "Q_ult": Qg_ult, "Q_ult_net": Qg_net, "Q_all": Qg_all,
                      "governing": governing,
                      "FS": Qg_net / self.Q, "utilisation": self.Q / Qg_all if Qg_all > 0
                      else float("inf")},
        }

    # ------------------------------------------------------------------ settlement
    def _settlement(self, ev: dict) -> Dict[str, Any]:
        L = ev["L"]
        z_tip = ev["z_tip"]
        tip_layer = self.profile.layer_at(z_tip)
        E_shaft = self.profile.average("E", self.top, z_tip)
        nu_shaft = self.profile.average("nu", self.top, z_tip)
        xi = 0.5 if self.distribution == "uniform" else 0.67
        single = stl.single_pile(ev["Q_pile"], ev["Qs"], ev["Qb"], L, self.D, self.area,
                                 self.perimeter, self.Ep, tip_layer["E"], tip_layer["nu"],
                                 E_shaft, nu_shaft, xi)
        Bg, Lg = grp.outline(self.nx, self.ny, self.sx, self.sy, self.D)
        z_raft = self.top + self.raft_fraction * L
        raft = stl.equivalent_raft(self.profile, self.Q, Bg, Lg, z_raft, self.spread)
        shortening = ev["Q_pile"] * self.raft_fraction * L / (self.area * 1000.0 * self.Ep)
        raft["shortening"] = shortening
        raft["total"] = raft["s"] + shortening
        if raft["reached_bottom"]:
            self.warnings.append(message("warn_raft_bottom", depth=self.profile.depth))
        vesic = stl.vesic_group(single["s"], Bg, self.D)

        meyerhof = None
        if tip_layer["behaviour"] == "granular":
            N60 = self.profile.average("N60", z_tip, z_tip + Bg, "granular")
            if math.isfinite(N60) and N60 > 0:
                meyerhof = stl.meyerhof_group(self.Q / (Bg * Lg), Bg, L, N60)
        values = {"raft": raft["total"], "vesic": vesic,
                  "meyerhof": meyerhof["s"] if meyerhof else float("nan")}
        method = self.group_settlement
        if not math.isfinite(values[method]):
            self.warnings.append(message("warn_meyerhof_settlement"))
            method = "raft"
        s = values[method]
        return {"single": single, "raft": raft, "vesic": vesic, "meyerhof": meyerhof,
                "values": values, "method": method, "s": s, "Bg": Bg, "Lg": Lg,
                "status": "OK" if s * 1000.0 <= self.s_allow + 1e-9 else "NOT OK"}

    # ------------------------------------------------------------------ length
    def length_curve(self) -> List[Dict[str, float]]:
        """Capacity against pile length, from the shortest trial to the profile's foot."""
        L_max = self.profile.depth - self.top
        lengths = []
        L = self.L_min
        while L <= L_max + 1e-9:
            lengths.append(L)
            L += self.L_step
        if not lengths or abs(lengths[-1] - L_max) > 1e-6:
            lengths.append(L_max)
        out = []
        for L in lengths:
            if L <= 0:
                continue
            ev = self.evaluate(L)
            out.append({"L": L, "Qs": ev["Qs"], "Qb": ev["Qb"], "W": ev["W_used"],
                        "Q_ult": ev["Q_ult"], "Q_ult_net": ev["Q_ult_net"],
                        "Q_all": ev["Q_all"], "Qg_all": ev["group"]["Q_all"],
                        "utilisation": ev["utilisation"],
                        "utilisation_group": ev["group"]["utilisation"],
                        "utilisation_seismic": ev["seismic"]["utilisation"]
                        if ev["seismic"] else 0.0,
                        "T_all": ev["seismic"]["tension"]["T_all"]
                        if ev["seismic"] else float("nan")})
        return out

    @staticmethod
    def required_length(curve: List[Dict[str, float]]) -> float:
        """The shortest length on the curve that passes every check."""
        for point in curve:
            if max(point["utilisation"], point["utilisation_group"],
                   point.get("utilisation_seismic", 0.0)) <= 1.0 + 1e-9:
                return point["L"]
        return float("nan")

    # ------------------------------------------------------------------ warnings
    def _check_inputs(self, ev: dict) -> None:
        z_tip = ev["z_tip"]
        tip = self.profile.layer_at(z_tip)
        for layer, _, _ in self.profile.segments(z_tip, z_tip + BELOW_TIP * self.D):
            if layer is tip:
                continue
            weaker = (tip["behaviour"] == "granular" and layer["behaviour"] == "cohesive") or \
                (tip["behaviour"] == "cohesive" and layer["behaviour"] == "cohesive"
                 and layer["cu"] < tip["cu"])
            if weaker:
                self.warnings.append(message("warn_weak_below", name=layer["name"],
                                             n=BELOW_TIP))
                break
        method = ev["base"]["methods"][self.tip_method]
        if method.get("limited"):
            self.warnings.append(message("warn_meyerhof_limit", limit=method["limit"]))
        if self.n > 1:
            s = min([v for v, k in ((self.sx, self.nx), (self.sy, self.ny)) if k > 1])
            if s < MIN_SPACING * self.D:
                self.warnings.append(message("warn_spacing", s=s, D=self.D, n=MIN_SPACING))
        if self.clay_method == "beta" and ev["shaft"]["cohesive"] and any(
                layer["behaviour"] == "cohesive" and layer["phi"] <= 0
                for layer, _, _ in self.profile.segments(self.top, z_tip)):
            self.warnings.append(message("warn_beta_phi"))
        if self.spt_on and self.installation == "bored" and math.isfinite(ev["base"]["Qb_spt"]):
            self.warnings.append(message("warn_spt_bored"))
        if self.critical_depth and z_tip > self.zc and any(
                layer["behaviour"] == "granular"
                for layer, _, _ in self.profile.segments(self.top, z_tip)):
            self.warnings.append(message("warn_critical_depth", zc=self.zc))
        if self.seismic_on and self.n == 1 and (self.M_B or self.M_L):
            self.warnings.append(message("warn_seismic_single_moment"))
        if self.seismic_on and ev["seismic"]["tension"]["n"]:
            self.warnings.append(message("warn_seismic_tension",
                                         n=ev["seismic"]["tension"]["n"],
                                         T=ev["seismic"]["tension"]["T"]))

    # ------------------------------------------------------------------ the run
    def run(self, with_length: bool = True) -> Dict[str, Any]:
        """The whole analysis. `with_length` off leaves the length search out,
        which is how a study runs its samples."""
        ev = self.evaluate(self.L)
        self._check_inputs(ev)
        settlement = self._settlement(ev)
        curve = self.length_curve() if with_length else []
        L_req = self.required_length(curve) if with_length else float("nan")
        if with_length and not math.isfinite(L_req):
            self.warnings.append(message("warn_no_length",
                                         hi=self.profile.depth - self.top))

        def status(utilisation: float) -> str:
            return "OK" if utilisation <= 1.0 + 1e-9 else "NOT OK"

        self.results = {
            **ev,
            "shape": self.shape, "D": self.D, "top": self.top, "A": self.area,
            "perimeter": self.perimeter, "n": self.n, "Q": self.Q,
            "installation": self.installation, "K_ratio": self.K_ratio,
            "zc": self.zc if self.critical_depth else float("nan"),
            "primary": {"clay": self.clay_method, "tip": self.tip_method},
            "checks": {
                "pile": {"actual": ev["FS"], "allowable": self.FS,
                         "status": status(ev["utilisation"]),
                         "utilisation": ev["utilisation"]},
                "group": {"actual": ev["group"]["FS"], "allowable": self.FS,
                          "status": status(ev["group"]["utilisation"]),
                          "utilisation": ev["group"]["utilisation"]},
                "settlement": {"actual": settlement["s"] * 1000.0,
                               "allowable": self.s_allow, "status": settlement["status"]},
            },
            "seismic_on": self.seismic_on,
            "settlement": settlement,
            "length_curve": curve, "required_length": L_req,
            "layers": self._layer_table(),
            "warnings": self.warnings,
        }
        seismic = ev["seismic"]
        if seismic:
            checks = self.results["checks"]
            c, t = seismic["compression"], seismic["tension"]
            checks["seismic_compression"] = {"actual": c["FS"], "allowable": c["allowable"],
                                             "status": status(c["utilisation"]),
                                             "utilisation": c["utilisation"]}
            checks["seismic_tension"] = {
                "actual": t["FS"], "allowable": t["allowable"],
                "status": "N/A" if t["T"] <= 0 else status(t["utilisation"]),
                "utilisation": t["utilisation"]}
            if seismic["group"]:
                g = seismic["group"]
                checks["seismic_group_tension"] = {
                    "actual": g["FS"], "allowable": g["allowable"],
                    "status": status(g["utilisation"]), "utilisation": g["utilisation"]}
        return self.results

    def _layer_table(self) -> List[dict]:
        rows = []
        for layer in self.profile.layers:
            mid = 0.5 * (layer["top"] + layer["bottom"])
            rows.append({**{key: layer[key] for key in LAYER_NUMBERS},
                         "name": layer["name"], "behaviour": layer["behaviour"],
                         "top": layer["top"], "bottom": layer["bottom"],
                         "sigma_v": self.profile.total_stress(mid),
                         "u": self.profile.pore_pressure(mid),
                         "sigma_eff": self.profile.effective_stress(mid)})
        return rows


def analyse(config: Dict[str, Any], with_length: bool = True) -> PileAnalysis:
    """Build and run a pile analysis in one call."""
    analysis = PileAnalysis(config)
    analysis.run(with_length=with_length)
    return analysis
