"""Optional dependencies: what each extra adds, and a readable error without it.

The analysis needs only NumPy and SciPy. Figures and the PDF report need more,
installed as an extra of the package:

    pip install "slipsurfaceiq-pile[plot]"     figures      matplotlib
    pip install "slipsurfaceiq-pile[report]"   PDF report   matplotlib, reportlab
    pip install "slipsurfaceiq-pile[all]"      both

A module that needs one of them imports it inside ``try`` and, when it is
missing, raises `missing(...)` instead of a bare ``No module named …``.
"""

from __future__ import annotations

#: Name of the distribution on PyPI
DISTRIBUTION = "slipsurfaceiq-pile"

#: Extra -> (what it is for, the modules it brings)
EXTRAS = {
    "plot": ("figures", ("matplotlib",)),
    "report": ("the PDF report", ("matplotlib", "reportlab")),
}


class MissingDependency(ImportError):
    """An optional dependency of the feature asked for is not installed."""


def missing(module: str, extra: str) -> MissingDependency:
    """The error to raise when `module`, brought by `extra`, cannot be imported."""
    return MissingDependency(
        f"{module} is needed for {EXTRAS[extra][0]} but is not installed. "
        f'Install it with:  pip install "{DISTRIBUTION}[{extra}]"', name=module)
