"""
Calculation report for SlipSurface IQ Pile.

The report is assembled as HTML (the inputs, the base and shaft resistance of
every method, the pile's weight, the capacity, the group, the settlement, the
checks and the required length, the figures, the warnings and the method
notes; the rock socket if one was analysed) and
typeset as a PDF through reportlab (see `slipsurface.pile.pdf`). The
HTML is only the intermediate form the PDF is built from; it is not exported.
"""

from __future__ import annotations

import base64
import datetime
import html
import io
import math
from typing import Any, Dict, List, Optional

from ._optional import missing

try:
    from matplotlib.figure import Figure
except ImportError as exc:
    raise missing("matplotlib", "report") from exc

from .config import (
    APP_NAME,
    APP_VERSION,
    CLAY_METHODS,
    SOCKET_BASE_METHODS,
    SOCKET_SIDE_METHODS,
    TIP_METHODS,
)
from .texts import TEXTS as L, warning_text
from .plotting import PLOT_KEYS, SOCKET_PLOT_KEYS, Plotter, SocketPlotter, available_figures
from .summary import method_label

REPORT_TEXTS = {
    "title": f"{APP_NAME} — Calculation Report",
    "date": "Date", "analyst": "Analyst", "software": "Software",
    "sec_inputs": "Input data", "sec_pile": "Pile, group and load",
    "sec_soil": "Soil profile", "sec_opts": "Methods, options and criteria",
    "sec_single": "Capacity of a single pile", "sec_base": "Base resistance",
    "sec_shaft_layers": "Shaft friction by layer",
    "sec_shaft_methods": "Shaft friction by method",
    "sec_capacity": "Ultimate and allowable capacity",
    "sec_matrix": "Net ultimate capacity, shaft method × base method",
    "sec_group": "Pile group", "sec_eff": "Group efficiency", "sec_block": "Block failure",
    "sec_group_cap": "Capacity of the group",
    "sec_settlement": "Settlement", "sec_single_s": "Single pile (Vesić)",
    "sec_group_s": "Group", "sec_raft": "Equivalent raft, slice by slice",
    "sec_checks": "Checks and the required length",
    "sec_seismic": "Seismic load case", "sec_seismic_loads": "Loads on the piles",
    "sec_seismic_checks": "Compression and uplift",
    "V_E": "Vertical load V", "M_B": "Moment M_B (loads varying along B)",
    "M_L": "Moment M_L (loads varying along L)", "x": "x (m)", "y": "y (m)",
    "P": "P (kN)", "pile_no": "Pile",
    "P_max": "Most compressed pile Pmax", "P_min": "Least loaded pile Pmin",
    "QaE": "Allowable compression Qult,net / FS", "ts": "Tension ratio, sand",
    "tc": "Tension ratio, clay", "cyclic": "Cyclic reduction ζ",
    "Qs_t": "Shaft friction in tension Qs,t", "W_t": "Pile weight W",
    "T_all": "Allowable uplift Qs,t / FS + W", "T": "Largest tension T",
    "block_up": "Block uplift: shear + weight, allowable",
    "group_comp": "Allowable group compression Qg,ult,net / FS",
    "c_seis_c": "Seismic, compression (FS)", "c_seis_t": "Seismic, uplift (FS on Qs,t)",
    "c_seis_gc": "Seismic, group compression (FS)",
    "c_seis_g": "Seismic, block uplift (FS)",
    "sec_figs": "Figures", "sec_warn": "Warnings", "sec_notes": "Method notes",
    "sec_socket": "Rock-socketed pile", "sec_socket_in": "Socket, rock and concrete",
    "sec_socket_side": "Unit side shear by correlation",
    "sec_socket_base": "Unit base resistance",
    "sec_socket_design": "Design, socket length and check",
    "sec_socket_s": "Elastic settlement", "sec_socket_figs": "Figures",
    "sec_socket_warn": "Warnings", "sec_socket_notes": "Method notes",
    "parameter": "Parameter", "value": "Value", "unit": "Unit",
    "shape": "Shape", "D": "Diameter / side D", "L": "Length L",
    "top": "Depth of the pile head", "tip": "Depth of the tip",
    "installation": "Installation", "gamma_p": "Unit weight of the pile γp",
    "Ep": "Modulus of the pile Ep", "A": "Base area Ab", "p": "Perimeter",
    "Q": "Load on the group Q", "n": "Number of piles", "Qp": "Load per pile",
    "sx": "Spacing along B", "sy": "Spacing along L",
    "zw": "Water table depth", "gw": "Unit weight of water γw",
    "yes": "yes", "no": "no",
    "layer": "Layer", "type": "Type", "top_l": "Top", "bottom": "Bottom",
    "clay_method": "Shaft friction in clay", "tip_method": "Base resistance",
    "K": "K / K0 in sand", "delta": "δ / φ'", "zc": "Critical depth zc",
    "weight": "Pile weight subtracted", "buoyant": "Buoyant below the water table",
    "efficiency": "Group efficiency", "block": "Block failure checked",
    "gs": "Group settlement for the check", "FS": "Factor of safety",
    "s_allow": "Allowable settlement",
    "method": "Method", "factor": "Factor", "qb": "qb (kPa)", "Qb": "Qb (kN)",
    "depth": "Depth (m)", "Qs": "Qs (kN)", "sv": "σ'v0 at the tip",
    "Qs_l": "Shaft friction Qs", "Qb_l": "Base resistance Qb", "Qu": "Qult = Qs + Qb",
    "W": "Pile weight W", "Qn": "Qult,net = Qult − W", "Qa": "Qall = Qult,net / FS",
    "eta": "η", "Bg": "Width of the block Bg", "Lg": "Length of the block Lg",
    "block_Qs": "Shaft of the block", "block_Qb": "Base of the block",
    "block_Q": "Capacity of the block", "Q_eff": "η · n · Qult",
    "Qg": "Qg,ult", "Qgn": "Qg,ult − n·W", "Qga": "Qg,all", "governs": "Governs",
    "s1": "Shortening of the pile s1", "s2": "Base load s2", "s3": "Shaft load s3",
    "s": "Settlement", "z": "z (m)", "h": "h (m)", "s0": "σ'v0 (kPa)",
    "ds": "Δσ (kPa)", "ds_mm": "s (mm)", "kind": "Model",
    "raft_z": "Depth of the raft", "raft_q": "Pressure on the raft",
    "raft_c": "Consolidation", "raft_e": "Elastic compression",
    "raft_sh": "Shortening of the piles above the raft", "raft_total": "Total",
    "check": "Check", "actual": "Actual", "allowable": "Allowable", "status": "Status",
    "c_pile": "Single pile (FS)", "c_group": "Group (FS)", "c_settle": "Settlement (mm)",
    "ok": "OK", "notok": "NOT OK", "na": "n/a",
    "socket_D": "Socket diameter D", "socket_Ls": "Socket length checked Ls",
    "socket_top": "Depth of the pile head", "rock": "Depth of the rock surface",
    "overburden": "Length through the overburden",
    "Qs_soil": "Shaft friction in the overburden Qs,soil", "not_counted": "not counted", "socket_Q": "Load Q",
    "qu": "Intact rock strength qu", "qu_side": "qu for the side shear (≤ f'c)",
    "RQD": "RQD", "Ei": "Intact modulus Ei", "Em": "Rock mass modulus Em",
    "ratio": "Em / Ei", "alpha_E": "Joint factor αE", "GSI": "GSI", "mi": "mi",
    "mb": "mb", "s_hb": "s", "fc": "Concrete strength f'c", "Ec": "Concrete modulus Ec",
    "correlation": "Correlation", "formula": "fs (MPa)", "fs": "fs (kPa)",
    "Ls_req": "Design Ls (m)", "Q_all": "Qall at Ls (kN)", "range": "In range",
    "base_formula": "qb (MPa)", "qb_mpa": "qb (MPa)",
    "fs_design": "Design side shear", "qb_design": "Design base resistance",
    "FS_side": "Factor of safety on the side", "FS_base": "Factor of safety on the base",
    "Ls_need": "Continuous capacity estimate (diagnostic)", "Ls_min": "Minimum socket length",
    "Ls_design": "Recommended whole-metre socket length",
    "rw": "Randolph & Wroth, side and base", "rw_side": "Randolph & Wroth, side only",
    "vesic": "Vesić", "shortening": "Shortening through the overburden",
    "base_share": "Share carried by the base",
    "notes": [
        "The ultimate capacity of a pile is Qult = Qs + Qb: the shaft friction "
        "integrated down the shaft, Qs = Σ fs·p·Δz, and the base resistance Qb = qb·Ab. "
        "The pile's weight W = γp·Ab·L, buoyant (γp − γw) below the water table, is "
        "taken off: Qult,net = Qult − W, and Qall = Qult,net / FS.",
        "Stresses are effective: σ'v0 = σv0 − u0, u0 hydrostatic below the water "
        "table. In sand the shaft friction is fs = K·σ'v·tan δ with K = (K/K0)·(1 − sin φ'), "
        "and σ'v is held constant below the critical depth zc when asked (Meyerhof; "
        "Vesić).",
        "In clay: API RP 2A α = 0.5·ψ^-0.5 (ψ ≤ 1) or 0.5·ψ^-0.25, ψ = cu/σ'v; Kulhawy & "
        "Phoon α = 0.21 + 0.26·pa/cu; Sladen α = C·(σ'v/cu)^0.45; each α ≤ 1 and "
        "fs = α·cu. The β method fs = (1 − sin φ')·tan φ'·√OCR·σ'v; the λ method "
        "fs = λ·(σ'v + 2cu), λ from the pile's penetration (Vijayvergiya & Focht).",
        "The base in sand: Meyerhof qb = σ'v·Nq* ≤ 0.5·pa·Nq*·tan φ'; Vesić "
        "qb = σ'm·Nσ = σ'v·[(1 + 2K0)/3]·Nσ, K0 = 1 − sin φ', and "
        "Nq = [(1 + 2K0)/3]·Nσ. Irr is the rigidity index reduced for volume change "
        "(USACE EM 1110-1-1905, equations 5-5b and 5-6a); Janbu "
        "qb = σ'v·(tan φ' + √(1 + tan² φ'))²·e^(2η'·tan φ'). In clay qb = Nc*·cu with "
        "Nc* = 9, Vesić's 4/3·(ln Ir + 1) + π/2 + 1, or Janbu's 2 + 2η'; the overburden "
        "term is left out, as it is balanced by the pile's own weight.",
        "The group's capacity is the smaller of η·n·Qult and the capacity of the block "
        "the group occupies (soil-on-soil shaft, the base resistance over the footprint; "
        "Skempton's Nc in clay); the piles' weight n·W is then taken off.",
        "The settlement of one pile is Vesić's s1 + s2 + s3, the working load shared "
        "between shaft and base in the proportion of their ultimate resistances. The "
        "group settles as an equivalent raft at 2/3 of the pile length, the load spread "
        "2 : 1 below it (clays by Cc, Cr, e0 and OCR, the others by their constrained "
        "modulus), plus the piles' shortening above it; by Vesić's s·√(Bg/D); or by "
        "Meyerhof's SPT rule in sand.",
        "The recommended length is the shortest whole-metre pile within the logged "
        "profile and the specified lower bound that passes single-pile capacity, "
        "group capacity, settlement and every active seismic check. Each whole-metre "
        "candidate is recalculated at its actual tip depth; passing a shorter "
        "fractional length does not establish that a longer pile passes in layered soil.",
        "Seismic load case: the rigid cap shares V, M_B and M_L among the piles, "
        "P = V/n + M_B·x/Σx² + M_L·y/Σy². The most compressed pile is checked against "
        "Qult,net / FS, and positive total V is checked against the group's net "
        "capacity divided by the seismic factor of safety. A moment about an axis "
        "with no pile lever arm is rejected. A pile in tension is resisted by its shaft friction in tension, "
        "Qs,t = Σ λt·ζ·fs·p·Δz (λt the tension ratio of sand or clay, ζ the cyclic "
        "reduction), and its own weight W: T ≤ Qs,t / FS + W. When the group as a whole "
        "is lifted (V < 0) the block is checked too: soil-on-soil shear round its "
        "outline and the effective weight of the soil and the piles inside it.",
    ],
    "socket_notes": [
        "The side shear is fs·π·D·Ls and the base resistance qb·π·D²/4. The allowable "
        "capacity is Qs/FSside + Qb/FSbase − W. Bisection provides a continuous "
        "capacity-only diagnostic. The recommendation is the first whole-metre "
        "length that passes capacity, minimum embedment and settlement after "
        "recalculation; an entered length is checked against all three criteria.",
        "qu in the side shear correlations is the weaker of the rock and the concrete. "
        "The linear rules (Reynolds & Kaderabek, Gupton & Logan, Toh et al.) were "
        "fitted to weak rock and are left out of the statistics above the weak rock "
        "limit.",
        "O'Neill & Reese's αE reduces the side shear of jointed rock through Em/Ei; "
        "the rock mass modulus comes from RQD (Gardner 1987), from GSI (Hoek & "
        "Diederichs 2006), or is entered.",
        "The settlement is Randolph & Wroth's closed form for a compressible pile in an "
        "elastic medium, with the socket's rock along the shaft and below the base, plus "
        "the elastic shortening of the pile through the overburden. The side-only "
        "solution governs the settlement check when base resistance is disabled; "
        "otherwise the side-and-base solution is used. Optional overburden shaft "
        "resistance contributes to capacity when enabled.",
    ],
}

