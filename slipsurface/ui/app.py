"""Desktop GUI for SlipSurfaceIQ Pile.

Card-based light interface: results and plots in the main window, all inputs
in a separate Data Entry dialog, dark mode toggle on the toolbar. Uses PySide6.

The pile type — bored pile or rock-socketed pile — is chosen first, in the
header of the window (and at the top of Data Entry). It decides which inputs
are asked for, which analysis the single Analyse command runs, and which
results, figures and report sections come back.
"""

from __future__ import annotations

import json
import math
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor, QPalette, QAction, QIcon, QPixmap, QPainter, QPen, QFont, \
    QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QDoubleSpinBox, QSpinBox, QComboBox, QPushButton,
    QTextEdit, QFileDialog, QMessageBox, QSplitter, QFormLayout,
    QStatusBar, QDialog, QDialogButtonBox, QButtonGroup,
)

from slipsurface.pile.forms import (
    defaults, to_config, from_config, project_file, study_spec, study_variables,
    PILE_TYPES, pile_type_of, default_title,
)
from slipsurface.pile.engine import analyse
from slipsurface.pile.errors import PileError
from slipsurface.pile.optimizer import optimize_length, Cancelled as OptCancelled
from slipsurface.pile.plotting import (
    Plotter, SocketPlotter, SOCKET_PLOT_KEYS, available_figures,
)
from slipsurface.pile.socket import analyse_socket
from slipsurface.pile import summary as summary_mod
from slipsurface.pile.study import Study
from slipsurface.pile import study as study_mod
from slipsurface.pile.i18n import t, TRANSLATIONS
from slipsurface.pile import report as report_mod
from slipsurface.pile import APP_NAME, __version__
from slipsurface.ui.interpret import InterpretWindow
from slipsurface.ui.icons import icon
from slipsurface.ui.data_entry import DataEntryDialog
from slipsurface.ui.cards import CardStrip
from slipsurface.ui.tasks import run_task, Cancelled

#: How many recently used projects the File menu remembers
MAX_RECENT = 8

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

#: Folder of the SVG icons, as a style-sheet url (forward slashes on every OS)
ICON_DIR = (Path(__file__).parent / "icons").as_posix()

#: Colour tokens of the two interface themes
LIGHT = dict(bg="#f7f8fa", card="#ffffff", input="#ffffff", text="#111827", muted="#6b7280",
             border="#e5e7eb", accent="#2563eb", accent_hover="#1d4ed8",
             disabled="#9ca3af", accent_soft="#eff6ff")
DARK = dict(bg="#111827", card="#1f2937", input="#111827", text="#f9fafb", muted="#9ca3af",
            border="#374151", accent="#60a5fa", accent_hover="#3b82f6",
            disabled="#4b5563", accent_soft="#1e3a5f")

# Kept for anything that imported the old module-level names
BG, CARD, ACCENT, ACCENT_HOVER = LIGHT["bg"], LIGHT["card"], LIGHT["accent"], \
    LIGHT["accent_hover"]
TEXT, MUTED, BORDER = LIGHT["text"], LIGHT["muted"], LIGHT["border"]


