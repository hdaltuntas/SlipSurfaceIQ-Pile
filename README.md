# SlipSurfaceIQ Pile

**Axial pile capacity, group action, settlement and rock-socket analysis — desktop GUI**

Standalone desktop program extracted from SlipSurfaceIQ-Suite, with a light PySide6 interface styled after SlipSurfaceIQ-LE (Fusion style, fixed light palette, professional form-based inputs).

## Features

- Layered soil profile with stresses, shaft friction (α, β, λ methods, SPT), base resistance (Meyerhof, Vesić, Janbu)
- Group efficiency (Converse-Labarre, etc.) and block failure
- Single-pile and group settlement
- Rock-socketed piles (side shear correlations, base, length, elastic settlement)
- Parametric / reliability studies
- **Automatic optimization** (differential evolution): shortest safe length or minimum-cost design (L and D)
- PDF / HTML / DOCX reports
- English / Turkish interface
- Project save/load (.pile.json)

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

License: see LICENSE.