#: The interface's palette: warm paper, ink, terracotta; serif headings
_CSS = """
body { font-family: system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
       font-size: 10pt; color: #141413; }
h1, h2, h3 { font-family: 'Tiempos Text', 'Source Serif 4', 'Iowan Old Style', Palatino,
             Georgia, 'DejaVu Serif', serif; font-weight: 500; }
h1 { font-size: 20pt; color: #141413; margin-bottom: 2px; }
h2 { font-size: 14pt; color: #C6613F; border-bottom: 1px solid #E3E0D5; padding-bottom: 2px;
     margin-top: 20px; }
h3 { font-size: 11.5pt; color: #141413; margin-top: 12px; }
table { border-collapse: collapse; margin: 4px 0 8px 0; }
th { background: #F0EEE6; text-align: left; padding: 3px 6px; border: 1px solid #E3E0D5;
     font-size: 9pt; }
td { padding: 3px 6px; border: 1px solid #E3E0D5; font-size: 9pt; }
.ok { color: #3F7F4F; font-weight: bold; } .bad { color: #B0413E; font-weight: bold; }
.meta { color: #73726C; } .note { color: #73726C; font-size: 9pt; }
"""


def _esc(x) -> str:
    return html.escape(str(x))


def _f(x, nd=2) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "—"
    return f"{x:,.{nd}f}"


