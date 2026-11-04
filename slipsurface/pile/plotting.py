"""
The analysis figures of SlipSurface IQ Pile.

Every figure is drawn on a Matplotlib `Figure` passed in by the caller, so the
same code serves the browser (PNG through `render`) and the report. Nothing
here needs a display.

Pile
    section      section through the group: layers, water table, cap, piles,
                 the critical depth and the equivalent raft
    profile      σ'v and u0, the unit shaft friction of every method, and the
                 load carried down the shaft
    methods      the shaft and the base resistance of every method
    length       capacity against pile length, the load, the required length
    group        plan of the group and the efficiency of every method
    settlement   the equivalent raft's stresses, and the settlement by method
    seismic      the seismic load on every pile of the cap, against the allowable
                 compression and uplift (when the earthquake is on)

Rock socket
    socket_section      the pile, the overburden and the socket
    socket_side         the unit side shear of every correlation
    socket_length       the socket length each correlation needs
    socket_settlement   head settlement against socket length
"""

from __future__ import annotations

import math

import numpy as np
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle

from .config import (
    CLAY_METHODS,
    METHOD_COLORS,
    PLOT_PALETTE,
    SOCKET_SIDE_METHODS,
    SOIL_FILL,
    TIP_METHODS,
)
from .i18n import TRANSLATIONS
from .plot_style import TITLE_FONT, label_box, style_axis, style_figure
from .settlement import raft_widening

#: The figures, in the order the interface offers them
PLOT_KEYS = ["section", "profile", "methods", "length", "group", "settlement", "seismic"]
SOCKET_PLOT_KEYS = ["socket_section", "socket_side", "socket_length", "socket_settlement"]


def _legend(ax, th, fontsize=8.5, **kwargs):
    legend = ax.legend(fontsize=fontsize, frameon=False, **kwargs)
    for text in legend.get_texts():
        text.set_color(th["fg"])
    return legend


def _ground(ax, th, x0, x1):
    """The ground surface: a line at z = 0 with short hatch ticks above it."""
    ax.plot([x0, x1], [0, 0], color=th["fg"], linewidth=1.4, zorder=6)
    step = (x1 - x0) / 40.0
    for x in np.arange(x0 + step / 2, x1, step):
        ax.plot([x, x - step * 0.6], [0, -step * 0.6], color=th["fg_dim"], linewidth=0.7,
                zorder=6)


def _water_mark(ax, th, x, zw, text):
    """The water table: dashed line plus the usual ▽ symbol and its label."""
    ax.axhline(zw, color=PLOT_PALETTE["water"], linewidth=1.4, linestyle="--", zorder=4)
    ax.plot([x], [zw], marker="v", markersize=8, color=PLOT_PALETTE["water"], zorder=7,
            linestyle="none")
    ax.annotate(text, xy=(x, zw), xytext=(8, 4), textcoords="offset points", fontsize=8,
                ha="left", va="bottom", color=PLOT_PALETTE["water"], zorder=7,
                bbox=label_box(th, 0.85))


def _boundaries(ax, th, profile, z_max):
    """Faint layer boundaries across a depth plot."""
    for layer in profile.layers[1:]:
        if layer["top"] < z_max:
            ax.axhline(layer["top"], color=th["border"], linewidth=0.9, zorder=0.5)


def _empty(fig, th, text):
    ax = fig.add_subplot(111)
    style_axis(ax, th, grid=False)
    ax.axis("off")
    ax.text(0.5, 0.5, text, ha="center", va="center", color=th["fg_dim"], fontsize=11)


class _Base:
    def __init__(self, analysis, lang: str = "en", theme="light", titles: bool = True):
        self.a = analysis
        self.res = analysis.results
        self.lang = lang
        self.L = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
        self.theme = theme
        self.titles = titles

    def _fills(self):
        name = self.theme if isinstance(self.theme, str) else "light"
        return SOIL_FILL.get(name, SOIL_FILL["light"])

    def _title(self, fig, th, key: str, extra: str = "") -> None:
        if not self.titles:
            return
        fig.suptitle(f"{self.L.get(f'fig_{key}', key)}{extra}", fontfamily=TITLE_FONT,
                     fontsize=12.5, color=th["fg"])

    def _method(self, key: str) -> str:
        return self.L.get(f"method_{key}", key)


