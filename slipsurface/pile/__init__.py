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
    slipsurface.pile.config        app identity, defaults, themes, palette
    slipsurface.pile.i18n          every text of the program (English)
    slipsurface.pile.profile       the layered soil column and its stresses
    slipsurface.pile.axial         unit shaft friction and base resistance, per method
    slipsurface.pile.group         group efficiency and block failure
    slipsurface.pile.settlement    pile and pile group settlement
    slipsurface.pile.socket        rock-socketed piles: side shear, base, length, settlement
    slipsurface.pile.engine        the pile analysis
    slipsurface.pile.optimizer     shortest safe length, cheapest safe length and diameter
    slipsurface.pile.summary       the results as text and headline values
    slipsurface.pile.forms         flat inputs <-> configuration, project files
    slipsurface.pile.plotting      analysis figures              (extra: plot)
    slipsurface.pile.report        calculation report as PDF     (extra: report)

Run it:  python main.py [command]   (or  python -m slipsurface.pile [command])
After `pip install slipsurfaceiq-pile`:  slipsurface-pile [command]

As a library
------------
    >>> from slipsurface import pile
    >>> values = pile.defaults()               # the starter bored pile
    >>> values["L"] = 18.0                     # flat inputs (see forms.defaults)
    >>> result = pile.analyse(pile.to_config(values))
    >>> result.results["FS"], result.results["Q_all"]
    >>> from slipsurface.pile import summary
    >>> print(summary.results_text(result))

or from a project file: `pile.analyse(pile.load_config("my.pile.json"))`. The
analysis needs only NumPy and SciPy; figures and the PDF report are extras
(`slipsurfaceiq-pile[plot]`, `[report]`, `[all]`).
"""

from importlib import import_module

from .versioning import module_version

__version__ = module_version(__file__)

APP_NAME = "SlipSurface IQ Pile"
ORG = "SlipSurface IQ"

#: The library's entry points -> the module that defines them. They load on
#: first use, so `import slipsurface.pile` stays standard-library only (the
#: command line checks the dependencies after importing it).
_API = {
    "analyse": "engine", "PileAnalysis": "engine",
    "analyse_socket": "socket", "SocketAnalysis": "socket",
    "defaults": "forms", "to_config": "forms", "from_config": "forms",
    "project_file": "forms", "load_config": "cli", "load_values": "cli",
    "optimize_length": "optimizer", "optimize_cost": "optimizer",
    "PileError": "errors", "MissingDependency": "_optional",
}

__all__ = ["__version__", "APP_NAME", "ORG", *_API]


def __getattr__(name: str):
    if name in _API:
        value = getattr(import_module(f".{_API[name]}", __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_API))