def _status(T, s: str) -> str:
    if s == "N/A":
        return T["na"]
    return (f'<span class="ok">{T["ok"]}</span>' if s == "OK"
            else f'<span class="bad">{T["notok"]}</span>')


def _table(headers: List[str], rows: List[List[Any]], widths: Optional[List[int]] = None) -> str:
    out = ["<table width='100%'>"]
    if widths:
        cells = "".join(f"<th width='{w}%'>{_esc(h)}</th>" for h, w in zip(headers, widths))
    else:
        cells = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    out.append("<tr>" + cells + "</tr>")
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def _kv_table(T, rows: List[List[Any]]) -> str:
    return _table([T["parameter"], T["value"], T["unit"]], rows, [50, 36, 14])


def _check_label(T, key: str) -> str:
    labels = {
        "pile": T["c_pile"], "group": T["c_group"], "settlement": T["c_settle"],
        "seismic_compression": T["c_seis_c"], "seismic_tension": T["c_seis_t"],
        "seismic_group_compression": T["c_seis_gc"],
        "seismic_group_tension": T["c_seis_g"],
        "capacity": "Socket capacity (kN)", "min_length": "Minimum socket length (m)",
        "shared_design": "Common design for every borehole",
    }
    return labels.get(key, key.replace("_", " "))


def _checks_table(T, checks: dict, *, boreholes: bool = False) -> str:
    rows = []
    for key, check in checks.items():
        row = [_esc(_check_label(T, key)), _f(check.get("actual")),
               _f(check.get("allowable")), _f(check.get("utilisation"), 3),
               _status(T, check["status"])]
        if boreholes:
            row.append(_esc(check.get("governing_borehole") or "—"))
        rows.append(row)
    headers = [T["check"], T["actual"], "Limit", "Utilisation", T["status"]]
    widths = [36, 17, 17, 15, 15]
    if boreholes:
        headers.append("Governing borehole")
        widths = [28, 12, 12, 12, 12, 24]
    return _table(headers, rows, widths)


class _Numbers:
    """Section numbers that follow whatever the report happens to contain."""

    def __init__(self):
        self.major = 0
        self.minor = 0

    def h2(self, text: str, page_break: bool = False) -> str:
        self.major += 1
        self.minor = 0
        style = " style='page-break-before:always'" if page_break else ""
        return f"<h2{style}>{self.major}. {_esc(text)}</h2>"

    def h3(self, text: str) -> str:
        self.minor += 1
        return f"<h3>{self.major}.{self.minor} {_esc(text)}</h3>"


# ----------------------------------------------------------------------
def _png(fig: Figure, dpi: int) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    return buf.getvalue()


def render_figures(analysis, keys=None, dpi: int = 130) -> Dict[str, bytes]:
    """The report figures of the pile analysis as PNG bytes (off-screen, white, untitled)."""
    if analysis is None:
        return {}
    if keys is None:
        keys = available_figures(analysis)
    plotter = Plotter(analysis, titles=False)
    out = {}
    for key in keys:
        fig = Figure(figsize=(10, 7), dpi=dpi)
        plotter.draw(key, fig)
        out[key] = _png(fig, dpi)
    return out


def render_socket_figures(socket, dpi: int = 130) -> Dict[str, bytes]:
    if socket is None:
        return {}
    if socket.results.get("envelope"):
        return render_figures(socket, dpi=dpi)
    plotter = SocketPlotter(socket, titles=False)
    out = {}
    for key in SOCKET_PLOT_KEYS:
        fig = Figure(figsize=(10, 7), dpi=dpi)
        plotter.draw(key, fig)
        out[key] = _png(fig, dpi)
    return out


