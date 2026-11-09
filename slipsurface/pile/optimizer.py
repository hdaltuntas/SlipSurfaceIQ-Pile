"""Integer-metre pile design with every active engineering check enforced.

The length-only search evaluates whole metres in ascending order. The cost
search uses constrained differential evolution with an integer length and a
continuous diameter. Feasibility is independent of the monetary units.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np
from scipy.optimize import NonlinearConstraint, differential_evolution

from .errors import PileError


FEASIBILITY_TOL = 1e-9


def governing_utilisation(res: Dict[str, Any]) -> float:
    """Largest utilisation of all active checks, including settlement.

    The public dispatcher supplies the envelope of independent borehole
    analyses. Invalid or incomplete evaluations cannot become feasible.
    """
    if res.get("error"):
        return float("inf")
    checks = res.get("checks")
    if "checks" in res:
        if not isinstance(checks, dict) or not checks:
            return float("inf")
        values = []
        for name, check in checks.items():
            if not isinstance(check, dict):
                return float("inf")
            if check.get("status") == "N/A":
                continue
            if check.get("status") not in ("OK", "NOT OK"):
                return float("inf")
            if any(isinstance(check.get(key), (int, float)) and math.isnan(check[key])
                   for key in ("actual", "allowable")):
                return float("inf")
            value = check.get("utilisation")
            if value is None and name == "settlement":
                allowable = check.get("allowable", 0.0)
                actual = check.get("actual")
                if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                           and math.isfinite(v) for v in (actual, allowable)):
                    return float("inf")
                value = actual / allowable if allowable > 0 else float("inf")
            elif value is None:
                return float("inf")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return float("inf")
            try:
                value = float(value)
            except (TypeError, ValueError):
                return float("inf")
            if not math.isfinite(value) or value < 0:
                return float("inf")
            if check.get("status") == "NOT OK":
                value = max(value, 1.0 + 2 * FEASIBILITY_TOL)
            values.append(value)
        return max(values, default=float("inf"))

    # Compatibility for callers passing old capacity-only result dictionaries.
    group = res.get("group") if isinstance(res.get("group"), dict) else {}
    seismic = res.get("seismic") if isinstance(res.get("seismic"), dict) else {}
    values = [res.get("utilisation", float("inf")),
              group.get("utilisation", float("inf")),
              seismic.get("utilisation", 0.0)]
    valid = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(v) and v >= 0 for v in values)
    return max(values) if valid else float("inf")


class Cancelled(Exception):
    """The user stopped the optimisation."""


def _check_cancelled(is_cancelled):
    if is_cancelled is not None and is_cancelled():
        raise Cancelled()


def _callback(is_cancelled, progress, maxiter):
    state = {"it": 0}

    def callback(*_args, **_kwargs):
        _check_cancelled(is_cancelled)
        state["it"] += 1
        if progress is not None:
            progress(min(state["it"], maxiter), maxiter)
        return False
    return callback


def _safe_evaluate(cfg: Dict[str, Any], L: float, D: Optional[float] = None) -> Dict[str, Any]:
    """Evaluate one geometry through the public, borehole-aware dispatcher."""
    from .analysis import analyse

    c = {**cfg, "pile": {**cfg.get("pile", {}), "L": float(L)}}
    if D is not None:
        c["pile"]["D"] = float(D)
    try:
        return analyse(c, with_length=False).results
    except (PileError, ValueError, ZeroDivisionError, KeyError, OverflowError) as exc:
        return {"error": str(exc), "utilisation": float("inf"), "checks": {}, "FS": 0.0}


def _prepare_config(base_config):
    from .project import normalize

    cfg = normalize(base_config)
    if cfg.get("pile_type") == "socket":
        raise ValueError(
            "Soil-pile optimisation does not support rock sockets; use analyse_socket."
        )
    return cfg


def _integer_bounds(bounds: Tuple[float, float]) -> Tuple[int, int]:
    lo, hi = map(float, bounds)
    if not all(math.isfinite(v) and v > 0 for v in (lo, hi)) or lo > hi:
        raise ValueError("Length bounds must be finite, positive and increasing.")
    lower, upper = math.ceil(lo), math.floor(hi)
    if lower > upper:
        raise ValueError("Length bounds contain no whole-metre candidate.")
    return lower, upper


def optimize_length(
    base_config: Dict[str, Any],
    L_bounds: Tuple[float, float] = (2.0, 40.0),
    popsize: int = 15,
    maxiter: int = 40,
    seed: Optional[int] = 42,
    atol: float = 0.05,
    tol: float = 0.01,
    mutation: float = 0.5,
    recombination: float = 0.7,
    polish: bool = True,
    progress: Optional[Callable[[int, int], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """Find the shortest feasible whole-metre length inside the given bounds.

    All integer candidates are considered in order, so layered, non-monotonic
    behaviour cannot be skipped. The historical differential-evolution
    options remain accepted for source compatibility; only the cost search
    uses them. Progress reports evaluated candidates / candidate count.
    """
    _check_cancelled(is_cancelled)
    cfg = _prepare_config(base_config)
    lo, hi = _integer_bounds(L_bounds)
    best_L, best_util = lo, float("inf")
    nfev = 0
    for L in range(lo, hi + 1):
        _check_cancelled(is_cancelled)
        res = _safe_evaluate(cfg, L)
        nfev += 1
        util = governing_utilisation(res)
        if util < best_util or nfev == 1:
            best_L, best_util = L, util
        if progress is not None:
            progress(nfev, hi - lo + 1)
        if util <= 1.0 + FEASIBILITY_TOL:
            best_L = L
            break
    _check_cancelled(is_cancelled)
    # Always re-evaluate the actual integer geometry returned to the caller.
    best_res = _safe_evaluate(cfg, best_L)
    nfev += 1
    success = governing_utilisation(best_res) <= 1.0 + FEASIBILITY_TOL
    return {
        "best_L": float(best_L), "best_results": best_res,
        "success": success, "feasible": success, "converged": True,
        "fun": float(best_L), "nfev": nfev,
        "message": "OK" if success else "No feasible whole-metre length in bounds",
        "length_increment": 1.0,
    }


def optimize_cost(
    base_config: Dict[str, Any],
    L_bounds: Tuple[float, float] = (2.0, 40.0),
    D_bounds: Tuple[float, float] = (0.3, 1.5),
    cost_a: float = 1.0,
    cost_b: float = 0.1,
    popsize: int = 12,
    maxiter: int = 30,
    seed: Optional[int] = 42,
    atol: float = 0.05,
    tol: float = 0.01,
    mutation: float = 0.5,
    recombination: float = 0.7,
    polish: bool = True,
    progress: Optional[Callable[[int, int], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """Minimise a·L·D² + b·L, with integer L and explicit safety constraints.

    success/feasible report rechecked engineering feasibility; converged
    independently reports numerical optimizer convergence. The normalized
    objective makes a change of monetary units immaterial.
    """
    _check_cancelled(is_cancelled)
    cfg = _prepare_config(base_config)
    lo, hi = _integer_bounds(L_bounds)
    dlo, dhi = map(float, D_bounds)
    if not all(math.isfinite(v) and v > 0 for v in (dlo, dhi)) or dlo > dhi:
        raise ValueError("Diameter bounds must be finite, positive and increasing.")
    a, b = float(cost_a), float(cost_b)
    if not all(math.isfinite(v) and v >= 0 for v in (a, b)) or max(a, b) <= 0:
        raise ValueError("Cost coefficients must be finite, nonnegative, and not both zero.")
    coefficient_scale = max(a, b)
    an, bn = a / coefficient_scale, b / coefficient_scale
    cost_scale = an * hi * dhi ** 2 + bn * hi
    cache = {}

    def evaluate(x):
        _check_cancelled(is_cancelled)
        key = (int(round(float(x[0]))), float(x[1]))
        if key not in cache:
            cache[key] = _safe_evaluate(cfg, *key)
        return cache[key]

    def objective(x: np.ndarray) -> float:
        _check_cancelled(is_cancelled)
        L, D = int(round(float(x[0]))), float(x[1])
        return (an * L * D ** 2 + bn * L) / cost_scale

    def constraint(x):
        value = governing_utilisation(evaluate(x))
        return value if math.isfinite(value) else 1e12

    result = differential_evolution(
        objective, [(lo, hi), (dlo, dhi)], integrality=[True, False],
        constraints=NonlinearConstraint(constraint, -np.inf, 1.0 + FEASIBILITY_TOL),
        popsize=popsize, maxiter=maxiter, seed=seed, atol=atol, tol=tol,
        mutation=mutation, recombination=recombination, polish=polish,
        workers=1, callback=_callback(is_cancelled, progress, maxiter),
    )
    _check_cancelled(is_cancelled)
    best_L, best_D = int(round(float(result.x[0]))), float(result.x[1])
    best_res = _safe_evaluate(cfg, best_L, best_D)
    success = (lo <= best_L <= hi and dlo <= best_D <= dhi
               and governing_utilisation(best_res) <= 1.0 + FEASIBILITY_TOL)
    cost = a * best_L * best_D ** 2 + b * best_L
    return {
        "best_L": float(best_L), "best_D": best_D, "best_cost": cost,
        "best_results": best_res, "success": success, "feasible": success,
        "converged": bool(result.success), "fun": cost,
        "normalized_objective": float(result.fun), "nfev": len(cache) + 1,
        "solver_nfev": result.nfev, "solver_message": str(result.message),
        "message": ("OK" if success else
                    "No feasible design found within bounds and search budget"),
        "length_increment": 1.0,
    }
