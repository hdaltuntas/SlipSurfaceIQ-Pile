"""
Configuration for SlipSurface IQ Pile: the default project, the choice lists, and the
theme and plot palette shared by the page and the figures.

The app name and version live in the package's ``__init__`` so that there is
one copy of each; the translations live in `slipsurface.pile.i18n`.
"""

from . import APP_NAME
from . import __version__ as APP_VERSION

__all__ = ["APP_NAME", "APP_VERSION", "DEFAULT_CONFIG", "THEMES", "PLOT_PALETTE",
           "SOIL_FILL", "METHOD_COLORS", "SHAPES", "INSTALLATIONS", "BEHAVIOURS",
           "CLAY_METHODS", "TIP_METHODS", "EFFICIENCY_METHODS", "GROUP_SETTLEMENT",
           "SKIN_DISTRIBUTIONS", "SOCKET_SIDE_METHODS", "SOCKET_BASE_METHODS",
           "SOCKET_DESIGN", "SOCKET_BASE_DESIGN", "MODULUS_METHODS", "ACCENT", "PA"]

#: Atmospheric pressure, the reference stress of the normalised correlations [kPa]
PA = 101.325

# --- Choice lists (the first entry is the default where one is needed) -----
SHAPES = ["circular", "square"]

#: How the pile is put in the ground: bored (or CFA), driven with a small
#: displacement (H section, open pipe), driven with a large one (precast
#: concrete, closed pipe). It sets the lateral earth pressure along the shaft.
INSTALLATIONS = ["bored", "driven_low", "driven_high"]

BEHAVIOURS = ["granular", "cohesive"]

#: Shaft friction in clay; a granular layer is always K·σ'v·tan δ
CLAY_METHODS = ["alpha_api", "alpha_kulhawy", "alpha_sladen", "beta", "lambda"]

#: Base resistance
TIP_METHODS = ["meyerhof", "vesic", "janbu"]

#: Group efficiency; `unity` takes the group as n single piles
EFFICIENCY_METHODS = ["converse_labarre", "los_angeles", "seiler_keeney", "feld", "unity"]

#: The group settlement the check is made against
GROUP_SETTLEMENT = ["raft", "vesic", "meyerhof"]

#: How the shaft friction is spread along the pile, for its elastic shortening
SKIN_DISTRIBUTIONS = ["uniform", "triangular"]

#: Unit side shear of a rock socket: every correlation the program knows
SOCKET_SIDE_METHODS = [
    "rosenberg_journeaux", "horvath_kenney", "meigh_wolski", "williams",
    "reynolds_kaderabek", "gupton_logan", "rowe_armitage", "carter_kulhawy",
    "toh", "zhang_einstein", "oneill_reese", "kulhawy_2005",
]

#: Base resistance of a rock socket
SOCKET_BASE_METHODS = ["coates", "rowe_armitage", "carter_kulhawy", "zhang_einstein",
                       "aashto", "cfem"]

#: Which side shear the design length is taken from: a statistic of the
#: correlations that apply, or one correlation by name
SOCKET_DESIGN = ["mean", "median", "lower", "upper"] + SOCKET_SIDE_METHODS
SOCKET_BASE_DESIGN = ["none", "min", "mean"] + SOCKET_BASE_METHODS

#: The rock mass modulus: from RQD (Gardner), from GSI (Hoek & Diederichs), or entered
MODULUS_METHODS = ["rqd", "gsi", "direct"]

# --- Interface theme (web/static/style.css) and plot palette ---------------
# --- kept together so the figures always match the page they are shown on. -
ACCENT = "#5B7A3A"  # the colour of its group in the suite (foundations)

THEMES = {
    "dark": dict(bg="#262624", panel="#30302E", input_bg="#262624", fg="#F5F4ED",
                 fg_dim="#A6A39A", border="#4A4944", hover="#3A3A37", btn="#3A3A37",
                 muted="#6B6A64", accent="#9BBA78", accent_hover="#AECB8D"),
    "light": dict(bg="#F5F4ED", panel="#FAF9F5", input_bg="#FFFFFF", fg="#141413",
                  fg_dim="#73726C", border="#E3E0D5", hover="#F0EEE6", btn="#F0EEE6",
                  muted="#B7B4AA", accent=ACCENT, accent_hover="#4A6630"),
}
# The report's figures: the light palette on white paper.
THEMES["paper"] = dict(THEMES["light"], bg="#FFFFFF", panel="#FFFFFF")