def make_style(c: dict) -> str:
    """The application style sheet for one set of colour tokens."""
    return f"""
QMainWindow, QDialog, QWidget {{ background: {c['bg']}; color: {c['text']};
    font-family: 'Segoe UI', system-ui, sans-serif; }}
QGroupBox {{
    background: {c['card']};
    border: 1px solid {c['border']};
    border-radius: 12px;
    margin-top: 12px;
    padding: 16px;
    font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {c['muted']}; }}
QPushButton {{
    background: {c['accent']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {c['accent_hover']}; }}
QPushButton:disabled {{ background: {c['disabled']}; color: {c['bg']}; }}
QPushButton[secondary="true"] {{
    background: {c['card']}; color: {c['accent']}; border: 1px solid {c['border']};
}}
QPushButton[secondary="true"]:hover {{ background: {c['accent_soft']}; }}
QPushButton[secondary="true"]:disabled {{ color: {c['disabled']}; }}
QPushButton[segment="true"] {{
    background: {c['card']}; color: {c['muted']}; border: 1px solid {c['border']};
    border-radius: 0; padding: 8px 16px;
}}
QPushButton[segment="true"]:checked {{ background: {c['accent']}; color: white;
    border-color: {c['accent']}; }}
QPushButton[segpos="first"] {{ border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
QPushButton[segpos="last"] {{ border-top-right-radius: 8px; border-bottom-right-radius: 8px; }}
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 6px 10px;
    background: {c['input']};
    color: {c['text']};
}}
QAbstractSpinBox {{ padding-right: 22px; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    subcontrol-origin: border; width: 20px; border: none; background: transparent;
}}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; margin-top: 3px; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; margin-bottom: 3px; }}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{
    background: {c['accent_soft']}; border-radius: 4px; }}
QAbstractSpinBox::up-arrow {{ image: url({ICON_DIR}/chevron-up.svg); width: 10px; height: 6px; }}
QAbstractSpinBox::down-arrow {{ image: url({ICON_DIR}/chevron-down.svg); width: 10px;
    height: 6px; }}
QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 8px;
    border: 2px solid {c['muted']}; background: {c['input']}; }}
QRadioButton::indicator:checked {{ border: 2px solid {c['accent']};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {c['accent']}, stop:0.55 {c['accent']}, stop:0.6 {c['input']}); }}
QComboBox QAbstractItemView {{ background: {c['card']}; color: {c['text']};
    selection-background-color: {c['accent']}; }}
QTableWidget {{ background: {c['card']}; alternate-background-color: {c['bg']};
    gridline-color: {c['border']}; color: {c['text']}; }}
QHeaderView::section {{ background: {c['bg']}; color: {c['muted']}; border: none;
    border-bottom: 1px solid {c['border']}; padding: 6px; }}
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: transparent;
    padding: 10px 16px;
    margin-right: 4px;
    border-radius: 8px;
    color: {c['muted']};
}}
QTabBar::tab:selected {{ background: {c['card']}; color: {c['accent']}; font-weight: 600; }}
QTextEdit {{ border: 1px solid {c['border']}; border-radius: 12px; background: {c['card']};
    color: {c['text']}; padding: 8px; }}
QStatusBar {{ background: {c['card']}; border-top: 1px solid {c['border']}; }}
QMenuBar, QMenu, QToolBar {{ background: {c['card']}; color: {c['text']}; }}
QMenu::item:selected, QMenuBar::item:selected {{ background: {c['accent']}; color: white; }}
QLabel, QRadioButton, QCheckBox {{ background: transparent; }}
QLabel#title {{ font-size: 22px; font-weight: 700; color: {c['text']}; }}
QLabel#muted {{ color: {c['muted']}; font-size: 13px; }}
QLabel#headline {{ color: {c['text']}; font-size: 13px; font-weight: 600; }}
QFrame#card {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 10px; }}
QLabel#cardTitle {{ color: {c['muted']}; font-size: 11px; }}
QLabel#cardValue {{ color: {c['text']}; font-size: 17px; font-weight: 700; }}
QLabel#cardSub {{ color: {c['muted']}; font-size: 11px; }}
"""


MODERN_STYLE = make_style(LIGHT)
DARK_STYLE = make_style(DARK)


