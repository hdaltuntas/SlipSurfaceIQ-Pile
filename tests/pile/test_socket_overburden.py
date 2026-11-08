"""Shaft friction of the soil above the rock, for a socketed pile (optional)."""
import pytest

from slipsurface.pile.errors import PileError
from slipsurface.pile.project import default_config
from slipsurface.pile.socket import analyse_socket


def _socket(**socket):
    cfg = default_config("socket")
    cfg["socket"].update(socket)
    return analyse_socket(cfg).results


def test_the_overburden_is_left_out_by_default():
    res = _socket()
    assert res["Qs_soil"] == 0.0 and res["overburden_layers"] == []
    assert res["check"]["Qs_soil"] == 0.0


def test_counting_the_overburden_adds_friction_and_shortens_the_socket():
    none, soil = _socket(), _socket(overburden_friction="soil")
    assert soil["Qs_soil"] > 0
    assert soil["Ls_design"] < none["Ls_design"]
    # the soil friction takes FS_side = 2.5, at the length both cases check
    at_checked = _socket(overburden_friction="soil", Ls=4.0)["check"]["Q_all"]
    assert at_checked == pytest.approx(_socket(Ls=4.0)["check"]["Q_all"]
                                       + soil["Qs_soil"] / 2.5, rel=1e-6)
    assert sum(layer["Qs"] for layer in soil["overburden_layers"]) == \
        pytest.approx(soil["Qs_soil"], rel=1e-9)
    assert all(layer["bottom"] <= 12.0 + 1e-9 for layer in soil["overburden_layers"])


def test_a_profile_that_stops_above_the_rock_is_refused():
    with pytest.raises(PileError) as err:
        _socket(overburden_friction="soil", rock_depth=40.0)
    assert err.value.key == "err_socket_profile"
