"""
Figures and text of a parametric / reliability study.

    oat      the output against each swept input, one panel per input
    hist     the distribution of an output, with the value it is checked against
    scatter  the output against each sampled input
    tornado  Spearman rank correlations of the output with the inputs
"""

from __future__ import annotations

import math
from typing import Dict, List

import numpy as np
from matplotlib.figure import Figure

from .config import PLOT_PALETTE
from .plot_style import TITLE_FONT, style_axis, style_figure
from .study import LIMIT_STATES, OUTPUTS, Study, _column

#: The colour of each output in the study figures
COLORS = {"Q_ult": PLOT_PALETTE["ultimate"], "Q_ult_net": PLOT_PALETTE["ultimate"],
          "Q_all": PLOT_PALETTE["allowable"], "FS": PLOT_PALETTE["design"],
          "utilisation": PLOT_PALETTE["applied"], "Qg_all": PLOT_PALETTE["allowable"],
          "FS_group": PLOT_PALETTE["base"], "utilisation_group": PLOT_PALETTE["applied"],
          "settlement": PLOT_PALETTE["settlement"], "T_pile": PLOT_PALETTE["applied"],
          "utilisation_seismic": PLOT_PALETTE["applied"]}


def _label(L: Dict[str, str], key: str) -> str:
    """An output's name; the translations carry its unit."""
    return L.get(f"out_{key}", key)


def _ok(study: Study) -> List[dict]:
    return [r for r in study.rows if not r.get("error")]


def default_outputs(study: Study) -> List[str]:
    """The outputs that have values, the factor of safety first."""
    stats = study.summary.get("stats", {}) if study.summary else {}
    order = ["FS", "utilisation", "Q_ult", "Q_ult_net", "Q_all", "FS_group",
             "utilisation_group", "Qg_all", "settlement", "utilisation_seismic", "T_pile"]
    return [key for key in order if key in stats]


def _grid(n: int):
    columns = 1 if n <= 1 else (2 if n <= 4 else 3)
    rows = int(math.ceil(n / columns))
    return rows, columns


def _capacity(study: Study, output: str):
    """The value the output is checked against, if it is a checked one."""
    for _, (key, capacity_of, _above) in LIMIT_STATES.items():
        if key == output:
            return capacity_of(study.config)
    return None


def _empty(fig: Figure, text: str, th) -> None:
    ax = fig.add_subplot(111)
    style_axis(ax, th, grid=False)
    ax.axis("off")
    ax.text(0.5, 0.5, text, ha="center", va="center", color=th["fg_dim"], fontsize=11)


def _title(fig, th, text):
    fig.suptitle(text, fontfamily=TITLE_FONT, fontsize=12.5, color=th["fg"])


def plot_oat(fig: Figure, study: Study, L: Dict[str, str], output: str = "FS",
             theme="light") -> None:
    """One panel per swept input: the output against it."""
    th = style_figure(fig, theme)
    rows = _ok(study)
    swept = [v for v in study.variables]
    if not rows or not swept:
        return _empty(fig, L.get("study_no_data", ""), th)
    nrows, ncols = _grid(len(swept))
    for index, variable in enumerate(swept, start=1):
        ax = fig.add_subplot(nrows, ncols, index)
        style_axis(ax, th)
        subset = [r for r in rows if r.get("_swept") == variable.path] or rows
        x = _column(subset, variable.path)
        y = _column(subset, output)
        order = np.argsort(x)
        ax.plot(x[order], y[order], "-o", color=COLORS.get(output, th["accent"]),
                markersize=3.5, linewidth=1.6)
        capacity = _capacity(study, output)
        if capacity is not None and math.isfinite(capacity):
            ax.axhline(capacity, color=PLOT_PALETTE["limit"], linestyle="--", linewidth=1.2)
        ax.set_xlabel(variable.label, fontsize=8.5)
        if (index - 1) % ncols == 0:
            ax.set_ylabel(_label(L, output), fontsize=8.5)
    _title(fig, th, L.get("study_fig_oat", ""))
    fig.tight_layout(rect=(0, 0, 1, 0.95))


def plot_hist(fig: Figure, study: Study, L: Dict[str, str], output: str = "FS",
              theme="light") -> None:
    """The distribution of one output, with the value it is checked against."""
    th = style_figure(fig, theme)
    rows = _ok(study)
    values = _column(rows, output)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return _empty(fig, L.get("study_no_data", ""), th)
    ax = fig.add_subplot(111)
    style_axis(ax, th, axis="y")
    ax.hist(values, bins=min(40, max(8, int(math.sqrt(values.size)))),
            color=COLORS.get(output, th["accent"]), edgecolor=th["panel"], linewidth=0.6)
    ax.axvline(float(values.mean()), color=th["fg_dim"], linestyle="-", linewidth=1.2,
               label=f"{L.get('st_mean', 'mean')} = {values.mean():.3g}")
    capacity = _capacity(study, output)
    if capacity is not None and math.isfinite(capacity):
        ax.axvline(capacity, color=PLOT_PALETTE["limit"], linestyle="--", linewidth=1.6,
                   label=f"{capacity:.3g}")
    ax.set_xlabel(_label(L, output), fontsize=9)
    ax.set_ylabel("n", fontsize=9)
    legend = ax.legend(fontsize=8.5, frameon=False)
    for text in legend.get_texts():
        text.set_color(th["fg"])
    _title(fig, th, L.get("study_fig_hist", ""))
    fig.tight_layout(rect=(0, 0, 1, 0.95))


