"""A rock socket is never shorter than three pile diameters."""
import pytest

from slipsurface.pile import forms
from slipsurface.pile.config import DEFAULT_CONFIG, MIN_SOCKET_RATIO
from slipsurface.pile.socket import analyse_socket


def _socket(**values):
    return analyse_socket(forms.to_config({**forms.defaults(), "pile_type": "socket",
                                           **values})).results


def test_the_minimum_is_three_diameters_by_default():
    assert MIN_SOCKET_RATIO == 3.0
    assert DEFAULT_CONFIG["socket"]["min_ratio"] == 3.0
    res = _socket()
    assert res["Ls_min"] == pytest.approx(3.0 * res["D"])
    assert res["Ls_design"] >= res["Ls_min"] - 1e-9


def test_a_tiny_load_still_needs_three_diameters():
    res = _socket(socket_Q=10.0, socket_D=1.2)
    assert res["Ls_min"] == pytest.approx(3.6)
    assert res["Ls_design"] == pytest.approx(3.6)


def test_an_old_ratio_below_three_is_raised_with_a_warning():
    cfg = forms.to_config({**forms.defaults(), "pile_type": "socket"})
    cfg["socket"]["min_ratio"] = 1.0
    analysis = analyse_socket(cfg)
    assert analysis.results["Ls_min"] == pytest.approx(3.0 * analysis.results["D"])
    assert any(key == "warn_socket_min_ratio" for key, _ in analysis.results["warnings"])


def test_a_larger_ratio_is_kept():
    res = _socket(min_ratio=4.0)
    assert res["Ls_min"] == pytest.approx(4.0 * res["D"])
    assert not any(key == "warn_socket_min_ratio" for key, _ in res["warnings"])


def test_the_form_does_not_offer_less_than_three():
    fields = {f["key"]: f for g in forms.schema()["socket"]["groups"] for f in g["fields"]}
    assert fields["min_ratio"]["min"] == 3