# ----------------------------------------------------------------------
def _pile_section(T, L, a, figures, img_src, N: _Numbers) -> List[str]:
    res = a.results
    parts = [N.h2(T["sec_inputs"]), N.h3(T["sec_pile"])]
    rows = [[T["shape"], L["shape_" + a.shape], ""], [T["D"], _f(a.D), "m"],
            [T["L"], _f(a.L), "m"], [T["top"], _f(a.top), "m"], [T["tip"], _f(res["z_tip"]), "m"],
            [T["installation"], L["installation_" + a.installation], ""],
            [T["gamma_p"], _f(a.gamma_p, 1), "kN/m³"], [T["Ep"], _f(a.Ep, 0), "MPa"],
            [T["A"], _f(res["A"], 4), "m²"], [T["p"], _f(res["perimeter"], 3), "m"],
            [T["Q"], _f(a.Q, 0), "kN"], [T["n"], f"{a.nx} × {a.ny} = {a.n}", ""],
            [T["Qp"], _f(res["Q_pile"], 0), "kN"]]
    if a.nx > 1:
        rows.append([T["sx"], _f(a.sx), "m"])
    if a.ny > 1:
        rows.append([T["sy"], _f(a.sy), "m"])
    rows += [[T["zw"], _f(a.profile.zw) if math.isfinite(a.profile.zw)
              else "Dry assumption", "m" if math.isfinite(a.profile.zw) else ""],
             [T["gw"], _f(a.profile.gw), "kN/m³"]]
    parts.append(_kv_table(T, rows))

    parts.append(N.h3(T["sec_soil"]))
    rows = [[_esc(r["name"]), L["behaviour_" + r["behaviour"]], _f(r["top"]), _f(r["bottom"]),
             _f(r["gamma"], 1), _f(r["gamma_sat"], 1), _f(r["phi"], 1),
             _f(r["cu"], 0) if r["behaviour"] == "cohesive" else "—",
             _f(r["OCR"], 1) if r["behaviour"] == "cohesive" else "—",
             _f(r["N60"], 0) if r["N60"] > 0 else "—", _f(r["E"], 0),
             _f(r["sigma_eff"], 1)] for r in res["layers"]]
    parts.append(_table([T["layer"], T["type"], T["top_l"], T["bottom"], L["col_gamma"],
                         L["col_gamma_sat"], L["col_phi"], L["col_cu"], L["col_OCR"],
                         L["col_N60"], L["col_E"], "σ'v0"], rows,
                        [15, 9, 6, 6, 8, 8, 7, 7, 6, 7, 8, 9]))

    parts.append(N.h3(T["sec_opts"]))
    rows = [[T["clay_method"], method_label(L, a.clay_method), ""],
            [T["tip_method"], method_label(L, a.tip_method), ""],
            [T["K"], _f(a.K_ratio), ""], [T["delta"], _f(a.delta_ratio), ""],
            [T["zc"], _f(res["zc"]) if math.isfinite(res["zc"]) else T["no"],
             "m" if math.isfinite(res["zc"]) else ""],
            [T["weight"], T["yes"] if a.subtract_weight else T["no"], ""],
            [T["buoyant"], T["yes"] if a.buoyant_weight else T["no"], ""],
            [T["efficiency"], L["eff_" + a.efficiency_method], ""],
            [T["block"], T["yes"] if a.use_block else T["no"], ""],
            [T["gs"], L["gs_" + a.group_settlement], ""],
            [T["FS"], _f(a.FS), ""], [T["s_allow"], _f(a.s_allow, 0), "mm"]]
    parts.append(_kv_table(T, rows))

    # ---------------------------------------------------------- single pile
    parts.append(N.h2(T["sec_single"]))
    base = res["base"]
    parts.append(N.h3(T["sec_base"]))
    parts.append(f"<p>{_esc(base['layer'])} · z = {_f(base['z'])} m · {T['sv']} = "
                 f"{_f(base['sv'], 1)} kPa</p>")
    rows = []
    for tip in TIP_METHODS:
        m = base["methods"][tip]
        name, value = ("Nc*", m["Nc"]) if "Nc" in m else ("Nq*", m["Nq"])
        mark = " *" if tip == a.tip_method else ""
        rows.append([_esc(method_label(L, tip) + mark), f"{name} = {_f(value, 1)}",
                     _f(m["qb"], 0), _f(m["Qb"], 0)])
    if math.isfinite(base["Qb_spt"]):
        rows.append([_esc(method_label(L, "spt")), "—", _f(base["qb_spt"], 0),
                     _f(base["Qb_spt"], 0)])
    parts.append(_table([T["method"], T["factor"], T["qb"], T["Qb"]], rows, [40, 20, 20, 20]))

    parts.append(N.h3(T["sec_shaft_layers"]))
    rows = []
    for layer, lo, hi in a.profile.segments(a.top, res["z_tip"]):
        part = sum(row[a.clay_method] * res["perimeter"] * row["h"]
                   for row in res["shaft"]["slices"] if lo - 1e-9 <= row["z"] <= hi + 1e-9)
        rows.append([_esc(layer["name"]), L["behaviour_" + layer["behaviour"]],
                     f"{lo:.2f} – {hi:.2f}", _f(part, 0)])
    parts.append(_table([T["layer"], T["type"], T["depth"], T["Qs"]], rows, [40, 20, 20, 20]))
    if res["shaft"]["cohesive"] or math.isfinite(res["shaft"]["Qs_spt"]):
        parts.append(N.h3(T["sec_shaft_methods"]))
        rows = [[_esc(method_label(L, m) + (" *" if m == a.clay_method else "")),
                 _f(res["shaft"]["Qs"][m], 0)]
                for m in (CLAY_METHODS if res["shaft"]["cohesive"] else [])]
        if math.isfinite(res["shaft"]["Qs_spt"]):
            rows.append([_esc(method_label(L, "spt")), _f(res["shaft"]["Qs_spt"], 0)])
        parts.append(_table([T["method"], T["Qs"]], rows, [60, 40]))

    parts.append(N.h3(T["sec_capacity"]))
    parts.append(_kv_table(T, [
        [T["Qs_l"], _f(res["Qs"], 0), "kN"], [T["Qb_l"], _f(res["Qb"], 0), "kN"],
        [T["Qu"], _f(res["Q_ult"], 0), "kN"],
        [T["W"], _f(res["W"], 0) + ("" if a.subtract_weight else f" ({T['no']})"), "kN"],
        [f"<b>{T['Qn']}</b>", f"<b>{_f(res['Q_ult_net'], 0)}</b>", "kN"],
        [f"<b>{T['Qa']}</b>", f"<b>{_f(res['Q_all'], 0)}</b>", "kN"],
    ]))
    parts.append(N.h3(T["sec_matrix"]))
    clays = CLAY_METHODS if res["shaft"]["cohesive"] else [a.clay_method]
    rows = [[_esc(method_label(L, c) if res["shaft"]["cohesive"] else L["method_granular"])]
            + [_f(res["combos"][f"{c}|{t}"]["Q_ult_net"], 0) for t in TIP_METHODS]
            for c in clays]
    parts.append(_table([T["method"]] + [method_label(L, t) for t in TIP_METHODS], rows,
                        [34, 22, 22, 22]))

    # ---------------------------------------------------------- group
    group = res["group"]
    parts.append(N.h2(T["sec_group"]))
    parts.append(N.h3(T["sec_eff"]))
    rows = [[_esc(L["eff_" + k] + (" *" if k == a.efficiency_method else "")), _f(v, 3)]
            for k, v in group["eta"].items()]
    parts.append(_table([T["method"], T["eta"]], rows, [70, 30]))
    if group["block"] is not None:
        b = group["block"]
        parts.append(N.h3(T["sec_block"]))
        parts.append(_kv_table(T, [[T["Bg"], _f(b["Bg"]), "m"], [T["Lg"], _f(b["Lg"]), "m"],
                                   [T["block_Qs"], _f(b["Qs"], 0), "kN"],
                                   [T["block_Qb"], _f(b["Qb"], 0), "kN"],
                                   [T["block_Q"], _f(b["Q_ult"], 0), "kN"]]))
    parts.append(N.h3(T["sec_group_cap"]))
    parts.append(_kv_table(T, [
        [T["Q_eff"], _f(group["Q_eff"], 0), "kN"],
        [T["Qg"], _f(group["Q_ult"], 0), "kN"],
        [T["governs"], L["gov_" + group["governing"]], ""],
        [T["Qgn"], _f(group["Q_ult_net"], 0), "kN"],
        [f"<b>{T['Qga']}</b>", f"<b>{_f(group['Q_all'], 0)}</b>", "kN"],
    ]))

    # ---------------------------------------------------------- settlement
    st = res["settlement"]
    parts.append(N.h2(T["sec_settlement"]))
    parts.append(N.h3(T["sec_single_s"]))
    single = st["single"]
    parts.append(_kv_table(T, [[T["s1"], _f(1000 * single["s1"]), "mm"],
                               [T["s2"], _f(1000 * single["s2"]), "mm"],
                               [T["s3"], _f(1000 * single["s3"]), "mm"],
                               [f"<b>{T['s']}</b>", f"<b>{_f(1000 * single['s'])}</b>", "mm"]]))
    parts.append(N.h3(T["sec_group_s"]))
    raft = st["raft"]
    rows = [[T["raft_z"], _f(raft["z_raft"]), "m"], [T["raft_q"], _f(raft["q"], 1), "kPa"],
            [T["raft_c"], _f(1000 * raft["consolidation"]), "mm"],
            [T["raft_e"], _f(1000 * raft["elastic"]), "mm"],
            [T["raft_sh"], _f(1000 * raft["shortening"]), "mm"],
            [f"{L['gs_raft']} — {T['raft_total']}", _f(1000 * raft["total"]), "mm"],
            [L["gs_vesic"], _f(1000 * st["vesic"]), "mm"]]
    if st["meyerhof"]:
        rows.append([L["gs_meyerhof"], _f(1000 * st["meyerhof"]["s"]), "mm"])
    parts.append(_kv_table(T, rows))
    if raft["rows"]:
        parts.append(N.h3(T["sec_raft"]))
        rows = [[_f(r["z"]), _f(r["h"]), _esc(r["layer"]), _f(r["sigma0"], 1),
                 _f(r["dsigma"], 1), L["model_" + r["kind"]], _f(1000 * r["s"])]
                for r in raft["rows"]]
        parts.append(_table([T["z"], T["h"], T["layer"], T["s0"], T["ds"], T["kind"],
                             T["ds_mm"]], rows, [10, 8, 24, 14, 14, 18, 12]))

    seismic = res.get("seismic")
    if seismic:
        parts.append(N.h2(T["sec_seismic"]))
        parts.append(N.h3(T["sec_seismic_loads"]))
        parts.append(_kv_table(T, [[T["V_E"], _f(a.V_E, 0), "kN"],
                                   [T["M_B"], _f(a.M_B, 0), "kN·m"],
                                   [T["M_L"], _f(a.M_L, 0), "kN·m"],
                                   [T["P_max"], _f(seismic["P_max"], 0), "kN"],
                                   [T["P_min"], _f(seismic["P_min"], 0), "kN"]]))
        rows = [[str(i + 1), _f(p["x"]), _f(p["y"]), _f(p["P"], 0)]
                for i, p in enumerate(seismic["loads"])]
        parts.append(_table([T["pile_no"], T["x"], T["y"], T["P"]], rows, [16, 28, 28, 28]))
        parts.append(N.h3(T["sec_seismic_checks"]))
        c, t = seismic["compression"], seismic["tension"]
        rows = [[T["QaE"], _f(c["Q_all"], 0), "kN"], [T["ts"], _f(a.tension_sand), ""],
                [T["tc"], _f(a.tension_clay), ""], [T["cyclic"], _f(a.cyclic), ""],
                [T["Qs_t"], _f(t["Qs"], 0), "kN"], [T["W_t"], _f(t["W"], 0), "kN"],
                [T["T_all"], _f(t["T_all"], 0), "kN"], [T["T"], _f(t["T"], 0), "kN"]]
        if seismic["group"]:
            rows.append([T["block_up"], _f(seismic["group"]["T_all"], 0), "kN"])
        if seismic.get("group_compression"):
            rows.append([T["group_comp"], _f(seismic["group_compression"]["Q_all"], 0), "kN"])
        parts.append(_kv_table(T, rows))

    # ---------------------------------------------------------- checks
    parts.append(N.h2(T["sec_checks"]))
    checks = res["checks"]
    parts.append(_checks_table(T, checks))
    length = res["required_length"]
    if not res.get("length_search_performed", True):
        text = L["res_length_not_searched"]
    else:
        text = (L["res_required_length"].format(L=length, z=a.top + length)
                if math.isfinite(length)
                else L["res_no_length"].format(hi=a.profile.depth - a.top))
    parts.append(f"<p>{_esc(text)}</p>")

    parts.append(N.h2(T["sec_figs"], page_break=True))
    for key in PLOT_KEYS:
        if key in figures:
            parts.append(f"<p class='lead'>{_esc(L.get('fig_' + key, key))}</p>")
            parts.append(f"<p><img src='{img_src(key)}' width='640'></p>")

    if res["warnings"]:
        parts.append(N.h2(T["sec_warn"]) + "<ul>")
        parts.extend(f"<li>{_esc(warning_text(w))}</li>" for w in res["warnings"])
        parts.append("</ul>")
    parts.append(N.h2(T["sec_notes"]) + "<ul class='note'>")
    parts.extend(f"<li>{_esc(n)}</li>" for n in T["notes"])
    parts.append("</ul>")
    return parts


