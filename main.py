"""SlipSurfaceIQ Pile — desktop GUI or command-line analysis / optimization.

Examples
--------
    python main.py                          # open the GUI
    python main.py --check                  # dependency check
    python main.py analyze project.json     # run analysis and print summary
    python main.py optimize-length project.json
    python main.py optimize-cost project.json --popsize 15 --maxiter 30
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = {
    "PySide6": "PySide6",
    "numpy": "numpy",
    "scipy": "scipy",
    "matplotlib": "matplotlib",
    "reportlab": "reportlab",
}
MIN_PYTHON = (3, 10)


def check_environment(verbose: bool = True) -> bool:
    ok = True
    if sys.version_info < MIN_PYTHON:
        print(f"[ERROR] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required (found {sys.version.split()[0]}).")
        ok = False
    missing = []
    for mod, pip_name in REQUIRED.items():
        try:
            m = importlib.import_module(mod)
            if verbose:
                print(f"  {mod:12s} {getattr(m, '__version__', '?')}")
        except ImportError:
            missing.append(pip_name)
    if missing:
        ok = False
        print("[ERROR] Missing package(s): " + ", ".join(missing))
        print(f"        Install:  {Path(sys.executable).name} -m pip install -r {ROOT / 'requirements.txt'}")
    if ok and verbose:
        print(f"  Python     {sys.version.split()[0]}  ({sys.executable})")
        print("Environment ready.")
    return ok


def _load_config(path: str):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    from slipsurface.pile.forms import to_config
    if isinstance(data, dict) and "config" in data:
        return data["config"]
    # assume flat project values or already a config
    if "pile" in data or "soil_profile" in data:
        return to_config(data)
    return data


def cmd_analyze(args) -> int:
    cfg = _load_config(args.project)
    from slipsurface.pile.engine import analyse
    result = analyse(cfg)
    res = result.results if hasattr(result, "results") else result
    print(json.dumps({
        "FS": res.get("FS"),
        "Q_ult": res.get("Q_ult"),
        "Q_all": res.get("Q_all"),
        "utilisation": res.get("utilisation"),
        "required_length": res.get("required_length"),
        "settlement_mm": (res.get("settlement") or {}).get("s", 0) * 1000
        if isinstance(res.get("settlement"), dict) else None,
    }, indent=2, default=str))
    return 0


def cmd_optimize_length(args) -> int:
    cfg = _load_config(args.project)
    from slipsurface.pile.optimizer import optimize_length
    res = optimize_length(
        cfg,
        L_bounds=(args.lmin, args.lmax),
        popsize=args.popsize,
        maxiter=args.maxiter,
        seed=args.seed,
    )
    print(json.dumps({
        "best_L": res["best_L"],
        "success": res["success"],
        "message": res["message"],
        "nfev": res["nfev"],
    }, indent=2))
    return 0 if res["success"] else 1


def cmd_optimize_cost(args) -> int:
    cfg = _load_config(args.project)
    from slipsurface.pile.optimizer import optimize_cost
    res = optimize_cost(
        cfg,
        L_bounds=(args.lmin, args.lmax),
        D_bounds=(args.dmin, args.dmax),
        cost_a=args.cost_a,
        cost_b=args.cost_b,
        popsize=args.popsize,
        maxiter=args.maxiter,
        seed=args.seed,
    )
    print(json.dumps({
        "best_L": res["best_L"],
        "best_D": res["best_D"],
        "best_cost": res["best_cost"],
        "success": res["success"],
        "message": res["message"],
        "nfev": res["nfev"],
    }, indent=2))
    return 0 if res["success"] else 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="SlipSurfaceIQ Pile",
        description="Axial pile capacity analysis and optimization",
    )
    p.add_argument("--check", action="store_true", help="check the dependencies and exit")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("gui", help="open the desktop GUI (default)")

    a = sub.add_parser("analyze", help="analyse a project file")
    a.add_argument("project", help="path to .json / .pile.json project")

    ol = sub.add_parser("optimize-length", help="find shortest safe length")
    ol.add_argument("project", help="path to project file")
    ol.add_argument("--lmin", type=float, default=3.0)
    ol.add_argument("--lmax", type=float, default=40.0)
    ol.add_argument("--popsize", type=int, default=12)
    ol.add_argument("--maxiter", type=int, default=30)
    ol.add_argument("--seed", type=int, default=42)

    oc = sub.add_parser("optimize-cost", help="minimise simple cost (L, D)")
    oc.add_argument("project", help="path to project file")
    oc.add_argument("--lmin", type=float, default=3.0)
    oc.add_argument("--lmax", type=float, default=40.0)
    oc.add_argument("--dmin", type=float, default=0.3)
    oc.add_argument("--dmax", type=float, default=1.5)
    oc.add_argument("--cost-a", type=float, default=1.0, dest="cost_a")
    oc.add_argument("--cost-b", type=float, default=0.1, dest="cost_b")
    oc.add_argument("--popsize", type=int, default=10)
    oc.add_argument("--maxiter", type=int, default=25)
    oc.add_argument("--seed", type=int, default=42)

    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.check:
        return 0 if check_environment() else 1
    if not check_environment(verbose=False):
        return 1

    if args.command == "analyze":
        return cmd_analyze(args)
    if args.command == "optimize-length":
        return cmd_optimize_length(args)
    if args.command == "optimize-cost":
        return cmd_optimize_cost(args)

    # default: GUI
    from slipsurface.ui.app import run
    return run()


if __name__ == "__main__":
    sys.exit(main())
