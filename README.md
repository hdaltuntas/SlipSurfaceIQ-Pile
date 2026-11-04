# SlipSurfaceIQ Pile

**Axial pile capacity, group action, settlement and rock-socket analysis — desktop GUI**

Standalone desktop program extracted from SlipSurfaceIQ-Suite, with a light PySide6 interface styled after SlipSurfaceIQ-LE (Fusion style, fixed light palette, professional form-based inputs). The interface language is English; see **Help → About** in the app for the full list of technologies and the license.

## Features

- **Pile type chosen first** — *Bored pile* or *Rock-socketed pile*, in the window header and at the top of Data Entry; it sets which inputs are shown, which analysis **Analyse** runs, and which results, figures and report sections come back (saved in the project file as `pile_type`)
- Layered soil profile with stresses, shaft friction (α, β, λ methods, SPT), base resistance (Meyerhof, Vesić, Janbu)
- Group efficiency and block failure
- Single-pile and group settlement
- Rock-socketed piles
- Parametric / reliability studies
- **Automatic optimization** (differential evolution)
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
python main.py --check
python main.py analyze examples/example.pile.json
python main.py optimize-length examples/example.pile.json --popsize 12 --maxiter 25
python main.py optimize-cost examples/example.pile.json
```

Or check dependencies:

```bash
python main.py --check
```

## Project layout

- `main.py` — entry point
- `slipsurface/pile/` — core analysis engine (copied from Suite)
- `slipsurface/ui/app.py` — desktop GUI matching LE style
- `slipsurface/common/`, `slipsurface/versioning.py` — shared utilities

## Engineering disclaimer

Results depend on input parameters and methods selected. Always verify with engineering judgement. No warranty.

## Technologies

Python 3.10+; PySide6 (Qt) desktop GUI; NumPy and SciPy for the analysis and optimization; Matplotlib for figures; ReportLab (PDF), python-docx (Word) and openpyxl (XLSX) for report/export files.

License: GNU Affero General Public License v3 (AGPLv3) — see [LICENSE](LICENSE).