def _socket_section(T, L, s, figures, img_src, N: _Numbers, page_break: bool,
                    shared_total_length=None) -> List[str]:
    res = s.results
    parts = [N.h2(T["sec_socket"], page_break=page_break), N.h3(T["sec_socket_in"])]
    m = res["modulus"]
    hb = res["hoek_brown"]
    parts.append(_kv_table(T, [
        [T["socket_D"], _f(s.D), "m"], [T["socket_Ls"], _f(res["Ls_check"]), "m"],
        ["Total head-to-tip length checked", _f(s.overburden + res["Ls_check"]), "m"],
        [T["socket_top"], _f(s.top), "m"], [T["rock"], _f(s.rock_depth), "m"],
        [T["overburden"], _f(res["overburden"]), "m"], [T["socket_Q"], _f(s.Q, 0), "kN"],
        [T["Qs_soil"], _f(res.get("Qs_soil", 0.0), 0) if res.get("Qs_soil", 0.0) > 0
         else T["not_counted"], "kN" if res.get("Qs_soil", 0.0) > 0 else ""],
        [T["qu"], _f(s.qu, 1), "MPa"], [T["qu_side"], _f(res["qu_side"], 1), "MPa"],
        [T["RQD"], _f(s.RQD, 0), "%"], [T["Ei"], _f(s.Ei, 0), "MPa"],
        [T["Em"], _f(m["Em"], 0), "MPa"], [T["ratio"], _f(m["ratio"], 3), ""],
        [T["alpha_E"], _f(m["alpha_E"], 3), ""], [T["GSI"], _f(s.GSI, 0), ""],
        [T["mi"], _f(s.mi, 1), ""], [T["mb"], _f(hb["mb"], 3), ""],
        [T["s_hb"], f"{hb['s']:.2e}", ""], [T["fc"], _f(s.fc, 1), "MPa"],
        [T["Ec"], _f(s.Ec, 0), "MPa"],
    ]))
    parts.append(N.h3(T["sec_socket_side"]))
    rows = []
    for key in SOCKET_SIDE_METHODS:
        e = res["side"][key]
        rows.append([_esc(L["side_" + key] + (" *" if key == res["design"] else "")),
                     _esc(e["formula"]), _f(e["fs"], 0), _f(e["Ls_design"], 0),
                     _f(e["Q_all"], 0),
                     T["yes"] if e["in_range"] else T["no"]])
    parts.append(_table([T["correlation"], T["formula"], T["fs"], T["Ls_req"], T["Q_all"],
                         T["range"]], rows, [30, 22, 11, 12, 14, 11]))
    st = res["stats"]
    parts.append(f"<p>{_esc(L['sock_stats'].format(n=st['n'], mean=st['mean'], median=st['median'], lo=st['lower'], hi=st['upper']))}</p>")
    parts.append(N.h3(T["sec_socket_base"]))
    rows = [[_esc(L["base_" + key]), _esc(res["base"][key]["formula"]),
             _f(res["base"][key]["qb"] / 1000.0)] for key in SOCKET_BASE_METHODS]
    parts.append(_table([T["method"], T["base_formula"], T["qb_mpa"]], rows, [45, 30, 25]))

    c = res["check"]
    parts.append(N.h3(T["sec_socket_design"]))
    recommended = res["Ls_design"] if shared_total_length is None else shared_total_length
    parts.append(_kv_table(T, [
        [T["fs_design"], _f(res["fs_design"], 0), "kPa"],
        [T["qb_design"], _f(res["qb_design"] / 1000.0), "MPa"],
        [T["FS_side"], _f(s.FS_side), ""], [T["FS_base"], _f(s.FS_base), ""],
        [T["Ls_need"], _f(res["Ls_req_continuous"]), "m"],
        [T["Ls_min"], _f(res["Ls_min"]), "m"],
        [f"<b>{T['Ls_design'] if shared_total_length is None else 'Common recommended whole-metre total pile length'}</b>",
         f"<b>{_f(recommended, 0)}</b>", "m"],
        [T["socket_Ls"], _f(res["Ls_check"]), "m"],
        [T["Qs_l"], _f(c["Qs"], 0), "kN"], [T["Qb_l"], _f(c["Qb"], 0), "kN"],
        [T["W"], _f(c["W"], 0), "kN"], [T["Qa"].split("=")[0].strip(), _f(c["Q_all"], 0), "kN"],
        [T["status"], _status(T, c["status"]), ""],
    ]))
    parts.append(_checks_table(T, res["checks"]))
    if shared_total_length is not None:
        explanation = ("The recommendation above is the common total head-to-tip length checked "
                       "in all boreholes. " if math.isfinite(shared_total_length)
                       else "No common length is recommended. ")
        parts.append(f"<p>{explanation}Correlation lengths in the side-shear table "
                     "apply to this log individually.</p>")
    if not math.isfinite(recommended):
        parts.append(f"<p>{_esc(L['sock_no_length'])}</p>")
    se = res["settlement"]
    parts.append(N.h3(T["sec_socket_s"]))
    parts.append(_kv_table(T, [
        [T["shortening"], _f(1000 * se["shortening"]), "mm"],
        [T["rw"], _f(1000 * se["rw"]["total"]), "mm"],
        [T["base_share"], _f(100 * se["rw"]["base_share"], 1), "%"],
        [T["rw_side"], _f(1000 * se["rw_side"]["total"]), "mm"],
        [T["vesic"], _f(1000 * se["vesic"]["total"]), "mm"],
        ["Settlement used in the check", _f(1000 * se["s"]), "mm"],
        ["Selected settlement method", T[se["method"]], ""],
        [T["s_allow"], _f(s.s_allow), "mm"],
    ]))
    parts.append(N.h3(T["sec_socket_figs"]))
    for key in SOCKET_PLOT_KEYS:
        if key in figures:
            parts.append(f"<p class='lead'>{_esc(L.get('fig_' + key, key))}</p>")
            parts.append(f"<p><img src='{img_src(key)}' width='640'></p>")
    if res["warnings"]:
        parts.append(N.h3(T["sec_socket_warn"]) + "<ul>")
        parts.extend(f"<li>{_esc(warning_text(w))}</li>" for w in res["warnings"])
        parts.append("</ul>")
    parts.append(N.h3(T["sec_socket_notes"]) + "<ul class='note'>")
    parts.extend(f"<li>{_esc(n)}</li>" for n in T["socket_notes"])
    parts.append("</ul>")
    return parts


