"""The one command line of SlipSurfaceIQ Pile.

`python main.py …` and `python -m slipsurface.pile …` both land here.

    (no command) | gui        open the desktop interface
    analyze  (alias: run)    analyse a project — its pile type decides which
                             analysis — print the results, optionally a PDF
    socket                   analyse a project as a rock-socketed pile
    study                    run the study defined in a project
    optimize-length          shortest safe length (bored or driven pile)
    optimize-cost            cheapest safe length and diameter (bored or driven pile)
    example                  write a starter project file
    --check                  check the Python version and the dependencies
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from pathlib import Path

from . import APP_NAME, __version__

#: Module -> pip package the program needs at run time
REQUIRED = {"PySide6": "PySide6", "numpy": "numpy", "scipy": "scipy",
            "matplotlib": "matplotlib", "reportlab": "reportlab"}
MIN_PYTHON = (3, 10)


# --------------------------------------------------------------------------- #
#  Environment
# --------------------------------------------------------------------------- #

def check_environment(verbose: bool = True, need_gui: bool = True) -> bool:
    """True when Python and the packages are there; says what is missing."""
    ok = True
    if sys.version_info < MIN_PYTHON:
        print(f"[ERROR] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required "
              f"(found {sys.version.split()[0]}).", file=sys.stderr)
        ok = False
    missing = []
    for mod, pip_name in REQUIRED.items():
        if mod == "PySide6" and not need_gui:
            continue
        try:
            m = importlib.import_module(mod)
            if verbose:
                print(f"  {mod:12s} {getattr(m, '__version__', '?')}")
        except ImportError:
            missing.append(pip_name)
    if missing:
        ok = False
        root = Path(__file__).resolve().parents[2]
        print("[ERROR] Missing package(s): " + ", ".join(missing), file=sys.stderr)
        print(f"        Install:  {Path(sys.executable).name} -m pip install -r "
              f"{root / 'requirements.txt'}", file=sys.stderr)
    if ok and verbose:
        print(f"  Python     {sys.version.split()[0]}  ({sys.executable})")
        print("Environment ready.")
    return ok


# --------------------------------------------------------------------------- #
#  Arguments
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="SlipSurfaceIQ Pile",
        description="Axial capacity, group action and settlement of bored piles, and "
                    "rock-socketed piles — desktop interface or command line.")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--check", action="store_true",
                        help="check the Python version and the dependencies, then exit")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("gui", help="open the desktop interface (the default)")

    for name, aliases, help_text in (
            ("analyze", ["run"], "analyse a project file (its pile type decides how)"),
            ("socket", [], "analyse a project file as a rock-socketed pile")):
        p = sub.add_parser(name, aliases=aliases, help=help_text)
        p.add_argument("project", help="path to a .pile.json project file")
        p.add_argument("-o", "--out", default=None, help="write a PDF report here")
        p.add_argument("--json", action="store_true",
                       help="print the key results as JSON instead of the text report")

    study = sub.add_parser("study", help="run the study defined in a project file")
    study.add_argument("project", help="path to a .pile.json project file")
    study.add_argument("-o", "--out", default=None, help="write the samples here (.csv / .xlsx)")

    ol = sub.add_parser("optimize-length", help="find the shortest safe length (bored or driven pile)")
    ol.add_argument("project", help="path to a .pile.json project file")
    ol.add_argument("--lmin", type=float, default=3.0)
    ol.add_argument("--lmax", type=float, default=40.0)
    ol.add_argument("--popsize", type=int, default=12)
    ol.add_argument("--maxiter", type=int, default=30)
    ol.add_argument("--seed", type=int, default=42)

    oc = sub.add_parser("optimize-cost",
                        help="cheapest safe length and diameter (bored or driven pile)")
    oc.add_argument("project", help="path to a .pile.json project file")
    oc.add_argument("--lmin", type=float, default=3.0)
    oc.add_argument("--lmax", type=float, default=40.0)
    oc.add_argument("--dmin", type=float, default=0.3)
    oc.add_argument("--dmax", type=float, default=1.5)
    oc.add_argument("--cost-a", type=float, default=1.0, dest="cost_a",
                    help="cost per m of pile per m² of cross-section (cost = a·L·D² + b·L)")
    oc.add_argument("--cost-b", type=float, default=0.1, dest="cost_b",
                    help="cost per m of pile, whatever its size")
    oc.add_argument("--popsize", type=int, default=10)
    oc.add_argument("--maxiter", type=int, default=25)
    oc.add_argument("--seed", type=int, default=42)

    example = sub.add_parser("example", help="write a starter project file")
    example.add_argument("-o", "--out", default="project.pile.json")
    example.add_argument("--type", choices=["bored", "driven", "socket"], default="bored",
                         help="the pile type of the starter project")
    return parser


# --------------------------------------------------------------------------- #
#  Project files
# --------------------------------------------------------------------------- #

def load_values(path: str) -> dict:
    """The flat values of a project file, whatever its layout."""
    from . import forms
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "config" in data:
        data = data["config"]
    if isinstance(data, dict) and ("format" in data or "pile" in data
                                   or "soil_profile" in data or "socket" in data):
        # A nested project file: read every section it carries into flat
        # values (to_config alone reads flat keys and would fall back to the
        # defaults for the rest).
        return forms.from_config(data)
    return {**forms.defaults(), **data}


def load_config(path: str) -> dict:
    """The analysis configuration of a project file."""
    from . import forms
    return forms.to_config(load_values(path))


def _example_study(values: dict) -> list:
    """Two study variables for the starter project, so `study` has something to do."""
    clay = values["soil_profile"][1]
    return [
        {"path": "loading.Q", "label": "Actions · Q", "mode": "dist", "dist": "lognormal",
         "mean": values["Q"], "cov": 0.15, "min": 0, "max": 0, "n_points": 5},
        {"path": "soil_profile.1.cu", "label": "Soft clay · cu", "mode": "dist",
         "dist": "lognormal", "mean": clay["cu"], "cov": 0.25, "min": 0, "max": 0,
         "n_points": 5},
    ]


def _finite(value):
    """JSON has no NaN: a missing number prints as null."""
    return value if isinstance(value, (int, float)) and math.isfinite(value) else None


# --------------------------------------------------------------------------- #
#  Commands
# --------------------------------------------------------------------------- #

def cmd_analyze(args, force_socket: bool = False) -> int:
    from . import report as report_mod, summary
    cfg = load_config(args.project)
    if force_socket or cfg.get("pile_type") == "socket":
        from .socket import analyse_socket
        socket = analyse_socket(cfg)
        res = socket.results
        if args.json:
            print(json.dumps({
                "pile_type": "socket",
                "Ls_design": _finite(res.get("Ls_design")),
                "fs_design": _finite(res.get("fs_design")),
                "Q_all": _finite(res["check"]["Q_all"]),
                "utilisation": _finite(res["check"]["utilisation"]),
                "status": res["check"]["status"],
                "settlement_mm": _finite(1000 * res["settlement"]["rw"]["total"]),
            }, indent=2))
        else:
            print(summary.socket_headline(socket))
            print(summary.socket_text(socket))
        if args.out:
            report_mod.export_report(args.out, None, "en", socket=socket)
            print(args.out, file=sys.stderr)
        return 0

    from .engine import analyse
    result = analyse(cfg)
    res = result.results
    if args.json:
        print(json.dumps({
            "pile_type": cfg["pile_type"],
            "FS": _finite(res.get("FS")),
            "Q_ult": _finite(res.get("Q_ult")),
            "Q_all": _finite(res.get("Q_all")),
            "utilisation": _finite(res.get("utilisation")),
            "required_length": _finite(res.get("required_length")),
            "settlement_mm": _finite(res["settlement"]["s"] * 1000),
            "checks": {k: c["status"] for k, c in res["checks"].items()},
        }, indent=2))
    else:
        print(summary.headline(result))
        print(summary.results_text(result))
    if args.out:
        report_mod.export_report(args.out, result, "en")
        print(args.out, file=sys.stderr)
    return 0


def _require_bored(cfg: dict, command: str) -> None:
    if cfg.get("pile_type") == "socket":
        raise ValueError(f"'{command}' works on piles in soil (bored or driven); this "
                         "project is a rock-socketed pile.")


def cmd_study(args) -> int:
    from . import forms, study_plots
    from .i18n import TRANSLATIONS
    from .study import Study, to_csv, to_xlsx
    values = load_values(args.project)
    cfg = forms.to_config(values)
    _require_bored(cfg, "study")
    spec = forms.study_spec(values)
    variables = forms.study_variables(values)
    if not variables:
        raise ValueError("The project defines no study variables.")
    study = Study(cfg, variables, spec["method"], spec["n"], spec["seed"])
    study.run(progress=lambda done, total: print(f"\r{done} / {total}", end="",
                                                  file=sys.stderr, flush=True))
    print("", file=sys.stderr)
    print(study_plots.summary_text(study, TRANSLATIONS["en"]))
    if args.out:
        (to_xlsx if args.out.lower().endswith(".xlsx") else to_csv)(study, args.out)
        print(args.out, file=sys.stderr)
    return 0


def cmd_optimize_length(args) -> int:
    from .optimizer import optimize_length
    cfg = load_config(args.project)
    _require_bored(cfg, "optimize-length")
    res = optimize_length(cfg, L_bounds=(args.lmin, args.lmax), popsize=args.popsize,
                          maxiter=args.maxiter, seed=args.seed)
    print(json.dumps({"best_L": res["best_L"], "success": res["success"],
                      "message": res["message"], "nfev": res["nfev"]}, indent=2))
    return 0 if res["success"] else 1


def cmd_optimize_cost(args) -> int:
    from .optimizer import optimize_cost
    cfg = load_config(args.project)
    _require_bored(cfg, "optimize-cost")
    res = optimize_cost(cfg, L_bounds=(args.lmin, args.lmax), D_bounds=(args.dmin, args.dmax),
                        cost_a=args.cost_a, cost_b=args.cost_b, popsize=args.popsize,
                        maxiter=args.maxiter, seed=args.seed)
    print(json.dumps({"best_L": res["best_L"], "best_D": res["best_D"],
                      "best_cost": res["best_cost"], "success": res["success"],
                      "message": res["message"], "nfev": res["nfev"]}, indent=2))
    return 0 if res["success"] else 1


def cmd_example(args) -> int:
    from . import forms
    values = forms.defaults()
    values["pile_type"] = args.type
    values["title"] = forms.default_title(args.type)
    if args.type != "socket":
        values["study_variables"] = _example_study(values)
    Path(args.out).write_text(json.dumps(forms.project_file(values), indent=2,
                                         ensure_ascii=False), encoding="utf-8")
    print(args.out)
    return 0


COMMANDS = {
    "analyze": cmd_analyze, "run": cmd_analyze,
    "socket": lambda args: cmd_analyze(args, force_socket=True),
    "study": cmd_study, "optimize-length": cmd_optimize_length,
    "optimize-cost": cmd_optimize_cost, "example": cmd_example,
}


def main(argv=None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    if args.check:
        return 0 if check_environment() else 1
    gui = args.command in (None, "gui")
    if not check_environment(verbose=False, need_gui=gui):
        return 1
    if gui:
        from slipsurface.ui.app import run
        return run()
    try:
        return COMMANDS[args.command](args)
    except (ValueError, RuntimeError, OSError) as exc:
        # Impossible input is refused with a sentence worth reading (a pile
        # below the profile, a clay with no cu, an unreadable file); a
        # traceback would bury it, so only unexpected failures keep theirs.
        print(f"{APP_NAME}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