# Semantic colours: the same quantity is the same colour in every figure. Warm
# and muted, to sit on the paper-coloured page; terracotta marks the capacity.
PLOT_PALETTE = dict(
    shaft="#5B8DB8", base="#8C6BB1", weight="#D9A55B",
    ultimate="#C6613F", allowable="#4E9A8A", applied="#B0413E", design="#5E8C4A",
    water="#6FA8C7", pile="#8A8680", cap="#6B6A64", stress="#A26A12",
    limit="#A26A12", block="#B0413E", settlement="#5B8DB8", rock="#9A938A",
    consolidation="#8C6BB1", elastic="#D9A55B",
)

#: One colour per method, so a method keeps its colour in every figure.
METHOD_COLORS = {
    "alpha_api": "#5B8DB8", "alpha_kulhawy": "#4E9A8A", "alpha_sladen": "#6FA8C7",
    "beta": "#8C6BB1", "lambda": "#D9A55B", "spt": "#73726C",
    "meyerhof": "#C6613F", "vesic": "#5E8C4A", "janbu": "#A26A12",
    "converse_labarre": "#5B8DB8", "los_angeles": "#8C6BB1", "seiler_keeney": "#D9A55B",
    "feld": "#4E9A8A", "unity": "#B7B4AA", "block": "#B0413E",
    "raft": "#8C6BB1", "vesic_group": "#5E8C4A", "meyerhof_spt": "#73726C",
}

# Fill colours of the soil behaviours in the section (theme-dependent, since a
# light sandy tone reads poorly on a dark background).
SOIL_FILL = {
    "light": {"granular": "#E3C98F", "cohesive": "#A7B8A0", "rock": "#B9B3A8"},
    "dark": {"granular": "#8A7250", "cohesive": "#5E6E58", "rock": "#6E6A62"},
}
SOIL_FILL["paper"] = SOIL_FILL["light"]