def _spt_section(N: _Numbers, spt) -> List[str]:
    """The SPT records and the layers derived from them, with each value's source."""
    parts = [N.h2("Soil profile from the boreholes")]
    if hasattr(spt, "profiles"):
        parts.append("<p>Each borehole is interpreted independently, with its own "
                     "groundwater condition. Layers and parameters are not pooled "
                     "between logs.</p>")
        for profile in spt.profiles:
            parts.extend(_spt_profile_section(N, profile))
        return parts
    parts.extend(_spt_profile_section(N, spt))
    return parts


def _spt_profile_section(N: _Numbers, spt) -> List[str]:
    parts = [N.h3(f"Borehole: {spt.name}")]
    zw = "dry assumption" if spt.water_depth is None else f"{_f(spt.water_depth)} m"
    parts.append(f"<p>Water table: {zw}. N60 = N·(ER/60)·CB·CS·CR (Skempton 1986); "
                 "(N1)60 = CN·N60, CN = √(pa/σ'v0) ≤ 1.7 (Liao &amp; Whitman 1986). "
                 "Tests in alike, adjacent depth ranges form one layer; laboratory "
                 "values take precedence over the correlations.</p>")
    parts.append(N.h3("SPT records"))
    rows = [[_esc(r["borehole"]), _f(r["depth"]), _f(r["N"], 0), _f(r["N60"], 1),
             _f(r["N1_60"], 1), _f(r["sigma_eff"], 1), _esc(r["uscs"] or "—"),
             r["behaviour"], r["layer"]] for r in spt.records]
    parts.append(_table(["Borehole", "z (m)", "N", "N60", "(N1)60", "σ'v0 (kPa)", "USCS",
                         "Behaviour", "Layer"], rows, [14, 9, 8, 9, 9, 13, 10, 16, 8]))
    parts.append(N.h3("Layer parameters and their sources"))
    labels = {"gamma": "γ / γsat", "phi": "φ'", "cu": "cu", "OCR": "OCR", "N60": "N60",
              "E": "E", "Cc": "Cc", "Cr": "Cr", "e0": "e0", "nu": "ν"}
    units = {"gamma": "kN/m³", "phi": "°", "cu": "kPa", "E": "MPa"}
    top = 0.0
    for i, (layer, src) in enumerate(zip(spt.layers, spt.sources), start=1):
        bottom = top + layer["thickness"]
        parts.append(f"<p><b>Layer {i}: {_esc(layer['name'])}</b>, {_f(top)}–{_f(bottom)} m, "
                     f"{layer['behaviour']}</p>")
        rows = []
        for key, label in labels.items():
            if key not in src:
                continue
            value = f"{_f(layer['gamma'], 1)} / {_f(layer['gamma_sat'], 1)}" \
                if key == "gamma" else _f(layer[key], 3 if key in ("Cc", "Cr", "e0") else 1)
            rows.append([label, value, units.get(key, ""), _esc(src[key])])
        parts.append(_table(["Parameter", "Value", "Unit", "Source"], rows, [16, 16, 10, 58]))
        top = bottom
    if spt.warnings:
        parts.append("<ul class='note'>")
        parts.extend(f"<li>{_esc(w)}</li>" for w in spt.warnings)
        parts.append("</ul>")
    return parts


