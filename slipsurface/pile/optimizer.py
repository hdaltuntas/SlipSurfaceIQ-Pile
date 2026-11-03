"""Automatic optimization for SlipSurfaceIQ Pile.

Uses scipy.optimize.differential_evolution to find:
- the shortest pile length that satisfies all checks (utilisation ≤ 1), or
- a minimum-cost design (simple cost = a·L·D² + b·L, subject to safety).

Length search in the engine is a linear scan; this is a global optimizer
that can also vary diameter and is more efficient for multi-variable cases.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import differential_evolution

from .engine import PileAnalysis, PileError
from .forms import to_config


def _safe_evaluate(cfg: Dict[str, Any], L: float, D: Optional[float] = None) -> Dict[str, Any]:
    """Run a single evaluation; return results or a penalty dict on failure."""
    c = {**cfg}
    c.setdefault("pile", {})
    c["pile"] = {**c["pile"], "L": float(L)}
    if D is not None:
        c["pile"]["D"] = float(D)
    try:
        analysis = PileAnalysis(c)
        res = analysis.run(with_length=False)
        return res
    except (PileError, ValueError, ZeroDivisionError, KeyError) as exc:
        return {"error": str(exc), "utilisation": 1e6, "utilisation_group": 1e6,
                "settlement": {"s": 1e6}, "FS": 0.0}


def optimize_length(
    base_config: Dict[str, Any],
    L_bounds: Tuple[float, float] = (2.0, 40.0),
    popsize: int = 15,
    maxiter: int = 40,
    seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """Find the shortest L that satisfies utilisation ≤ 1 (pile + group).

    Returns dict with best_L, best_results, success, message.
    """
    def objective(x: np.ndarray) -> float:
        L = float(x[0])
        res = _safe_evaluate(base_config, L)
        util = max(res.get("utilisation", 1e6),
                   res.get("group", {}).get("utilisation", 1e6) if isinstance(res.get("group"), dict) else 1e6)
        # Penalise unsafe designs heavily; among safe ones minimise L
        if util > 1.0 + 1e-6:
            return 1000.0 + L + 100.0 * (util - 1.0)
        return L

    bounds = [L_bounds]
    result = differential_evolution(
        objective,
        bounds,
        popsize=popsize,
        maxiter=maxiter,
        seed=seed,
        atol=0.05,
        tol=0.01,
        polish=True,
        workers=1,
    )
    best_L = float(result.x[0])
    best_res = _safe_evaluate(base_config, best_L)
    util = max(best_res.get("utilisation", 1e6),
               best_res.get("group", {}).get("utilisation", 1e6) if isinstance(best_res.get("group"), dict) else 1e6)
    success = util <= 1.0 + 1e-4
    return {
        "best_L": best_L,
        "best_results": best_res,
        "success": success,
        "fun": float(result.fun),
        "nfev": result.nfev,
        "message": "OK" if success else "No safe length found in bounds",
    }


def optimize_cost(
    base_config: Dict[str, Any],
    L_bounds: Tuple[float, float] = (2.0, 40.0),
    D_bounds: Tuple[float, float] = (0.3, 1.5),
    cost_a: float = 1.0,   # cost ~ a * L * D**2
    cost_b: float = 0.1,   # + b * L
    popsize: int = 12,
    maxiter: int = 30,
    seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """Minimise a simple cost subject to safety (utilisation ≤ 1).

    cost = cost_a * L * D**2 + cost_b * L
    """
    def objective(x: np.ndarray) -> float:
        L, D = float(x[0]), float(x[1])
        res = _safe_evaluate(base_config, L, D)
        util = max(res.get("utilisation", 1e6),
                   res.get("group", {}).get("utilisation", 1e6) if isinstance(res.get("group"), dict) else 1e6)
        cost = cost_a * L * D ** 2 + cost_b * L
        if util > 1.0 + 1e-6:
            return 1000.0 + cost + 50.0 * (util - 1.0)
        return cost

    bounds = [L_bounds, D_bounds]
    result = differential_evolution(
        objective,
        bounds,
        popsize=popsize,
        maxiter=maxiter,
        seed=seed,
        polish=True,
        workers=1,
    )
    best_L, best_D = float(result.x[0]), float(result.x[1])
    best_res = _safe_evaluate(base_config, best_L, best_D)
    util = max(best_res.get("utilisation", 1e6),
               best_res.get("group", {}).get("utilisation", 1e6) if isinstance(best_res.get("group"), dict) else 1e6)
    success = util <= 1.0 + 1e-4
    cost = cost_a * best_L * best_D ** 2 + cost_b * best_L
    return {
        "best_L": best_L,
        "best_D": best_D,
        "best_cost": cost,
        "best_results": best_res,
        "success": success,
        "fun": float(result.fun),
        "nfev": result.nfev,
        "message": "OK" if success else "No safe design found in bounds",
    }