DEFAULT_CONFIG = {
    "project_info": {
        "title": "Project: Bored pile group in layered ground",
        "analyst": "",
    },
    "pile": {
        "shape": "circular",
        "D": 0.80,                 # diameter, or side of a square pile [m]
        "L": 20.0,                 # length below the pile head [m]
        "top": 1.5,                # depth of the pile head, the underside of the cap [m]
        "installation": "bored",
        "gamma_p": 25.0,           # unit weight of the pile material [kN/m³]
        "Ep": 30000.0,             # Young's modulus of the pile material [MPa]
    },
    # The vertical load on the whole group (on the one pile when the group is
    # 1 × 1), at the underside of the cap; the cap's own weight belongs in it.
    "loading": {
        "Q": 10000.0,              # [kN]
    },
    "group": {
        "nx": 3,                   # piles along B
        "ny": 3,                   # piles along L
        "sx": 2.40,                # centre-to-centre spacing along B [m]
        "sy": 2.40,                # centre-to-centre spacing along L [m]
        "efficiency": "converse_labarre",
        "block": True,             # check block failure of the group as well
    },
    "groundwater": {
        "depth": 2.5,              # below ground surface [m]
        "gamma_water": 9.81,       # [kN/m³]
    },
    # Layers from the ground surface down. φ' is the effective friction angle
    # (of a clay too: the β method and the drained checks use it), cu the
    # undrained shear strength, OCR the overconsolidation ratio, N60 the SPT
    # blow count (0: not measured), E [MPa] and ν the elastic constants, Cc, Cr
    # and e0 the compressibility of a clay for the settlement of the group.
    "soil_profile": [
        {"name": "Fill", "thickness": 2.0, "behaviour": "granular", "gamma": 18.0,
         "gamma_sat": 19.0, "phi": 28.0, "cu": 0.0, "OCR": 1.0, "N60": 8.0, "E": 10.0,
         "nu": 0.30, "Cc": 0.0, "Cr": 0.0, "e0": 0.0},
        {"name": "Soft clay", "thickness": 6.0, "behaviour": "cohesive", "gamma": 17.0,
         "gamma_sat": 18.0, "phi": 22.0, "cu": 35.0, "OCR": 1.5, "N60": 0.0, "E": 8.0,
         "nu": 0.40, "Cc": 0.35, "Cr": 0.05, "e0": 1.00},
        {"name": "Medium dense sand", "thickness": 7.0, "behaviour": "granular", "gamma": 19.0,
         "gamma_sat": 20.0, "phi": 32.0, "cu": 0.0, "OCR": 1.0, "N60": 20.0, "E": 30.0,
         "nu": 0.30, "Cc": 0.0, "Cr": 0.0, "e0": 0.0},
        {"name": "Stiff clay", "thickness": 5.0, "behaviour": "cohesive", "gamma": 19.5,
         "gamma_sat": 20.0, "phi": 26.0, "cu": 120.0, "OCR": 3.0, "N60": 0.0, "E": 45.0,
         "nu": 0.35, "Cc": 0.18, "Cr": 0.02, "e0": 0.70},
        {"name": "Dense sand", "thickness": 12.0, "behaviour": "granular", "gamma": 20.0,
         "gamma_sat": 21.0, "phi": 36.0, "cu": 0.0, "OCR": 1.0, "N60": 40.0, "E": 70.0,
         "nu": 0.30, "Cc": 0.0, "Cr": 0.0, "e0": 0.0},
    ],
    "options": {
        "clay_method": "alpha_api",
        "tip_method": "meyerhof",
        "K_ratio": 0.0,            # K / K0 along the shaft in sand (0: by installation)
        "delta_ratio": 0.75,       # δ / φ' of the pile–soil interface
        "critical_depth": True,    # σ'v in sand held constant below zc = ratio·D
        "zc_ratio": 15.0,
        "janbu_eta": 90.0,         # Janbu's angle of the failure surface η' [°]
        "sladen_C": 0.0,           # Sladen's C (0: 0.4 bored, 0.5 driven)
        "subtract_weight": True,   # the pile's weight is taken off the capacity
        "buoyant_weight": True,    # below the water table the pile weighs γp − γw
        "spt_method": True,        # Meyerhof's SPT rule beside the others, where N60 is given
    },
    "settlement": {
        "group_method": "raft",    # the group settlement the check uses
        "raft_fraction": 0.667,    # depth of the equivalent raft, as a share of L
        "spread": 2.0,             # load spread below the raft, vertical : horizontal
        "distribution": "uniform", # shaft friction along the pile, for its shortening
    },
    # The seismic load combination on the group, from the structural analysis:
    # the vertical load and the overturning moments at the underside of the
    # cap. The rigid cap shares them among the piles, the outer ones in the
    # direction of the moment take more, those opposite less — and in tension
    # when the moment is large enough. Uplift is resisted by the shaft friction
    # in tension and by the pile's own weight.
    "seismic": {
        "enabled": True,
        "V": 8000.0,               # vertical load on the group [kN] (negative: uplift)
        "M_B": 16000.0,            # overturning moment, loads varying along B [kN·m]
        "M_L": 0.0,                # overturning moment, loads varying along L [kN·m]
        "tension_sand": 0.75,      # shaft friction in tension / in compression, sand
        "tension_clay": 1.0,       # the same in clay
        "cyclic": 1.0,             # reduction of the shaft friction for cyclic loading
        "FS_compression": 1.5,     # factor of safety in compression, seismic case
        "FS_tension": 2.0,         # factor of safety on the shaft friction in tension
    },
    "criteria": {
        "FS": 2.5,                 # factor of safety on the net ultimate capacity
        "s_allow": 40.0,           # allowable settlement of the group [mm]
        "L_min": 4.0,              # the shortest pile the length search tries [m]
        "L_step": 0.25,            # the step of the length search [m]
    },
    # A pile socketed into rock, analysed on its own: the socket carries the
    # load, the overburden above the rock only its own share of the weight.
    "socket": {
        "D": 1.00,                 # socket diameter [m]
        "Ls": 4.0,                 # socket length being checked [m]
        "top": 1.0,                # depth of the pile head below the ground [m]
        "rock_depth": 12.0,        # depth of the rock surface below the ground [m]
        "Q": 9000.0,               # vertical load on the pile [kN]
        "qu": 20.0,                # uniaxial compressive strength of the intact rock [MPa]
        "RQD": 70.0,               # rock quality designation [%]
        "Ei": 20000.0,             # modulus of the intact rock [MPa]
        "modulus_method": "rqd",
        "Em": 8000.0,              # rock mass modulus, when entered directly [MPa]
        "GSI": 60.0,               # Geological Strength Index
        "mi": 10.0,                # Hoek–Brown constant of the intact rock
        "D_blast": 0.0,            # disturbance factor
        "nu_r": 0.25,              # Poisson's ratio of the rock mass
        "Eb_ratio": 1.0,           # modulus below the base / along the socket
        "spacing": 0.60,           # spacing of the discontinuities [m]
        "aperture": 1.0,           # aperture of the discontinuities [mm]
        "fc": 30.0,                # concrete cylinder strength [MPa]
        "Ec": 30000.0,             # concrete modulus [MPa]
        "gamma_c": 25.0,           # unit weight of the concrete [kN/m³]
        "design": "mean",
        "base_design": "min",
        "FS_side": 2.5,
        "FS_base": 3.0,
        "min_ratio": 1.0,          # the socket is at least this many diameters long
        "weak_rock": 5.0,          # the linear rules hold below this qu [MPa]
    },
}
