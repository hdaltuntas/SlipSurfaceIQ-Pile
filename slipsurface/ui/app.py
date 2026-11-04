"""Desktop GUI for SlipSurfaceIQ Pile.

Card-based light interface: results and plots in the main window, all inputs
in a separate Data Entry dialog, dark mode toggle on the toolbar. Uses PySide6.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette, QAction, QIcon, QPixmap, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QDoubleSpinBox, QSpinBox, QComboBox, QPushButton,
    QTextEdit, QFileDialog, QMessageBox, QSplitter,
    QStatusBar, QDialog, QDialogButtonBox,
)

from slipsurface.pile.forms import defaults, to_config, from_config, project_file
from slipsurface.pile.engine import analyse
from slipsurface.pile.optimizer import optimize_length
from slipsurface.pile.plotting import Plotter, PLOT_KEYS
from slipsurface.pile import APP_NAME, __version__
from slipsurface.ui.interpret import InterpretWindow
from slipsurface.ui.icons import icon
from slipsurface.ui.data_entry import DataEntryDialog

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    FigureCanvas = None
    Figure = None

BG = "#f7f8fa"
CARD = "#ffffff"
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
TEXT = "#111827"
MUTED = "#6b7280"
BORDER = "#e5e7eb"

DARK_BG = "#111827"
DARK_CARD = "#1f2937"
DARK_TEXT = "#f9fafb"
DARK_MUTED = "#9ca3af"
DARK_BORDER = "#374151"

MODERN_STYLE = f"""
QMainWindow, QWidget {{ background: {BG}; color: {TEXT}; font-family: 'Segoe UI', system-ui, sans-serif; }}
QGroupBox {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    margin-top: 12px;
    padding: 16px;
    font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {MUTED}; }}
QPushButton {{
    background: {ACCENT};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {ACCENT_HOVER}; }}