def make_palette(c: dict) -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(c["bg"]))
    pal.setColor(QPalette.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.Base, QColor(c["card"]))
    pal.setColor(QPalette.AlternateBase, QColor(c["bg"]))
    pal.setColor(QPalette.Text, QColor(c["text"]))
    pal.setColor(QPalette.Button, QColor(c["card"]))
    pal.setColor(QPalette.ButtonText, QColor(c["text"]))
    pal.setColor(QPalette.ToolTipBase, QColor(c["card"]))
    pal.setColor(QPalette.ToolTipText, QColor(c["text"]))
    pal.setColor(QPalette.Highlight, QColor(c["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    return pal


def modern_palette() -> QPalette:
    return make_palette(LIGHT)


def figure_label(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(f"fig_{key}", key)


def figure_keys(pile_type: str, analysis=None) -> list:
    """The figures that belong to the pile type (and to the analysis just run)."""
    if pile_type == "socket":
        return list(SOCKET_PLOT_KEYS)
    return available_figures(analysis)


def error_box(parent, title: str, exc: Exception, lang: str) -> None:
    """Input problems in plain words; anything else with the traceback tucked
    away under 'Show Details…'."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    if isinstance(exc, PileError):
        box.setIcon(QMessageBox.Warning)
        box.setText(t(lang, "ui_input_error"))
        box.setInformativeText(str(exc))
    else:
        box.setIcon(QMessageBox.Critical)
        box.setText(f"{type(exc).__name__}: {exc}")
        box.setDetailedText(getattr(exc, "trace", "") or traceback.format_exc())
    box.exec()


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
        self._path = None          # the project file, once saved or opened
        self._dirty = False        # inputs changed since the last save
        self.settings = QSettings("SlipSurfaceIQ", "Pile")
        self.setStyleSheet(MODERN_STYLE)
        self._build_ui()
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.retranslate_ui()
        self._sync_pile_type()
        self._update_title()

    # ------------------------------------------------------------------ document
    def _update_title(self):
        name = Path(self._path).name if self._path else t(self.lang, "ui_untitled")
        self.setWindowTitle(f"{name}{'*' if self._dirty else ''} — {APP_NAME}  {__version__}")
        self.setWindowModified(self._dirty)

    def _set_dirty(self, dirty: bool = True):
        self._dirty = dirty
        self._update_title()

    def _confirm_discard(self) -> bool:
        """True when there is nothing unsaved, or the user is happy to lose it
        (or saved it just now)."""
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self, APP_NAME, t(self.lang, "ui_unsaved"),
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save_project()
        return answer == QMessageBox.Discard

    def closeEvent(self, event):
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def _recent(self) -> list:
        value = self.settings.value("recent", [])
        if isinstance(value, str):
            value = [value]
        return [p for p in (value or []) if Path(p).is_file()]

    def _remember(self, path: str):
        recent = [str(Path(path).resolve())] + [p for p in self._recent()
                                                 if p != str(Path(path).resolve())]
        self.settings.setValue("recent", recent[:MAX_RECENT])
        self._fill_recent_menu()

    def _fill_recent_menu(self):
        self.recent_menu.clear()
        recent = self._recent()
        for path in recent:
            self.recent_menu.addAction(Path(path).name, lambda p=path: self.open_project(p)) \
                .setToolTip(path)
        self.recent_menu.setEnabled(bool(recent))

    # ------------------------------------------------------------------ pile type
    @property
    def pile_type(self) -> str:
        return pile_type_of(self.values.get("pile_type"))

    @property
    def theme(self) -> str:
        return "dark" if self._dark else "light"

    def _sync_socket_ui(self):
        """Kept for callers of the old name."""
        self._sync_pile_type()

    def _sync_pile_type(self):
        """Inputs, commands and figures follow the pile type."""
        is_bored = self.pile_type == "bored"
        for value, button in self.type_buttons.items():
            button.blockSignals(True)
            button.setChecked(value == self.pile_type)
            button.blockSignals(False)
        for widget in self._bored_only:
            widget.setEnabled(is_bored)
            widget.setToolTip("" if is_bored else t(self.lang, "ui_bored_only"))
        self._fill_plot_combo()
        self._show_current_results()

    def set_pile_type(self, pile_type: str):
        pile_type = pile_type_of(pile_type)
        if pile_type == self.pile_type:
            return
        self.values["pile_type"] = pile_type
        self.values["title"] = default_title(pile_type, self.values.get("title", ""))
        self._set_dirty()
        self._sync_pile_type()
        self.status.showMessage(t(self.lang, "ui_pile_type_changed",
                                  name=t(self.lang, f"pile_type_{pile_type}")))

    def _current_analysis(self):
        return self.last_socket if self.pile_type == "socket" else self.last_result

    # ------------------------------------------------------------------ layout
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("SlipSurfaceIQ  Pile")
        title.setObjectName("title")
        header.addWidget(title)
        header.addSpacing(24)
        self.lbl_pile_type = QLabel()
        self.lbl_pile_type.setObjectName("muted")
        header.addWidget(self.lbl_pile_type)
        self.type_group = QButtonGroup(self)
        self.type_group.setExclusive(True)
        self.type_buttons = {}
        for index, value in enumerate(PILE_TYPES):
            button = QPushButton()
            button.setCheckable(True)
            button.setProperty("segment", "true")
            if index == 0:
                button.setProperty("segpos", "first")
            elif index == len(PILE_TYPES) - 1:
                button.setProperty("segpos", "last")
            button.setCursor(Qt.PointingHandCursor)
            self.type_group.addButton(button, index)
            self.type_buttons[value] = button
            button.toggled.connect(lambda on, v=value: on and self.set_pile_type(v))
            header.addWidget(button)
        header.setSpacing(0)
        header.addStretch()
        self.subtitle = QLabel()
        self.subtitle.setObjectName("muted")
        header.addWidget(self.subtitle)
        root.addLayout(header)

        self.headline = QLabel()
        self.headline.setObjectName("headline")
        root.addWidget(self.headline)
        self.cards = CardStrip(columns=6)
        root.addWidget(self.cards)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        right = QTabWidget()
        self.tabs = right
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        mono = QFont("DejaVu Sans Mono")
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSize(10)
        self.results.setFont(mono)
        self.results.setLineWrapMode(QTextEdit.NoWrap)
        right.addTab(self.results, "Results")

        plot_w = QWidget()
        pl = QVBoxLayout(plot_w)
        top = QHBoxLayout()
        self.lbl_figure = QLabel("Figure")
        top.addWidget(self.lbl_figure)
        self.plot_combo = QComboBox()
        self.plot_combo.setMinimumWidth(320)
        self.plot_combo.currentIndexChanged.connect(self._update_plot)
        top.addWidget(self.plot_combo)
        top.addStretch()
        pl.addLayout(top)
        if HAS_MPL:
            self.fig = Figure(figsize=(6, 4), dpi=100)
            self.canvas = FigureCanvas(self.fig)
            self.nav = NavigationToolbar(self.canvas, plot_w)
            pl.addWidget(self.nav)
            pl.addWidget(self.canvas, 1)
        else:
            self.canvas = QLabel("Plots unavailable")
            pl.addWidget(self.canvas)
        right.addTab(plot_w, "Plots")
        splitter.addWidget(right)

        btn_row = QHBoxLayout()

        def button(slot, secondary=True):
            b = QPushButton()
            if secondary:
                b.setProperty("secondary", "true")
            b.clicked.connect(slot)
            btn_row.addWidget(b)
            return b

        self.btn_data = button(self.open_data_entry, secondary=False)
        self.btn_analyse = button(self.run_analysis, secondary=False)
        self.btn_study = button(self.run_study)
        self.btn_opt = button(self.run_optimize_length)
        self.btn_interpret = button(self.open_interpret)
        self.btn_report = button(self.export_report)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self._build_menu()
        self._build_toolbar()
        self._bored_only = [self.btn_study, self.btn_opt, self.act_study,
                            self.act_export_study, self.act_opt]

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        self._actions = []

        def act(ic, key, slot, shortcut=None):
            a = QAction(icon(ic), key, self)
            a.triggered.connect(slot)
            if shortcut is not None:
                a.setShortcut(shortcut)
            self._actions.append((a, key))
            return a

        act_new = act("new", "ui_new", self.new_project, QKeySequence.New)
        act_open = act("open", "ui_open", lambda: self.open_project(), QKeySequence.Open)
        act_save = act("save", "ui_save", self.save_project, QKeySequence.Save)
        act_data = act("settings", "ui_data_entry", self.open_data_entry, "Ctrl+E")
        act_analyse = act("analyse", "run_analysis_button", self.run_analysis, "F5")
        self.act_study = act("study", "study_run", self.run_study)
        self.act_export_study = act("export_data", "ui_export_study", self.export_study)
        self.act_opt = act("optimize", "ui_optimize_length", self.run_optimize_length)
        act_interpret = act("interpret", "ui_interpret", self.open_interpret)
        act_refresh = act("refresh", "ui_refresh", self._update_plot)
        act_export = act("image", "ui_export_plot", self.export_plot)
        act_report = act("report", "report_action", self.export_report)
        act_help = act("help", "ui_help", self.show_help, QKeySequence.HelpContents)
        act_about = act("about", "ui_about", self.show_about)

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

        for a in (act_new, act_open, act_save):
            tb.addAction(a)
        tb.addSeparator()
        for a in (act_data, act_analyse, self.act_study, self.act_export_study, self.act_opt,
                  act_interpret):
            tb.addAction(a)
        tb.addSeparator()
        for a in (act_refresh, act_export, act_report):
            tb.addAction(a)
        tb.addSeparator()
        for a in (act_dark, act_help, act_about):
            tb.addAction(a)

    def _build_menu(self):
        menu = self.menuBar()
        self._menus = []
        file_m = menu.addMenu("&File")
        self._menus.append((file_m, "ui_menu_file"))
        self._file_actions = [
            file_m.addAction("New", self.new_project),
            file_m.addAction("Open…", lambda: self.open_project()),
        ]
        self.recent_menu = file_m.addMenu("Open Recent")
        self._menus.append((self.recent_menu, "ui_open_recent"))
        save_as = file_m.addAction("Save As…", self.save_project_as)
        save_as.setShortcut(QKeySequence.SaveAs)
        self._file_actions += [file_m.addAction("Save", self.save_project), save_as]
        self._file_keys = ["ui_new", "ui_open", "ui_save", "ui_save_as"]
        self._fill_recent_menu()
        file_m.addSeparator()
        self._file_actions.append(file_m.addAction("report", self.export_report))
        self._file_keys.append("report_action")
        file_m.addSeparator()
        quit_action = file_m.addAction("Quit", self.close)
        quit_action.setShortcut(QKeySequence.Quit)
        self._file_actions.append(quit_action)
        self._file_keys.append("ui_quit")
        view_m = menu.addMenu("&View")
        self._menus.append((view_m, "ui_menu_view"))
        view_m.addAction("Interpret", self.open_interpret)
        self._view_key_action = view_m.actions()[0]
        help_m = menu.addMenu("&Help")
        self._menus.append((help_m, "ui_help"))
        help_m.addAction("Help", self.show_help)
        help_m.addAction("About…", self.show_about)

    def retranslate_ui(self):
        L = self.lang
        self.btn_data.setText(t(L, "ui_data_entry"))
        self.btn_analyse.setText(t(L, "run_analysis_button"))
        self.btn_study.setText(t(L, "study_run"))
        self.btn_opt.setText(t(L, "ui_optimize_length"))
        self.btn_interpret.setText(t(L, "ui_interpret"))
        self.btn_report.setText(t(L, "report_action"))
        self.lbl_pile_type.setText(t(L, "ui_pile_type") + "  ")
        for value, button in self.type_buttons.items():
            button.setText(t(L, f"pile_type_{value}"))
        self.subtitle.setText("Axial capacity · Group · Settlement · Socket")
        self.tabs.setTabText(0, t(L, "ui_results_tab"))
        self.tabs.setTabText(1, t(L, "ui_plots_tab"))
        self.lbl_figure.setText(t(L, "ui_figure"))
        self.results.setPlaceholderText(t(L, "ui_ready"))
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

    def show_about(self):
        QMessageBox.about(
            self, t(self.lang, "ui_about"),
            t(self.lang, "ui_about_text", app=APP_NAME, version=__version__))

    # ------------------------------------------------------------------ data
    def open_data_entry(self):
        dlg = DataEntryDialog(self, self.lang, self.values)
        if dlg.exec() == QDialog.Accepted:
            new_values = dlg.collect()
            if new_values != self.values:
                self._set_dirty()
            self.values = new_values
            # The inputs changed: earlier results no longer describe them.
            self.last_result = None
            self.last_socket = None
            self.last_study = None
            self._sync_pile_type()
            self.status.showMessage(t(self.lang, "ui_data_updated"))

    # ------------------------------------------------------------------ results
    def _show_current_results(self):
        """Shows the results of the current pile type, or the placeholder."""
        L = self.lang
        if self.pile_type == "socket" and self.last_socket is not None:
            socket = self.last_socket
            self.headline.setText(summary_mod.socket_headline(socket, L))
            self.cards.set_cards(summary_mod.socket_cards(socket, L))
            self.results.setPlainText(summary_mod.socket_text(socket, L))
        elif self.pile_type == "bored" and self.last_result is not None:
            self.headline.setText(summary_mod.headline(self.last_result, L))
            self.cards.set_cards(summary_mod.cards(self.last_result, L))
            self.results.setPlainText(summary_mod.results_text(self.last_result, L))
        else:
            self.headline.setText("")
            self.cards.clear()
            self.results.clear()
        self._update_plot()
        if self.interpret is not None and self.interpret.isVisible():
            self.interpret.set_analysis(self._current_analysis(), self.lang, self.pile_type,
                                        self.theme)

    def _fill_plot_combo(self):
        current = self.plot_combo.currentData()
        keys = figure_keys(self.pile_type, self.last_result
                           if self.pile_type == "bored" else None)
        self.plot_combo.blockSignals(True)
        self.plot_combo.clear()
        for key in keys:
            self.plot_combo.addItem(figure_label(self.lang, key), key)
        index = self.plot_combo.findData(current)
        self.plot_combo.setCurrentIndex(max(index, 0))
        self.plot_combo.blockSignals(False)

    def run_analysis(self):
        """Runs the analysis of the chosen pile type."""
        if self.pile_type == "socket":
            return self.run_socket()
        L = self.lang
        cfg = to_config(self.values)
        self.status.showMessage(t(L, "running_analysis"))
        ok, result = run_task(self, t(L, "run_analysis_button"), t(L, "running_analysis"),
                              lambda progress, cancelled: analyse(cfg),
                              t(L, "ui_cancel"))
        if not ok:
            self.status.clearMessage()
            if not isinstance(result, Cancelled):
                error_box(self, t(L, "ui_analysis_error"), result, L)
            return False
        self.last_result = result
        self._fill_plot_combo()
        self._show_current_results()
        self.status.showMessage(t(L, "analysis_complete"))
        return True

    def run_socket(self):
        L = self.lang
        if self.pile_type != "socket":
            return
        try:
            self.last_socket = analyse_socket(to_config(self.values))
            self._fill_plot_combo()
            self._show_current_results()
            self.status.showMessage(t(L, "socket_complete"))
        except Exception as e:
            error_box(self, t(L, "ui_analysis_error"), e, L)

    def _update_plot(self, *_):
        if not HAS_MPL:
            return
        key = self.plot_combo.currentData()
        self.fig.clear()
        try:
            analysis = self._current_analysis()
            if key is None or analysis is None:
                ax = self.fig.add_subplot(111)
                ax.axis("off")
                ax.text(0.5, 0.5, t(self.lang, "ui_no_figure"), ha="center", va="center",
                        color="#9ca3af", fontsize=11)
                self.fig.patch.set_facecolor(DARK["card"] if self._dark else LIGHT["card"])
            elif key in SOCKET_PLOT_KEYS:
                SocketPlotter(analysis, self.lang, self.theme).draw(key, self.fig)
            else:
                Plotter(analysis, self.lang, self.theme).draw(key, self.fig)
        except Exception as exc:
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.axis("off")
            ax.text(0.5, 0.5, t(self.lang, "ui_figure_error", e=exc), ha="center",
                    va="center", wrap=True)
        self.canvas.draw_idle()

    # ------------------------------------------------------------------ study
    def run_study(self):
        L = self.lang
        if self.pile_type != "bored":
            return
        spec = study_spec(self.values)
        variables = study_variables(self.values)
        if not variables:
            QMessageBox.warning(self, t(L, "study_run"), t(L, "study_no_vars"))
            return
        try:
            cfg = to_config(self.values)
            study = Study(cfg, variables, spec["method"], spec["n"], spec["seed"])
            ok, result = run_task(
                self, t(L, "study_run"), t(L, "study_running"),
                lambda progress, cancelled: study.run(progress=progress,
                                                      is_cancelled=cancelled),
                t(L, "ui_cancel"), delay_ms=0)
            if not ok:
                if isinstance(result, Cancelled):
                    self.status.showMessage(t(L, "ui_cancelled"))
                    return
                raise result
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
                path = path if path.lower().endswith(".csv") else path + ".csv"
                study_mod.to_csv(self.last_study, path)
            self.status.showMessage(t(L, "ui_saved", path=path))
        except Exception as e:
            QMessageBox.critical(self, t(L, "ui_export_study"), str(e))

    # ------------------------------------------------------------------ report
    def export_report(self):
        L = self.lang
        is_socket = self.pile_type == "socket"
        if self._current_analysis() is None:
            QMessageBox.information(self, t(L, "report_action"), t(L, "ui_no_analysis"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t(L, "report_action"), "report.pdf",
            "PDF (*.pdf)")
        if not path:
            return
        try:
            self.status.showMessage(t(L, "report_running"))
            QApplication.processEvents()
            report_mod.export_report(
                path, None if is_socket else self.last_result, L,
                study=None if is_socket else self.last_study,
                socket=self.last_socket if is_socket else None)
            self.status.showMessage(t(L, "ui_report_written", path=path))
        except Exception as e:
            error_box(self, t(L, "report_action"), e, L)

    # ------------------------------------------------------------------ optimize
    def run_optimize_length(self):
        L = self.lang
        if self.pile_type != "bored":
            return
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
            ok, res = run_task(
                self, t(L, "ui_opt_title"), t(L, "ui_opt_running"),
                lambda progress, cancelled: optimize_length(
                    cfg, L_bounds=(sp_lmin.value(), sp_lmax.value()),
                    popsize=sp_pop.value(), maxiter=sp_iter.value(),
                    progress=progress, is_cancelled=cancelled),
                t(L, "ui_cancel"), delay_ms=0)
            if not ok:
                if isinstance(res, (Cancelled, OptCancelled)):
                    self.status.showMessage(t(L, "ui_cancelled"))
                    return
                raise res
            best_L = res["best_L"]
            # Rounded up, so the length written back is never shorter than the safe one
            self.values["L"] = math.ceil(best_L * 100.0 - 1e-6) / 100.0
            self._set_dirty()
            # Show the design at the optimised length, then the optimiser's log.
            self.run_analysis()
            lines = [
                t(L, "ui_opt_header"),
                f"Best L: {best_L:.2f} m",
                f"Success: {res['success']}",
                f"Message: {res['message']}",
                f"Evaluations: {res['nfev']}",
                "",
            ]
            self.results.setPlainText("\n".join(lines) + self.results.toPlainText())
            self.status.showMessage(t(L, "ui_best_l", L=best_L))
        except Exception as e:
            error_box(self, t(L, "ui_opt_title"), e, L)

    # ------------------------------------------------------------------ project
    def _ask_pile_type(self) -> str | None:
        """Asks which pile the new project is about, before anything else."""
        L = self.lang
        box = QMessageBox(self)
        box.setWindowTitle(t(L, "ui_new"))
        box.setText(t(L, "ui_select_pile_type"))
        box.setInformativeText(t(L, "pile_type_note"))
        buttons = {box.addButton(t(L, f"pile_type_{v}"), QMessageBox.AcceptRole): v
                   for v in PILE_TYPES}
        box.addButton(QMessageBox.Cancel)
        box.exec()
        return buttons.get(box.clickedButton())

    def new_project(self):
        if not self._confirm_discard():
            return
        pile_type = self._ask_pile_type()
        if pile_type is None:
            return
        self.values = defaults(self.lang)
        self.values["pile_type"] = pile_type
        self.values["title"] = default_title(pile_type)
        self.last_result = None
        self.last_study = None
        self.last_socket = None
        self._path = None
        self._set_dirty(False)
        self._sync_pile_type()
        self.status.showMessage(t(self.lang, "ui_new_project"))

    def export_plot(self):
        if not HAS_MPL or not hasattr(self, "fig"):
            QMessageBox.information(self, "Export", "No plot available.")
            return
        key = self.plot_combo.currentData() or "plot"
        path, _ = QFileDialog.getSaveFileName(self, t(self.lang, "ui_export_plot"),
                                              f"{key}.png",
                                              "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)")
        if path:
            self.fig.savefig(path, dpi=200, bbox_inches="tight",
                             facecolor=self.fig.get_facecolor())
            self.status.showMessage(t(self.lang, "ui_saved", path=path))

    def show_help(self):
        QMessageBox.information(
            self, t(self.lang, "ui_help"),
            t(self.lang, "ui_help_text", app=APP_NAME, version=__version__))

    def open_interpret(self):
        if self.interpret is None or not self.interpret.isVisible():
            self.interpret = InterpretWindow(self, self.lang)
        self.interpret.set_analysis(self._current_analysis(), self.lang, self.pile_type,
                                    self.theme)
        self.interpret.show()
        self.interpret.raise_()
        self.interpret.activateWindow()

    def toggle_dark(self):
        self._dark = not self._dark
        tokens = DARK if self._dark else LIGHT
        app = QApplication.instance()
        if app is not None:
            app.setPalette(make_palette(tokens))
            app.setStyleSheet(make_style(tokens))
        self.setStyleSheet(make_style(tokens))
        self.act_dark.setChecked(self._dark)
        self.act_dark.setText(t(self.lang, "ui_light_mode" if self._dark else "ui_dark_mode"))
        self._update_plot()
        if self.interpret is not None and self.interpret.isVisible():
            self.interpret.set_analysis(self._current_analysis(), self.lang, self.pile_type,
                                        self.theme)

    def open_project(self, path: str | None = None):
        if not self._confirm_discard():
            return
        if not path:
            start = str(Path(self._recent()[0]).parent) if self._recent() else ""
            path, _ = QFileDialog.getOpenFileName(self, t(self.lang, "ui_open"), start,
                                                  "SlipSurfaceIQ Pile (*.pile.json *.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(data, dict) and "config" in data:
                self.values = from_config(data["config"])
            elif isinstance(data, dict) and ("format" in data or "pile" in data
                                             or "soil_profile" in data):
                self.values = from_config(data)
            else:
                self.values = {**defaults(self.lang), **data}
            self.values["pile_type"] = pile_type_of(self.values.get("pile_type"))
            self.last_result = None
            self.last_study = None
            self.last_socket = None
            self._path = path
            self._set_dirty(False)
            self._remember(path)
            self._sync_pile_type()
            self.status.showMessage(t(self.lang, "ui_opened", path=path))
        except Exception as e:
            error_box(self, t(self.lang, "ui_open"), e, self.lang)

    def save_project(self) -> bool:
        """Saves to the project's file; asks for one the first time."""
        if not self._path:
            return self.save_project_as()
        return self._write(self._path)

    def save_project_as(self) -> bool:
        start = self._path or "project.pile.json"
        path, _ = QFileDialog.getSaveFileName(self, t(self.lang, "ui_save_as"), start,
                                              "SlipSurfaceIQ Pile (*.pile.json)")
        if not path:
            return False
        if not path.lower().endswith(".json"):
            path += ".pile.json"
        return self._write(path)

    def _write(self, path: str) -> bool:
        try:
            Path(path).write_text(json.dumps(project_file(self.values), indent=2,
                                             ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            error_box(self, t(self.lang, "ui_save"), e, self.lang)
            return False
        self._path = path
        self._set_dirty(False)
        self._remember(path)
        self.status.showMessage(t(self.lang, "ui_saved", path=path))
        return True


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