def _envelope_section(T, L, analysis, figures, img_src, N: _Numbers) -> List[str]:
    res = analysis.results
    is_socket = res["pile_type"] == "socket"
    length_label = "Common total head-to-tip length checked L"
    parts = [N.h2("Borehole envelope and common design")]
    parts.append("<p>Every borehole is analysed separately at the same pile geometry "
                 "and load. For each check the largest utilisation governs; different "
                 "checks may be governed by different boreholes. A design passes only "
                 "when every active check passes in every log. Utilisation must be "
                 "at most 1.000.</p>")
    checked_length = _f(res["L"]) if res["L"] > 0 else "No common length selected"
    parts.append(_kv_table(T, [["Number of boreholes", str(len(analysis.analyses)), ""],
                               ["Common diameter D", _f(res["D"]), "m"],
                               [length_label, checked_length, "m" if res["L"] > 0 else ""],
                               ["Status at the checked length", _status(T, res["status"]), ""]]))
    parts.append(N.h3("Controlling checks at the checked length"))
    parts.append(_checks_table(T, res["checks"], boreholes=True))
    parts.append(N.h3("Common recommended length"))
    length = res["required_length"]
    if not res.get("length_search_performed", True):
        parts.append("<p>A common length search was not requested.</p>")
    elif math.isfinite(length):
        parts.append(f"<p><b>Common recommended whole-metre length: L = "
                     f"{_f(length, 0)} m.</b> Every log was recalculated at this exact "
                     "length and all active checks pass.</p>")
        parts.append(_checks_table(T, res["design_checks"], boreholes=True))
    else:
        parts.append("<p><b>No common whole-metre length passes every active check "
                     "within the available search range.</b></p>")
    if is_socket:
        parts.append(N.h3("Socket embedment in each borehole"))
        parts.append("<p>The common length is measured from the pile head to its tip. "
                     "Each socket embedment is calculated from that total length and "
                     "the rock depth in its own log. These derived embedments may be "
                     "fractional; the recommended total pile length is a whole metre.</p>")
        rows = [[_esc(name), _f(child.rock_depth), _f(child.overburden),
                 _f(res["checked_socket_lengths"].get(name)),
                 _f(res["design_socket_lengths"].get(name))]
                for name, child in analysis.analyses.items()]
        parts.append(_table(["Borehole", "Rock depth (m)", "Overburden (m)",
                             "Checked embedment (m)", "Embedment at common recommendation (m)"],
                            rows, [24, 17, 17, 20, 22]))
    parts.append("<p>The following sections preserve each borehole's own soil, "
                 "water and rock conditions. Each section states its checked geometry. "
                 "Individual correlation recommendations apply only to that log; "
                 "the shared recommendation is reported above.</p>")
    for index, (name, child) in enumerate(analysis.analyses.items()):
        prefix = f"log{index}:"
        child_figures = {key[len(prefix):]: value for key, value in figures.items()
                         if key.startswith(prefix)}

        def child_src(key, prefix=prefix):
            return img_src(prefix + key)

        parts.append(N.h2(f"Borehole: {name}", page_break=True))
        if is_socket:
            parts.extend(_socket_section(T, L, child, child_figures, child_src, N,
                                         page_break=False, shared_total_length=length
                                         if res.get("length_search_performed", True) else None))
        else:
            parts.extend(_pile_section(T, L, child, child_figures, child_src, N))
    return parts


