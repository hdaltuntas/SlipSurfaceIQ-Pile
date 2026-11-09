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
from .texts import TEXTS as L, warning_text

def status_text(L: dict, status: str) -> tuple:
    """A check status as (short text, state) — state drives the card colour."""
    if status == "N/A":
        return L["na_short"], "na"
    return (L["ok_short"], "ok") if status == "OK" else (L["notok_short"], "bad")


def method_label(L: dict, key: str) -> str:
    return L.get(f"method_{key}", key)


def _num(value, nd: int = 1) -> str:
    if value is None or not math.isfinite(value):
        return "—"
    return f"{value:,.{nd}f}"


def _row(first: str, values, width: int = 28, cell: int = 13) -> str:
    return f"  {first:<{width}}" + "".join(f"{v:>{cell}}" for v in values)


def _check_label(key: str) -> str:
    return {
        "pile": "Single-pile capacity", "group": "Group capacity",
        "capacity": "Socket capacity", "min_length": "Minimum socket length",
        "settlement": "Settlement", "seismic_compression": "Seismic compression",
        "seismic_group_compression": "Seismic group compression",
        "seismic_tension": "Seismic uplift", "seismic_group_tension": "Seismic block uplift",
        "shared_design": "Common design",
    }.get(key, key.replace("_", " "))


def _check_line(key: str, check: dict, *, governing: bool = False) -> str:
    """One complete check; never combine demand from one log with another's limit."""
    status = status_text(L, check["status"])[0]
    actual, limit = _num(check.get("actual"), 2), _num(check.get("allowable"), 2)
    unit = " mm" if key == "settlement" else " m" if key == "min_length" else \
        " kN" if key == "capacity" else ""
    relation = "minimum" if key == "min_length" or key in {
        "pile", "group", "seismic_compression", "seismic_group_compression",
        "seismic_tension", "seismic_group_tension",
    } else "maximum"
    line = (f"  {_check_label(key)}: {actual}{unit} ({relation} {limit}{unit}); "
            f"utilisation = {_num(check.get('utilisation'), 3)} — {status}")
    if governing:
        line += f"; governing borehole: {check.get('governing_borehole') or '—'}"
    return line


def borehole_text(analysis) -> str:
    """Common geometry and controlling checks, followed by separate log results."""
    res = analysis.results
    is_socket = res["pile_type"] == "socket"
    has_checked_geometry = not is_socket or bool(res["checked_socket_lengths"])
    geometry = (f"Checked common geometry: D = {res['D']:.2f} m, L = {res['L']:.2f} m"
                if has_checked_geometry else
                f"No checked common geometry is available; D = {res['D']:.2f} m.")
    lines = ["BOREHOLE ENVELOPE", "-" * 84,
             geometry,
             f"Independent boreholes: {len(analysis.analyses)}; soil profiles are not combined."]
    if is_socket:
        lines.append("L is the common total head-to-tip pile length. Each borehole has its own "
                     "rock embedment Ls = L minus the overburden length; Ls may be fractional.")
    lines += ["", "CHECKS AT THE CHECKED COMMON GEOMETRY"]
    lines.extend(_check_line(key, check, governing=True)
                 for key, check in res["checks"].items())
    lines.append(f"  Overall: {status_text(L, res['status'])[0]}")
    required = res["required_length"]
    lines += ["", "COMMON RECOMMENDATION"]
    if math.isfinite(required):
        lines.append(f"  Recommended whole-metre L = {required:.0f} m; "
                     "every active check was re-evaluated in every borehole at this length.")
        if res.get("design_checks"):
            lines.extend(_check_line(key, check, governing=True)
                         for key, check in res["design_checks"].items())
    elif not res.get("length_search_performed", True):
        lines.append("  Length search was not requested; no common length recommendation is available.")
    else:
        lines.append("  No verified common whole-metre length was found within the search bounds.")
    if is_socket:
        lines += ["", "SOCKET GEOMETRY BY BOREHOLE",
                  "Checked columns refer to the entered or automatically selected common geometry; "
                  "design columns refer to the common recommendation.",
                  _row("Borehole", ["Overburden (m)", "Checked Ls (m)", "Checked L (m)",
                                     "Design Ls (m)", "Design L (m)"], 28, 17)]
        checked_lengths = res["checked_socket_lengths"]
        design_lengths = res.get("design_socket_lengths") or {}
        for name, child in analysis.analyses.items():
            lines.append(_row(name, [_num(child.results["overburden"], 2),
                                     _num(checked_lengths.get(name), 2),
                                     _num(res["L"] if has_checked_geometry else None, 2),
                                     _num(design_lengths.get(name), 2),
                                     _num(required, 0)], 28, 17))
    lines += ["", "INDEPENDENT BOREHOLE RESULTS",
              ("Each log below is evaluated at the checked common geometry. "
               if has_checked_geometry else "No common checked geometry was established. ") +
              "Any log-specific recommendation does not replace the common recommendation above."]
    for name, child in analysis.analyses.items():
        lines += ["", f"BOREHOLE: {name}",
                  socket_text(child, log_only=True) if is_socket else results_text(child)]
    return "\n".join(lines)


