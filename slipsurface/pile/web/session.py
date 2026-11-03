"""
The one working session the server keeps.

Kept apart from the HTTP layer: there is no network here, only "take a
dictionary of inputs, run the analysis, give the results back as a
dictionary". Everything the interface does can therefore be tested without
opening a socket.

A pile analysis, the length search included, takes a fraction of a second and
runs inline, as does the rock socket. A parametric or reliability study of a
few hundred samples does not: it runs in a thread, reports progress through
`state()`, and can be cancelled.
"""

from __future__ import annotations

import math
import threading
import traceback
from typing import Any, Dict, Optional

from .. import forms, render, report, study_plots, summary
from .. import study as study_mod
from ..engine import PileAnalysis
from ..errors import PileError
from ..i18n import TRANSLATIONS
from ..socket import SocketAnalysis
from ..study import Study
from .strings import shell_strings

#: Languages the interface offers
LANGS = ("en", "tr")


def _cell(value) -> str:
    """One table cell as text: numbers short, missing values empty."""
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        number = float(value)
        return "" if not math.isfinite(number) else f"{number:.4g}"
    return str(value)


class Session:
    """The single analysis session the server knows about."""

    def __init__(self, lang: str = "en", theme: str = "light"):
        self.lock = threading.Lock()
        self.lang = lang if lang in LANGS else "en"
        self.theme = theme
        self.analysis: Optional[PileAnalysis] = None
        self.socket: Optional[SocketAnalysis] = None
        self.values: Dict[str, Any] = {}
        self.study: Optional[Study] = None
        # background job
        self.job = "idle"                    # idle | running | done | error
        self.job_kind = ""
        self.job_error = ""
        self.job_detail = ""
        self.job_note = ""
        self.done = 0
        self.total = 0
        self.cancelled = False

    # ------------------------------------------------------------------ language
    def set_language(self, lang: str) -> str:
        with self.lock:
            self.lang = lang if lang in LANGS else "en"
            return self.lang

    def set_theme(self, theme: str) -> str:
        with self.lock:
            self.theme = "dark" if theme == "dark" else "light"
            return self.theme

    @property
    def t(self) -> dict:
        return TRANSLATIONS.get(self.lang, TRANSLATIONS["en"])

    def _explain(self, exc: Exception) -> str:
        """An input error in the user's language."""
        if isinstance(exc, PileError):
            return self.t.get(exc.key, exc.key).format(**exc.params)
        return str(exc)

    # ------------------------------------------------------------------ what the page loads with
    def meta(self) -> dict:
        """Everything the interface reads on startup: version, texts, schema."""
        from .. import APP_NAME, __version__
        return {
            "app": APP_NAME,
            "version": __version__,
            "language": self.lang,
            "languages": list(LANGS),
            "strings": shell_strings(self.lang),
            "schema": forms.schema(self.lang),
            "defaults": forms.defaults(self.lang),
            "figures": render.PLOT_KEYS,
            "socket_figures": render.SOCKET_PLOT_KEYS,
            "figure_labels": {key: self.t[f"fig_{key}"]
                              for key in render.PLOT_KEYS + render.SOCKET_PLOT_KEYS},
            "study_views": render.STUDY_VIEWS,
            "study_view_labels": {view: self.t[f"study_fig_{view}"]
                                  for view in render.STUDY_VIEWS},
        }

    # ------------------------------------------------------------------ job state
    def _begin(self, kind: str, total: int = 0) -> bool:
        with self.lock:
            if self.job == "running":
                return False
            self.job, self.job_kind = "running", kind
            self.job_error = self.job_detail = self.job_note = ""
            self.done, self.total, self.cancelled = 0, total, False
        return True

    def _finish(self, note: str = "") -> None:
        with self.lock:
            self.job, self.job_note = "done", note

    def _fail(self, exc: Exception) -> None:
        with self.lock:
            self.job = "error"
            self.job_error = f"{type(exc).__name__}: {exc}"
            self.job_detail = traceback.format_exc(limit=4)

    def cancel(self) -> dict:
        """Asks a running study to stop at the next sample."""
        with self.lock:
            self.cancelled = True
        return {"ok": True}

    def state(self) -> dict:
        with self.lock:
            return {
                "job": self.job,
                "kind": self.job_kind,
                "error": self.job_error,
                "detail": self.job_detail if self.job == "error" else "",
                "note": self.job_note,
                "done": self.done,
                "total": self.total,
                "has_analysis": self.analysis is not None,
                "has_socket": self.socket is not None,
                "has_study": self.study is not None and bool(self.study.rows),
            }

    # ================================================================== analysis
    def analyse(self, values: dict) -> dict:
        """Runs the pile analysis on the interface's values."""
        try:
            analysis = PileAnalysis(forms.to_config(values))
            analysis.run()
        except PileError as exc:
            raise ValueError(self._explain(exc)) from exc

        with self.lock:
            self.analysis = analysis
            # A study belongs to the inputs it was run on: analysing the same
            # inputs again (a change of language, which also relabels the
            # study variables) keeps it.
            if analysis.config != forms.to_config(self.values):
                self.study = None
            self.values = dict(values)

        res = analysis.results
        return {
            "ok": True,
            "cards": summary.cards(analysis, self.lang),
            "text": summary.results_text(analysis, self.lang),
            "headline": summary.headline(analysis, self.lang),
            "figures": render.available_figures(analysis),
            "warnings": summary.warnings(analysis, self.lang),
            "table": summary.method_table(analysis, self.lang),
            "Q_ult_net": res["Q_ult_net"],
            "FS": res["FS"],
            "required_length": res["required_length"],
        }

    def analyse_socket(self, values: dict) -> dict:
        """Runs the rock socket on the interface's values."""
        try:
            socket = SocketAnalysis(forms.to_config(values))
            socket.run()
        except PileError as exc:
            raise ValueError(self._explain(exc)) from exc
        with self.lock:
            self.socket = socket
        res = socket.results
        return {
            "ok": True,
            "cards": summary.socket_cards(socket, self.lang),
            "text": summary.socket_text(socket, self.lang),
            "headline": summary.socket_headline(socket, self.lang),
            "figures": list(render.SOCKET_PLOT_KEYS),
            "warnings": summary.socket_warnings(socket, self.lang),
            "table": summary.socket_table(socket, self.lang),
            "Ls_design": res["Ls_design"],
        }

    # ------------------------------------------------------------------ figures
    def plot(self, target: str, kind: str, output: str = "") -> bytes:
        """The requested figure as PNG."""
        if target == "study":
            with self.lock:
                study, theme = self.study, self.theme
            if study is None or not study.rows:
                raise ValueError(self.t["study_no_data"])
            outputs = study_plots.default_outputs(study)
            return render.figure_to_png(render.study_figure(
                study, kind, output or (outputs[0] if outputs else "FS"), self.lang, theme))

        if target == "socket":
            with self.lock:
                socket, theme = self.socket, self.theme
            if socket is None:
                raise ValueError(shell_strings(self.lang)["no_socket"])
            return render.figure_to_png(render.socket_figure(socket, kind, self.lang, theme))

        with self.lock:
            analysis, theme = self.analysis, self.theme
        if analysis is None:
            raise ValueError(shell_strings(self.lang)["no_results"])
        return render.figure_to_png(render.analysis_figure(analysis, kind, self.lang, theme))

    # ================================================================== study
    def study_variables(self, values: dict) -> dict:
        """Which inputs a study may vary, for the variable table's select."""
        return {"ok": True, "choices": forms.variable_choices(values, self.lang)}

    def start_study(self, values: dict) -> dict:
        """Starts the parametric / reliability study in the background."""
        spec = forms.study_spec(values)
        if not spec["variables"]:
            return {"ok": False, "error": self.t["study_no_vars"]}
        try:
            cfg = forms.to_config(values)
            PileAnalysis(cfg).run(with_length=False)   # the base case must be analysable
            variables = forms.study_variables(values)
            study = Study(cfg, variables, spec["method"], spec["n"], spec["seed"])
        except Exception as exc:
            return {"ok": False, "error": self.t["study_failed"].format(e=self._explain(exc))}

        if not self._begin("study"):
            return {"ok": False, "error": shell_strings(self.lang)["busy"]}
        with self.lock:
            self.values = dict(values)
            self.study = None
        threading.Thread(target=self._run_study, args=(study,), daemon=True).start()
        return {"ok": True}

    def _run_study(self, study: Study) -> None:
        def progress(done: int, total: int) -> None:
            with self.lock:
                self.done, self.total = done, total

        def cancel_asked() -> bool:
            with self.lock:
                return self.cancelled

        try:
            study.run(progress=progress, is_cancelled=cancel_asked)
            with self.lock:
                self.study = study
                cancelled = self.cancelled
            note = self.t["study_done"].format(n=len(study.rows))
            if cancelled:
                note = f"{note} {self.t['study_cancelled']}"
            self._finish(note)
        except Exception as exc:
            self._fail(exc)

    def study_payload(self) -> dict:
        """What the study view shows: summary text, figures and outputs."""
        with self.lock:
            study = self.study
        if study is None or not study.rows:
            return {"ok": False, "error": self.t["study_no_data"]}
        outputs = study_plots.default_outputs(study)
        return {
            "ok": True,
            "method": study.method,
            "n": len(study.rows),
            "text": study_plots.summary_text(study, self.t),
            "views": render.available_study_views(study),
            "outputs": [{"value": key, "label": self.t.get(f"out_{key}", key)}
                        for key in outputs],
            "table": self._study_table(study),
        }

    #: How many sampled rows the page is given; the full table is the CSV / XLSX
    TABLE_LIMIT = 500

    def _study_table(self, study: Study) -> dict:
        """The sampled table, trimmed to what a page can usefully show."""
        by_path = {variable.path: variable.label for variable in study.variables}
        columns = study_mod.table_columns(study)
        header = [self.t.get(f"out_{column}", by_path.get(column, column))
                  for column in columns]
        rows = [[_cell(row.get(column)) for column in columns]
                for row in study.rows[:self.TABLE_LIMIT]]
        return {"columns": header, "rows": rows, "truncated": len(study.rows) > len(rows)}

    def export_study(self, kind: str, path: str) -> str:
        """Writes the sampled table as CSV or XLSX and returns the path."""
        with self.lock:
            study = self.study
        if study is None or not study.rows:
            raise ValueError(self.t["study_no_data"])
        (study_mod.to_csv if kind == "csv" else study_mod.to_xlsx)(study, path)
        return path

    # ================================================================== report
    def report(self, fmt: str, path: str) -> str:
        """Writes the calculation report in the chosen format; returns the path.

        It carries whatever has been analysed: the pile, the rock socket, the
        study, or any of them together.
        """
        with self.lock:
            analysis, study, socket = self.analysis, self.study, self.socket
        if analysis is None and socket is None:
            raise ValueError(shell_strings(self.lang)["no_results"])
        writer = {"pdf": report.export_pdf, "html": report.export_html,
                  "docx": report.export_docx}.get(fmt)
        if writer is None:
            raise ValueError(f"unknown report format: {fmt}")
        study = study if (analysis is not None and study is not None and study.rows) else None
        writer(path, analysis, self.lang, study, socket)
        return path

    # ================================================================== project files
    def project_file(self, values: dict) -> dict:
        """What `Save` downloads."""
        return forms.project_file(values)

    def load_project(self, data: dict) -> dict:
        """Flat interface values from a project file, defaults filling the gaps."""
        if not isinstance(data, dict) or data.get("format") not in (None, *forms.READ_FORMATS):
            raise ValueError(shell_strings(self.lang)["bad_file"])
        return {"ok": True, "values": forms.from_config(data, forms.defaults(self.lang))}