QPushButton:disabled {{ background: #9ca3af; }}
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    background: white;
}}
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: transparent;
    padding: 10px 16px;
    margin-right: 4px;
    border-radius: 8px;
    color: {MUTED};
}}
QTabBar::tab:selected {{ background: {CARD}; color: {ACCENT}; font-weight: 600; }}
QTextEdit {{ border: 1px solid {BORDER}; border-radius: 12px; background: {CARD}; padding: 8px; }}
QStatusBar {{ background: {CARD}; border-top: 1px solid {BORDER}; }}
"""

DARK_STYLE = (MODERN_STYLE
              .replace(TEXT, DARK_TEXT)
              .replace(MUTED, DARK_MUTED)
              .replace(BORDER, DARK_BORDER)
              .replace(CARD, DARK_CARD)
              .replace(BG, DARK_BG))


def modern_palette() -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.WindowText, QColor(TEXT))
    pal.setColor(QPalette.Base, QColor(CARD))
    pal.setColor(QPalette.Text, QColor(TEXT))
    pal.setColor(QPalette.Button, QColor(CARD))
    pal.setColor(QPalette.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    return pal


class PileWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  {__version__}")
        self.resize(1280, 840)
        self.lang = "en"
        self.values = defaults(self.lang)
        self.last_result = None
        self.interpret = None
        self.setStyleSheet(MODERN_STYLE)
        self._build_ui()
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — enter pile and soil data, then Analyse")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("SlipSurfaceIQ  Pile")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #111827;")
        subtitle = QLabel("Axial capacity · Group · Settlement · Socket")
        subtitle.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(subtitle)
        root.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        # Main area is results only
        right = QTabWidget()
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setPlaceholderText("Analysis results will appear here…\n\nUse Data Entry to enter pile and soil data.")
        right.addTab(self.results, "Results")

        plot_w = QWidget()
        pl = QVBoxLayout(plot_w)
        top = QHBoxLayout()
        top.addWidget(QLabel("Figure"))
        self.plot_combo = QComboBox()
        self.plot_combo.addItems(PLOT_KEYS)
        self.plot_combo.currentTextChanged.connect(self._update_plot)
        top.addWidget(self.plot_combo)
        top.addStretch()
        pl.addLayout(top)
        if HAS_MPL:
            self.fig = Figure(figsize=(6, 4), dpi=100)
            self.canvas = FigureCanvas(self.fig)
            pl.addWidget(self.canvas)
        else:
            self.canvas = QLabel("Plots unavailable")
            pl.addWidget(self.canvas)
        right.addTab(plot_w, "Plots")
        splitter.addWidget(right)

        btn_row = QHBoxLayout()
        self.btn_data = QPushButton("Data Entry…")
        self.btn_data.clicked.connect(self.open_data_entry)
        self.btn_analyse = QPushButton("Analyse")
        self.btn_analyse.clicked.connect(self.run_analysis)
        self.btn_opt = QPushButton("Optimize L")
        self.btn_opt.setStyleSheet(f"background: white; color: {ACCENT}; border: 1px solid {BORDER};")
        self.btn_opt.clicked.connect(self.run_optimize_length)
        self.btn_interpret = QPushButton("Interpret")
        self.btn_interpret.setStyleSheet(f"background: white; color: {ACCENT}; border: 1px solid {BORDER};")
        self.btn_interpret.clicked.connect(self.open_interpret)
        btn_row.addWidget(self.btn_data)
        btn_row.addWidget(self.btn_analyse)
        btn_row.addWidget(self.btn_opt)
        btn_row.addWidget(self.btn_interpret)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self._build_menu()
        self._build_toolbar()

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(tb.iconSize())

        act_new = QAction(icon("new"), "New", self)
        act_new.triggered.connect(self.new_project)
        act_open = QAction(icon("open"), "Open", self)
        act_open.triggered.connect(self.open_project)
        act_save = QAction(icon("save"), "Save", self)
        act_save.triggered.connect(self.save_project)
        act_data = QAction(icon("settings"), "Data Entry", self)
        act_data.triggered.connect(self.open_data_entry)
        act_analyse = QAction(icon("analyse"), "Analyse", self)
        act_analyse.triggered.connect(self.run_analysis)
        act_opt = QAction(icon("optimize"), "Optimize L", self)
        act_opt.triggered.connect(self.run_optimize_length)
        act_interpret = QAction(icon("interpret"), "Interpret", self)
        act_interpret.triggered.connect(self.open_interpret)
        act_refresh = QAction(icon("refresh"), "Refresh Plot", self)
        act_refresh.triggered.connect(self._update_plot)
        act_export = QAction(icon("export"), "Export Plot", self)
        act_export.triggered.connect(self.export_plot)
        act_help = QAction(icon("help"), "Help", self)
        act_help.triggered.connect(self.show_help)
        act_lang = QAction(icon("language"), "Language", self)
        act_lang.triggered.connect(self.toggle_language)

        # Dark mode icon (custom)
        pm = QPixmap(24, 24)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setPen(QPen(QColor("#111827"), 2))
        p.setBrush(QColor("#1f2937"))
        p.drawEllipse(4, 4, 16, 16)
        p.setBrush(QColor("#fbbf24"))
        p.drawEllipse(10, 6, 8, 8)
        p.end()
        act_dark = QAction(QIcon(pm), "Dark mode", self)
        act_dark.setCheckable(True)
        act_dark.triggered.connect(self.toggle_dark)
        self.act_dark = act_dark

        tb.addAction(act_new)
        tb.addAction(act_open)
        tb.addAction(act_save)
        tb.addSeparator()
        tb.addAction(act_data)
        tb.addAction(act_analyse)
        tb.addAction(act_opt)
        tb.addAction(act_interpret)
        tb.addSeparator()
        tb.addAction(act_refresh)
        tb.addAction(act_export)
        tb.addSeparator()
        tb.addAction(act_dark)
        tb.addAction(act_lang)
        tb.addAction(act_help)

    def _build_menu(self):
        menu = self.menuBar()
        file_m = menu.addMenu("&File")
        file_m.addAction("Open…", self.open_project)
        file_m.addAction("Save…", self.save_project)
        file_m.addSeparator()
        file_m.addAction("Quit", self.close)
        lang_m = menu.addMenu("&Language")
        lang_m.addAction("English", lambda: self.set_language("en"))
        lang_m.addAction("Türkçe", lambda: self.set_language("tr"))
        view_m = menu.addMenu("&View")
        view_m.addAction("Interpret Window", self.open_interpret)

    def set_language(self, lang: str):
        if lang == self.lang:
            return
        self.lang = lang
        self.status.showMessage(f"Language: {lang}")

    def open_data_entry(self):
        dlg = DataEntryDialog(self, self.lang, self.values)
        if dlg.exec() == QDialog.Accepted:
            self.values = dlg.collect()
            self.status.showMessage("Data updated")

    def run_analysis(self):
        try:
            cfg = to_config(self.values)
            result = analyse(cfg)
            self.last_result = result
            res = result.results if hasattr(result, "results") else {}
            lines = [
                "=== Analysis Results ===",
                f"FS: {res.get('FS', '—')}",
                f"Q_ult: {res.get('Q_ult', '—')} kN",
                f"Q_all: {res.get('Q_all', '—')} kN",
                f"Utilisation: {res.get('utilisation', '—')}",
                f"Required length: {res.get('required_length', '—')} m",
                f"L: {getattr(result, 'L', '—')} m",
                f"D: {getattr(result, 'D', '—')} m",
            ]
            if hasattr(result, "warnings") and result.warnings:
                lines.append("\nWarnings:")
                for w in result.warnings:
                    lines.append(f"  - {w}")
            try:
                full = json.dumps(vars(result), indent=2, default=str, ensure_ascii=False)[:8000]
                lines.append("\n--- Full data ---\n" + full)
            except Exception:
                pass
            self.results.setPlainText("\n".join(lines))
            self.status.showMessage("Analysis complete")
            self._update_plot()
            if self.interpret is not None:
                self.interpret.set_analysis(self.last_result, self.lang)
        except Exception as e:
            QMessageBox.critical(self, "Analysis error", f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

    def _update_plot(self):
        if not HAS_MPL or not hasattr(self, "last_result"):
            return
        key = self.plot_combo.currentText()
        try:
            self.fig.clear()
            Plotter(self.last_result, self.lang).draw(key, self.fig)
            self.canvas.draw()
        except Exception as exc:
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, str(exc), ha="center", va="center")
            self.canvas.draw()

    def run_optimize_length(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Length optimization")
        form = QFormLayout(dlg)
        sp_pop = QSpinBox(); sp_pop.setRange(5, 50); sp_pop.setValue(10)
        sp_iter = QSpinBox(); sp_iter.setRange(5, 100); sp_iter.setValue(25)
        sp_lmin = QDoubleSpinBox(); sp_lmin.setRange(0.5, 100); sp_lmin.setValue(3.0)
        sp_lmax = QDoubleSpinBox(); sp_lmax.setRange(1.0, 200); sp_lmax.setValue(40.0)
        form.addRow("Population size", sp_pop)
        form.addRow("Max iterations", sp_iter)
        form.addRow("L min (m)", sp_lmin)
        form.addRow("L max (m)", sp_lmax)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            cfg = to_config(self.values)
            self.status.showMessage("Optimizing length…")
            QApplication.processEvents()
            res = optimize_length(cfg, L_bounds=(sp_lmin.value(), sp_lmax.value()),
                                  popsize=sp_pop.value(), maxiter=sp_iter.value())
            best_L = res["best_L"]
            lines = [
                "=== Length Optimization ===",
                f"Best L: {best_L:.2f} m",
                f"Success: {res['success']}",
                f"Message: {res['message']}",
                f"Evaluations: {res['nfev']}",
            ]
            self.results.setPlainText("\n".join(lines))
            self.status.showMessage(f"Best L = {best_L:.2f} m")
            self.values["L"] = best_L
        except Exception as e:
            QMessageBox.critical(self, "Optimization error", str(e))

    def new_project(self):
        self.values = defaults(self.lang)
        self.last_result = None
        self.results.clear()
        self.status.showMessage("New project")

    def toggle_language(self):
        self.set_language("tr" if self.lang == "en" else "en")

    def export_plot(self):
        if not HAS_MPL or not hasattr(self, "fig"):
            QMessageBox.information(self, "Export", "No plot available.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export plot", "plot.png", "PNG (*.png);;PDF (*.pdf)")
        if path:
            self.fig.savefig(path, dpi=150, bbox_inches="tight")
            self.status.showMessage(f"Plot saved to {path}")

    def show_help(self):
        QMessageBox.information(
            self, "Help",
            f"{APP_NAME} {__version__}\n\n"
            "1. Enter soil profile and pile data via Data Entry\n"
            "2. Analyse\n"
            "3. View results and plots, or open Interpret\n"
            "4. Optimize L for shortest safe length\n\n"
            "CLI: python main.py analyze|optimize-length ..."
        )

    def open_interpret(self):
        if self.interpret is None or not self.interpret.isVisible():
            self.interpret = InterpretWindow(self)
        if hasattr(self, "last_result"):
            self.interpret.set_analysis(self.last_result, self.lang)
        else:
            self.interpret.summary.setPlainText("Run an analysis first.")
        self.interpret.show()
        self.interpret.raise_()
        self.interpret.activateWindow()

    def toggle_dark(self):
        if not hasattr(self, "_dark"):
            self._dark = False
        self._dark = not self._dark
        if self._dark:
            self.setStyleSheet(DARK_STYLE)
            self.act_dark.setText("Light")
        else:
            self.setStyleSheet(MODERN_STYLE)
            self.act_dark.setText("Dark")
        self.status.showMessage("Dark mode" if self._dark else "Light mode")

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(data, dict) and "config" in data:
                self.values = from_config(data["config"])
            elif isinstance(data, dict) and ("format" in data or "pile" in data or "soil_profile" in data):
                self.values = from_config(data)
            else:
                self.values = data
            self.last_result = None
            self.status.showMessage(f"Opened {path}")
        except Exception as e:
            QMessageBox.critical(self, "Open error", str(e))

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save", "project.pile.json", "JSON (*.json)")
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(project_file(self.values), indent=2, ensure_ascii=False), encoding="utf-8")
            self.status.showMessage(f"Saved {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))


def run(argv=None) -> int:
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    app.setPalette(modern_palette())
    win = PileWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