def borehole_headline(analysis) -> str:
    res = analysis.results
    status = status_text(L, res["status"])[0]
    required = res["required_length"]
    recommendation = (f" · common Ldesign = {required:.0f} m"
                      if math.isfinite(required) else "")
    governing = res.get("governing_borehole") or "—"
    basis = " total head-to-tip" if res["pile_type"] == "socket" else ""
    geometry = ("checked common L unavailable"
                if res["pile_type"] == "socket" and not res["checked_socket_lengths"] else
                f"checked L = {res['L']:.2f} m{basis}")
    return (f"{len(analysis.analyses)} boreholes · {geometry} · "
            f"{L['card_checks']}: {status} · governing borehole: {governing} "
            f"({_check_label(res.get('governing_check') or 'checks')}, "
            f"u = {_num(res['utilisation'], 3)}){recommendation}")


# --------------------------------------------------------------------------- #
#  Pile
# --------------------------------------------------------------------------- #

def results_text(analysis) -> str:
    """The complete soil, socket or independent-borehole analysis as text."""
    a, res = analysis, analysis.results
    if res.get("envelope"):
        return borehole_text(analysis)
    if "Ls_check" in res:
        return socket_text(analysis)
    lines = [L["res_title"], "-" * 84]
    lines.append(L["res_pile"].format(shape=L["shape_" + a.shape], D=a.D, L=a.L, top=a.top,
                                      tip=res["z_tip"],
                                      inst=L["installation_" + a.installation]))
    lines.append(L["res_area"].format(A=res["A"], p=res["perimeter"]))
    lines.append(L["res_group"].format(nx=a.nx, ny=a.ny, n=a.n, sx=a.sx, sy=a.sy, Q=a.Q,
                                       Qp=res["Q_pile"]))
    lines.append(L["res_water"].format(zw=a.profile.zw) if math.isfinite(a.profile.zw)
                 else "No water table: dry-ground assumption.")
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
    for key in ("seismic_compression", "seismic_group_compression",
                "seismic_tension", "seismic_group_tension"):
        if key in checks and checks[key]["status"] != "N/A":
            c = checks[key]
            lines.append("  " + L[f"res_check_{key}"].format(
                actual=c["actual"], allowable=c["allowable"],
                status=status_text(L, c["status"])[0]))

    length = res["required_length"]
    if math.isfinite(length):
        length_text = L["res_required_length"].format(L=length, z=a.top + length)
    elif not res.get("length_search_performed", True):
        length_text = "Length search was not requested; no length recommendation is available."
    else:
        length_text = L["res_no_length"].format(hi=a.profile.depth - a.top)
    lines += ["", "  " + length_text]

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
        lines += ["  • " + warning_text(w) for w in res["warnings"]]
    return "\n".join(lines)


def warnings(analysis) -> List[str]:
    return [warning_text(w) for w in analysis.results.get("warnings", [])]


def headline(analysis) -> str:
    """One line for the status bar: the capacity, the checks and the length."""
    res = analysis.results
    if res.get("envelope"):
        return borehole_headline(analysis)
    if "Ls_check" in res:
        return socket_headline(analysis)
    status, _ = status_text(L, "OK" if all(c["status"] in ("OK", "N/A")
                                           for c in res["checks"].values()) else "NOT OK")
    length = res["required_length"]
    tail = f" · Ldesign = {length:.0f} m" if math.isfinite(length) else ""
    return (f"Qult,net = {res['Q_ult_net']:,.0f} kN · FS = {res['FS']:.2f} · "
            f"{L['card_checks']}: {status}{tail}")


