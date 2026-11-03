"""
Results as text and as summary cards.

Both the browser interface and the command line show the same thing: the
headline numbers as a row of cards, and the full account of the analysis as
text. Assembling them here keeps that promise without either side copying the
other's wording, and it needs no interface toolkit at all — pass a finished
analysis and a language code.
"""

from __future__ import annotations

import math
from typing import List

from .config import CLAY_METHODS, SOCKET_BASE_METHODS, SOCKET_SIDE_METHODS, TIP_METHODS
from .i18n import TRANSLATIONS, warning_text

#: Card order, as the interface lays them out
CARD_KEYS = ["Q_ult", "Q_net", "Q_all", "pile_load", "check_pile", "check_group",
             "settlement", "length"]

#: The cards the seismic load case adds when the earthquake is on
SEISMIC_CARD_KEYS = ["seismic_compression", "seismic_tension"]

SOCKET_CARD_KEYS = ["socket_fs", "socket_qb", "socket_length", "socket_Q_all",
                    "socket_check", "socket_settlement"]


def _lang(lang: str) -> dict:
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"])


def status_text(L: dict, status: str) -> tuple:
    """A check status as (short text, state) — state drives the card colour."""
    if status == "N/A":
        return L["na_short"], "na"
    return (L["ok_short"], "ok") if status == "OK" else (L["notok_short"], "bad")


def method_label(L: dict, key: str) -> str:
    return L.get(f"method_{key}", key)


def _kn(value: float, nd: int = 0) -> str:
    if value is None or not math.isfinite(value):
        return "—"
    return f"{value:,.{nd}f} kN"


def _num(value, nd: int = 1) -> str:
    if value is None or not math.isfinite(value):
        return "—"
    return f"{value:,.{nd}f}"


def _row(first: str, values, width: int = 28, cell: int = 13) -> str:
    return f"  {first:<{width}}" + "".join(f"{v:>{cell}}" for v in values)


# --------------------------------------------------------------------------- #
#  Pile
# --------------------------------------------------------------------------- #

def cards(analysis, lang: str = "en") -> List[dict]:
    """The headline numbers: the capacity, the load, the checks and the length."""
    L = _lang(lang)
    res = analysis.results
    checks = res["checks"]
    out = []

    def card(key, value, sub="", state=""):
        out.append({"key": key, "title": L[f"card_{key}"], "value": value, "sub": sub,
                    "state": state})

    card("Q_ult", _kn(res["Q_ult"]), f"Qs = {res['Qs']:,.0f} · Qb = {res['Qb']:,.0f} kN")
    card("Q_net", _kn(res["Q_ult_net"]), L["card_weight"].format(W=res["W"]))
    card("Q_all", _kn(res["Q_all"]), f"FS = {analysis.FS:.2f}")
    card("pile_load", _kn(res["Q_pile"]), L["card_piles"].format(n=res["n"], Q=res["Q"]))
    text, state = status_text(L, checks["pile"]["status"])
    card("check_pile", text, f"FS = {checks['pile']['actual']:.2f} / "
         f"{checks['pile']['allowable']:.2f}", state)
    group = res["group"]
    text, state = status_text(L, checks["group"]["status"])
    card("check_group", text, f"η = {group['eta_used']:.2f} · FS = {group['FS']:.2f}", state)
    s = checks["settlement"]
    text, state = status_text(L, s["status"])
    card("settlement", f"{s['actual']:.1f} mm",
         f"{L['gs_' + res['settlement']['method']]} · ≤ {s['allowable']:.0f} mm", state)
    length = res["required_length"]
    card("length", f"{length:.2f} m" if math.isfinite(length) else L["card_none"],
         L["card_tip"].format(z=analysis.top + length) if math.isfinite(length) else "",
         "" if math.isfinite(length) else "na")
    seismic = res.get("seismic")
    if seismic:
        c = checks["seismic_compression"]
        text, state = status_text(L, c["status"])
        card("seismic_compression", text,
             f"Pmax = {seismic['P_max']:,.0f} kN · FS = {c['actual']:.2f}", state)
        t = checks["seismic_tension"]
        text, state = status_text(L, t["status"])
        tension = seismic["tension"]
        card("seismic_tension", text if tension["T"] > 0 else L["card_no_tension"],
             f"T = {tension['T']:,.0f} kN · Tall = {tension['T_all']:,.0f} kN", state)
    return out


