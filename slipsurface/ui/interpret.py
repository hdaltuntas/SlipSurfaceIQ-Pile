"""Interpret window for SlipSurfaceIQ Pile — results and plots (LE-style)."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QTextEdit,
    QComboBox,
    QLabel,
    QToolBar,
    QStatusBar,
)

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    FigureCanvas = None
    Figure = None

from slipsurface.pile.plotting import Plotter, PLOT_KEYS
from slipsurface.pile.i18n import t


class InterpretWindow(QMainWindow):
    """Separate results window showing summary text and interactive plots."""

    def __init__(self, parent=None, lang: str = "en"):
        super().__init__(parent)
        self.lang = lang
        self.analysis = None
        self.setWindowTitle(t(lang, "ui_interpret_title"))
        self.resize(900, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Summary
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.tabs.addTab(self.summary, "Summary")

        # Plots
        plot_w = QWidget()
        pl = QVBoxLayout(plot_w)
        top = QHBoxLayout()
        self.lbl_figure = QLabel("Figure:")
        top.addWidget(self.lbl_figure)
        self.plot_combo = QComboBox()
        self.plot_combo.addItems(PLOT_KEYS)
        self.plot_combo.currentTextChanged.connect(self.refresh_plot)
        top.addWidget(self.plot_combo)
        top.addStretch()
        pl.addLayout(top)
        if HAS_MPL:
            self.fig = Figure(figsize=(7, 5), dpi=100)
            self.canvas = FigureCanvas(self.fig)
            pl.addWidget(self.canvas)
        else:
            self.canvas = QLabel("Matplotlib canvas unavailable")
            pl.addWidget(self.canvas)
        self.tabs.addTab(plot_w, "Plots")

        # Toolbar
        tb = QToolBar("Interpret")
        self.addToolBar(tb)
        self.act_refresh = QAction("Refresh", self)
        self.act_refresh.triggered.connect(self.refresh)
        tb.addAction(self.act_refresh)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.retranslate(lang)

    def retranslate(self, lang: str):
        self.lang = lang
        self.setWindowTitle(t(lang, "ui_interpret_title"))
        self.tabs.setTabText(0, t(lang, "ui_summary_tab"))
        self.tabs.setTabText(1, t(lang, "ui_plots_tab"))
        self.lbl_figure.setText(t(lang, "ui_figure") + ":")
        self.act_refresh.setText(t(lang, "ui_refresh"))

    def set_analysis(self, analysis, lang: str = "en"):
        self.analysis = analysis
        self.lang = lang
        self.refresh()

    def refresh(self):
        if self.analysis is None:
            self.summary.setPlainText(t(self.lang, "ui_no_analysis"))
            return
        # Summary text
        res = getattr(self.analysis, "results", self.analysis)
        lines = [
            "=== Pile Analysis Results ===",
            f"FS: {res.get('FS', '—')}",
            f"Q_ult: {res.get('Q_ult', '—')} kN",
            f"Q_all: {res.get('Q_all', '—')} kN",
            f"Utilisation: {res.get('utilisation', '—')}",
            f"Required length: {res.get('required_length', '—')} m",
        ]
        sett = res.get("settlement") or {}
        if isinstance(sett, dict):
            lines.append(f"Settlement: {sett.get('s', 0)*1000:.1f} mm")
        if res.get("warnings"):
            lines.append("\nWarnings:")
            for w in res["warnings"]:
                lines.append(f"  - {w}")
        self.summary.setPlainText("\n".join(lines))
        self.refresh_plot()
        self.status.showMessage(t(self.lang, "analysis_complete"))

    def refresh_plot(self):
        if not HAS_MPL or self.analysis is None:
            return
        key = self.plot_combo.currentText()
        try:
            self.fig.clear()
            Plotter(self.analysis, self.lang).draw(key, self.fig)
            self.canvas.draw()
        except Exception as exc:
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, str(exc), ha="center", va="center")
            self.canvas.draw()