# --------------------------------------------------------------------------- #
#  Rock socket
# --------------------------------------------------------------------------- #

def socket_text(socket, *, log_only: bool = False) -> str:
    """The rock socket as text."""
    s, res = socket, socket.results
    if res.get("envelope"):
        return borehole_text(socket)
    lines = [L["sock_title"], "-" * 84]
    if log_only:
        lines.append("Independent log-only socket recommendations below apply to this borehole. "
                     "Use the common total L above for the shared design.")
    lines.append(L["sock_geometry"].format(D=s.D, top=s.top, rock=s.rock_depth,
                                           Lo=res["overburden"], Ls=res["Ls_check"], Q=s.Q))
    m = res["modulus"]
    lines.append(L["sock_rock"].format(qu=s.qu, qs=res["qu_side"], fc=s.fc, Em=m["Em"],
                                       ratio=m["ratio"], aE=m["alpha_E"]))
    hb = res["hoek_brown"]
    lines.append(L["sock_hb"].format(GSI=s.GSI, mi=s.mi, mb=hb["mb"], s=hb["s"]))
    if res.get("Qs_soil", 0.0) > 0:
        lines.append(L["sock_overburden"].format(Qs=res["Qs_soil"]))

    lines += ["", L["sock_side_title"],
              _row(L["head_correlation"], [L["head_fs"],
                   "Log-only Ls (m)" if log_only else L["head_Ls_req"], L["head_Q_all"]],
                   34, 17)]
    for key in SOCKET_SIDE_METHODS:
        e = res["side"][key]
        mark = "" if e["in_range"] else " †"
        star = " *" if key == res["design"] else ""
        lines.append(_row((L[f"side_{key}"] + star + mark)[:34],
                          [f"{e['fs']:,.0f}", _num(e["Ls_design"], 0), f"{e['Q_all']:,.0f}"],
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
    if math.isfinite(res["Ls_design"]):
        label = "Independent log-only whole-metre Ls" if log_only else "Recommended whole-metre Ls"
        lines.append(f"  {label} = {res['Ls_design']:.0f} m; "
                     "capacity, minimum length and settlement rechecked at this geometry.")
        lines.append(f"  Continuous capacity-only diagnostic Ls = {_num(res['Ls_req'], 2)} m; "
                     f"geometric minimum = {_num(res['Ls_min'], 2)} m.")
    else:
        lines.append("  " + L["sock_no_length"])
    lines.append("  " + L["sock_check"].format(Ls=res["Ls_check"], Qs=c["Qs"], Qb=c["Qb"],
                                               W=c["W"], Qa=c["Q_all"], Q=s.Q,
                                               u=c["utilisation"],
                                               status=status_text(L, c["status"])[0]))
    lines.extend(_check_line(key, check) for key, check in res["checks"].items())

    st = res["settlement"]
    lines += ["", L["sock_settlement_title"].format(Ls=st["Ls"])]
    lines.append("  " + L["sock_shortening"].format(s=1000 * st["shortening"]))
    lines.append("  " + L["sock_rw"].format(s=1000 * st["rw"]["total"],
                                            share=100 * st["rw"]["base_share"]))
    lines.append("  " + L["sock_rw_side"].format(s=1000 * st["rw_side"]["total"]))
    lines.append("  " + L["sock_vesic"].format(s=1000 * st["vesic"]["total"]))
    selected = L["plot_rw_side"] if st["method"] == "rw_side" else L["plot_rw"]
    lines.append(f"  Selected settlement ({selected}): {1000 * st['s']:.1f} mm — "
                 f"{status_text(L, st['status'])[0]}")

    if res["warnings"]:
        lines += ["", L["warnings_title"]]
        lines += ["  • " + warning_text(w) for w in res["warnings"]]
    return "\n".join(lines)


def socket_headline(socket) -> str:
    res = socket.results
    if res.get("envelope"):
        return borehole_headline(socket)
    length = res["Ls_design"]
    status, _ = status_text(L, res["check"]["status"])
    head = f"Ls design = {length:.0f} m" if math.isfinite(length) else L["card_none"]
    return (f"{head} · checked Ls = {res['Ls_check']:.2f} m · "
            f"fs = {res['fs_design']:,.0f} kPa · {L['card_checks']}: {status} · "
            f"s = {1000 * res['settlement']['s']:.1f} mm")