def plot_scatter(fig: Figure, study: Study, L: Dict[str, str], output: str = "FS",
                 theme="light") -> None:
    """The output against each sampled input, one panel each."""
    th = style_figure(fig, theme)
    rows = _ok(study)
    if not rows or not study.variables:
        return _empty(fig, L.get("study_no_data", ""), th)
    nrows, ncols = _grid(len(study.variables))
    y = _column(rows, output)
    capacity = _capacity(study, output)
    for index, variable in enumerate(study.variables, start=1):
        ax = fig.add_subplot(nrows, ncols, index)
        style_axis(ax, th)
        ax.scatter(_column(rows, variable.path), y, s=9,
                   color=COLORS.get(output, th["accent"]), alpha=0.6, linewidths=0)
        if capacity is not None and math.isfinite(capacity):
            ax.axhline(capacity, color=PLOT_PALETTE["limit"], linestyle="--", linewidth=1.2)
        ax.set_xlabel(variable.label, fontsize=8.5)
        if (index - 1) % ncols == 0:
            ax.set_ylabel(_label(L, output), fontsize=8.5)
    _title(fig, th, L.get("study_fig_scatter", ""))
    fig.tight_layout(rect=(0, 0, 1, 0.95))


def plot_tornado(fig: Figure, study: Study, L: Dict[str, str], output: str = "FS",
                 theme="light") -> None:
    """Spearman rank correlations, the strongest at the top."""
    th = style_figure(fig, theme)
    rho = (study.summary.get("spearman") or {}).get(output, {})
    pairs = [(v.label, rho.get(v.path, float("nan"))) for v in study.variables]
    pairs = [(label, value) for label, value in pairs if math.isfinite(value)]
    if not pairs:
        return _empty(fig, L.get("st_no_sens", ""), th)
    pairs.sort(key=lambda pair: abs(pair[1]))
    ax = fig.add_subplot(111)
    style_axis(ax, th, axis="x")
    labels = [label for label, _ in pairs]
    values = [value for _, value in pairs]
    colors = [PLOT_PALETTE["allowable"] if value >= 0 else PLOT_PALETTE["applied"]
              for value in values]
    ax.barh(range(len(values)), values, color=colors, height=0.62)
    ax.set_yticks(range(len(values)))
    ax.set_yticklabels(labels, fontsize=8.5, color=th["fg"])
    ax.axvline(0, color=th["border"], linewidth=1.0)
    ax.set_xlabel("Spearman ρ", fontsize=9)
    ax.set_xlim(-1.05, 1.05)
    _title(fig, th, f"{L.get('study_fig_tornado', '')} — {_label(L, output)}")
    fig.tight_layout(rect=(0, 0, 1, 0.95))


def _beta_text(beta: float, n: int) -> str:
    if beta == float("inf"):
        return f"> {_inv(1.0 / n):.2f}"
    if beta == float("-inf"):
        return f"< {-_inv(1.0 / n):.2f}"
    if not math.isfinite(beta):
        return "—"
    return f"{beta:.2f}"


def _inv(p: float) -> float:
    from statistics import NormalDist
    return -NormalDist().inv_cdf(min(max(p, 1e-12), 1 - 1e-12))


def summary_text(study: Study, L: Dict[str, str]) -> str:
    """The study as text, for the interface and the report alike."""
    s = study.summary or {}
    lines = [L.get("st_title", "STUDY"), "-" * 78,
             L.get("st_info", "").format(method=L.get(f"sampling_{study.method}", study.method),
                                         n=s.get("n_total", 0), ok=s.get("n_ok", 0)), ""]
    stats = s.get("stats", {})
    if stats:
        lines.append(L.get("st_stats_title", ""))
        head = f"  {'':26}{'n':>7}{L.get('st_mean', 'mean'):>12}{L.get('st_std', 'std'):>12}" \
               f"{'P5':>12}{'P50':>12}{'P95':>12}"
        lines.append(head)
        for key, _ in OUTPUTS:
            if key not in stats:
                continue
            st = stats[key]
            lines.append(f"  {_label(L, key)[:26]:26}{st['n']:>7}{st['mean']:>12.4g}"
                         f"{st['std']:>12.4g}{st['p5']:>12.4g}{st['p50']:>12.4g}"
                         f"{st['p95']:>12.4g}")
        lines.append("")

    rel = s.get("reliability", {})
    if rel:
        lines.append(L.get("st_rel_title", ""))
        for name, r in rel.items():
            lines.append("  " + L.get("st_rel_line", "").format(
                name=L.get(name, name), k=r["n_fail"], n=r["n"], pf=r["pf"],
                lo=r["pf_lo"], hi=r["pf_hi"], beta=_beta_text(r["beta"], r["n"])))
        lines.append("")

    rho = (s.get("spearman") or {}).get("FS", {})
    lines.append(L.get("st_sens_title", ""))
    if rho:
        for variable in sorted(study.variables,
                               key=lambda v: -abs(rho.get(v.path, 0.0) or 0.0)):
            value = rho.get(variable.path, float("nan"))
            lines.append(f"  {variable.label[:34]:34}{value:+8.3f}"
                         if math.isfinite(value) else f"  {variable.label[:34]:34}       —")
    else:
        lines.append("  " + L.get("st_no_sens", ""))
    return "\n".join(lines)
