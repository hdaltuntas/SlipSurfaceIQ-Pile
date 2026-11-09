"""Analysis routing and the envelope of independently analysed borehole logs.

No layer properties are pooled between logs. A common geometry must pass
every active check in every log. A different log may govern each check.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict

from .errors import PileError, message
from .project import normalize


def _utilisation(check: dict) -> float:
    if check.get("status") == "N/A":
        return 0.0
    value = check.get("utilisation", float("inf"))
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or value < 0:
        return float("inf")
    if any(isinstance(check.get(k), (int, float)) and math.isnan(check[k])
           for k in ("actual", "allowable")):
        return float("inf")
    if check.get("status") not in ("OK", "NOT OK"):
        return float("inf")
    if check["status"] != "OK" and value <= 1:
        return float("inf")
    return value


def envelope_checks(results: Dict[str, dict]) -> Dict[str, dict]:
    """Copy the least favourable *complete check*, retaining its log identity."""
    keys = sorted({key for result in results.values() for key in result["checks"]})
    out = {}
    for key in keys:
        missing = {"status": "NOT OK", "actual": None, "allowable": None,
                   "utilisation": float("inf"), "reason": f"Missing {key} check"}
        candidates = [(name, result["checks"].get(key, missing))
                      for name, result in sorted(results.items())]
        active = [(name, check) for name, check in candidates if check["status"] != "N/A"]
        if not active:
            out[key] = {**copy.deepcopy(candidates[0][1]), "utilisation": 0.0,
                        "governing_borehole": None}
            continue
        name, check = max(active, key=lambda pair: _utilisation(pair[1]))
        utilisation = _utilisation(check)
        status = "OK" if (check["status"] == "OK" and math.isfinite(utilisation)
                          and utilisation <= 1.0 + 1e-9) else "NOT OK"
        out[key] = {**copy.deepcopy(check), "utilisation": utilisation, "status": status,
                    "governing_borehole": name}
    return out


def _governing(checks: dict) -> tuple:
    active = [(key, check) for key, check in checks.items() if check["status"] != "N/A"]
    if not active:
        return float("inf"), None, None
    key, check = max(active, key=lambda pair: _utilisation(pair[1]))
    return _utilisation(check), key, check.get("governing_borehole")


class BoreholeAnalysis:
    """All logs at the same geometry, with controlling checks and whole-metre design.

    ``analyses[name]`` exposes each complete analysis. ``results['checks']``
    contains the worst check of each kind and ``governing_borehole`` on each
    entry. The envelope is not a synthetic soil profile. Its length always
    means total head-to-tip pile length, including for rock sockets; each
    log has its own socket embedment below its rock surface.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = normalize(config)
        if not self.config.get("boreholes"):
            raise PileError("err_config", field="boreholes", reason="at least one log is required")
        self.pile_type = self.config["pile_type"]
        self.analyses: Dict[str, Any] = {}
        self.results: Dict[str, Any] = {}
        self._configs = {}
        for log in self.config["boreholes"]:
            cfg = {k: copy.deepcopy(v) for k, v in self.config.items() if k != "boreholes"}
            cfg["soil_profile"] = copy.deepcopy(log["soil_profile"])
            cfg["groundwater"] = copy.deepcopy(log["groundwater"])
            cfg["socket"].update(log.get("socket", {}))
            self._configs[log["name"]] = cfg

    def _run_log(self, name: str, cfg: dict):
        try:
            return analyse(cfg, with_length=False)
        except PileError as exc:
            raise PileError("err_borehole", name=name, reason=str(exc)) from exc

    def evaluate_length(self, length: float) -> dict:
        """Re-evaluate a common total head-to-tip length in every log."""
        if not math.isfinite(length) or length <= 0:
            raise ValueError("length must be finite and positive")
        by_log = {}
        for name, cfg in self._configs.items():
            if self.pile_type == "socket":
                socket_length = length - self.analyses[name].overburden
                if socket_length < 0:
                    raise PileError("err_borehole", name=name,
                                    reason="the common pile tip is above the rock surface")
                by_log[name] = self.analyses[name].check_length(socket_length)
                by_log[name]["total_length"] = float(length)
            else:
                trial = copy.deepcopy(cfg)
                trial["pile"]["L"] = float(length)
                by_log[name] = self._run_log(name, trial).results
        checks = envelope_checks(by_log)
        utilisation, key, name = _governing(checks)
        return {"L": float(length), "length_basis": "total_pile",
                "checks": checks, "boreholes": by_log,
                "utilisation": utilisation, "governing_check": key,
                "governing_borehole": name,
                "status": "OK" if math.isfinite(utilisation) and all(c["status"] in ("OK", "N/A")
                                       for c in checks.values()) else "NOT OK"}

    def _set_socket_length(self, total_length: float) -> None:
        """Make every complete child report describe the same total length."""
        for name, cfg in self._configs.items():
            trial = copy.deepcopy(cfg)
            trial["socket"]["Ls"] = total_length - self.analyses[name].overburden
            self.analyses[name] = self._run_log(name, trial)
            self.analyses[name].results["total_length"] = float(total_length)

    def run(self, with_length: bool = True) -> dict:
        self.analyses = {name: self._run_log(name, cfg) for name, cfg in self._configs.items()}
        is_socket = self.pile_type == "socket"
        geometry = self.config["socket" if is_socket else "pile"]
        length = geometry["Ls" if is_socket else "L"]
        if is_socket:
            if length == 0:
                # No common checked geometry exists until automatic sizing
                # has found a total length that passes every log.
                with_length = True
            else:
                # A supplied Ls specifies embedment at the deepest rock. The
                # other logs are checked with their actual, longer embedment.
                length += max(a.overburden for a in self.analyses.values())
                self._set_socket_length(length)
        by_log = {name: a.results for name, a in self.analyses.items()}
        checks = envelope_checks(by_log)
        utilisation, governing_check, governing_log = _governing(checks)
        warnings = [message("warn_borehole", name=name, reason=_warning(w))
                    for name, result in by_log.items() for w in result.get("warnings", [])]
        required = float("nan")
        design = None
        curve = []
        if with_length:
            if is_socket:
                from .socket import MAX_SOCKET
                lower = math.ceil(max(a.overburden + a.min_ratio * a.D
                                      for a in self.analyses.values()))
                upper = math.floor(min(a.overburden + MAX_SOCKET
                                       for a in self.analyses.values()))
            else:
                lower = math.ceil(self.config["criteria"]["L_min"])
                upper = math.floor(min(a.profile.depth - a.top for a in self.analyses.values()))
            for trial_length in range(max(lower, 1), upper + 1):
                trial = self.evaluate_length(trial_length)
                curve.append({k: trial[k] for k in
                              ("L", "utilisation", "governing_check", "governing_borehole", "status")})
                if trial["status"] == "OK":
                    required, design = float(trial_length), trial
                    break
            if design is None:
                warnings.append(message("warn_borehole_no_length", hi=upper))
        if is_socket and length == 0:
            if design is not None:
                length = required
                self._set_socket_length(required)
                by_log = {name: a.results for name, a in self.analyses.items()}
                checks = envelope_checks(by_log)
                utilisation, governing_check, governing_log = _governing(checks)
                warnings = [message("warn_borehole", name=name, reason=_warning(w))
                            for name, result in by_log.items()
                            for w in result.get("warnings", [])]
            else:
                # The individual auto-sized lengths differ. They cannot form
                # checks for a common geometry when the shared search failed.
                checks = {"shared_design": {"actual": None, "allowable": 1.0,
                    "utilisation": float("inf"), "status": "NOT OK",
                    "governing_borehole": None}}
                utilisation = float("inf")
                governing_check, governing_log = "shared_design", None
        self.results = {
            "envelope": True, "pile_type": self.pile_type, "L": float(length),
            "length_basis": "total_pile",
            "D": geometry["D"], "checks": checks, "boreholes": by_log,
            "utilisation": utilisation, "governing_check": governing_check,
            "governing_borehole": governing_log,
            "status": "OK" if math.isfinite(utilisation) and all(c["status"] in ("OK", "N/A") for c in checks.values())
                      else "NOT OK",
            "required_length": required, "length_curve": curve,
            "length_search_performed": bool(with_length),
            "design_checks": design["checks"] if design else None,
            "design_governing_borehole": design["governing_borehole"] if design else None,
            "design_governing_check": design["governing_check"] if design else None,
            "warnings": warnings,
        }
        if is_socket:
            self.results["total_length_design"] = required
            self.results["checked_socket_lengths"] = (
                {name: a.results["Ls_check"] for name, a in self.analyses.items()}
                if length > 0 else {})
            self.results["design_socket_lengths"] = (
                {name: required - a.overburden for name, a in self.analyses.items()}
                if design else {})
        return self.results


def _warning(warning) -> str:
    from .texts import warning_text
    return warning_text(warning)


def analyse(config: Dict[str, Any], with_length: bool = True):
    """Run the selected soil/socket analysis or the envelope of separate logs."""
    cfg = normalize(config)
    if cfg.get("boreholes"):
        analysis = BoreholeAnalysis(cfg)
        analysis.run(with_length=with_length)
    elif cfg["pile_type"] == "socket":
        from .socket import SocketAnalysis
        analysis = SocketAnalysis(cfg)
        analysis.run()
    else:
        from .engine import PileAnalysis
        analysis = PileAnalysis(cfg)
        analysis.run(with_length=with_length)
    return analysis
