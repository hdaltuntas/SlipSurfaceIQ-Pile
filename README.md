# SlipSurfaceIQ Pile

**Axial pile capacity, group action, settlement and rock-socket analysis — desktop GUI**

Standalone desktop program extracted from SlipSurfaceIQ-Suite, with a PySide6 interface styled after SlipSurfaceIQ-LE (Fusion style, light and dark themes, form-based inputs). The interface language is English; see **Help → About** in the app for the full list of technologies and the license.

## Features

- **Pile type chosen first** — *Bored pile*, *Driven pile* (high or low displacement) or *Rock-socketed pile*, in the window header and at the top of Data Entry; it sets which inputs are shown, which analysis **Analyse** runs, and which results, figures and report sections come back (saved in the project file as `pile_type`)
- Layered soil profile with stresses, shaft friction (α, β, λ methods, SPT), base resistance (Meyerhof, Vesić, Janbu)
- Group efficiency and block failure
- Single-pile and group settlement
- Rock-socketed piles, optionally counting the shaft friction of the overburden soil above the rock
- Parametric / reliability studies, with their figures (distribution, scatter, sensitivities, one-at-a-time sweeps) in the main window for any output
- **Automatic optimization** (differential evolution): shortest safe length, or cheapest safe length and diameter (cost = a·L·D² + b·L)
- **Interactive plots** (section, profile, methods, length curve, group, settlement, seismic)
- LE-style desktop GUI (Fusion, light palette, menus, toolbar, docks)
- Separate **Interpret** window for results and plots
- Project save/load (.pile.json) with Save As, Open Recent and an unsaved-changes prompt
- Data Entry with a live, to-scale preview of the section, unit-aware fields that show only the inputs the chosen methods use, and soil-table checks that mark invalid cells in red
- Headline result cards (capacity, checks, length / socket length, settlement)
- Analysis, studies and optimization run in the background with progress and Cancel

## Installation and start-up

Python 3.10+ required. From the repository root:

```bash
python -m pip install -r requirements.txt
python main.py                  # GUI
python main.py --check          # check Python and the dependencies
```

The same commands work as `python -m slipsurface.pile …`:

```bash
python main.py example --type driven -o my.pile.json   # starter project (bored, driven or socket)
python main.py analyze examples/example.pile.json      # follows the file's pile type; --json, -o report.pdf
python main.py study examples/example.pile.json
python main.py optimize-length examples/example.pile.json --popsize 12 --maxiter 25
python main.py optimize-cost examples/example.pile.json
```

`python main.py <command> --help` lists each command's options. Study and optimization work on piles in soil (bored or driven). Reports are PDF.

## Development

```bash
python -m pip install pytest
python -m pytest -q          # engine, forms and headless GUI tests (Qt offscreen)
```

GitHub Actions runs the tests on Python 3.10 and 3.12 for every pull request and push to `main`.

## Project layout

- `main.py` — entry point (same command line as `python -m slipsurface.pile`, see `slipsurface/pile/cli.py`)
- `slipsurface/pile/` — core analysis engine (copied from Suite)
- `slipsurface/ui/app.py` — desktop GUI matching LE style
- `slipsurface/common/`, `slipsurface/versioning.py` — shared utilities

## Engineering disclaimer

Results depend on input parameters and methods selected. Always verify with engineering judgement. No warranty.

## Technologies

Python 3.10+; PySide6 (Qt) desktop GUI; NumPy and SciPy for the analysis and optimization; Matplotlib for figures; ReportLab for the PDF report and openpyxl (XLSX) for study exports.

License: GNU Affero General Public License v3 (AGPLv3) — see [LICENSE](LICENSE).