def method_table(analysis, lang: str = "en") -> dict:
    """The shaft methods against the base methods: the net ultimate capacity of each."""
    L = _lang(lang)
    res = analysis.results
    columns = [L["head_shaft_method"], L["head_Qs"]] + \
        [method_label(L, tip) for tip in TIP_METHODS]
    rows = []
    primary = res["primary"]
    clay_rows = CLAY_METHODS if res["shaft"]["cohesive"] else [primary["clay"]]
    for clay in clay_rows:
        cells = [method_label(L, clay) if res["shaft"]["cohesive"] else L["method_granular"],
                 f"{res['shaft']['Qs'][clay]:,.0f}"]
        states = ["", ""]
        for tip in TIP_METHODS:
            combo = res["combos"][f"{clay}|{tip}"]
            cells.append(f"{combo['Q_ult_net']:,.0f}")
            fs = combo["Q_ult_net"] / res["Q_pile"]
            states.append("ok" if fs >= analysis.FS else "bad")
        rows.append({"cells": cells, "states": states, "primary": clay == primary["clay"]})
    if math.isfinite(res["shaft"]["Qs_spt"]) and math.isfinite(res["base"]["Qb_spt"]):
        net = res["shaft"]["Qs_spt"] + res["base"]["Qb_spt"] - res["W_used"]
        rows.append({"cells": [method_label(L, "spt"), f"{res['shaft']['Qs_spt']:,.0f}",
                               f"{net:,.0f}", "", ""],
                     "states": ["", "", "ok" if net / res["Q_pile"] >= analysis.FS else "bad",
                                "", ""],
                     "primary": False})
    return {"columns": columns, "rows": rows}


