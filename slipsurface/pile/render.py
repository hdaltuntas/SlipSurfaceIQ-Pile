"""
Figure production for SlipSurface IQ Pile.

The interface runs in a browser, so figures are drawn on the server and sent
as PNG. The same functions draw the figures that go into the report, so what
is on screen and what is in the report are the same picture.

Matplotlib is used through the Agg backend: the server needs no display.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure  # noqa: E402

from . import study_plots  # noqa: E402
from .i18n import TRANSLATIONS  # noqa: E402
from .plotting import (  # noqa: E402
    PLOT_KEYS,
    SOCKET_PLOT_KEYS,
    Plotter,
    SocketPlotter,
    available_figures,
)

#: Resolution of the PNGs (enough for the screen, and used by the report)
DPI = 130

#: The study figures
STUDY_VIEWS = ["oat", "hist", "scatter", "tornado"]

__all__ = ["DPI", "PLOT_KEYS", "SOCKET_PLOT_KEYS", "STUDY_VIEWS", "figure_to_png",
           "analysis_figure", "socket_figure", "study_figure", "available_figures",
           "available_study_views"]


def figure_to_png(fig: Figure, dpi: int = DPI) -> bytes:
    """The figure as PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    return buf.getvalue()


def analysis_figure(analysis, key: str, lang: str = "en", theme: str = "light",
                    size=(10.0, 7.0)) -> Figure:
    """One analysis figure."""
    if key not in PLOT_KEYS:
        raise ValueError(f"unknown figure: {key}")
    fig = Figure(figsize=size, dpi=DPI)
    Plotter(analysis, lang, theme).draw(key, fig)
    return fig


def socket_figure(socket, key: str, lang: str = "en", theme: str = "light",
                  size=(10.0, 7.0)) -> Figure:
    """One rock socket figure."""
    if key not in SOCKET_PLOT_KEYS:
        raise ValueError(f"unknown figure: {key}")
    fig = Figure(figsize=size, dpi=DPI)
    SocketPlotter(socket, lang, theme).draw(key, fig)
    return fig


def study_figure(study, view: str, output: str, lang: str = "en",
                 theme: str = "light", size=(10.0, 7.0)) -> Figure:
    """One study figure: sweep, histogram, scatter or tornado."""
    if view not in STUDY_VIEWS:
        raise ValueError(f"unknown study view: {view}")
    L = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    fig = Figure(figsize=size, dpi=DPI)
    {"oat": study_plots.plot_oat, "hist": study_plots.plot_hist,
     "scatter": study_plots.plot_scatter,
     "tornado": study_plots.plot_tornado}[view](fig, study, L, output, theme=theme)
    return fig


def available_study_views(study) -> list:
    """The study figures that apply to the sampling method used."""
    if study is None or not study.rows:
        return []
    if study.method == "oat":
        return ["oat", "hist"]
    return ["hist", "scatter", "tornado"]
