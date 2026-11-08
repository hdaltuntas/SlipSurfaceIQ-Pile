"""SlipSurfaceIQ Pile — command-line analysis / optimization from a source checkout.

Installed from PyPI, the same commands are `slipsurface-pile …`.

Examples
--------
    python main.py --check                       # dependency check
    python main.py analyze project.pile.json     # analyse, print the results
    python main.py analyze project.pile.json -o report.pdf
    python main.py optimize-length project.pile.json
    python main.py optimize-cost project.pile.json --popsize 15 --maxiter 30
    python main.py example --type socket -o socket.pile.json

`python -m slipsurface.pile …` takes the same commands; both run
`slipsurface.pile.cli`.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slipsurface.pile.cli import (  # noqa: E402  (the path above comes first)
    build_parser, check_environment, load_config as _load_config, main,
)

__all__ = ["main", "build_parser", "check_environment", "_load_config"]

if __name__ == "__main__":
    sys.exit(main())
