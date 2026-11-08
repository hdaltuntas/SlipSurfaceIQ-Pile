# SlipSurfaceIQ Pile

**Axial capacity, group action, settlement and rock-socket design of piles: a Python library with a command line**

Extracted from SlipSurfaceIQ-Suite. The analysis needs only NumPy and SciPy; figures and the PDF calculation report are optional extras.

## Features

- **Bored, driven (high or low displacement) and rock-socketed piles**: the pile type (`pile_type` in the project file) decides which analysis runs and what comes back
- Layered soil profile with stresses, shaft friction (α, β, λ methods, SPT) and base resistance (Meyerhof, Vesić, Janbu)
- Group efficiency and block failure
- Single-pile and group settlement
- Seismic load case of the pile group
- Rock-socketed piles: side shear of every published correlation, base resistance, socket length and settlement, optionally counting the shaft friction of the overburden soil above the rock
- **Optimization** (differential evolution): shortest safe length, or cheapest safe length and diameter (cost = a·L·D² + b·L)
- Figures (section, profile, methods, length curve, group, settlement, seismic, socket) with the `[plot]` extra
- PDF calculation report with the `[report]` extra

## Installation

Python 3.10+.

```bash
pip install slipsurfaceiq-pile              # the analysis (numpy, scipy)
pip install "slipsurfaceiq-pile[plot]"      # + figures (matplotlib)
pip install "slipsurfaceiq-pile[report]"    # + the PDF report (matplotlib, reportlab)
pip install "slipsurfaceiq-pile[all]"       # everything
```

Without an extra, the analysis still works; asking for a figure or a report then fails with a message naming the extra to install.

## As a library

```python
from slipsurface import pile
from slipsurface.pile import summary

cfg = pile.default_config("bored")  # a complete starter configuration: "bored", "driven" or "socket"
cfg["pile"].update(D=1.0, L=18.0)   # diameter and length (m)
result = pile.analyse(cfg)

r = result.results
print(r["FS"], r["Q_all"], r["required_length"], r["settlement"]["s"])
print(summary.results_text(result))  # the full text report
```

The configuration is a nested dictionary (`pile`, `loading`, `group`, `groundwater`, `soil_profile`, `options`, `settlement`, `seismic`, `criteria`, `socket`); `slipsurface.pile.config.DEFAULT_CONFIG` lists every key. `pile.normalize(cfg)` completes a partial one with the defaults. Project files (`*.pile.json`, see `examples/`) hold the same dictionary:

```python
cfg = pile.load_config("examples/example.pile.json")
result = pile.analyse(cfg)
pile.save_config(cfg, "copy.pile.json")

best = pile.optimize_length(cfg, L_bounds=(5, 40))
print(best["best_L"], best["success"])
```

A rock-socketed pile: `pile.analyse_socket(pile.default_config("socket"))`.

Figures (`[plot]`) and the PDF report (`[report]`):

```python
from matplotlib.figure import Figure
from slipsurface.pile.plotting import Plotter, available_figures
from slipsurface.pile import report

fig = Figure(figsize=(8, 6))
Plotter(result, "en", "light").draw("section", fig)   # one of available_figures(result)
fig.savefig("section.png", dpi=150)

report.export_report("report.pdf", result, "en")
```

## Command line

Installed, the commands are `slipsurface-pile …` (also `python -m slipsurface.pile …`):

```bash
slipsurface-pile example --type driven -o my.pile.json   # starter project (bored, driven or socket)
slipsurface-pile analyze my.pile.json                    # follows the file's pile type; --json
slipsurface-pile analyze my.pile.json -o report.pdf      # needs the [report] extra
slipsurface-pile optimize-length my.pile.json --popsize 12 --maxiter 25
slipsurface-pile optimize-cost my.pile.json
slipsurface-pile --check                                 # Python and the dependencies
```

`slipsurface-pile <command> --help` lists each command's options. Optimization works on piles in soil (bored or driven).

## Development

```bash
python -m pip install -e ".[all]" pytest
python -m pytest -q
```

GitHub Actions runs the tests on Python 3.10 and 3.12 for every pull request and push to `main`, and builds the package and runs it from a clean install, with and without the extras.

### Releasing to PyPI

1. Once, on PyPI: add a *Trusted Publisher* for this repository with workflow `publish.yml` and environment `pypi`.
2. Raise `__version__` in `slipsurface/pile/__init__.py` (the only place it is written).
3. Tag and push: `git tag v2026.0.0 && git push origin v2026.0.0`. The `publish` workflow tests, builds and uploads.

## Project layout

- `slipsurface/pile/`: the package (`engine`, `socket`, `optimizer`, `project`, `summary`, `plotting`, `report`, `cli`)
- `slipsurface/` is a namespace shared by the programs of the suite; this package ships only `slipsurface.pile`, so the others can be installed beside it
- `examples/`: a project file

## Engineering disclaimer

Results depend on input parameters and methods selected. Always verify with engineering judgement. No warranty.

## License

GNU Affero General Public License v3 (AGPLv3): see [LICENSE](https://github.com/hdaltuntas/SlipSurfaceIQ-Pile/blob/main/LICENSE).
