"""Reports retain checked geometry, governing logs and serviceability checks."""

import copy
import math

from slipsurface import pile
from slipsurface.pile import report


def envelope_config():
    cfg = pile.default_config()
    cfg["pile"].update(D=0.8, L=15, top=0)
    cfg["group"].update(nx=1, ny=1)
    cfg["loading"]["Q"] = 300
    cfg["seismic"]["enabled"] = False
    layer = {**cfg["soil_profile"][0], "name": "Sand", "thickness": 40,
             "phi": 25, "E": 150}
    cfg["boreholes"] = [
        {"name": "BH-capacity", "soil_profile": [layer], "groundwater": {"depth": 2}},
        {"name": "BH-settlement", "soil_profile": [{**layer, "phi": 40, "E": 5}],
         "groundwater": {"depth": None}},
    ]
    return cfg


def test_envelope_report_identifies_both_controlling_logs_and_shared_design():
    result = pile.analyse(envelope_config())
    html = report.build_html(result, {})
    assert "Governing borehole" in html
    assert "Borehole: BH-capacity" in html
    assert "Borehole: BH-settlement" in html
    assert "Common recommended whole-metre length: L = 24 m" in html
    assert "Every log was recalculated at this exact length" in html
    assert "Dry assumption" in html
    assert "An individual length search was not requested" in html
    assert "No whole-metre length down to" not in html


def test_skipped_length_search_does_not_report_an_unsuccessful_search():
    result = pile.analyse(pile.default_config(), with_length=False)
    html = report.build_html(result, {})
    assert "An individual length search was not requested" in html
    assert "No whole-metre length down to" not in html


def test_seismic_group_compression_is_reported():
    result = pile.analyse(pile.default_config(), with_length=False)
    assert "seismic_group_compression" in result.results["checks"]
    html = report.build_html(result, {})
    assert "Seismic, group compression (FS)" in html
    assert "Allowable group compression" in html


def test_public_socket_dispatch_reports_selected_settlement_and_integer_design():
    cfg = pile.default_config("socket")
    cfg["socket"]["base_design"] = "none"
    result = pile.analyse(cfg)
    html = report.build_html(result, {})
    assert "Rock-socketed pile" in html
    assert "Minimum socket length (m)" in html
    assert "Settlement used in the check" in html
    assert "Randolph &amp; Wroth, side only" in html or "Randolph & Wroth, side only" in html
    assert "Continuous capacity estimate (diagnostic)" in html
    recommended = result.results["Ls_design"]
    assert math.isfinite(recommended)
    assert f"<b>{recommended:.0f}</b>" in html
    assert f"<b>{recommended:.2f}</b>" not in html


def test_multiple_spt_logs_export_with_separate_provenance_and_figures(tmp_path):
    logs = [
        {"name": "Wet sand", "water_depth": 1,
         "records": [{"depth": 2, "N": 10, "uscs": "SP"},
                     {"depth": 25, "N": 30, "uscs": "SP"}]},
        {"name": "Dry clay", "water_depth": None,
         "records": [{"depth": 2, "N": 10, "uscs": "CL", "cu": 30},
                     {"depth": 25, "N": 20, "uscs": "CL", "cu": 80}]},
    ]
    investigation = pile.derive_profile(logs)
    cfg = investigation.apply(pile.default_config())
    cfg["pile"]["L"] = 12
    result = pile.analyse(cfg, with_length=False)
    figures = report.render_figures(result, keys=["log0:section", "log1:section"], dpi=40)
    assert all(value.startswith(b"\x89PNG") for value in figures.values())
    html = report.build_html(result, figures, img_src=lambda key: f"fig://{key}",
                             spt=investigation)
    assert "Borehole: Wet sand" in html and "Borehole: Dry clay" in html
    assert "Water table: dry assumption" in html
    assert "fig://log0:section" in html and "fig://log1:section" in html
    from slipsurface.pile.pdf import html_to_pdf
    path = tmp_path / "boreholes.pdf"
    html_to_pdf(str(path), html, figures)
    assert path.read_bytes().startswith(b"%PDF-")


def test_automatic_socket_envelope_reports_one_shared_length():
    cfg = pile.default_config("socket")
    cfg["socket"]["Ls"] = 0
    cfg["boreholes"] = [
        {"name": "Rock-A", "soil_profile": copy.deepcopy(cfg["soil_profile"]),
         "socket": {"qu": 10}},
        {"name": "Rock-B", "soil_profile": copy.deepcopy(cfg["soil_profile"]),
         "socket": {"qu": 3}},
    ]
    result = pile.analyse(cfg)
    html = report.build_html(result, {})
    length = result.results["required_length"]
    assert math.isfinite(length)
    assert f"Common recommended whole-metre length: L = {length:.0f} m" in html
    assert "Common recommended whole-metre total pile length" in html
    assert "Socket embedment in each borehole" in html
    assert all(a.overburden + a.results["Ls_check"] == length
               for a in result.analyses.values())
    # The legacy explicit socket argument also accepts the envelope.
    assert "Borehole: Rock-B" in report.build_html(None, {}, socket=result)
