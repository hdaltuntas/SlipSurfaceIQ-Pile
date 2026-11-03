"""
Parametric and probabilistic (reliability) studies for SlipSurface IQ Pile.

A study is defined by a list of variables, each addressing one input of the
project configuration by a dotted path (``pile.L``, ``loading.Q``,
``soil_profile.1.cu`` …), and either

* a **range** (min, max)                      -> parametric / sensitivity, or
* a **distribution** (normal, lognormal, uniform; mean, CoV) -> reliability.

Sampling methods
    oat   one-at-a-time sweep over each range variable (the others at their
          project values)
    lhs   Latin hypercube (ranges as uniform distributions)
    mc    plain Monte Carlo

Every sample is a complete pile analysis, less the length search — a few
milliseconds —
so the runner works in one thread, reporting progress and honouring
cancellation between samples. Post-processing gives summary statistics,
Spearman rank sensitivities and, for each limit state, the probability of
failure with a 95 % confidence interval and the reliability index β.
"""

from __future__ import annotations

import copy
import csv
import math
from statistics import NormalDist
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .engine import PileAnalysis

DISTRIBUTIONS = ["normal", "lognormal", "uniform"]
METHODS = ["oat", "lhs", "mc"]

#: Outputs collected for every sample: (key, unit)
OUTPUTS = [
    ("Q_ult", "kN"), ("Q_ult_net", "kN"), ("Q_all", "kN"), ("FS", ""), ("utilisation", ""),
    ("Qg_all", "kN"), ("FS_group", ""), ("utilisation_group", ""), ("settlement", "mm"),
    ("T_pile", "kN"), ("utilisation_seismic", ""),
]

#: The limit states the reliability analysis counts:
#: key -> (output, capacity from the configuration, failure when above)
LIMIT_STATES = {
    "ls_pile": ("utilisation", lambda cfg: 1.0, True),
    "ls_group": ("utilisation_group", lambda cfg: 1.0, True),
    "ls_settlement": ("settlement", lambda cfg: float(cfg.get("criteria", {})
                                                      .get("s_allow", 40.0)), True),
    "ls_seismic": ("utilisation_seismic", lambda cfg: 1.0, True),
}

#: The inputs of each section a study may vary
PILE_KEYS = ["D", "L", "top"]
GROUP_KEYS = ["sx", "sy"]
OPTION_KEYS = ["delta_ratio"]
SEISMIC_KEYS = ["V", "M_B", "M_L", "cyclic"]
LAYER_KEYS = ["thickness", "gamma", "gamma_sat", "phi", "cu", "OCR", "N60", "E", "nu",
              "Cc", "Cr", "e0"]


# --------------------------------------------------------------------------- #
#  The inputs a study may address
# --------------------------------------------------------------------------- #

