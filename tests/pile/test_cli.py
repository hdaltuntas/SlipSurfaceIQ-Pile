"""The command line: `slipsurface-pile` and `python -m slipsurface.pile`."""
import json

import pytest

from slipsurface.pile import cli


@pytest.fixture
def project(tmp_path):
    def make(pile_type="bored"):
        path = tmp_path / f"{pile_type}.pile.json"
        assert cli.main(["example", "--type", pile_type, "-o", str(path)]) == 0
        return str(path)
    return make


def test_analyze_follows_the_pile_type(project, capsys):
    for pile_type in ("bored", "socket"):
        path = project(pile_type)
        capsys.readouterr()
        assert cli.main(["analyze", path, "--json"]) == 0
        assert json.loads(capsys.readouterr().out)["pile_type"] == pile_type


def test_run_is_kept_as_an_alias(project, capsys):
    assert cli.main(["run", project()]) == 0
    assert "PILE CAPACITY RESULTS" in capsys.readouterr().out


def test_analyze_writes_a_pdf_report(project, tmp_path):
    out = tmp_path / "r.pdf"
    assert cli.main(["analyze", project("socket"), "-o", str(out)]) == 0
    assert out.read_bytes()[:5] == b"%PDF-"


def test_bored_only_commands_refuse_a_socket(project, capsys):
    assert cli.main(["optimize-length", project("socket")]) == 1
    assert "piles in soil" in capsys.readouterr().err