def build_html(analysis, figures: Dict[str, bytes], img_src=None,
               socket=None, spt=None) -> str:
    """
    Builds the report HTML. img_src(key) -> value for the <img src> attribute;
    the default embeds base64 data URIs (the self-contained HTML file). The PDF
    and DOCX writers pass a `fig://<key>` mapper and resolve the keys against
    the figure dictionary themselves.

    The first argument accepts any result of ``pile.analyse``: a soil pile,
    a socket or a borehole envelope. ``spt`` accepts an SPTProfile or an
    SPTInvestigation and adds the records and independent layer derivations.
    """
    if analysis is None and socket is None:
        raise ValueError("nothing to report")
    T = REPORT_TEXTS
    source = analysis if analysis is not None else socket
    info = source.config.get("project_info", {})
    if img_src is None:
        def img_src(key):
            return "data:image/png;base64," + base64.b64encode(figures[key]).decode("ascii")

    parts = [f"<html><head><meta charset='utf-8'><style>{_CSS}</style></head><body>"]
    parts.append(f"<h1>{_esc(info.get('title') or T['title'])}</h1>")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    meta = f"{T['date']}: {stamp}"
    if info.get("analyst"):
        meta += f" &nbsp;·&nbsp; {T['analyst']}: {_esc(info['analyst'])}"
    meta += f" &nbsp;·&nbsp; {T['software']}: {APP_NAME} v{APP_VERSION}"
    parts.append(f"<p class='meta'>{meta}</p>")

    N = _Numbers()
    if spt is not None:
        parts.extend(_spt_section(N, spt))
    if analysis is not None:
        if analysis.results.get("envelope"):
            parts.extend(_envelope_section(T, L, analysis, figures, img_src, N))
        elif analysis.config.get("pile_type") == "socket":
            parts.extend(_socket_section(T, L, analysis, figures, img_src, N,
                                         page_break=False))
        else:
            parts.extend(_pile_section(T, L, analysis, figures, img_src, N))
    if socket is not None:
        if socket.results.get("envelope"):
            parts.extend(_envelope_section(T, L, socket, figures, img_src, N))
        else:
            parts.extend(_socket_section(T, L, socket, figures, img_src, N,
                                         page_break=analysis is not None))
    parts.append("</body></html>")
    return "\n".join(parts)


# ----------------------------------------------------------------------
# exporters
# ----------------------------------------------------------------------
def _all_figures(analysis, socket):
    figures = render_figures(analysis)
    figures.update(render_socket_figures(socket))
    return figures


def export_pdf(path: str, analysis, socket=None, spt=None) -> None:
    """PDF through reportlab; the figures travel as `fig://<key>` references."""
    from . import pdf as pdf_writer

    T = REPORT_TEXTS
    source = analysis if analysis is not None else socket
    info = source.config.get("project_info", {})
    figures = _all_figures(analysis, socket)
    html_text = build_html(analysis, figures, img_src=lambda k: f"fig://{k}",
                           socket=socket, spt=spt)
    pdf_writer.html_to_pdf(path, html_text, figures,
                           title=info.get("title", T["title"]),
                           author=info.get("analyst", ""),
                           footer=f"{info.get('title', '')} — {APP_NAME} v{APP_VERSION}")


def export_report(path: str, analysis, socket=None, spt=None) -> None:
    """The calculation report, always as PDF; '.pdf' is added when missing.
    `spt`: the SPTProfile or SPTInvestigation used to derive the logs."""
    if not path.lower().endswith(".pdf"):
        path = f"{path}.pdf"
    export_pdf(path, analysis, socket, spt)
