"""
SlipSurface IQ Pile — axial capacity, group action and settlement of piles, and the
length of a rock socket, driven from a browser.

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

On top of it, a parametric or reliability study sweeps any input (a range, or
a distribution) and reports sensitivities and the probability of failure.

The interface is a local web server driven from the browser (standard library
only), so the program also runs over a remote session or inside a container,
where a desktop toolkit would need a display it does not have.

Package layout
--------------
    slipsurface.pile.config        app identity, defaults, themes, palette
    slipsurface.pile.i18n          every text of the program, English and Turkish
    slipsurface.pile.profile       the layered soil column and its stresses
    slipsurface.pile.axial         unit shaft friction and base resistance, per method
    slipsurface.pile.group         group efficiency and block failure
    slipsurface.pile.settlement    pile and pile group settlement
    slipsurface.pile.socket        rock-socketed piles: side shear, base, length, settlement
    slipsurface.pile.engine        the pile analysis
    slipsurface.pile.study         parametric / reliability studies
    slipsurface.pile.plotting      analysis figures
    slipsurface.pile.study_plots   study figures
    slipsurface.pile.report        calculation report: HTML, PDF, DOCX
    slipsurface.pile.forms         input schema and readers (interface-independent)
    slipsurface.pile.web           local web server and the browser interface

Run it:  slipsurface-pile          (or  python -m slipsurface.pile)
"""

from slipsurface.versioning import module_version

__version__ = module_version(__file__)

APP_NAME = "SlipSurface IQ Pile"
ORG = "SlipSurface IQ"

__all__ = ["__version__", "APP_NAME", "ORG"]