def results_text(analysis, lang: str = "en") -> str:
    """The whole pile analysis as text, in the chosen language."""
    L = _lang(lang)
    a, res = analysis, analysis.results
    lines = [L["res_title"], "-" * 84]
    lines.append(L["res_pile"].format(shape=L["shape_" + a.shape], D=a.D, L=a.L, top=a.top,
                                      tip=res["z_tip"],
                                      inst=L["installation_" + a.installation]))
    lines.append(L["res_area"].format(A=res["A"], p=res["perimeter"]))
    lines.append(L["res_group"].format(nx=a.nx, ny=a.ny, n=a.n, sx=a.sx, sy=a.sy, Q=a.Q,
                                       Qp=res["Q_pile"]))
    lines.append(L["res_water"].format(zw=a.profile.zw))
    if math.isfinite(res["zc"]):
        lines.append(L["res_zc"].format(zc=res["zc"], ratio=a.zc_ratio))
    lines.append(L["res_K"].format(K=a.K_ratio, delta=a.delta_ratio))

    base = res["base"]
    lines += ["", L["res_tip_title"]]
    lines.append("  " + L["res_tip_layer"].format(name=base["layer"], z=base["z"],
                                                  sv=base["sv"],
                                                  kind=L["behaviour_" + base["behaviour"]]))
    for tip in TIP_METHODS:
        m = base["methods"][tip]
        factor = m.get("Nq", m.get("Nc", float("nan")))
        name = "Nc*" if "Nc" in m else "Nq*"
        mark = " *" if tip == a.tip_method else ""
        lines.append(_row(method_label(L, tip)[:26] + mark,
                          [f"{name} = {_num(factor, 1)}", f"{m['qb']:,.0f} kPa",
                           f"{m['Qb']:,.0f} kN"]))
    if math.isfinite(base["Qb_spt"]):
        lines.append(_row(method_label(L, "spt")[:26],
                          ["", f"{base['qb_spt']:,.0f} kPa", f"{base['Qb_spt']:,.0f} kN"]))

    lines += ["", L["res_shaft_title"], _row(L["head_layer"], [L["head_depth"],
                                                               L["head_Qs"]])]
    for layer, lo, hi in a.profile.segments(a.top, res["z_tip"]):
        part = sum(row[a.clay_method] * res["perimeter"] * row["h"]
                   for row in res["shaft"]["slices"] if lo - 1e-9 <= row["z"] <= hi + 1e-9)
        lines.append(_row(layer["name"][:26], [f"{lo:.2f}–{hi:.2f}", f"{part:,.0f} kN"]))
    if res["shaft"]["cohesive"]:
        lines.append("  " + L["res_clay_methods"])
        for clay in CLAY_METHODS:
            mark = " *" if clay == a.clay_method else ""
            lines.append(_row(method_label(L, clay)[:26] + mark,
                              [f"{res['shaft']['Qs'][clay]:,.0f} kN"]))
    if math.isfinite(res["shaft"]["Qs_spt"]):
        lines.append(_row(method_label(L, "spt")[:26],
                          [f"{res['shaft']['Qs_spt']:,.0f} kN"]))

    lines += ["", L["res_capacity_title"]]
    lines.append("  " + L["res_capacity"].format(Qs=res["Qs"], Qb=res["Qb"], Qu=res["Q_ult"]))
    lines.append("  " + L["res_weight"].format(W=res["W"],
                                               used=L["yes"] if a.subtract_weight
                                               else L["no"]))
    lines.append("  " + L["res_net"].format(Qn=res["Q_ult_net"], FS=a.FS, Qa=res["Q_all"]))

    group = res["group"]
    lines += ["", L["res_group_title"]]
    for key, value in group["eta"].items():
        mark = " *" if key == a.efficiency_method else ""
        lines.append(_row(L["eff_" + key][:26] + mark, [f"η = {_num(value, 3)}"]))
    lines.append("  " + L["res_group_eff"].format(eta=group["eta_used"], n=a.n,
                                                  Q=group["Q_eff"]))
    if group["block"] is not None:
        b = group["block"]
        lines.append("  " + L["res_block"].format(Bg=b["Bg"], Lg=b["Lg"], Qs=b["Qs"],
                                                  Qb=b["Qb"], Q=b["Q_ult"]))
    lines.append("  " + L["res_group_capacity"].format(
        Q=group["Q_ult"], gov=L["gov_" + group["governing"]], Qn=group["Q_ult_net"],
        Qa=group["Q_all"]))

    st = res["settlement"]
    single = st["single"]
    lines += ["", L["res_settlement_title"]]
    lines.append("  " + L["res_single"].format(s1=1000 * single["s1"], s2=1000 * single["s2"],
                                               s3=1000 * single["s3"], s=1000 * single["s"]))
    raft = st["raft"]
    lines.append("  " + L["res_raft"].format(z=raft["z_raft"], q=raft["q"],
                                             c=1000 * raft["consolidation"],
                                             e=1000 * raft["elastic"],
                                             sh=1000 * raft["shortening"],
                                             s=1000 * raft["total"]))
    lines.append("  " + L["res_vesic_group"].format(s=1000 * st["vesic"], Bg=st["Bg"], D=a.D))
    if st["meyerhof"]:
        m = st["meyerhof"]
        lines.append("  " + L["res_meyerhof_group"].format(s=1000 * m["s"], N=m["N60"],
                                                           I=m["I"], q=m["q"]))

    seismic = res.get("seismic")
    if seismic:
        lines += ["", L["res_seismic_title"]]
        lines.append("  " + L["res_seismic_loads"].format(V=a.V_E, MB=a.M_B, ML=a.M_L,
                                                          pmax=seismic["P_max"],
                                                          pmin=seismic["P_min"]))
        c = seismic["compression"]
        lines.append("  " + L["res_seismic_compression"].format(
            Qn=res["Q_ult_net"], FS=a.FS_E_c, Qa=c["Q_all"], P=c["P"]))
        t = seismic["tension"]
        lines.append("  " + L["res_seismic_uplift"].format(
            ts=a.tension_sand, tc=a.tension_clay, cy=a.cyclic, Qs=t["Qs"], W=t["W"],
            FS=a.FS_E_t, Ta=t["T_all"]))
        lines.append("  " + (L["res_seismic_tension"].format(T=t["T"], n=t["n"])
                             if t["T"] > 0 else L["res_seismic_no_tension"]))
        if seismic["group"]:
            g = seismic["group"]
            lines.append("  " + L["res_seismic_block"].format(
                Bg=g["Bg"], Lg=g["Lg"], Qs=g["Qs"], W=g["W"], Ta=g["T_all"], T=g["T"]))

    checks = res["checks"]
    lines += ["", L["res_checks_title"]]
    for key in ("pile", "group"):
        c = checks[key]
        lines.append("  " + L[f"res_check_{key}"].format(
            actual=c["actual"], allowable=c["allowable"], status=status_text(L, c["status"])[0]))
    c = checks["settlement"]
    lines.append("  " + L["res_check_settlement"].format(
        actual=c["actual"], allowable=c["allowable"], status=status_text(L, c["status"])[0]))
    for key in ("seismic_compression", "seismic_tension", "seismic_group_tension"):
        if key in checks and checks[key]["status"] != "N/A":
            c = checks[key]
            lines.append("  " + L[f"res_check_{key}"].format(
                actual=c["actual"], allowable=c["allowable"],
                status=status_text(L, c["status"])[0]))

    length = res["required_length"]
    lines += ["", ("  " + L["res_required_length"].format(L=length, z=a.top + length))
              if math.isfinite(length)
              else ("  " + L["res_no_length"].format(hi=a.profile.depth - a.top))]

    lines += ["", L["res_layers_title"],
              _row(L["head_layer"], [L["head_depth"], L["col_gamma"], L["col_phi"],
                                     L["col_cu"], L["col_N60"], L["head_sigma"]])]
    for row in res["layers"]:
        lines.append(_row(row["name"][:26],
                          [f"{row['top']:.1f}–{row['bottom']:.1f}", _num(row["gamma"], 1),
                           _num(row["phi"], 1),
                           _num(row["cu"], 1) if row["behaviour"] == "cohesive" else "—",
                           _num(row["N60"], 0) if row["N60"] > 0 else "—",
                           _num(row["sigma_eff"], 1)]))

    if res["warnings"]:
        lines += ["", L["warnings_title"]]
        lines += ["  • " + warning_text(lang, w) for w in res["warnings"]]
    return "\n".join(lines)


