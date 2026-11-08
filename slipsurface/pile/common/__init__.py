"""Pile's copy of the code the programs of the suite share.

It lives inside `slipsurface.pile` so that every program of the suite can be
installed on its own, side by side, without two of them owning the same files.

    slipsurface.pile.common.factors   bearing capacity and correction factors
                                      (Bearing, MSEW and Wall)
    slipsurface.pile.common.pdf       the report HTML typeset as a PDF with
                                      reportlab (Bearing, MSEW, Pile, Rock,
                                      Settle and Wall)
"""
