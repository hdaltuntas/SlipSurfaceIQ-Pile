"""Interpret window for SlipSurfaceIQ Pile — results and plots (LE-style)."""

from __future__ import annotations

from PySide6.QtCore import Qt
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


class InterpretWindow(QMainWindow):
    """Separate results window showing summary text and interactive plots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SlipSurfaceIQ Pile — Interpret")
        self.resize(900, 700)
        self.analysis = None
        self.lang = "en"

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
        top.addWidget(QLabel("Figure:"))
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
        act_refresh = QAction("Refresh", self)
        act_refresh.triggered.connect(self.refresh)
        tb.addAction(act_refresh)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def set_analysis(self, analysis, lang: str = "en"):
        self.analysis = analysis
        self.lang = lang
        self.refresh()

    def refresh(self):
        if self.analysis is None:
            self.summary.setPlainText("No analysis yet.")
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
        self.status.showMessage("Results updated")

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