def warnings(analysis, lang: str = "en") -> List[str]:
    return [warning_text(lang, w) for w in analysis.results.get("warnings", [])]


def headline(analysis, lang: str = "en") -> str:
    """One line for the status bar: the capacity, the checks and the length."""
    L = _lang(lang)
    res = analysis.results
    status, _ = status_text(L, "OK" if all(c["status"] in ("OK", "N/A")
                                           for c in res["checks"].values()) else "NOT OK")
    length = res["required_length"]
    tail = f" · L ≥ {length:.2f} m" if math.isfinite(length) else ""
    return (f"Qult,net = {res['Q_ult_net']:,.0f} kN · FS = {res['FS']:.2f} · "
            f"{L['card_checks']}: {status}{tail}")


# --------------------------------------------------------------------------- #
#  Rock socket
# --------------------------------------------------------------------------- #

def socket_cards(socket, lang: str = "en") -> List[dict]:
    L = _lang(lang)
    res = socket.results
    out = []

    def card(key, value, sub="", state=""):
        out.append({"key": key, "title": L[f"card_{key}"], "value": value, "sub": sub,
                    "state": state})

    design = res["design"]
    name = L[f"design_{design}"] if design in res["stats"] else L[f"side_{design}"]
    card("socket_fs", f"{res['fs_design']:,.0f} kPa", name)
    card("socket_qb", f"{res['qb_design'] / 1000.0:,.1f} MPa",
         L[f"base_design_{res['base_design']}"] if res["base_design"] in ("none", "min", "mean")
         else L[f"base_{res['base_design']}"])
    length = res["Ls_design"]
    lo, hi = res["Ls_spread"]
    card("socket_length", f"{length:.2f} m" if math.isfinite(length) else L["card_none"],
         f"{lo:.2f} – {hi:.2f} m" if math.isfinite(lo) else "",
         "" if math.isfinite(length) else "na")
    check = res["check"]
    card("socket_Q_all", _kn(check["Q_all"]), L["card_at_length"].format(Ls=res["Ls_check"]))
    text, state = status_text(L, check["status"])
    card("socket_check", text, f"Q/Qall = {check['utilisation']:.2f}", state)
    st = res["settlement"]
    card("socket_settlement", f"{1000 * st['rw']['total']:.1f} mm",
         L["card_base_share"].format(share=100 * st["rw"]["base_share"]))
    return out


def socket_table(socket, lang: str = "en") -> dict:
    """Every side shear correlation: fs, the length it needs, the capacity it gives."""
    L = _lang(lang)
    res = socket.results
    columns = [L["head_correlation"], L["head_formula"], L["head_fs"], L["head_Ls_req"],
               L["head_Q_all"]]
    rows = []
    for key in SOCKET_SIDE_METHODS:
        entry = res["side"][key]
        Ls = entry["Ls_req"]
        rows.append({
            "cells": [L[f"side_{key}"], entry["formula"], f"{entry['fs']:,.0f}",
                      f"{Ls:.2f}" if math.isfinite(Ls) else "—",
                      f"{entry['Q_all']:,.0f}"],
            "states": ["", "", "", "" if entry["in_range"] else "off",
                       "ok" if entry["Q_all"] >= res["Q"] else "bad"],
            "primary": key == res["design"],
            "muted": not entry["in_range"],
        })
    return {"columns": columns, "rows": rows}