def available_variables(cfg: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Every input a study may vary, as (dotted path, group)."""
    out = [(f"pile.{key}", "pile") for key in PILE_KEYS]
    out.append(("loading.Q", "loading"))
    group = cfg.get("group") or {}
    if int(group.get("nx", 1)) > 1:
        out.append(("group.sx", "group"))
    if int(group.get("ny", 1)) > 1:
        out.append(("group.sy", "group"))
    out.append(("groundwater.depth", "water"))
    out += [(f"options.{key}", "options") for key in OPTION_KEYS]
    if (cfg.get("seismic") or {}).get("enabled"):
        out += [(f"seismic.{key}", "seismic") for key in SEISMIC_KEYS]
    for index, _ in enumerate(cfg.get("soil_profile") or []):
        out += [(f"soil_profile.{index}.{key}", "layer") for key in LAYER_KEYS]
    return out


def pretty_label(cfg: Dict[str, Any], path: str, L: Dict[str, str]) -> str:
    """A readable name for a dotted path, in the interface's language."""
    parts = path.split(".")
    if parts[0] == "soil_profile":
        index, key = int(parts[1]), parts[2]
        layers = cfg.get("soil_profile") or []
        name = layers[index]["name"] if index < len(layers) else f"#{index + 1}"
        return f"{name} · {L.get('var_' + key, key)}"
    group = {"pile": "grp_pile", "loading": "grp_loading", "group": "grp_group",
             "groundwater": "grp_water", "options": "grp_options",
             "seismic": "grp_seismic"}.get(parts[0])
    label = L.get(("var_E_" if parts[0] == "seismic" else "var_") + parts[-1], parts[-1])
    return f"{L.get(group, parts[0])} · {label}"


def get_value(cfg: Dict[str, Any], path: str) -> Any:
    node: Any = cfg
    for part in path.split("."):
        node = node[int(part)] if part.isdigit() else node[part]
    return node


def set_value(cfg: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    node: Any = cfg
    for part in parts[:-1]:
        node = node[int(part)] if part.isdigit() else node[part]
    last = parts[-1]
    if last.isdigit():
        node[int(last)] = value
    else:
        node[last] = value


# --------------------------------------------------------------------------- #
#  One variable
# --------------------------------------------------------------------------- #

class StudyVariable:
    """One input a study varies, by a range or by a distribution."""

    def __init__(self, path: str, label: str = "", mode: str = "range",
                 vmin: float = 0.0, vmax: float = 0.0, dist: str = "normal",
                 mean: float = 0.0, cov: float = 0.1, n_points: int = 5):
        self.path = path
        self.label = label or path
        self.mode = mode if mode in ("range", "dist") else "range"
        self.vmin, self.vmax = float(vmin), float(vmax)
        self.dist = dist if dist in DISTRIBUTIONS else "normal"
        self.mean = float(mean)
        self.cov = max(float(cov), 0.0)
        self.n_points = max(int(n_points), 2)

    @classmethod
    def from_dict(cls, spec: dict) -> "StudyVariable":
        return cls(path=str(spec.get("path", "")), label=str(spec.get("label", "")),
                   mode=str(spec.get("mode", "range")),
                   vmin=spec.get("min", 0.0) or 0.0, vmax=spec.get("max", 0.0) or 0.0,
                   dist=str(spec.get("dist", "normal")),
                   mean=spec.get("mean", 0.0) or 0.0, cov=spec.get("cov", 0.1) or 0.0,
                   n_points=spec.get("n_points", 5) or 5)

    def to_dict(self) -> dict:
        return {"path": self.path, "label": self.label, "mode": self.mode,
                "min": self.vmin, "max": self.vmax, "dist": self.dist,
                "mean": self.mean, "cov": self.cov, "n_points": self.n_points}

    @property
    def std(self) -> float:
        return abs(self.mean) * self.cov

    def sweep(self) -> np.ndarray:
        """The values of a one-at-a-time sweep."""
        if self.mode == "dist":
            spread = 2.0 * self.std
            return np.linspace(self.mean - spread, self.mean + spread, self.n_points)
        return np.linspace(self.vmin, self.vmax, self.n_points)

    def draw(self, u: np.ndarray) -> np.ndarray:
        """Values from uniform numbers in (0, 1) — the inverse transform."""
        u = np.clip(np.asarray(u, dtype=float), 1e-9, 1.0 - 1e-9)
        if self.mode == "range":
            return self.vmin + u * (self.vmax - self.vmin)
        if self.dist == "uniform":
            half = math.sqrt(3.0) * self.std
            return self.mean - half + u * 2.0 * half
        normal = np.array([NormalDist().inv_cdf(float(value)) for value in u])
        if self.dist == "lognormal":
            if self.mean <= 0 or self.std <= 0:
                return np.full_like(u, self.mean)
            sigma = math.sqrt(math.log(1.0 + (self.std / self.mean) ** 2))
            mu = math.log(self.mean) - 0.5 * sigma ** 2
            return np.exp(mu + sigma * normal)
        return self.mean + self.std * normal


# --------------------------------------------------------------------------- #
#  Sampling
# --------------------------------------------------------------------------- #

def sample(variables: Sequence[StudyVariable], method: str, n: int = 100,
           seed: int = 0) -> List[Dict[str, float]]:
    """The samples a study will analyse, one dictionary of values each."""
    if not variables:
        return []
    rng = np.random.default_rng(seed or None)
    if method == "oat":
        base = {v.path: (v.mean if v.mode == "dist" else 0.5 * (v.vmin + v.vmax))
                for v in variables}
        rows = []
        for variable in variables:
            for value in variable.sweep():
                row = dict(base)
                row[variable.path] = float(value)
                row["_swept"] = variable.path
                rows.append(row)
        return rows

    count = max(int(n), 2)
    if method == "lhs":
        grid = np.empty((count, len(variables)))
        for j in range(len(variables)):
            cuts = (np.arange(count) + rng.random(count)) / count
            grid[:, j] = rng.permutation(cuts)
    else:
        grid = rng.random((count, len(variables)))
    rows = []
    for i in range(count):
        row = {}
        for j, variable in enumerate(variables):
            row[variable.path] = float(variable.draw(np.array([grid[i, j]]))[0])
        rows.append(row)
    return rows


def evaluate(base_cfg: Dict[str, Any], values: Dict[str, Any]) -> Dict[str, Any]:
    """One sample: the configuration with the values set, analysed."""
    cfg = copy.deepcopy(base_cfg)
    for path, value in values.items():
        if path.startswith("_"):
            continue
        try:
            set_value(cfg, path, float(value))
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    row: Dict[str, Any] = {key: values[key] for key in values}
    try:
        analysis = PileAnalysis(cfg)
        res = analysis.run(with_length=False)
    except Exception as exc:                  # an impossible sample is recorded, not fatal
        row["error"] = f"{exc}"
        for key, _ in OUTPUTS:
            row[key] = float("nan")
        return row

    row.update({
        "Q_ult": res["Q_ult"], "Q_ult_net": res["Q_ult_net"], "Q_all": res["Q_all"],
        "FS": res["FS"], "utilisation": res["utilisation"],
        "Qg_all": res["group"]["Q_all"], "FS_group": res["group"]["FS"],
        "utilisation_group": res["group"]["utilisation"],
        "settlement": 1000.0 * res["settlement"]["s"],
        "T_pile": res["seismic"]["tension"]["T"] if res["seismic"] else float("nan"),
        "utilisation_seismic": res["seismic"]["utilisation"] if res["seismic"]
        else float("nan"),
        "error": "",
    })
    return row


# --------------------------------------------------------------------------- #
#  The study
# --------------------------------------------------------------------------- #

class Study:
    """A set of samples of one project, and what they say."""

    def __init__(self, config: Dict[str, Any], variables: Sequence[StudyVariable],
                 method: str = "lhs", n: int = 200, seed: int = 0):
        self.config = copy.deepcopy(config)
        self.variables = list(variables)
        self.method = method if method in METHODS else "lhs"
        self.n = max(int(n), 2)
        self.seed = int(seed)
        self.rows: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {}

    def run(self, progress: Optional[Callable[[int, int], None]] = None,
            is_cancelled: Optional[Callable[[], bool]] = None) -> "Study":
        samples = sample(self.variables, self.method, self.n, self.seed)
        total = len(samples)
        self.rows = []
        for index, values in enumerate(samples, start=1):
            if is_cancelled is not None and is_cancelled():
                break
            self.rows.append(evaluate(self.config, values))
            if progress is not None:
                progress(index, total)
        self.summary = summarize(self)
        return self


def _column(rows: List[Dict[str, Any]], key: str) -> np.ndarray:
    return np.array([float(row.get(key, float("nan")) or float("nan")) for row in rows])


def _ranks(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(x), dtype=float)
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """The rank correlation of two samples; nan when there is nothing to rank."""
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return float("nan")
    rx, ry = _ranks(x[mask]), _ranks(y[mask])
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def reliability(values: np.ndarray, capacity: float,
                failure_above: bool = True) -> Dict[str, float]:
    """The probability of failure, its 95 % interval and the reliability index.

    The interval is Wilson's, which behaves when no sample failed at all; β is
    the standard normal deviate of the probability.
    """
    good = values[np.isfinite(values)]
    n = int(good.size)
    if n == 0 or not math.isfinite(capacity):
        return {"n": 0, "n_fail": 0, "pf": float("nan"), "pf_lo": float("nan"),
                "pf_hi": float("nan"), "beta": float("nan")}
    failed = int((good > capacity).sum() if failure_above else (good < capacity).sum())
    pf = failed / n
    z = 1.959963985
    denom = 1.0 + z ** 2 / n
    centre = (pf + z ** 2 / (2 * n)) / denom
    half = z * math.sqrt(pf * (1 - pf) / n + z ** 2 / (4 * n ** 2)) / denom
    lo, hi = max(centre - half, 0.0), min(centre + half, 1.0)
    if pf <= 0:
        beta = float("inf")
    elif pf >= 1:
        beta = float("-inf")
    else:
        beta = -NormalDist().inv_cdf(pf)
    return {"n": n, "n_fail": failed, "pf": pf, "pf_lo": lo, "pf_hi": hi, "beta": beta}


def summarize(study: Study) -> Dict[str, Any]:
    """Statistics, sensitivities and probabilities of failure."""
    rows = [row for row in study.rows if not row.get("error")]
    out: Dict[str, Any] = {"n_total": len(study.rows), "n_ok": len(rows),
                           "stats": {}, "spearman": {}, "reliability": {}}
    if not rows:
        return out

    for key, unit in OUTPUTS:
        column = _column(rows, key)
        good = column[np.isfinite(column)]
        if good.size == 0:
            continue
        out["stats"][key] = {
            "n": int(good.size), "unit": unit, "mean": float(good.mean()),
            "std": float(good.std(ddof=1)) if good.size > 1 else 0.0,
            "min": float(good.min()), "max": float(good.max()),
            "p5": float(np.percentile(good, 5)), "p50": float(np.percentile(good, 50)),
            "p95": float(np.percentile(good, 95)),
        }

    if study.method != "oat":
        for key, _ in OUTPUTS:
            column = _column(rows, key)
            if not np.isfinite(column).any():
                continue
            out["spearman"][key] = {
                variable.path: spearman(_column(rows, variable.path), column)
                for variable in study.variables}

    for name, (output, capacity_of, above) in LIMIT_STATES.items():
        capacity = capacity_of(study.config)
        column = _column(rows, output)
        if not np.isfinite(column).any():
            continue
        out["reliability"][name] = {**reliability(column, capacity, above),
                                    "capacity": capacity, "output": output}
    return out


def table_columns(study: Study) -> List[str]:
    """The columns of the sampled table: the inputs, then the outputs."""
    return [variable.path for variable in study.variables] + \
        [key for key, _ in OUTPUTS] + ["error"]


def to_csv(study: Study, path: str) -> None:
    columns = table_columns(study)
    header = [variable.label for variable in study.variables] + \
        [key for key, _ in OUTPUTS] + ["error"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in study.rows:
            writer.writerow([row.get(column, "") for column in columns])


def to_xlsx(study: Study, path: str) -> None:
    """The sampled table as a spreadsheet; needs openpyxl."""
    try:
        from openpyxl import Workbook
    except ImportError as exc:               # pragma: no cover - the extra is optional
        raise RuntimeError("openpyxl is not installed (pip install openpyxl).") from exc
    columns = table_columns(study)
    book = Workbook()
    sheet = book.active
    sheet.title = "samples"
    sheet.append([variable.label for variable in study.variables]
                 + [key for key, _ in OUTPUTS] + ["error"])
    for row in study.rows:
        sheet.append([row.get(column, "") for column in columns])
    book.save(path)
