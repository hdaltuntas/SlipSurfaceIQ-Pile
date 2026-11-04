"""Command line interface."""

from __future__ import annotations

import argparse
import json
import sys

from . import APP_NAME, __version__


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="slipsurface-pile",
        description="Axial capacity of piles in layered ground: shaft friction and base "
                    "resistance by the \u03b1, \u03b2 and \u03bb methods and by Meyerhof, Vesi\u0107 and Janbu, "
                    "the pile's weight, group efficiency and block failure, the required "
                    "length, the settlement of a pile and of a group, rock-socketed piles "
                    "by every published side shear correlation, and parametric / "
                    "reliability studies.")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="analyse a project file and print the results")
    run.add_argument("project", help="path to a .pile / .json project file")
    run.add_argument("-o", "--out", default=None,
                     help="write a report here (.pdf / .html / .docx)")
    run.add_argument("--socket", action="store_true",
                     help="analyse the rock socket of the project as well")

    socket = sub.add_parser("socket", help="analyse the rock socket of a project file")
    socket.add_argument("project", help="path to a .pile / .json project file")
    socket.add_argument("-o", "--out", default=None,
                        help="write a report here (.pdf / .html / .docx)")

    study = sub.add_parser("study", help="run the study defined in a project file")
    study.add_argument("project", help="path to a .pile / .json project file")
    study.add_argument("-o", "--out", default=None, help="write the samples here (.csv / .xlsx)")

    example = sub.add_parser("example", help="write a starter project file")
    example.add_argument("-o", "--out", default="project.pile")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    try:
        return _dispatch(args.command, args)
    except (ValueError, RuntimeError, OSError) as exc:
        # The analysis refuses impossible input with a sentence worth reading
        # (a pile below the profile, a clay with no cu, an unreadable project
        # file). A traceback would bury it, so only unexpected failures keep
        # theirs.
        print(f"{APP_NAME}: {exc}", file=sys.stderr)
        return 1


def _example_study(values: dict) -> list:
    """Two study variables for the starter project, so `study` has something to do."""
    clay = values["soil_profile"][1]
    return [
        {"path": "loading.Q", "label": "Actions \u00b7 Q", "mode": "dist", "dist": "lognormal",
         "mean": values["Q"], "cov": 0.15, "min": 0, "max": 0, "n_points": 5},
        {"path": "soil_profile.1.cu", "label": "Soft clay \u00b7 cu", "mode": "dist",
         "dist": "lognormal", "mean": clay["cu"], "cov": 0.25, "min": 0, "max": 0,
         "n_points": 5},
    ]


def _load_values(path: str) -> dict:
    from . import forms
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and ("format" in data or "pile" in data or "soil_profile" in data):
        return forms.from_config(data)
    if isinstance(data, dict) and "config" in data:
        return forms.from_config(data["config"])
    return data


def _dispatch(command: str, args) -> int:
    """Runs one command; raises on anything that goes wrong."""
    from . import forms, report as report_mod, summary, study_plots
    from .engine import analyse
    from .socket import analyse_socket
    from .study import Study, to_csv, to_xlsx

    if command == "example":
        values = forms.defaults()
        values["study_variables"] = _example_study(values)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(forms.project_file(values), fh, indent=2, ensure_ascii=False)
        print(args.out)
        return 0

    values = _load_values(args.project)
    cfg = forms.to_config(values)

    if command == "run":
        result = analyse(cfg)
        print(summary.headline(result))
        print(summary.results_text(result))
        socket = None
        if args.socket:
            socket = analyse_socket(cfg)
            print()
            print(summary.socket_text(socket))
        if args.out:
            report_mod.export_report(args.out, result, "en", socket=socket)
            print(args.out)
        return 0

    if command == "socket":
        socket = analyse_socket(cfg)
        print(summary.socket_text(socket))
        if args.out:
            report_mod.export_report(args.out, analyse(cfg), "en", socket=socket)
            print(args.out)
        return 0

    # A study: analyse the pile first, so the report and the figures have
    # something to sit beside, then sample.
    analyse(cfg)
    spec = forms.study_spec(values)
    study = Study(cfg, forms.study_variables(values), spec["method"], spec["n"], spec["seed"])
    study.run(progress=lambda done, total: print(f"\r{done} / {total}", end="",
                                                  file=sys.stderr, flush=True))
    print("", file=sys.stderr)
    print(study_plots.summary_text(study, __import__("slipsurface.pile.i18n", fromlist=["TRANSLATIONS"]).TRANSLATIONS["en"]))
    if args.out:
        (to_xlsx if args.out.lower().endswith(".xlsx") else to_csv)(study, args.out)
        print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
