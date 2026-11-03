"""Desktop GUI for SlipSurfaceIQ Pile — Slide2-style light interface matching LE.

Form-based inputs generated from the pile schema, analysis via the core engine,
results display and PDF/HTML reports. Uses PySide6 Fusion + LE light palette.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPalette, QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QScrollArea,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QPushButton,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox,
    QSplitter,
    QStatusBar,
)

from slipsurface.pile.forms import schema, defaults, to_config, from_config, project_file
from slipsurface.pile.engine import analyse
from slipsurface.pile.optimizer import optimize_length, optimize_cost
from slipsurface.pile import APP_NAME, __version__


def light_palette() -> QPalette:
    """LE-style fixed light palette so CAD-like results stay readable."""
    pal = QPalette()
    c = {
        QPalette.Window: "#f0f0f0",
        QPalette.WindowText: "#000000",
        QPalette.Base: "#ffffff",
        QPalette.AlternateBase: "#f5f6f8",
        QPalette.ToolTipBase: "#ffffdc",
        QPalette.ToolTipText: "#000000",
        QPalette.Text: "#000000",
        QPalette.Button: "#f0f0f0",
        QPalette.ButtonText: "#000000",
        QPalette.BrightText: "#ff0000",
        QPalette.Highlight: "#3478d4",
        QPalette.HighlightedText: "#ffffff",
        QPalette.Link: "#2a7ad0",
        QPalette.PlaceholderText: "#8a8a8a",
    }
    for role, col in c.items():
        pal.setColor(role, QColor(col))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor("#9a9a9a"))
    return pal


class PileWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  {__version__}")
        self.resize(1200, 800)
        self.lang = "en"
        self.values = defaults(self.lang)
        self.fields: dict[str, QWidget] = {}
        self.soil_table: QTableWidget | None = None

        self._build_ui()
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — enter pile and soil data, then Analyse")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left: inputs
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        self.tabs = QTabWidget()
        input_layout.addWidget(self.tabs)
        self._build_tabs()
        btn_row = QHBoxLayout()
        self.btn_analyse = QPushButton("Analyse")
        self.btn_analyse.clicked.connect(self.run_analysis)
        self.btn_opt = QPushButton("Optimize L")
        self.btn_opt.clicked.connect(self.run_optimize_length)
        self.btn_report = QPushButton("Save Results…")
        self.btn_report.clicked.connect(self.generate_report)
        self.btn_report.setEnabled(False)
        btn_row.addWidget(self.btn_analyse)
        btn_row.addWidget(self.btn_opt)
        btn_row.addWidget(self.btn_report)
        btn_row.addStretch()
        input_layout.addLayout(btn_row)
        splitter.addWidget(input_widget)

        # Right: results
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setPlaceholderText("Analysis results will appear here…")
        splitter.addWidget(self.results)
        splitter.setSizes([500, 700])

        self._build_menu()

    def _build_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        open_act = QAction("&Open Project…", self)
        open_act.triggered.connect(self.open_project)
        save_act = QAction("&Save Project…", self)
        save_act.triggered.connect(self.save_project)
        file_menu.addAction(open_act)
        file_menu.addAction(save_act)
        file_menu.addSeparator()
        quit_act = QAction("&Quit", self)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        lang_menu = menu.addMenu("&Language")
        en_act = QAction("English", self)
        en_act.triggered.connect(lambda: self.set_language("en"))
        tr_act = QAction("Türkçe", self)
        tr_act.triggered.connect(lambda: self.set_language("tr"))
        lang_menu.addAction(en_act)
        lang_menu.addAction(tr_act)

    def set_language(self, lang: str):
        self.lang = lang
        # Rebuild tabs (simple approach)
        while self.tabs.count():
            self.tabs.removeTab(0)
        self.fields.clear()
        self.values = defaults(lang)
        self._build_tabs()
        self.status.showMessage(f"Language set to {lang}")

    def _build_tabs(self):
        sch = schema(self.lang)
        # Soil table first
        self._add_soil_tab(sch["soil"])
        for part in ("project", "pile", "options", "socket", "study"):
            if part in sch:
                self._add_part_tab(part, sch[part])

    def _add_soil_tab(self, soil_spec: dict):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        lay = QVBoxLayout(w)
        note = QLabel(soil_spec.get("note", ""))
        note.setWordWrap(True)
        lay.addWidget(note)
        self.soil_table = QTableWidget()
        cols = soil_spec["columns"]
        self.soil_table.setColumnCount(len(cols))
        self.soil_table.setHorizontalHeaderLabels([c["label"] for c in cols])
        rows = soil_spec.get("rows", [])
        self.soil_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, col in enumerate(cols):
                key = col["key"]
                val = row.get(key, "")
                self.soil_table.setItem(r, c, QTableWidgetItem(str(val)))
        lay.addWidget(self.soil_table)
        btn = QPushButton("+ Add Layer")
        btn.clicked.connect(self._add_soil_row)
        lay.addWidget(btn)
        scroll.setWidget(w)
        self.tabs.addTab(scroll, "Soil Profile")

    def _add_soil_row(self):
        if self.soil_table is None:
            return
        r = self.soil_table.rowCount()
        self.soil_table.insertRow(r)
        # simple defaults
        for c in range(self.soil_table.columnCount()):
            self.soil_table.setItem(r, c, QTableWidgetItem(""))

    def _add_part_tab(self, name: str, part: dict):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        lay = QVBoxLayout(w)
        for group in part.get("groups", []):
            gb = QGroupBox(group.get("title", name))
            form = QFormLayout(gb)
            for field in group.get("fields", []):
                widget = self._make_field(field)
                form.addRow(field.get("label", field["key"]), widget)
                self.fields[field["key"]] = widget
            lay.addWidget(gb)
        lay.addStretch()
        scroll.setWidget(w)
        self.tabs.addTab(scroll, name.capitalize())

    def _make_field(self, field: dict) -> QWidget:
        kind = field.get("kind", "number")
        key = field["key"]
        default = field.get("default")
        if kind == "select":
            cb = QComboBox()
            for opt in field.get("options", []):
                cb.addItem(str(opt.get("label", opt.get("value", ""))), opt.get("value"))
            # set default
            idx = cb.findData(default)
            if idx >= 0:
                cb.setCurrentIndex(idx)
            return cb
        if kind == "check":
            chk = QCheckBox()
            chk.setChecked(bool(default))
            return chk
        if kind in ("number", "float"):
            sp = QDoubleSpinBox()
            sp.setDecimals(field.get("dec", 2))
            sp.setRange(field.get("lo", -1e9), field.get("hi", 1e9))
            sp.setValue(float(default or 0))
            if field.get("step"):
                sp.setSingleStep(field["step"])
            return sp
        # text fallback
        le = QLineEdit(str(default or ""))
        return le

    def _collect_values(self) -> dict:
        vals = dict(self.values)
        for key, widget in self.fields.items():
            if isinstance(widget, QComboBox):
                vals[key] = widget.currentData()
            elif isinstance(widget, QCheckBox):
                vals[key] = widget.isChecked()
            elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                vals[key] = widget.value()
            elif isinstance(widget, QLineEdit):
                vals[key] = widget.text()
        # soil profile — respect column kinds
        if self.soil_table is not None:
            rows = []
            cols = schema(self.lang)["soil"]["columns"]
            for r in range(self.soil_table.rowCount()):
                row = {}
                has_data = False
                for c, col in enumerate(cols):
                    item = self.soil_table.item(r, c)
                    text = (item.text() if item else "").strip()
                    key = col["key"]
                    kind = col.get("kind", "text")
                    if kind == "number":
                        try:
                            row[key] = float(text) if text else 0.0
                        except ValueError:
                            row[key] = 0.0
                    else:
                        row[key] = text
                    if text:
                        has_data = True
                if has_data:
                    rows.append(row)
            vals["soil_profile"] = rows
        return vals

    def run_analysis(self):
        try:
            vals = self._collect_values()
            cfg = to_config(vals)
            result = analyse(cfg)
            self.last_result = result
            self.last_cfg = cfg
            # User-friendly summary
            lines = [
                "=== Analysis Results ===",
                f"Factor of Safety (FS): {getattr(result, 'FS', '—')}",
                f"Ultimate Capacity Q: {getattr(result, 'Q', '—')} kN",
                f"Required Length L_min: {getattr(result, 'L_min', '—')} m",
                f"Pile Length L: {getattr(result, 'L', '—')} m",
                f"Diameter D: {getattr(result, 'D', '—')} m",
            ]
            if hasattr(result, "warnings") and result.warnings:
                lines.append("\nWarnings:")
                for w in result.warnings:
                    lines.append(f"  - {w}")
            lines.append("\n--- Full data (for debugging) ---")
            try:
                full = json.dumps(vars(result), indent=2, default=str, ensure_ascii=False)[:8000]
                lines.append(full)
            except Exception:
                lines.append(str(result))
            self.results.setPlainText("\n".join(lines))
            self.btn_report.setEnabled(True)
            self.status.showMessage("Analysis complete")
        except Exception as e:
            QMessageBox.critical(self, "Analysis error", f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

    def run_optimize_length(self):
        try:
            vals = self._collect_values()
            cfg = to_config(vals)
            self.status.showMessage("Optimizing length (differential evolution)…")
            QApplication.processEvents()
            res = optimize_length(cfg, L_bounds=(3.0, 40.0), popsize=10, maxiter=25)
            best_L = res["best_L"]
            success = res["success"]
            lines = [
                "=== Length Optimization (Differential Evolution) ===",
                f"Best L: {best_L:.2f} m",
                f"Success: {success}",
                f"Message: {res['message']}",
                f"Function evaluations: {res['nfev']}",
            ]
            if success and "best_results" in res:
                br = res["best_results"]
                lines += [
                    f"FS: {br.get('FS', '—')}",
                    f"Utilisation: {br.get('utilisation', '—')}",
                    f"Group utilisation: {br.get('group', {}).get('utilisation', '—') if isinstance(br.get('group'), dict) else '—'}",
                ]
            self.results.setPlainText("\n".join(lines))
            self.status.showMessage(f"Optimization finished — best L = {best_L:.2f} m")
            # Optionally write the best L back into the L field if it exists
            if "L" in self.fields and isinstance(self.fields["L"], (QDoubleSpinBox, QSpinBox)):
                self.fields["L"].setValue(best_L)
        except Exception as e:
            QMessageBox.critical(self, "Optimization error", f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

    def generate_report(self):
        if not hasattr(self, "last_result"):
            QMessageBox.information(self, "Report", "Run an analysis first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save results summary", "pile_results.json", "JSON (*.json);;Text (*.txt)"
        )
        if not path:
            return
        try:
            data = {
                "config": self.last_cfg,
                "results": vars(self.last_result) if hasattr(self.last_result, "__dict__") else str(self.last_result),
            }
            Path(path).write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
            self.status.showMessage(f"Results saved to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open project", "", "Pile projects (*.pile.json *.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(data, dict) and "config" in data:
                self.values = from_config(data["config"])
            elif isinstance(data, dict):
                # flat values or project file
                self.values = data.get("values", data)
            else:
                raise ValueError("Unrecognized project format")
            # Rebuild UI so widgets get new defaults, then user can re-check
            self.set_language(self.lang)
            QMessageBox.information(self, "Open", "Project loaded. Please review the inputs and re-run analysis if needed.")
            self.status.showMessage(f"Opened {path}")
        except Exception as e:
            QMessageBox.critical(self, "Open error", f"{type(e).__name__}: {e}")

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save project", "project.pile.json", "JSON (*.json)")
        if not path:
            return
        try:
            vals = self._collect_values()
            data = project_file(vals)
            Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            self.status.showMessage(f"Saved {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))


def run(argv=None) -> int:
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("SlipSurface")
    app.setStyle("Fusion")
    app.setPalette(light_palette())

    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        print(text, file=sys.stderr)
        box = QMessageBox(QMessageBox.Critical, "Unexpected error", f"{exc_type.__name__}: {exc}")
        box.setDetailedText(text)
        box.exec()

    sys.excepthook = hook

    win = PileWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
