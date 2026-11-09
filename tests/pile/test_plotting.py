"""Every advertised plot accepts public dispatch results without mixing logs."""

import copy
import math
import re

import pytest

pytest.importorskip("matplotlib")
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from slipsurface import pile
from slipsurface.pile.config import SOCKET_SIDE_METHODS
from slipsurface.pile.plotting import Plotter, available_figures, SOCKET_PLOT_KEYS


@pytest.fixture(scope="module")
def socket():
    cfg = pile.default_config("socket")
    cfg["socket"].update(base_design="none", modulus_method="direct", Em=100.0)
    return pile.analyse(cfg)


def _draw(analysis, key):
    fig = Figure(figsize=(10, 7))
    Plotter(analysis).draw(key, fig)
    FigureCanvasAgg(fig).draw()
    return fig


def test_every_advertised_public_socket_figure_renders(socket):
    assert available_figures(socket) == SOCKET_PLOT_KEYS
    assert Plotter(socket).keys == SOCKET_PLOT_KEYS
    for key in available_figures(socket):
        assert _draw(socket, key).axes


def test_socket_length_bars_show_rechecked_integer_designs(socket):
    fig = _draw(socket, "socket_length")
    ax = fig.axes[0]
    expected = [socket.results["side"][key]["Ls_design"] for key in SOCKET_SIDE_METHODS
                if math.isfinite(socket.results["side"][key]["Ls_design"])]
    assert [patch.get_width() for patch in ax.patches] == pytest.approx(
        [min(length, ax.get_xlim()[1]) for length in expected])
    assert all(re.fullmatch(r"[\d,]+(?: »)?", text.get_text().strip())
               for text in ax.texts)
    assert "whole-metre" in ax.get_xlabel()


def test_socket_settlement_marker_uses_the_selected_side_only_model(socket):
    fig = _draw(socket, "socket_settlement")
    selected = socket.results["settlement"]
    point = fig.axes[0].collections[0].get_offsets()[0]
    assert list(point) == pytest.approx([selected["Ls"], 1000 * selected["s"]])
    assert selected["method"] == "rw_side"
    selected_labels = [line.get_label() for line in fig.axes[0].lines
                       if "(selected)" in line.get_label()]
    assert len(selected_labels) == 1
    assert "side" in selected_labels[0].lower()


@pytest.mark.parametrize("kind, child_key", [("bored", "section"), ("socket", "socket_section")])
def test_envelope_figures_are_prefixed_and_keep_borehole_identity(kind, child_key):
    cfg = pile.default_config(kind)
    cfg["seismic"]["enabled"] = False
    cfg["boreholes"] = [
        {"name": "BH: West", "soil_profile": copy.deepcopy(cfg["soil_profile"])},
        {"name": "BH-East", "soil_profile": copy.deepcopy(cfg["soil_profile"])},
    ]
    analysis = pile.analyse(cfg, with_length=False)
    keys = available_figures(analysis)
    assert all(key.startswith(("log0:", "log1:")) for key in keys)
    assert f"log0:{child_key}" in keys and f"log1:{child_key}" in keys
    fig = _draw(analysis, f"log0:{child_key}")
    assert any("BH: West" in text.get_text() for text in fig.texts)
    assert not any("BH-East" in text.get_text() for text in fig.texts)
    with pytest.raises(ValueError, match="borehole-prefixed"):
        Plotter(analysis).draw(child_key, Figure())


def test_seismic_plot_exposes_group_failure_even_when_individual_piles_pass():
    cfg = pile.default_config("bored")
    cfg["loading"]["Q"] = 100.0
    cfg["seismic"].update(V=24709.080608388136, M_B=0.0, M_L=0.0)
    analysis = pile.analyse(cfg, with_length=False)
    fig = _draw(analysis, "seismic")
    assert "Group compression: u = 1.20 — NOT OK" in fig.axes[1].get_title()
