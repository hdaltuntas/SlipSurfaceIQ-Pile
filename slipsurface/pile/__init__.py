"""
SlipSurface IQ Pile — axial capacity, group action and settlement of piles, and the
length of a rock socket: a Python library with a command line.

The program works out how much load a pile, or a group of piles, in a layered
soil profile can carry, how long it has to be, and how much it settles:

    1. Stresses        — σv0, u0 and σ'v0 down the shaft, with the water table
    2. Shaft friction  — the α methods (API RP 2A, Kulhawy & Phoon, Sladen),
                         the β method and the λ method in clay; K·σ'v·tan δ in
                         sand, with Meyerhof's critical depth; the SPT rule
    3. Base resistance — Meyerhof, Vesić and Janbu; 9·cu, Vesić's Nc* and
                         Janbu's Nc* in clay
    4. Pile weight     — subtracted from the ultimate capacity, buoyant below
                         the water table
    5. Group action    — the efficiency by Converse–Labarre, Los Angeles,
                         Seiler–Keeney and Feld, and block failure
    6. Required length — the shortest pile that satisfies the single-pile and
                         the group check
    7. Settlement      — a single pile (Vesić), and the group by the
                         equivalent raft (consolidation and elastic), Vesić's
                         √(Bg/D) rule and Meyerhof's SPT rule
    8. Rock socket     — the unit side shear of every published correlation,
                         the base resistance, the socket length each of them
                         needs, and the elastic settlement of the socket
                         (Randolph & Wroth; Vesić)

On top of it, an optimizer finds the shortest safe length, or the cheapest
safe length and diameter.

Package layout
--------------
    slipsurface.pile.config        defaults, choice lists, figure colours
    slipsurface.pile.texts         every text of the program
    slipsurface.pile.profile       the layered soil column and its stresses
    slipsurface.pile.axial         unit shaft friction and base resistance, per method
    slipsurface.pile.group         group efficiency and block failure
    slipsurface.pile.settlement    pile and pile group settlement
    slipsurface.pile.socket        rock-socketed piles: side shear, base, length, settlement
    slipsurface.pile.engine        the pile analysis
    slipsurface.pile.optimizer     shortest safe length, cheapest safe length and diameter
    slipsurface.pile.summary       the results as text and headline values
    slipsurface.pile.project       complete starter configurations, checking
    slipsurface.pile.spt           the soil profile from SPT records and their tests
    slipsurface.pile.plotting      analysis figures              (extra: plot)
    slipsurface.pile.report        calculation report as PDF     (extra: report)

As a library
------------
    >>> from slipsurface import pile
    >>> cfg = pile.default_config("bored")     # a complete starter configuration
    >>> cfg["pile"]["L"] = 18.0
    >>> result = pile.analyse(cfg)
    >>> result.results["FS"], result.results["Q_all"]
    >>> from slipsurface.pile import summary
    >>> print(summary.results_text(result))

The analysis needs only NumPy and SciPy; figures and the PDF report are
extras (`slipsurfaceiq-pile[plot]`, `[report]`, `[all]`).
"""

__version__ = "2026.0.0"

APP_NAME = "SlipSurface IQ Pile"

from ._optional import MissingDependency  # noqa: E402
from .engine import PileAnalysis, analyse  # noqa: E402
from .analysis import BoreholeAnalysis  # noqa: E402
from .errors import PileError  # noqa: E402
from .optimizer import optimize_cost, optimize_length  # noqa: E402
from .project import default_config, normalize  # noqa: E402
from .socket import SocketAnalysis, analyse_socket  # noqa: E402
from .spt import SPTInvestigation, SPTProfile, derive_profile  # noqa: E402

__all__ = ["__version__", "APP_NAME", "analyse", "PileAnalysis", "BoreholeAnalysis", "analyse_socket",
           "SocketAnalysis", "default_config", "normalize", "optimize_length",
           "optimize_cost", "derive_profile", "SPTProfile", "SPTInvestigation", "PileError",
           "MissingDependency"]
