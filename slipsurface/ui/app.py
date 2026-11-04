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
    QTextEdit, QFileDialog, QMessageBox, QSplitter, QFormLayout,
    QStatusBar, QDialog, QDialogButtonBox,
)

from slipsurface.pile.forms import (
    defaults, to_config, from_config, project_file, study_spec, study_variables,
)
from slipsurface.pile.engine import analyse
from slipsurface.pile.optimizer import optimize_length
from slipsurface.pile.plotting import Plotter, SocketPlotter, PLOT_KEYS, SOCKET_PLOT_KEYS
from slipsurface.pile.socket import analyse_socket
from slipsurface.pile import summary as summary_mod
from slipsurface.pile.study import Study
from slipsurface.pile import study as study_mod
from slipsurface.pile.i18n import t, warning_text, TRANSLATIONS
from slipsurface.pile import report as report_mod
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
        self.last_study = None
        self.last_socket = None
        self.interpret = None
        self._dark = False
        self.setStyleSheet(MODERN_STYLE)
        self._build_ui()
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.retranslate_ui()

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
        self.tabs = right
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setPlaceholderText("Analysis results will appear here…\n\nUse Data Entry to enter pile and soil data.")
        right.addTab(self.results, "Results")

        plot_w = QWidget()
        pl = QVBoxLayout(plot_w)
        top = QHBoxLayout()
        self.lbl_figure = QLabel("Figure")
        top.addWidget(self.lbl_figure)
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
        self.btn_study = QPushButton("Run study")
        self.btn_study.setStyleSheet(f"background: white; color: {ACCENT}; border: 1px solid {BORDER};")
        self.btn_study.clicked.connect(self.run_study)
        self.btn_socket = QPushButton("Analyse socket")
        self.btn_socket.setStyleSheet(f"background: white; color: {ACCENT}; border: 1px solid {BORDER};")
        self.btn_socket.clicked.connect(self.run_socket)
        self.btn_opt = QPushButton("Optimize L")
        self.btn_opt.setStyleSheet(f"background: white; color: {ACCENT}; border: 1px solid {BORDER};")
        self.btn_opt.clicked.connect(self.run_optimize_length)
        self.btn_interpret = QPushButton("Interpret")
        self.btn_interpret.setStyleSheet(f"background: white; color: {ACCENT}; border: 1px solid {BORDER};")
        self.btn_interpret.clicked.connect(self.open_interpret)
        self.btn_report = QPushButton("Export report…")
        self.btn_report.setStyleSheet(f"background: white; color: {ACCENT}; border: 1px solid {BORDER};")
        self.btn_report.clicked.connect(self.export_report)
        btn_row.addWidget(self.btn_data)
        btn_row.addWidget(self.btn_analyse)
        btn_row.addWidget(self.btn_socket)
        btn_row.addWidget(self.btn_study)
        btn_row.addWidget(self.btn_opt)
        btn_row.addWidget(self.btn_interpret)
        btn_row.addWidget(self.btn_report)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self._build_menu()
        self._build_toolbar()

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        self._actions = []

        def act(ic, key, slot):
            a = QAction(icon(ic), key, self)
            a.triggered.connect(slot)
            self._actions.append((a, key))
            return a

        act_new = act("new", "ui_new", self.new_project)
        act_open = act("open", "ui_open", self.open_project)
        act_save = act("save", "ui_save", self.save_project)
        act_data = act("settings", "ui_data_entry", self.open_data_entry)
        act_analyse = act("analyse", "run_analysis_button", self.run_analysis)
        act_socket = act("analyse", "run_socket_button", self.run_socket)
        act_study = act("analyse", "study_run", self.run_study)
        act_export_study = act("export", "ui_export_study", self.export_study)
        act_opt = act("optimize", "ui_optimize_length", self.run_optimize_length)
        act_interpret = act("interpret", "ui_interpret", self.open_interpret)
        act_refresh = act("refresh", "ui_refresh", self._update_plot)
        act_export = act("export", "ui_export_plot", self.export_plot)
        act_report = act("report", "report_action", self.export_report)
        act_help = act("help", "ui_help", self.show_help)
        act_lang = act("language", "ui_menu_language", self.toggle_language)

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
        self._actions.append((act_dark, "ui_dark_mode"))

        tb.addAction(act_new)
        tb.addAction(act_open)
        tb.addAction(act_save)
        tb.addSeparator()
        tb.addAction(act_data)
        tb.addAction(act_analyse)
        tb.addAction(act_socket)
        tb.addAction(act_study)
        tb.addAction(act_export_study)
        tb.addAction(act_opt)
        tb.addAction(act_interpret)
        tb.addSeparator()
        tb.addAction(act_refresh)
        tb.addAction(act_export)
        tb.addAction(act_report)
        tb.addSeparator()
        tb.addAction(act_dark)
        tb.addAction(act_lang)
        tb.addAction(act_help)

    def _build_menu(self):
        menu = self.menuBar()
        self._menus = []
        file_m = menu.addMenu("&File")
        self._menus.append((file_m, "ui_menu_file"))
        self._file_actions = [
            file_m.addAction("Open…", self.open_project),
            file_m.addAction("Save…", self.save_project),
        ]
        file_m.addSeparator()
        self._file_actions.append(file_m.addAction("Quit", self.close))
        self._file_keys = ["ui_open", "ui_save", "ui_quit"]
        file_m.addSeparator()
        self._file_actions.append(file_m.addAction("report", self.export_report))
        self._file_keys.append("report_action")
        lang_m = menu.addMenu("&Language")
        self._menus.append((lang_m, "ui_menu_language"))
        lang_m.addAction("English", lambda: self.set_language("en"))
        lang_m.addAction("Türkçe", lambda: self.set_language("tr"))
        view_m = menu.addMenu("&View")
        self._menus.append((view_m, "ui_menu_view"))
        view_m.addAction("Interpret", self.open_interpret)
        self._view_key_action = view_m.actions()[0]

    def retranslate_ui(self):
        L = self.lang
        self.btn_data.setText(t(L, "ui_data_entry"))
        self.btn_analyse.setText(t(L, "run_analysis_button"))
        self.btn_socket.setText(t(L, "run_socket_button"))
        self.btn_study.setText(t(L, "study_run"))
        self.btn_opt.setText(t(L, "ui_optimize_length"))
        self.btn_interpret.setText(t(L, "ui_interpret"))
        self.btn_report.setText(t(L, "report_action"))
        self.tabs.setTabText(0, t(L, "ui_results_tab"))
        self.tabs.setTabText(1, t(L, "ui_plots_tab"))
        self.lbl_figure.setText(t(L, "ui_figure"))
        self.results.setPlaceholderText(t(L, "ui_no_analysis"))
        for a, key in self._actions:
            a.setText(t(L, "ui_light_mode") if key == "ui_dark_mode" and self._dark
                      else t(L, key))
        for m, key in self._menus:
            m.setTitle(t(L, key))
        for a, key in zip(self._file_actions, self._file_keys):
            a.setText(t(L, key))
        self._view_key_action.setText(t(L, "ui_interpret"))
        if self.interpret is not None:
            self.interpret.retranslate(L)

    def set_language(self, lang: str):
        if lang == self.lang:
            return
        self.lang = lang
        self.retranslate_ui()
        self.status.showMessage(t(lang, "ui_language", code=lang))

    def open_data_entry(self):
        dlg = DataEntryDialog(self, self.lang, self.values)
        if dlg.exec() == QDialog.Accepted:
            self.values = dlg.collect()
            self.status.showMessage(t(self.lang, "ui_data_updated"))

    def run_analysis(self):
        try:
            cfg = to_config(self.values)
            result = analyse(cfg)
            self.last_result = result
            res = result.results if hasattr(result, "results") else {}
            L = self.lang
            lines = [
                t(L, "ui_results_header"),
                f"FS: {res.get('FS', '—')}",
                f"Q_ult: {res.get('Q_ult', '—')} kN",
                f"Q_all: {res.get('Q_all', '—')} kN",
                f"Utilisation: {res.get('utilisation', '—')}",
                f"Required length: {res.get('required_length', '—')} m",
                f"L: {getattr(result, 'L', '—')} m",
                f"D: {getattr(result, 'D', '—')} m",
            ]
            if hasattr(result, "warnings") and result.warnings:
                lines.append("\n" + t(L, "ui_warnings"))
                for w in result.warnings:
                    lines.append(f"  - {warning_text(L, w)}")
            try:
                full = json.dumps(vars(result), indent=2, default=str, ensure_ascii=False)[:8000]
                lines.append("\n" + t(L, "ui_full_data") + "\n" + full)
            except Exception:
                pass
            self.results.setPlainText("\n".join(lines))
            self.status.showMessage(t(L, "analysis_complete"))
            self.plot_combo.blockSignals(True)
            self.plot_combo.clear()
            self.plot_combo.addItems(PLOT_KEYS)
            self.plot_combo.blockSignals(False)
            self._update_plot()
            if self.interpret is not None:
                self.interpret.set_analysis(self.last_result, self.lang)
        except Exception as e:
            QMessageBox.critical(self, "Analysis error", f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

    def _update_plot(self):
        if not HAS_MPL:
            return
        key = self.plot_combo.currentText()
        try:
            self.fig.clear()
            if key in SOCKET_PLOT_KEYS:
                if self.last_socket is None:
                    return
                SocketPlotter(self.last_socket, self.lang).draw(key, self.fig)
            else:
                if not hasattr(self, "last_result") or self.last_result is None:
                    return
                Plotter(self.last_result, self.lang).draw(key, self.fig)
            self.canvas.draw()
        except Exception as exc:
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, str(exc), ha="center", va="center")
            self.canvas.draw()

    def run_socket(self):
        L = self.lang
        try:
            socket = analyse_socket(to_config(self.values))
            self.last_socket = socket
            lines = [
                t(L, "ui_socket_header"),
                summary_mod.socket_headline(socket, L),
                "",
                summary_mod.socket_text(socket, L),
            ]
            if socket.warnings:
                lines.append("\n" + t(L, "ui_warnings"))
                for w in socket.warnings:
                    lines.append(f"  - {warning_text(L, w)}")
            self.results.setPlainText("\n".join(lines))
            self.status.showMessage(t(L, "socket_complete"))
            self.plot_combo.blockSignals(True)
            self.plot_combo.clear()
            self.plot_combo.addItems(SOCKET_PLOT_KEYS)
            self.plot_combo.blockSignals(False)
            self._update_plot()
        except Exception as e:
            QMessageBox.critical(self, t(L, "run_socket_button"),
                                 f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

    def run_study(self):
        L = self.lang
        spec = study_spec(self.values)
        variables = study_variables(self.values)
        if not variables:
            QMessageBox.warning(self, t(L, "study_run"), t(L, "study_no_vars"))
            return
        try:
            cfg = to_config(self.values)
            study = Study(cfg, variables, spec["method"], spec["n"], spec["seed"])

            def progress(done, total):
                self.status.showMessage(t(L, "study_progress", done=done, total=total))
                QApplication.processEvents()

            study.run(progress=progress)
            self.last_study = study
            s = study.summary
            lines = [t(L, "ui_study_header"),
                     t(L, "st_info", method=study.method, n=s.get("n_total", 0),
                       ok=s.get("n_ok", 0))]
            rel = s.get("reliability") or {}
            if rel:
                lines.append("\n" + t(L, "st_rel_title"))
                for key, r in rel.items():
                    label = TRANSLATIONS.get(L, TRANSLATIONS["en"]).get("out_" + key, key)
                    lines.append(f"  {label}: pf = {r.get('pf', float('nan')):.4f}, "
                                 f"β = {r.get('beta', float('nan')):.2f}")
            stats = s.get("stats") or {}
            if stats:
                lines.append("\n" + t(L, "st_stats_title"))
                for key, st in stats.items():
                    lines.append(f"  {key}: mean {st['mean']:.2f}, std {st['std']:.2f}, "
                                 f"p5 {st['p5']:.2f}, p95 {st['p95']:.2f} {st.get('unit', '')}")
            self.results.setPlainText("\n".join(lines))
            self.status.showMessage(t(L, "study_done", n=len(study.rows)))
        except Exception as e:
            QMessageBox.critical(self, t(L, "study_run"),
                                 t(L, "study_failed", e=f"{type(e).__name__}: {e}"))

    def export_study(self):
        L = self.lang
        if self.last_study is None or not self.last_study.rows:
            QMessageBox.information(self, t(L, "ui_export_study"), t(L, "study_no_data"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t(L, "ui_export_study"), "study.csv",
            f"{t(L, 'study_export_csv')} (*.csv);;{t(L, 'study_export_xlsx')} (*.xlsx)")
        if not path:
            return
        try:
            if path.lower().endswith(".xlsx"):
                study_mod.to_xlsx(self.last_study, path)
            else:
                study_mod.to_csv(self.last_study, path if path.lower().endswith(".csv")
                                 else path + ".csv")
                path = path if path.lower().endswith(".csv") else path + ".csv"
            self.status.showMessage(t(L, "ui_saved", path=path))
        except Exception as e:
            QMessageBox.critical(self, t(L, "ui_export_study"), str(e))

    def export_report(self):
        L = self.lang
        if not hasattr(self, "last_result") or self.last_result is None:
            QMessageBox.information(self, t(L, "report_action"), t(L, "ui_no_analysis"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t(L, "report_action"), "report.pdf",
            "PDF (*.pdf);;HTML (*.html);;Word (*.docx)")
        if not path:
            return
        try:
            self.status.showMessage(t(L, "report_running"))
            QApplication.processEvents()
            report_mod.export_report(path, self.last_result, L, study=self.last_study,
                                     socket=self.last_socket)
            self.status.showMessage(t(L, "ui_report_written", path=path))
        except Exception as e:
            QMessageBox.critical(self, t(L, "report_action"), str(e))

    def run_optimize_length(self):
        L = self.lang
        dlg = QDialog(self)
        dlg.setWindowTitle(t(L, "ui_opt_title"))
        form = QFormLayout(dlg)
        sp_pop = QSpinBox(); sp_pop.setRange(5, 50); sp_pop.setValue(10)
        sp_iter = QSpinBox(); sp_iter.setRange(5, 100); sp_iter.setValue(25)
        sp_lmin = QDoubleSpinBox(); sp_lmin.setRange(0.5, 100); sp_lmin.setValue(3.0)
        sp_lmax = QDoubleSpinBox(); sp_lmax.setRange(1.0, 200); sp_lmax.setValue(40.0)
        form.addRow(t(L, "ui_popsize"), sp_pop)
        form.addRow(t(L, "ui_maxiter"), sp_iter)
        form.addRow(t(L, "ui_lmin"), sp_lmin)
        form.addRow(t(L, "ui_lmax"), sp_lmax)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            cfg = to_config(self.values)
            self.status.showMessage(t(L, "running_analysis"))
            QApplication.processEvents()
            res = optimize_length(cfg, L_bounds=(sp_lmin.value(), sp_lmax.value()),
                                  popsize=sp_pop.value(), maxiter=sp_iter.value())
            best_L = res["best_L"]
            lines = [
                t(L, "ui_opt_header"),
                f"Best L: {best_L:.2f} m",
                f"Success: {res['success']}",
                f"Message: {res['message']}",
                f"Evaluations: {res['nfev']}",
            ]
            self.results.setPlainText("\n".join(lines))
            self.status.showMessage(t(L, "ui_best_l", L=best_L))
            self.values["L"] = best_L
        except Exception as e:
            QMessageBox.critical(self, "Optimization error", str(e))

    def new_project(self):
        self.values = defaults(self.lang)
        self.last_result = None
        self.last_study = None
        self.last_socket = None
        self.results.clear()
        self.status.showMessage(t(self.lang, "ui_new_project"))

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
            self, t(self.lang, "ui_help"),
            t(self.lang, "ui_help_text", app=APP_NAME, version=__version__))

    def open_interpret(self):
        if self.interpret is None or not self.interpret.isVisible():
            self.interpret = InterpretWindow(self, self.lang)
        if hasattr(self, "last_result") and self.last_result is not None:
            self.interpret.set_analysis(self.last_result, self.lang)
        else:
            self.interpret.summary.setPlainText(t(self.lang, "ui_no_analysis"))
        self.interpret.show()
        self.interpret.raise_()
        self.interpret.activateWindow()

    def toggle_dark(self):
        if not hasattr(self, "_dark"):
            self._dark = False
        self._dark = not self._dark
        if self._dark:
            self.setStyleSheet(DARK_STYLE)
        else:
            self.setStyleSheet(MODERN_STYLE)
        self.act_dark.setText(t(self.lang, "ui_light_mode" if self._dark else "ui_dark_mode"))
        self.status.showMessage(t(self.lang, "ui_dark_mode" if self._dark else "ui_light_mode"))

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
            self.last_study = None
            self.last_socket = None
            self.status.showMessage(t(self.lang, "ui_opened", path=path))
        except Exception as e:
            QMessageBox.critical(self, "Open error", str(e))

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save", "project.pile.json", "JSON (*.json)")
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(project_file(self.values), indent=2, ensure_ascii=False), encoding="utf-8")
            self.status.showMessage(t(self.lang, "ui_saved", path=path))
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