def socket_text(socket, lang: str = "en") -> str:
    """The rock socket as text."""
    L = _lang(lang)
    s, res = socket, socket.results
    lines = [L["sock_title"], "-" * 84]
    lines.append(L["sock_geometry"].format(D=s.D, top=s.top, rock=s.rock_depth,
                                           Lo=res["overburden"], Ls=res["Ls_check"], Q=s.Q))
    m = res["modulus"]
    lines.append(L["sock_rock"].format(qu=s.qu, qs=res["qu_side"], fc=s.fc, Em=m["Em"],
                                       ratio=m["ratio"], aE=m["alpha_E"]))
    hb = res["hoek_brown"]
    lines.append(L["sock_hb"].format(GSI=s.GSI, mi=s.mi, mb=hb["mb"], s=hb["s"]))

    lines += ["", L["sock_side_title"],
              _row(L["head_correlation"], [L["head_fs"], L["head_Ls_req"], L["head_Q_all"]],
                   34, 17)]
    for key in SOCKET_SIDE_METHODS:
        e = res["side"][key]
        mark = "" if e["in_range"] else " †"
        star = " *" if key == res["design"] else ""
        lines.append(_row((L[f"side_{key}"] + star + mark)[:34],
                          [f"{e['fs']:,.0f}", _num(e["Ls_req"], 2), f"{e['Q_all']:,.0f}"],
                          34, 17))
    st = res["stats"]
    lines.append("  " + L["sock_stats"].format(n=st["n"], mean=st["mean"], median=st["median"],
                                               lo=st["lower"], hi=st["upper"]))
    if any(not e["in_range"] for e in res["side"].values()):
        lines.append("  " + L["sock_weak_note"].format(limit=s.weak_rock))

    lines += ["", L["sock_base_title"]]
    for key in SOCKET_BASE_METHODS:
        e = res["base"][key]
        lines.append(_row(L[f"base_{key}"][:38], [e["formula"], f"{e['qb'] / 1000:,.2f} MPa"],
                          38, 24))

    c = res["check"]
    lines += ["", L["sock_design_title"]]
    lines.append("  " + L["sock_design"].format(fs=res["fs_design"], qb=res["qb_design"] / 1000,
                                                FSs=s.FS_side, FSb=s.FS_base))
    if math.isfinite(res["Ls_req"]):
        lines.append("  " + L["sock_length"].format(Ls=res["Ls_req"], mn=res["Ls_min"],
                                                    Ld=res["Ls_design"]))
    else:
        lines.append("  " + L["sock_no_length"])
    lines.append("  " + L["sock_check"].format(Ls=res["Ls_check"], Qs=c["Qs"], Qb=c["Qb"],
                                               W=c["W"], Qa=c["Q_all"], Q=s.Q,
                                               u=c["utilisation"],
                                               status=status_text(L, c["status"])[0]))

    st = res["settlement"]
    lines += ["", L["sock_settlement_title"].format(Ls=st["Ls"])]
    lines.append("  " + L["sock_shortening"].format(s=1000 * st["shortening"]))
    lines.append("  " + L["sock_rw"].format(s=1000 * st["rw"]["total"],
                                            share=100 * st["rw"]["base_share"]))
    lines.append("  " + L["sock_rw_side"].format(s=1000 * st["rw_side"]["total"]))
    lines.append("  " + L["sock_vesic"].format(s=1000 * st["vesic"]["total"]))

    if res["warnings"]:
        lines += ["", L["warnings_title"]]
        lines += ["  • " + warning_text(lang, w) for w in res["warnings"]]
    return "\n".join(lines)


def socket_warnings(socket, lang: str = "en") -> List[str]:
    return [warning_text(lang, w) for w in socket.results.get("warnings", [])]


def socket_headline(socket, lang: str = "en") -> str:
    L = _lang(lang)
    res = socket.results
    length = res["Ls_design"]
    status, _ = status_text(L, res["check"]["status"])
    head = f"Ls ≥ {length:.2f} m" if math.isfinite(length) else L["card_none"]
    return (f"{head} · fs = {res['fs_design']:,.0f} kPa · {L['card_checks']}: {status} · "
            f"s = {1000 * res['settlement']['rw']['total']:.1f} mm")
