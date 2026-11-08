"""
The package as published on PyPI: one version, its own namespace, and an
analysis that runs with only NumPy and SciPy installed (figures and the PDF
report are the [plot] / [report] extras).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "example.pile.json"


def test_the_version_has_one_home():
    # pyproject.toml reads it from here (setuptools, statically), and so does
    # the publish workflow's tag check: it must stay a plain string literal
    from slipsurface import pile
    text = (ROOT / "slipsurface" / "pile" / "__init__.py").read_text(encoding="utf-8")
    literal = re.search(r'^__version__ = "([^"]+)"$', text, re.MULTILINE)
    assert literal and literal.group(1) == pile.__version__
    assert 'dynamic = ["version"]' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_the_package_owns_nothing_outside_slipsurface_pile():
    # `slipsurface` is shared by the programs of the suite: whoever ships
    # slipsurface/__init__.py (or slipsurface/ui …) would overwrite the files
    # of the others
    assert not (ROOT / "slipsurface" / "__init__.py").exists()
    assert [p.name for p in (ROOT / "slipsurface").iterdir()
            if p.name != "__pycache__"] == ["pile"]


def test_the_library_entry_points_resolve():
    from slipsurface import pile
    for name in pile.__all__:
        assert getattr(pile, name) is not None, name


#: Runs in a fresh interpreter in which the optional packages cannot be imported
WITHOUT_EXTRAS = """
import json, sys
sys.path.insert(0, {root!r})

class NoExtras:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("matplotlib", "reportlab"):
            raise ImportError(f"No module named {{name!r}} (blocked)")

sys.meta_path.insert(0, NoExtras())

from slipsurface import pile
assert "numpy" not in sys.modules            # importing the package is free
result = pile.analyse(pile.default_config("bored"))
socket = pile.analyse_socket(pile.default_config("socket"))
from slipsurface.pile import summary
text = summary.results_text(result)

try:
    from slipsurface.pile import plotting
except pile.MissingDependency as exc:
    figures = str(exc)
else:
    raise AssertionError("plotting imported without matplotlib")

from slipsurface.pile import cli
code = cli.main(["analyze", {example!r}, "-o", "never.pdf"])
print(json.dumps({{"FS": result.results["FS"], "text": bool(text),
                  "socket": socket.results["Ls_design"] > 0,
                  "figures": figures, "report_exit": code,
                  "loaded": sorted(m for m in ("matplotlib", "reportlab")
                                   if m in sys.modules)}}))
"""


def test_the_analysis_runs_without_the_extras(tmp_path):
    script = WITHOUT_EXTRAS.format(root=str(ROOT), example=str(EXAMPLE))
    run = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True,
                         text=True, cwd=tmp_path, timeout=300)
    assert run.returncode == 0, run.stderr
    out = json.loads(run.stdout.strip().splitlines()[-1])
    assert out["FS"] > 0 and out["text"] and out["socket"]
    assert 'pip install "slipsurfaceiq-pile[plot]"' in out["figures"]
    # the report is refused before the analysis, with the extra to install
    assert out["report_exit"] == 1
    assert 'slipsurfaceiq-pile[report]' in run.stderr
    assert not (tmp_path / "never.pdf").exists()
    assert out["loaded"] == []