class Plotter(_Base):
    """Draws the figures of one finished `PileAnalysis`."""

    keys = PLOT_KEYS

    def draw(self, key: str, fig: Figure) -> None:
        if key not in PLOT_KEYS:
            raise ValueError(f"unknown figure: {key}")
        getattr(self, f"_draw_{key}")(fig)

    # ------------------------------------------------------------------ section
    def _draw_section(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        ax = fig.add_subplot(111)
        style_axis(ax, th, grid=False)
        a, res = self.a, self.res
        D, top, tip = a.D, a.top, res["z_tip"]
        xs = sorted({round(x, 6) for x, _ in _positions(a)})
        span = (max(xs) - min(xs)) if len(xs) > 1 else 0.0
        half = max(span / 2.0 + 2.5 * D + 0.35 * tip, 0.45 * tip, 3.0)
        bottom = min(max(tip + max(3.0 * D, 0.25 * tip), tip + 1.0), a.profile.depth)

        fills = self._fills()
        for layer in a.profile.layers:
            if layer["top"] >= bottom:
                break
            y0, y1 = layer["top"], min(layer["bottom"], bottom)
            ax.add_patch(Rectangle((-half, y0), 2 * half, y1 - y0,
                                   facecolor=fills[layer["behaviour"]], edgecolor=th["border"],
                                   linewidth=0.8, zorder=1))
            # the name in the layer's own band, clear of the cap
            ax.text(-half * 0.97, 0.5 * (y0 + y1), layer["name"], fontsize=8.5, va="center",
                    color=th["fg"], zorder=6, bbox=label_box(th, 0.8))
            if layer["top"] > 0:
                ax.text(half * 0.985, y0, f"{y0:.2f} m", fontsize=7.5, ha="right",
                        va="bottom", color=th["fg_dim"], zorder=6)
        _ground(ax, th, -half, half)
        if a.profile.zw < bottom:
            _water_mark(ax, th, half * 0.55, a.profile.zw, self.L["plot_water"])

        # the cap and the piles of the row along B
        cap_t = min(max(0.9 * D, 0.6), top) if top > 0 else min(max(0.9 * D, 0.6), 1.0)
        left, right = min(xs) - D, max(xs) + D
        ax.add_patch(Rectangle((left, top - cap_t), right - left, cap_t,
                               facecolor=PLOT_PALETTE["cap"], edgecolor=th["border"],
                               linewidth=1.0, zorder=5))
        for x in xs:
            ax.add_patch(Rectangle((x - D / 2, top), D, tip - top,
                                   facecolor=PLOT_PALETTE["pile"], edgecolor=th["border"],
                                   linewidth=1.0, zorder=5))
        # critical depth and equivalent raft
        zc = res["zc"]
        if math.isfinite(zc) and zc < bottom:
            ax.axhline(zc, color=PLOT_PALETTE["limit"], linestyle=":", linewidth=1.2, zorder=4)
            ax.text(half * 0.55, zc, f"zc = {zc:.1f} m", fontsize=8, ha="left", va="bottom",
                    color=th["fg"], zorder=6, bbox=label_box(th, 0.8))
        raft = res["settlement"]["raft"]["z_raft"]
        if a.n > 1:
            Bg = res["settlement"]["Bg"]
            ax.plot([-Bg / 2, Bg / 2], [raft, raft], color=PLOT_PALETTE["consolidation"],
                    linewidth=2.2, zorder=6)
            depth = bottom - raft
            widen = raft_widening(depth, a.spread) / 2.0   # one side
            for sign in (-1, 1):
                ax.plot([sign * Bg / 2, sign * (Bg / 2 + widen)], [raft, bottom],
                        color=PLOT_PALETTE["consolidation"], linewidth=1.0, linestyle="--",
                        zorder=6)
            ax.annotate(self.L["plot_raft"], xy=(Bg / 2, raft), xytext=(14, -14),
                        textcoords="offset points", fontsize=8, va="top", color=th["fg"],
                        zorder=7, bbox=label_box(th, 0.85),
                        arrowprops=dict(arrowstyle="-", color=th["fg_dim"], lw=0.8))

        # the load, the dimensions
        arrow_top = top - cap_t - max(0.18 * tip, 1.0)
        ax.annotate("", xy=(0, top - cap_t), xytext=(0, arrow_top),
                    arrowprops=dict(arrowstyle="-|>", color=PLOT_PALETTE["applied"], lw=2.0),
                    zorder=7)
        ax.text(0, arrow_top, f"Q = {a.Q:,.0f} kN", fontsize=8.5, ha="center", va="bottom",
                color=th["fg"], bbox=label_box(th), zorder=8)
        # the length on the left of the group, the raft label sits on the right
        x_dim = min(xs) - D * 1.1
        ax.annotate("", xy=(x_dim, top), xytext=(x_dim, tip),
                    arrowprops=dict(arrowstyle="<->", color=th["fg"], lw=1.0), zorder=7)
        ax.text(x_dim - 0.15, 0.5 * (top + tip), f"L = {a.L:.2f} m", fontsize=8.5,
                va="center", ha="right", rotation=90, color=th["fg"], bbox=label_box(th),
                zorder=8)
        ax.plot([min(xs) - D / 2, max(xs) + D / 2], [tip, tip], color=th["fg"],
                linewidth=0.8, linestyle=":", zorder=6)
        ax.text(max(xs) + D * 0.7, tip, f"{self.L['plot_tip']} {tip:.2f} m", fontsize=8,
                va="top", color=th["fg"], zorder=8, bbox=label_box(th, 0.8))

        ax.set_xlim(-half, half)
        ax.set_ylim(bottom, arrow_top - 0.8)
        ax.set_xlabel("x (m)", fontsize=9)
        ax.set_ylabel("z (m)", fontsize=9)
        self._title(fig, th, "section",
                    f" — {a.nx} × {a.ny}, D = {D:.2f} m, L = {a.L:.2f} m")
        fig.tight_layout(rect=(0, 0, 1, 0.95))

    # ------------------------------------------------------------------ profile
    def _draw_profile(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        a, res = self.a, self.res
        slices = res["shaft"]["slices"]
        tip = res["z_tip"]
        z = np.array([row["z"] for row in slices])

        ax1 = fig.add_subplot(1, 3, 1)
        style_axis(ax1, th)
        depths = np.linspace(0.0, tip, 120)
        ax1.plot([a.profile.effective_stress(d) for d in depths], depths,
                 color=PLOT_PALETTE["stress"], linewidth=2.0, label="σ'v0")
        ax1.plot([a.profile.pore_pressure(d) for d in depths], depths,
                 color=PLOT_PALETTE["water"], linewidth=1.6, linestyle="--", label="u0")
        if math.isfinite(res["zc"]):
            used = [a._sigma_sand(d) for d in depths]
            ax1.plot(used, depths, color=PLOT_PALETTE["limit"], linewidth=1.2, linestyle=":",
                     label=self.L["plot_sv_sand"])
        ax1.set_xlabel(f"{self.L['plot_stress']} (kPa)", fontsize=9)
        ax1.set_ylabel(f"{self.L['plot_depth']} (m)", fontsize=9)

        ax2 = fig.add_subplot(1, 3, 2, sharey=ax1)
        style_axis(ax2, th)
        methods = CLAY_METHODS if res["shaft"]["cohesive"] else [a.clay_method]
        for method in methods:
            primary = method == a.clay_method
            ax2.plot([row[method] for row in slices], z, color=METHOD_COLORS[method],
                     linewidth=2.2 if primary else 1.1, alpha=1.0 if primary else 0.7,
                     label=self._method(method) if res["shaft"]["cohesive"]
                     else self.L["method_granular"], drawstyle="steps-mid")
        spt = np.array([row.get("spt", float("nan")) for row in slices], dtype=float)
        if math.isfinite(res["shaft"]["Qs_spt"]):
            ax2.plot(spt, z, color=METHOD_COLORS["spt"], linewidth=1.0, linestyle="--",
                     label=self._method("spt"))
        ax2.set_xlabel("fs (kPa)", fontsize=9)
        # below the panel: inside it the six methods hide their own curves
        _legend(ax2, th, loc="upper center", fontsize=7, ncol=2,
                bbox_to_anchor=(0.5, -0.13))

        ax3 = fig.add_subplot(1, 3, 3, sharey=ax1)
        style_axis(ax3, th)
        load = np.cumsum([row[a.clay_method] * res["perimeter"] * row["h"] for row in slices])
        # the ultimate shaft resistance mobilised from the head down to z
        ax3.plot(load, z, color=PLOT_PALETTE["shaft"], linewidth=2.0,
                 label=self.L["plot_qs_cumulative"])
        ax3.axvline(res["Q_pile"], color=PLOT_PALETTE["applied"], linestyle="--",
                    linewidth=1.3, label=f"{self.L['plot_pile_load']} = {res['Q_pile']:,.0f} kN")
        ax3.scatter([res["Qs"] + res["Qb"]], [tip], s=40, color=PLOT_PALETTE["ultimate"],
                    zorder=5, label=f"Qs + Qb = {res['Q_ult']:,.0f} kN")
        ax3.plot([res["Qs"], res["Qs"] + res["Qb"]], [tip, tip], color=PLOT_PALETTE["base"],
                 linewidth=3.0, label=f"Qb = {res['Qb']:,.0f} kN")
        ax3.set_xlabel(f"{self.L['plot_resistance']} (kN)", fontsize=9)
        _legend(ax3, th, loc="upper center", fontsize=7, bbox_to_anchor=(0.5, -0.13))
        _legend(ax1, th, loc="upper center", fontsize=7, bbox_to_anchor=(0.5, -0.13))

        for ax in (ax1, ax2, ax3):
            _boundaries(ax, th, a.profile, tip)
            ax.axhline(a.top, color=th["fg_dim"], linewidth=0.8, linestyle=":")
            ax.axhline(a.profile.zw, color=PLOT_PALETTE["water"], linewidth=0.8,
                       linestyle="--")
            ax.set_xlim(left=0)
        ax1.set_ylim(tip * 1.02, 0)
        for ax in (ax2, ax3):
            ax.tick_params(labelleft=False)
        self._title(fig, th, "profile")
        fig.tight_layout(rect=(0, 0, 1, 0.95))

    # ------------------------------------------------------------------ methods
    def _draw_methods(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        a, res = self.a, self.res
        ax1 = fig.add_subplot(1, 2, 1)
        style_axis(ax1, th, axis="x")
        shaft = [(m, res["shaft"]["Qs"][m]) for m in
                 (CLAY_METHODS if res["shaft"]["cohesive"] else [a.clay_method])]
        if math.isfinite(res["shaft"]["Qs_spt"]):
            shaft.append(("spt", res["shaft"]["Qs_spt"]))
        self._bars(ax1, th, shaft, a.clay_method)
        ax1.set_xlabel("Qs (kN)", fontsize=9)
        ax1.set_title(self.L["plot_shaft"], fontsize=10, color=th["fg"])

        ax2 = fig.add_subplot(1, 2, 2)
        style_axis(ax2, th, axis="x")
        base = [(m, res["base"]["methods"][m]["Qb"]) for m in TIP_METHODS]
        if math.isfinite(res["base"]["Qb_spt"]):
            base.append(("spt", res["base"]["Qb_spt"]))
        self._bars(ax2, th, base, a.tip_method)
        ax2.set_xlabel("Qb (kN)", fontsize=9)
        ax2.set_title(self.L["plot_base"], fontsize=10, color=th["fg"])
        self._title(fig, th, "methods",
                    f" — W = {res['W']:,.0f} kN, Qult,net = {res['Q_ult_net']:,.0f} kN")
        fig.tight_layout(rect=(0, 0, 1, 0.94))

    def _bars(self, ax, th, items, primary):
        y = np.arange(len(items))
        values = [v for _, v in items]
        colors = [METHOD_COLORS.get(key, th["accent"]) for key, _ in items]
        alphas = [1.0 if key == primary else 0.55 for key, _ in items]
        for index, (value, colour, alpha) in enumerate(zip(values, colors, alphas)):
            ax.barh(y[index], value, color=colour, alpha=alpha, height=0.62)
            ax.text(value, y[index], f" {value:,.0f}", va="center", fontsize=8,
                    color=th["fg"])
        ax.set_yticks(y)
        ax.set_yticklabels([self._method(key) for key, _ in items], fontsize=8.5,
                           color=th["fg"])
        ax.invert_yaxis()
        ax.set_xlim(0, max(values + [1.0]) * 1.22)

    # ------------------------------------------------------------------ length
    def _draw_length(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        a, res = self.a, self.res
        curve = res["length_curve"]
        if not curve:
            return _empty(fig, th, self.L["plot_no_data"])
        ax = fig.add_subplot(111)
        style_axis(ax, th)
        L = np.array([p["L"] for p in curve])
        ax.plot(L, [p["Q_ult_net"] for p in curve], color=PLOT_PALETTE["ultimate"],
                linewidth=2.0, label=self.L["plot_Q_net"])
        ax.plot(L, [p["Q_all"] for p in curve], color=PLOT_PALETTE["allowable"],
                linewidth=2.2, label=self.L["plot_Q_all"])
        if a.n > 1:
            ax.plot(L, [p["Qg_all"] / a.n for p in curve], color=PLOT_PALETTE["base"],
                    linewidth=1.6, linestyle="-.", label=self.L["plot_group_per_pile"])
        ax.axhline(res["Q_pile"], color=PLOT_PALETTE["applied"], linestyle="--", linewidth=1.6,
                   label=f"{self.L['plot_pile_load']} = {res['Q_pile']:,.0f} kN")
        ax.axvline(a.L, color=th["fg_dim"], linestyle=":", linewidth=1.2)
        # where the tip passes from one layer into the next: the curve jumps there
        y_top = max(max(p["Q_ult_net"] for p in curve), res["Q_pile"]) * 1.12
        for layer in a.profile.layers[1:]:
            Lb = layer["top"] - a.top
            if L[0] < Lb < L[-1]:
                ax.axvline(Lb, color=th["border"], linewidth=1.0, zorder=0.5)
                ax.text(Lb, y_top, f" {layer['name']}", rotation=90, fontsize=7.5,
                        va="top", ha="left", color=th["fg_dim"])
        required = res["required_length"]
        if math.isfinite(required):
            ax.axvline(required, color=PLOT_PALETTE["design"], linewidth=1.4)
            ax.annotate(self.L["plot_required"].format(L=required),
                        xy=(required, res["Q_pile"]), xytext=(10, 18),
                        textcoords="offset points", fontsize=8.5, color=th["fg"],
                        bbox=label_box(th),
                        arrowprops=dict(arrowstyle="-", color=th["fg_dim"], lw=0.8))
        ax.set_xlabel(f"{self.L['plot_length']} (m)", fontsize=9)
        ax.set_ylabel(f"{self.L['plot_load']} (kN)", fontsize=9)
        ax.set_ylim(0, y_top * 1.02)
        _legend(ax, th, loc="lower right")
        self._title(fig, th, "length")
        fig.tight_layout(rect=(0, 0, 1, 0.95))

    # ------------------------------------------------------------------ group
    def _draw_group(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        a, res = self.a, self.res
        group = res["group"]
        ax = fig.add_subplot(1, 2, 1)
        style_axis(ax, th, grid=False)
        points = _positions(a)
        Bx = (a.nx - 1) * a.sx + a.D
        By = (a.ny - 1) * a.sy + a.D
        ax.add_patch(Rectangle((-Bx / 2, -By / 2), Bx, By, fill=False,
                               edgecolor=PLOT_PALETTE["block"], linestyle="--", linewidth=1.3))
        pad = max(0.6 * a.D, 0.4)
        ax.add_patch(Rectangle((-Bx / 2 - pad, -By / 2 - pad), Bx + 2 * pad, By + 2 * pad,
                               facecolor=PLOT_PALETTE["cap"], alpha=0.18,
                               edgecolor=th["border"]))
        for x, y in points:
            if a.shape == "circular":
                ax.add_patch(Circle((x, y), a.D / 2, facecolor=PLOT_PALETTE["pile"],
                                    edgecolor=th["fg_dim"], linewidth=0.8))
            else:
                ax.add_patch(Rectangle((x - a.D / 2, y - a.D / 2), a.D, a.D,
                                       facecolor=PLOT_PALETTE["pile"], edgecolor=th["fg_dim"],
                                       linewidth=0.8))
        lim = max(Bx, By) / 2 + 1.6 * pad
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(f"Bg = {Bx:.2f} m, sx = {a.sx:.2f} m", fontsize=9)
        ax.set_ylabel(f"Lg = {By:.2f} m, sy = {a.sy:.2f} m", fontsize=9)
        ax.set_title(f"{a.nx} × {a.ny} = {a.n}", fontsize=10, color=th["fg"])

        ax2 = fig.add_subplot(1, 2, 2)
        style_axis(ax2, th, axis="x")
        items = [(key, value) for key, value in group["eta"].items() if math.isfinite(value)]
        if group["block"] is not None:
            items.append(("block", group["block"]["Q_ult"] / (a.n * res["Q_ult"])))
        y = np.arange(len(items))
        for index, (key, value) in enumerate(items):
            primary = key == a.efficiency_method or (key == "block"
                                                     and group["governing"] == "block")
            ax2.barh(y[index], min(value, 1.5), height=0.62,
                     color=METHOD_COLORS.get(key, th["accent"]),
                     alpha=1.0 if primary else 0.55)
            off = value > 1.5
            ax2.text(min(value, 1.5), y[index], f" {value:.3f}" + (" »" if off else ""),
                     va="center", fontsize=8, color=th["fg"],
                     fontweight="bold" if off else "normal")
        ax2.axvline(1.0, color=th["fg_dim"], linestyle=":", linewidth=1.0)
        ax2.set_yticks(y)
        ax2.set_yticklabels([self.L[f"eff_{key}"] for key, _ in items], fontsize=8.5,
                            color=th["fg"])
        ax2.invert_yaxis()
        ax2.set_xlim(0, 1.7)
        ax2.set_xlabel("η", fontsize=9)
        self._title(fig, th, "group",
                    f" — Qg,all = {group['Q_all']:,.0f} kN ({self.L['gov_' + group['governing']]})")
        fig.tight_layout(rect=(0, 0, 1, 0.94))

    # ------------------------------------------------------------------ settlement
    def _draw_settlement(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        a, res = self.a, self.res
        st = res["settlement"]
        raft = st["raft"]
        ax1 = fig.add_subplot(1, 2, 1)
        style_axis(ax1, th)
        rows = raft["rows"]
        if rows:
            z = [r["z"] for r in rows]
            ax1.plot([r["sigma0"] for r in rows], z, color=PLOT_PALETTE["stress"], linewidth=1.8,
                     label="σ'v0")
            ax1.plot([r["dsigma"] for r in rows], z, color=PLOT_PALETTE["applied"],
                     linewidth=2.0, label="Δσ")
            ax1.set_ylim(max(z) + 0.5, raft["z_raft"] - 0.5)
        ax1.axhline(raft["z_raft"], color=PLOT_PALETTE["consolidation"], linewidth=1.6)
        ax1.set_xlabel(f"{self.L['plot_stress']} (kPa)", fontsize=9)
        ax1.set_ylabel(f"{self.L['plot_depth']} (m)", fontsize=9)
        ax1.set_xlim(left=0)
        _legend(ax1, th, loc="lower right")
        ax1.set_title(self.L["plot_raft_title"].format(z=raft["z_raft"]), fontsize=10,
                      color=th["fg"])

        ax2 = fig.add_subplot(1, 2, 2)
        style_axis(ax2, th, axis="y")
        items = [("single", st["single"]["s"], PLOT_PALETTE["pile"]),
                 ("raft", raft["total"], METHOD_COLORS["raft"]),
                 ("vesic", st["vesic"], METHOD_COLORS["vesic_group"])]
        if st["meyerhof"]:
            items.append(("meyerhof", st["meyerhof"]["s"], METHOD_COLORS["meyerhof_spt"]))
        x = np.arange(len(items))
        for index, (key, value, colour) in enumerate(items):
            primary = key == st["method"]
            ax2.bar(x[index], 1000 * value, width=0.6, color=colour,
                    alpha=1.0 if primary else 0.6)
            ax2.text(x[index], 1000 * value, f"{1000 * value:.1f}", ha="center",
                     va="bottom", fontsize=8.5, color=th["fg"])
        if raft["total"] > 0:
            ax2.bar(x[1], 1000 * raft["consolidation"], width=0.6, fill=False,
                    hatch="//", edgecolor=th["panel"], linewidth=0)
        ax2.axhline(a.s_allow, color=PLOT_PALETTE["limit"], linestyle="--", linewidth=1.4,
                    label=f"{self.L['plot_allowable']} = {a.s_allow:.0f} mm")
        ax2.set_xticks(x)
        ax2.set_xticklabels([self.L[f"plot_s_{key}"] for key, _, _ in items], fontsize=8,
                            color=th["fg"], rotation=25, ha="right")
        ax2.set_ylabel(f"{self.L['plot_settlement']} (mm)", fontsize=9)
        ax2.set_ylim(0, max([1000 * v for _, v, _ in items] + [a.s_allow]) * 1.2)
        handles = [Line2D([0], [0], color=PLOT_PALETTE["limit"], linestyle="--",
                          linewidth=1.4,
                          label=f"{self.L['plot_allowable']} = {a.s_allow:.0f} mm")]
        if raft["total"] > 0 and raft["consolidation"] > 0:
            handles.append(Rectangle((0, 0), 1, 1, facecolor=METHOD_COLORS["raft"],
                                     hatch="//", edgecolor=th["panel"],
                                     label=self.L["plot_consolidation_part"]))
        _legend(ax2, th, handles=handles, loc="upper left")
        self._title(fig, th, "settlement")
        fig.tight_layout(rect=(0, 0, 1, 0.94))


    # ------------------------------------------------------------------ seismic
    def _draw_seismic(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        a, res = self.a, self.res
        seismic = res.get("seismic")
        if not seismic:
            return _empty(fig, th, self.L["plot_no_seismic"])
        loads = seismic["loads"]
        comp, tens = seismic["compression"], seismic["tension"]
        top = max(abs(p["P"]) for p in loads) or 1.0

        ax = fig.add_subplot(1, 2, 1)
        style_axis(ax, th, grid=False)
        Bx = (a.nx - 1) * a.sx + a.D
        By = (a.ny - 1) * a.sy + a.D
        pad = max(0.6 * a.D, 0.4)
        ax.add_patch(Rectangle((-Bx / 2 - pad, -By / 2 - pad), Bx + 2 * pad, By + 2 * pad,
                               facecolor=PLOT_PALETTE["cap"], alpha=0.15,
                               edgecolor=th["border"]))
        for p in loads:
            colour = PLOT_PALETTE["applied"] if p["P"] < 0 else PLOT_PALETTE["shaft"]
            radius = a.D / 2 * (0.55 + 0.45 * abs(p["P"]) / top)
            ax.add_patch(Circle((p["x"], p["y"]), radius, facecolor=colour, alpha=0.85,
                                edgecolor=th["fg_dim"], linewidth=0.8))
            ax.text(p["x"], p["y"] - a.D * 0.75, f"{p['P']:,.0f}", ha="center", va="top",
                    fontsize=8, color=th["fg"])
        lim = max(Bx, By) / 2 + 2.2 * pad
        # the moments as double-headed vectors (right-hand rule) beside the cap
        arrow = dict(arrowstyle="-|>", color=PLOT_PALETTE["applied"], lw=1.6)
        if a.M_B:
            y_m = By / 2 + pad + 0.45 * pad
            sign = 1 if a.M_B > 0 else -1
            ax.annotate("", xy=(sign * Bx / 3, y_m), xytext=(-sign * Bx / 3, y_m),
                        arrowprops=arrow)
            ax.text(0, y_m, "M_B", ha="center", va="bottom", fontsize=8, color=th["fg"])
        if a.M_L:
            x_m = Bx / 2 + pad + 0.45 * pad
            sign = 1 if a.M_L > 0 else -1
            ax.annotate("", xy=(x_m, sign * By / 3), xytext=(x_m, -sign * By / 3),
                        arrowprops=arrow)
            ax.text(x_m, 0, " M_L", ha="left", va="center", fontsize=8, color=th["fg"])
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(f"B — M_B = {a.M_B:,.0f} kN·m", fontsize=9)
        ax.set_ylabel(f"L — M_L = {a.M_L:,.0f} kN·m", fontsize=9)
        ax.set_title(f"V = {a.V_E:,.0f} kN", fontsize=10, color=th["fg"])
        handles = [Rectangle((0, 0), 1, 1, facecolor=PLOT_PALETTE["shaft"],
                             label=self.L["plot_compression"]),
                   Rectangle((0, 0), 1, 1, facecolor=PLOT_PALETTE["applied"],
                             label=self.L["plot_tension"])]
        _legend(ax, th, handles=handles, loc="upper center", ncol=2,
                bbox_to_anchor=(0.5, -0.12))

        ax2 = fig.add_subplot(1, 2, 2)
        style_axis(ax2, th, axis="y")
        order = sorted(range(len(loads)), key=lambda i: loads[i]["P"])
        values = [loads[i]["P"] for i in order]
        colours = [PLOT_PALETTE["applied"] if v < 0 else PLOT_PALETTE["shaft"] for v in values]
        ax2.bar(range(len(values)), values, color=colours, width=0.7)
        ax2.axhline(comp["Q_all"], color=PLOT_PALETTE["allowable"], linestyle="--",
                    linewidth=1.5, label=f"Qall,E = {comp['Q_all']:,.0f} kN")
        ax2.axhline(-tens["T_all"], color=PLOT_PALETTE["limit"], linestyle="--",
                    linewidth=1.5, label=f"Tall = {tens['T_all']:,.0f} kN ({self.L['plot_tension']})")
        ax2.axhline(0, color=th["border"], linewidth=1.0)
        ax2.set_xticks([])
        ax2.set_xlabel(self.L["plot_piles_sorted_short"], fontsize=9)
        ax2.set_ylabel(f"{self.L['plot_pile_force']} (kN)", fontsize=9)
        span = max(comp["Q_all"], tens["T_all"], top) * 1.3
        ax2.set_ylim(-span, span)
        _legend(ax2, th, loc="lower right")
        self._title(fig, th, "seismic")
        fig.tight_layout(rect=(0, 0, 1, 0.94))


def _positions(a):
    from .group import positions
    return positions(a.nx, a.ny, a.sx, a.sy)


# --------------------------------------------------------------------------- #
#  Rock socket
# --------------------------------------------------------------------------- #

class SocketPlotter(_Base):
    """Draws the figures of one finished `SocketAnalysis`."""

    keys = SOCKET_PLOT_KEYS

    def draw(self, key: str, fig: Figure) -> None:
        if key not in SOCKET_PLOT_KEYS:
            raise ValueError(f"unknown figure: {key}")
        getattr(self, f"_draw_{key}")(fig)

    def _side_label(self, key: str) -> str:
        return self.L.get(f"side_{key}", key)

    def _draw_socket_section(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        ax = fig.add_subplot(111)
        style_axis(ax, th, grid=False)
        s, res = self.a, self.res
        D, Ls = s.D, res["Ls_check"]
        tip = s.rock_depth + Ls
        Ls_design = res.get("Ls_design", float("nan"))
        deepest = s.rock_depth + max(Ls, Ls_design if math.isfinite(Ls_design) else 0.0)
        bottom = max(tip, deepest) + max(2.0 * D, 0.25 * tip, 1.0)
        half = max(0.45 * bottom, 3.0 * D)
        fills = self._fills()
        layers = res.get("overburden_layers") or []
        if layers:
            # the soil profile above the rock, when its friction is counted
            for layer in layers:
                y0, y1 = layer["top"], layer["bottom"]
                ax.add_patch(Rectangle((-half, y0), 2 * half, y1 - y0,
                                       facecolor=fills[layer["behaviour"]],
                                       edgecolor=th["border"], linewidth=0.8, zorder=1))
                ax.text(-half * 0.97, 0.5 * (y0 + y1),
                        f"{layer['name']}  ·  Qs = {layer['Qs']:,.0f} kN", fontsize=8,
                        va="center", color=th["fg"], bbox=label_box(th, 0.8), zorder=6)
            first = layers[0]["top"]
            if first > 0:
                ax.add_patch(Rectangle((-half, 0), 2 * half, first, facecolor=fills["granular"],
                                       edgecolor=th["border"], zorder=1))
        else:
            ax.add_patch(Rectangle((-half, 0), 2 * half, s.rock_depth,
                                   facecolor=fills["granular"], edgecolor=th["border"],
                                   zorder=1))
        rock = Rectangle((-half, s.rock_depth), 2 * half, bottom - s.rock_depth,
                         facecolor=fills["rock"], edgecolor=th["fg_dim"], hatch="/",
                         linewidth=0, zorder=1, alpha=0.9)
        ax.add_patch(rock)
        ax.plot([-half, half], [s.rock_depth, s.rock_depth], color=th["fg"], linewidth=1.2,
                zorder=2)
        _ground(ax, th, -half, half)
        if not layers:
            ax.text(-half * 0.97, s.rock_depth / 2, self.L["plot_overburden"], fontsize=8.5,
                    va="center", color=th["fg"], bbox=label_box(th, 0.8), zorder=6)
        ax.text(-half * 0.97, 0.5 * (s.rock_depth + bottom),
                f"{self.L['plot_rock']}: qu = {s.qu:.1f} MPa", fontsize=8.5, va="center",
                color=th["fg"], bbox=label_box(th, 0.8), zorder=6)
        if s.zw < bottom:
            _water_mark(ax, th, half * 0.45, s.zw, self.L["plot_water"])
        ax.add_patch(Rectangle((-D / 2, s.top), D, s.rock_depth - s.top,
                               facecolor=PLOT_PALETTE["pile"], edgecolor=th["border"],
                               zorder=5))
        ax.add_patch(Rectangle((-D / 2, s.rock_depth), D, Ls, facecolor=PLOT_PALETTE["ultimate"],
                               alpha=0.85, edgecolor=th["border"], zorder=5))
        arrow_top = s.top - max(0.12 * bottom, 1.0)
        ax.annotate("", xy=(0, s.top), xytext=(0, arrow_top),
                    arrowprops=dict(arrowstyle="-|>", color=PLOT_PALETTE["applied"], lw=2.0),
                    zorder=7)
        ax.text(0, arrow_top, f"Q = {s.Q:,.0f} kN", fontsize=8.5, ha="center", va="bottom",
                color=th["fg"], bbox=label_box(th), zorder=8)
        # side shear (up along the socket) and base resistance (up under the base)
        check = res.get("check") or {}
        n_arrows = max(int(Ls / max(D * 0.8, 0.4)), 2) if Ls > 0 else 0
        for zi in np.linspace(s.rock_depth + 0.15 * Ls, tip - 0.15 * Ls, n_arrows):
            for side in (-1, 1):
                ax.annotate("", xy=(side * D * 0.62, zi - 0.35 * D),
                            xytext=(side * D * 0.62, zi + 0.15 * D),
                            arrowprops=dict(arrowstyle="-|>", color=PLOT_PALETTE["shaft"],
                                            lw=1.1), zorder=7)
        if Ls > 0:
            ax.annotate("", xy=(0, tip + 0.05), xytext=(0, tip + max(0.9 * D, 0.6)),
                        arrowprops=dict(arrowstyle="-|>", color=PLOT_PALETTE["base"],
                                        lw=2.0), zorder=7)
            if check:
                ax.text(-D * 0.8, s.rock_depth + Ls / 2, f"Qs = {check['Qs']:,.0f} kN",
                        ha="right", va="center", fontsize=8, color=th["fg"],
                        bbox=label_box(th), zorder=8)
                ax.text(0, tip + max(0.9 * D, 0.6), f"Qb = {check['Qb']:,.0f} kN",
                        ha="center", va="top", fontsize=8, color=th["fg"],
                        bbox=label_box(th), zorder=8)
        x_dim = D * 1.3
        ax.annotate("", xy=(x_dim, s.rock_depth), xytext=(x_dim, tip),
                    arrowprops=dict(arrowstyle="<->", color=th["fg"], lw=1.0), zorder=7)
        ax.text(x_dim + 0.15, s.rock_depth + Ls / 2,
                f"{self.L['plot_ls_checked']} = {Ls:.2f} m", fontsize=8.5,
                va="center", color=th["fg"], bbox=label_box(th), zorder=8)
        Ls_design = res.get("Ls_design", float("nan"))
        if math.isfinite(Ls_design) and Ls_design > 0:
            z_d = s.rock_depth + Ls_design
            ax.plot([-D * 0.9, x_dim + 0.1], [z_d, z_d], color=PLOT_PALETTE["design"],
                    linewidth=1.6, linestyle="--", zorder=8)
            ax.text(x_dim + 0.15, z_d, f"{self.L['plot_ls_design']} = {Ls_design:.2f} m",
                    fontsize=8, va="top" if Ls_design >= Ls else "bottom",
                    color=PLOT_PALETTE["design"], zorder=8)
        ax.text(half * 0.97, s.rock_depth,
                f"{self.L['plot_rock_surface']} {s.rock_depth:.2f} m", fontsize=8,
                ha="right", va="bottom", color=th["fg"], zorder=8, bbox=label_box(th, 0.8))
        ax.set_xlim(-half, half)
        ax.set_ylim(bottom, arrow_top - 0.8)
        ax.set_xlabel("x (m)", fontsize=9)
        ax.set_ylabel("z (m)", fontsize=9)
        self._title(fig, th, "socket_section", f" — D = {D:.2f} m")
        fig.tight_layout(rect=(0, 0, 1, 0.95))

    def _scale(self, values, extra=()):
        """The axis length: the correlations within their range set it, so a
        weak-rock rule far outside its range does not squash the others."""
        side = self.res["side"]
        inside = [v for k, v in values.items() if math.isfinite(v) and side[k]["in_range"]]
        pool = inside or [v for v in values.values() if math.isfinite(v)]
        return max(pool + [v for v in extra if math.isfinite(v)] + [1e-9]) * 1.25

    def _hbar(self, ax, th, values, design_key, x_max=None):
        side = self.res["side"]
        y = np.arange(len(SOCKET_SIDE_METHODS))
        for index, key in enumerate(SOCKET_SIDE_METHODS):
            value = values[key]
            if not math.isfinite(value):
                continue
            in_range = side[key]["in_range"]
            shown = min(value, x_max) if x_max else value
            ax.barh(y[index], shown, height=0.62,
                    color=PLOT_PALETTE["ultimate"] if key == design_key else PLOT_PALETTE["shaft"],
                    alpha=1.0 if in_range else 0.3, hatch=None if in_range else "//",
                    edgecolor=th["panel"])
            text = f" {value:,.2f}" if value < 100 else f" {value:,.0f}"
            if x_max and value > x_max:
                ax.text(shown, y[index], text + " »", va="center", ha="right", fontsize=8,
                        color=th["fg"], fontweight="bold")
            else:
                ax.text(shown, y[index], text, va="center", fontsize=8, color=th["fg"])
        ax.set_yticks(y)
        ax.set_yticklabels([self._side_label(key) for key in SOCKET_SIDE_METHODS],
                           fontsize=8.5, color=th["fg"])
        ax.invert_yaxis()

    def _draw_socket_side(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        res = self.res
        ax = fig.add_subplot(111)
        style_axis(ax, th, axis="x")
        values = {key: res["side"][key]["fs"] for key in SOCKET_SIDE_METHODS}
        x_max = self._scale(values, [res["fs_design"]])
        self._hbar(ax, th, values, res["design"], x_max)
        ax.axvline(res["fs_design"], color=PLOT_PALETTE["design"], linewidth=1.6,
                   label=f"{self.L['plot_design']} = {res['fs_design']:,.0f} kPa")
        ax.set_xlabel("fs (kPa)", fontsize=9)
        ax.set_xlim(0, x_max)
        handles = [Line2D([0], [0], color=PLOT_PALETTE["design"], linewidth=1.6,
                          label=f"{self.L['plot_design']} = {res['fs_design']:,.0f} kPa"),
                   Rectangle((0, 0), 1, 1, facecolor=PLOT_PALETTE["shaft"], alpha=0.3,
                             hatch="//", label=self.L["plot_out_of_range"])]
        _legend(ax, th, handles=handles, loc="lower right")
        self._title(fig, th, "socket_side",
                    f" — qu = {res['qu_side']:.1f} MPa")
        fig.tight_layout(rect=(0, 0, 1, 0.95))

    def _draw_socket_length(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        res = self.res
        ax = fig.add_subplot(111)
        style_axis(ax, th, axis="x")
        values = {key: res["side"][key]["Ls_req"] for key in SOCKET_SIDE_METHODS}
        x_max = self._scale(values, [res["Ls"], res["Ls_design"], 1.0])
        self._hbar(ax, th, values, res["design"], x_max)
        handles = []
        if math.isfinite(res["Ls_design"]):
            ax.axvline(res["Ls_design"], color=PLOT_PALETTE["design"], linewidth=1.6)
            handles.append(Line2D([0], [0], color=PLOT_PALETTE["design"], linewidth=1.6,
                                  label=self.L["plot_design_length"].format(
                                      Ls=res["Ls_design"])))
        if res["Ls"] > 0:
            ax.axvline(res["Ls"], color=PLOT_PALETTE["applied"], linestyle="--", linewidth=1.4)
            handles.append(Line2D([0], [0], color=PLOT_PALETTE["applied"], linestyle="--",
                                  linewidth=1.4,
                                  label=self.L["plot_checked_length"].format(Ls=res["Ls"])))
        ax.set_xlim(0, x_max)
        ax.set_xlabel("Ls (m)", fontsize=9)
        if handles:
            _legend(ax, th, handles=handles, loc="lower right")
        self._title(fig, th, "socket_length", f" — Q = {res['Q']:,.0f} kN")
        fig.tight_layout(rect=(0, 0, 1, 0.95))

    def _draw_socket_settlement(self, fig: Figure) -> None:
        th = style_figure(fig, self.theme)
        s, res = self.a, self.res
        top = max(res["Ls_check"], res["Ls_design"] if math.isfinite(res["Ls_design"]) else 0.0,
                  3.0 * s.D) * 1.6
        curve = s.settlement_curve(np.linspace(s.D, max(top, 2.0 * s.D), 40))
        ax = fig.add_subplot(111)
        style_axis(ax, th)
        Ls = [p["Ls"] for p in curve]
        ax.plot(Ls, [1000 * p["rw"] for p in curve], color=PLOT_PALETTE["ultimate"],
                linewidth=2.2, label=self.L["plot_rw"])
        ax.plot(Ls, [1000 * p["rw_side"] for p in curve], color=PLOT_PALETTE["shaft"],
                linewidth=1.6, linestyle="--", label=self.L["plot_rw_side"])
        ax.plot(Ls, [1000 * p["vesic"] for p in curve], color=PLOT_PALETTE["design"],
                linewidth=1.6, linestyle="-.", label=self.L["plot_vesic_socket"])
        current = res["settlement"]
        ax.scatter([current["Ls"]], [1000 * current["rw"]["total"]], s=50,
                   color=PLOT_PALETTE["applied"], zorder=6, edgecolor=th["panel"])
        ax.annotate(f"{1000 * current['rw']['total']:.1f} mm", xy=(current["Ls"],
                    1000 * current["rw"]["total"]), xytext=(10, 12),
                    textcoords="offset points", fontsize=8.5, color=th["fg"],
                    bbox=label_box(th),
                    arrowprops=dict(arrowstyle="-", color=th["fg_dim"], lw=0.8))
        ax.set_xlabel("Ls (m)", fontsize=9)
        ax.set_ylabel(f"{self.L['plot_settlement']} (mm)", fontsize=9)
        ax.set_ylim(bottom=0)
        _legend(ax, th, loc="upper right")
        self._title(fig, th, "socket_settlement",
                    f" — Em = {res['modulus']['Em']:,.0f} MPa")
        fig.tight_layout(rect=(0, 0, 1, 0.95))


def available_figures(analysis=None) -> list:
    """The figures that can be drawn for the analysis just run: the seismic
    one only when the earthquake is on."""
    if analysis is not None and not analysis.results.get("seismic"):
        return [key for key in PLOT_KEYS if key != "seismic"]
    return list(PLOT_KEYS)


__all__ = ["PLOT_KEYS", "SOCKET_PLOT_KEYS", "Plotter", "SocketPlotter", "available_figures"]
