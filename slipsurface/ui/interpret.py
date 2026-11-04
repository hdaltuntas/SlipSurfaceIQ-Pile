"""Interpret window for SlipSurfaceIQ Pile — results and plots (LE-style).

Shows the results of the pile type the main window has selected: the bored
pile analysis, or the rock socket.
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QFont
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
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    FigureCanvas = None
    NavigationToolbar = None
    Figure = None

from slipsurface.pile.plotting import Plotter, SocketPlotter, SOCKET_PLOT_KEYS, \
    available_figures
from slipsurface.pile import summary as summary_mod
from slipsurface.pile.i18n import t, TRANSLATIONS


class InterpretWindow(QMainWindow):
    """Separate results window showing summary text and interactive plots."""

    def __init__(self, parent=None, lang: str = "en"):
        super().__init__(parent)
        self.lang = lang
        self.analysis = None
        self.pile_type = "bored"
        self.theme = "light"
        self.setWindowTitle(t(lang, "ui_interpret_title"))
        self.resize(1000, 760)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Summary
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        mono = QFont("DejaVu Sans Mono")
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSize(10)
        self.summary.setFont(mono)
        self.summary.setLineWrapMode(QTextEdit.NoWrap)
        self.tabs.addTab(self.summary, "Summary")

        # Plots
        plot_w = QWidget()
        pl = QVBoxLayout(plot_w)
        top = QHBoxLayout()
        self.lbl_figure = QLabel("Figure:")
        top.addWidget(self.lbl_figure)
        self.plot_combo = QComboBox()
        self.plot_combo.setMinimumWidth(320)
        self.plot_combo.currentIndexChanged.connect(self.refresh_plot)
        top.addWidget(self.plot_combo)
        top.addStretch()
        pl.addLayout(top)
        if HAS_MPL:
            self.fig = Figure(figsize=(7, 5), dpi=100)
            self.canvas = FigureCanvas(self.fig)
            pl.addWidget(NavigationToolbar(self.canvas, plot_w))
            pl.addWidget(self.canvas, 1)
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

    def set_analysis(self, analysis, lang: str = "en", pile_type: str = "bored",
                     theme: str = "light"):
        self.analysis = analysis
        self.lang = lang
        self.pile_type = pile_type
        self.theme = theme
        self._fill_combo()
        self.refresh()

    def _fill_combo(self):
        current = self.plot_combo.currentData()
        if self.pile_type == "socket":
            keys = list(SOCKET_PLOT_KEYS)
        else:
            keys = available_figures(self.analysis)
        names = TRANSLATIONS.get(self.lang, TRANSLATIONS["en"])
        self.plot_combo.blockSignals(True)
        self.plot_combo.clear()
        for key in keys:
            self.plot_combo.addItem(names.get(f"fig_{key}", key), key)
        self.plot_combo.setCurrentIndex(max(self.plot_combo.findData(current), 0))
        self.plot_combo.blockSignals(False)

    def refresh(self):
        if self.analysis is None:
            self.summary.setPlainText(t(self.lang, "ui_no_analysis"))
            if HAS_MPL:
                self.fig.clear()
                self.canvas.draw_idle()
            return
        if self.pile_type == "socket":
            text = summary_mod.socket_headline(self.analysis, self.lang) + "\n\n" + \
                summary_mod.socket_text(self.analysis, self.lang)
        else:
            text = summary_mod.headline(self.analysis, self.lang) + "\n\n" + \
                summary_mod.results_text(self.analysis, self.lang)
        self.summary.setPlainText(text)
        self.refresh_plot()
        self.status.showMessage(t(self.lang, "analysis_complete"))

    def refresh_plot(self, *_):
        if not HAS_MPL or self.analysis is None:
            return
        key = self.plot_combo.currentData()
        try:
            self.fig.clear()
            if key in SOCKET_PLOT_KEYS:
                SocketPlotter(self.analysis, self.lang, self.theme).draw(key, self.fig)
            elif key is not None:
                Plotter(self.analysis, self.lang, self.theme).draw(key, self.fig)
        except Exception as exc:
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.axis("off")
            ax.text(0.5, 0.5, t(self.lang, "ui_figure_error", e=exc), ha="center",
                    va="center", wrap=True)
        self.canvas.draw_idle()
