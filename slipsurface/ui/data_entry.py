"""Data entry dialog for SlipSurfaceIQ Pile (separate window).

The pile type is chosen at the top of the dialog, before anything else. It
decides which tabs, groups and fields are shown: a bored pile asks for the
soil profile, the pile, the group, the methods and the study; a rock-socketed
pile asks for the socket, the rock and the concrete. Groundwater and the
project title apply to both. Fields and groups also follow the `when`
conditions of the schema (e.g. Janbu's η only with the Janbu base method).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QScrollArea,
    QFormLayout, QGroupBox, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QCheckBox, QPushButton, QTableWidget, QTableWidgetItem,
    QDialogButtonBox, QWidget, QRadioButton, QButtonGroup, QHeaderView,
    QAbstractItemView, QSplitter, QMessageBox,
)

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle
    HAS_MPL = True
except ImportError:  # the dialog works without the preview
    HAS_MPL = False

from slipsurface.pile.forms import (
    schema, defaults, PART_TYPES, PILE_TYPES, pile_type_of, variable_choices,
    uses_soil_profile,
)
from slipsurface.pile.i18n import t

#: Schema table name -> flat key the values dictionary uses
TABLE_VALUE_KEYS = {"soil": "soil_profile", "study_vars": "study_variables"}

#: Tab title of each schema part
PART_TITLES = {"project": "ui_tab_project", "pile": "ui_tab_pile",
               "options": "ui_tab_options", "socket": "ui_tab_socket_pile",
               "study": "ui_tab_study"}

#: Background of a soil-table cell that means nothing for the layer's behaviour
UNUSED_CELL = QColor("#eef0f3")

#: Background of a table cell whose value the analysis cannot use
INVALID_CELL = QColor("#fecaca")

#: Soil-table checks: column -> (test on the number, message); the engine
#: raises the same problems, this only shows them where they are typed
SOIL_RULES = {
    "thickness": (lambda v: v > 0, "t > 0"),
    "gamma": (lambda v: v > 0, "γ > 0"),
    "gamma_sat": (lambda v: v > 10.0, "γsat > γw"),
    "phi": (lambda v: 0 <= v < 50, "0 ≤ φ' < 50"),
    "nu": (lambda v: 0 <= v < 0.5, "0 ≤ ν < 0.5"),
    "E": (lambda v: v > 0, "E > 0"),
    "OCR": (lambda v: v >= 1, "OCR ≥ 1"),
}

FILLS = {"granular": "#E3C98F", "cohesive": "#A7B8A0", "rock": "#B9B3A8"}


def draw_preview(fig, values: dict) -> None:
    """A to-scale sketch of what the inputs describe: the layers, the water
    table and the pile (bored) or the overburden, rock and socket (socket)."""
    fig.clear()
    ax = fig.add_subplot(111)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(labelsize=7)

    def f(key, default=0.0):
        try:
            return float(values.get(key, default) or 0.0)
        except (TypeError, ValueError):
            return default

    zw = f("water_depth")
    if pile_type_of(values.get("pile_type")) == "socket":
        D, top = f("socket_D", 1.0), f("socket_top")
        rock, Ls = f("rock_depth", 10.0), f("socket_Ls", 3.0)
        bottom = rock + Ls + max(2 * D, 2.0)
        half = max(0.35 * bottom, 2.5 * D)
        drawn = 0.0
        if values.get("overburden_friction") == "soil":
            for row in values.get("soil_profile") or []:
                try:
                    h = float(row.get("thickness") or 0)
                except (TypeError, ValueError):
                    h = 0
                if h <= 0 or drawn >= rock:
                    continue
                ax.add_patch(Rectangle((-half, drawn), 2 * half, min(h, rock - drawn),
                                       facecolor=FILLS.get(row.get("behaviour"), "#ddd"),
                                       edgecolor="white", linewidth=0.8))
                drawn += h
        if drawn < rock:
            ax.add_patch(Rectangle((-half, drawn), 2 * half, rock - drawn,
                                   color=FILLS["granular"]))
        ax.add_patch(Rectangle((-half, rock), 2 * half, bottom - rock, facecolor=FILLS["rock"],
                               hatch="/", edgecolor="#8f877c", linewidth=0))
        ax.add_patch(Rectangle((-D / 2, top), D, max(rock - top, 0), color="#8A8680"))
        ax.add_patch(Rectangle((-D / 2, rock), D, Ls, color="#C6613F"))
        ax.text(-half * 0.95, rock + 0.3, f"rock {rock:.1f} m", fontsize=7, va="top")
        ax.text(D * 0.7, rock + Ls / 2, f"Ls {Ls:.2f} m", fontsize=7, va="center")
    else:
        D, L, top = f("D", 0.8), f("L", 10.0), f("top")
        layers = values.get("soil_profile") or []
        z = 0.0
        tip = top + L
        rows = []
        for row in layers:
            try:
                h = float(row.get("thickness") or 0)
            except (TypeError, ValueError):
                h = 0
            if h > 0:
                rows.append((row, z, z + h))
                z += h
        depth = z
        bottom = max(min(depth, tip + max(3 * D, 0.2 * tip)), tip + 0.5)
        try:
            nx = max(int(round(f("nx", 1))), 1)
        except ValueError:
            nx = 1
        sx = f("sx", 3 * D)
        span = (nx - 1) * sx
        half = max(span / 2 + 2 * D + 0.3 * tip, 0.4 * bottom, 3.0)
        for row, z0, z1 in rows:
            if z0 >= bottom:
                break
            ax.add_patch(Rectangle((-half, z0), 2 * half, min(z1, bottom) - z0,
                                   facecolor=FILLS.get(row.get("behaviour"), "#ddd"),
                                   edgecolor="white", linewidth=0.8))
            ax.text(-half * 0.95, (z0 + min(z1, bottom)) / 2, str(row.get("name", ""))[:18],
                    fontsize=7, va="center")
        for i in range(nx):
            x = -span / 2 + i * sx
            ax.add_patch(Rectangle((x - D / 2, top), D, L, color="#8A8680", zorder=3))
        if tip > depth:
            ax.axhline(depth, color="#dc2626", linewidth=1.5)
            ax.text(0, depth, "  tip below the profile!", color="#dc2626", fontsize=8,
                    va="bottom")
    if 0 < zw < bottom:
        ax.axhline(zw, color="#6FA8C7", linestyle="--", linewidth=1.2)
        ax.plot([half * 0.6], [zw], marker="v", color="#6FA8C7")
    ax.axhline(0, color="#111827", linewidth=1.2)
    ax.set_xlim(-half, half)
    ax.set_ylim(bottom, -0.05 * bottom)
    ax.set_aspect("equal", adjustable="box")
    ax.set_ylabel("z (m)", fontsize=7)
    fig.tight_layout()


class DataEntryDialog(QDialog):
    def __init__(self, parent=None, lang: str = "en", values: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"{t(lang, 'ui_data_entry')} — SlipSurfaceIQ Pile")
        self.resize(980, 760)
        self.lang = lang
        self.values = dict(values or defaults(lang))
        self.values["pile_type"] = pile_type_of(self.values.get("pile_type"))
        self.schema = schema(lang)
        self.fields: dict = {}
        self.tables: dict = {}
        #: (widget, form layout, conditions) of every field with a `when`
        self._conditional_fields: list = []
        #: (group box, conditions) of every group with a `when`
        self._conditional_groups: list = []
        #: (tab index, part name, [group boxes]) of every tab
        self._tab_parts: list = []

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(250)
        self._preview_timer.timeout.connect(self._refresh_preview)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_pile_type())
        split = QSplitter(Qt.Horizontal)
        self.tabs = QTabWidget()
        split.addWidget(self.tabs)
        if HAS_MPL:
            box = QGroupBox(t(lang, "ui_preview"))
            bl = QVBoxLayout(box)
            self.preview_fig = Figure(figsize=(3.2, 5), dpi=90)
            self.preview = FigureCanvas(self.preview_fig)
            self.preview.setMinimumWidth(240)
            bl.addWidget(self.preview)
            split.addWidget(box)
            split.setStretchFactor(0, 3)
            split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)
        self._build_tabs()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._apply_conditions()
        self._refresh_preview()

    # ------------------------------------------------------------------ pile type
    def _build_pile_type(self) -> QWidget:
        spec = self.schema["pile_type"]
        field = spec["fields"][0]
        box = QGroupBox(spec["title"])
        lay = QVBoxLayout(box)
        row = QHBoxLayout()
        self.type_group = QButtonGroup(self)
        self.type_buttons: dict = {}
        for index, option in enumerate(field["options"]):
            rb = QRadioButton(option["label"])
            rb.setStyleSheet("font-weight: 600;")
            self.type_group.addButton(rb, index)
            self.type_buttons[option["value"]] = rb
            row.addWidget(rb)
        row.addStretch()
        lay.addLayout(row)
        if spec.get("note"):
            lay.addWidget(self._note(spec["note"]))
        self.type_buttons.get(self.values["pile_type"],
                              self.type_buttons[PILE_TYPES[0]]).setChecked(True)
        self.type_group.idToggled.connect(lambda _id, on: on and self._apply_conditions())
        return box

    def pile_type(self) -> str:
        for value, rb in self.type_buttons.items():
            if rb.isChecked():
                return value
        return PILE_TYPES[0]

    # ------------------------------------------------------------------ tabs
    def _build_tabs(self):
        sch = self.schema
        order = [("project", "groups"), ("soil", "table"), ("pile", "groups"),
                 ("options", "groups"), ("socket", "groups"), ("study", "groups"),
                 ("study_vars", "table")]
        for name, kind in order:
            if name not in sch:
                continue
            if kind == "table":
                title = t(self.lang, "ui_soil_tab" if name == "soil" else "ui_study_vars_tab")
                index = self.tabs.addTab(self._make_table_page(name, sch[name]), title)
                self._tab_parts.append((index, name, []))
            else:
                page, boxes = self._make_groups_page(name, sch[name])
                index = self.tabs.addTab(page, t(self.lang, PART_TITLES.get(name, name)))
                self._tab_parts.append((index, name, boxes))

    @staticmethod
    def _note(text: str) -> QLabel:
        note = QLabel(text)
        note.setWordWrap(True)
        note.setStyleSheet("color: #6b7280; font-weight: 400; font-size: 12px;")
        return note

    def _make_groups_page(self, name: str, part: dict):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        lay = QVBoxLayout(w)
        boxes = []
        for group in part.get("groups", []):
            gb = QGroupBox(group.get("title", name))
            outer = QVBoxLayout(gb)
            form = QFormLayout()
            form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
            outer.addLayout(form)
            for field in group.get("fields", []):
                widget = self._make_field(field)
                label = field.get("label", field["key"])
                if field.get("unit"):
                    widget.setToolTip(f"{label} [{field['unit']}]")
                form.addRow(label, widget)
                self.fields[field["key"]] = widget
                if field.get("when"):
                    self._conditional_fields.append((widget, form, field["when"]))
                self._watch(widget)
            if group.get("note"):
                outer.addWidget(self._note(group["note"]))
            if group.get("when"):
                self._conditional_groups.append((gb, group["when"]))
            lay.addWidget(gb)
            boxes.append(gb)
        lay.addStretch()
        scroll.setWidget(w)
        return scroll, boxes

    def _watch(self, widget):
        """Fields that other fields depend on re-evaluate the conditions."""
        if isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self._apply_conditions)
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(self._apply_conditions)
        elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
            widget.valueChanged.connect(self._schedule_preview)

    def _make_field(self, field: dict):
        kind = field.get("kind", "number")
        default = self.values.get(field["key"], field.get("default"))
        if kind == "select":
            cb = QComboBox()
            for opt in field.get("options", []):
                cb.addItem(str(opt.get("label", opt.get("value", ""))), opt.get("value"))
            idx = cb.findData(default)
            if idx >= 0:
                cb.setCurrentIndex(idx)
            return cb
        if kind == "check":
            chk = QCheckBox()
            chk.setChecked(bool(default))
            return chk
        if kind in ("number", "float"):
            decimals = int(field.get("decimals", 2))
            lo = field.get("min", -1e9)
            hi = field.get("max", 1e9)
            if decimals == 0 and hi <= 1e6 and float(field.get("step") or 1).is_integer():
                sp = QSpinBox()
                sp.setRange(int(lo), int(hi))
                sp.setValue(int(round(float(default or 0))))
            else:
                sp = QDoubleSpinBox()
                sp.setDecimals(decimals)
                sp.setRange(lo, hi)
                sp.setValue(float(default or 0))
            if field.get("step"):
                sp.setSingleStep(field["step"])
            if field.get("unit"):
                sp.setSuffix(f"  {field['unit']}")
            sp.setAlignment(Qt.AlignRight)
            sp.setMinimumWidth(160)
            return sp
        return QLineEdit(str(default or ""))

    # ------------------------------------------------------------------ conditions
    def _current(self, key: str):
        if key == "pile_type":
            return self.pile_type()
        widget = self.fields.get(key)
        if isinstance(widget, QComboBox):
            return widget.currentData()
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, (QDoubleSpinBox, QSpinBox)):
            return widget.value()
        return self.values.get(key)

    def _holds(self, conditions) -> bool:
        return all(self._current(c["key"]) in c["in"] for c in conditions)

    def _apply_conditions(self, *_):
        for widget, form, conditions in self._conditional_fields:
            form.setRowVisible(widget, self._holds(conditions))
        for gb, conditions in self._conditional_groups:
            gb.setVisible(self._holds(conditions))
        pile_type = self.pile_type()
        for index, name, boxes in self._tab_parts:
            types = PART_TYPES.get(name)
            visible = types is None or pile_type in types
            if name == "soil":
                visible = uses_soil_profile({"pile_type": pile_type,
                                             "overburden_friction":
                                                 self._current("overburden_friction")})
            if visible and boxes:
                visible = any(not gb.isHidden() for gb in boxes)
            self.tabs.setTabVisible(index, visible)
        if not self.tabs.isTabVisible(self.tabs.currentIndex()):
            self.tabs.setCurrentIndex(0)
        self._schedule_preview()

    # ------------------------------------------------------------------ preview
    def _schedule_preview(self, *_):
        if HAS_MPL:
            self._preview_timer.start()

    def _refresh_preview(self):
        if not HAS_MPL:
            return
        try:
            draw_preview(self.preview_fig, self.collect())
        except Exception:  # a half-typed input must never break the dialog
            self.preview_fig.clear()
        self.preview.draw_idle()

    # ------------------------------------------------------------------ validation
    def _validate_table(self, name: str):
        """Marks the cells the analysis cannot use; returns their descriptions."""
        table = self.tables.get(name)
        if table is None:
            return []
        cols = self.schema[name]["columns"]
        problems = []
        table.blockSignals(True)
        for r in range(table.rowCount()):
            row_has_data = any((table.item(r, c).text().strip() if table.item(r, c) else "")
                               for c, col in enumerate(cols) if col.get("kind") != "select")
            for c, col in enumerate(cols):
                item = table.item(r, c)
                if item is None or col.get("kind") != "number":
                    continue
                text = item.text().strip().replace(",", ".")
                message = ""
                if text:
                    try:
                        value = float(text)
                    except ValueError:
                        message = f"'{item.text()}' is not a number"
                    else:
                        rule = SOIL_RULES.get(col["key"]) if name == "soil" else None
                        if rule and not rule[0](value):
                            message = rule[1]
                elif name == "soil" and col["key"] == "thickness" and row_has_data:
                    message = "t > 0"
                if message:
                    item.setBackground(QBrush(INVALID_CELL))
                    item.setToolTip(message)
                    problems.append(f"{t(self.lang, 'ui_soil_tab') if name == 'soil' else name}"
                                    f" row {r + 1}, {col.get('label', col['key'])}: {message}")
                else:
                    item.setToolTip("")
                    if item.background().color() == INVALID_CELL:
                        item.setBackground(QBrush())
        table.blockSignals(False)
        if name == "soil":
            behaviour = [c["key"] for c in cols].index("behaviour")
            for r in range(table.rowCount()):
                cb = table.cellWidget(r, behaviour)
                if cb is not None:
                    self._grey_unused(table, cols, cb, keep_invalid=True)
        return problems

    def _accept(self):
        problems = []
        for index, name, _boxes in self._tab_parts:
            if name in self.tables and self.tabs.isTabVisible(index):
                problems += self._validate_table(name)
        if problems:
            answer = QMessageBox.warning(
                self, self.windowTitle(),
                t(self.lang, "ui_invalid_cells", cells="\n".join(problems[:12])),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        self.accept()

    # ------------------------------------------------------------------ tables
    def _select_options(self, name: str, col: dict) -> list:
        if name == "study_vars" and col["key"] == "path":
            return variable_choices(self.values, self.lang)
        return col.get("options", [])

    def _make_table_page(self, name: str, spec: dict) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        lay = QVBoxLayout(w)
        if spec.get("note"):
            lay.addWidget(self._note(spec["note"]))
        table = QTableWidget()
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        cols = spec.get("columns", [])
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels([c.get("label", c["key"]) for c in cols])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        value_key = TABLE_VALUE_KEYS.get(name, name)
        rows = self.values.get(value_key)
        if rows is None:
            rows = spec.get("rows", [])
        self.tables[name] = table
        for row in rows:
            self._append_row(name, table, cols, row)
        if not rows:
            self._append_row(name, table, cols, {})
        table.itemChanged.connect(lambda _item, n=name: (self._validate_table(n),
                                                         self._schedule_preview()))
        self._validate_table(name)
        lay.addWidget(table, 1)

        buttons = QHBoxLayout()
        add = QPushButton(t(self.lang, "ui_add_row"))
        add.clicked.connect(lambda: self._append_row(name, table, cols, {}))
        delete = QPushButton(t(self.lang, "ui_delete_row"))
        delete.clicked.connect(lambda: (self._delete_rows(table), self._schedule_preview()))
        buttons.addWidget(add)
        buttons.addWidget(delete)
        buttons.addStretch()
        lay.addLayout(buttons)
        scroll.setWidget(w)
        return scroll

    def _append_row(self, name: str, table: QTableWidget, cols: list, row: dict):
        r = table.rowCount()
        table.insertRow(r)
        for c, col in enumerate(cols):
            value = row.get(col["key"], "")
            if col.get("kind") == "select":
                cb = QComboBox()
                cb.setFrame(False)
                for opt in self._select_options(name, col):
                    cb.addItem(str(opt.get("label", opt.get("value"))), opt.get("value"))
                idx = cb.findData(value)
                if idx < 0 and value not in ("", None):
                    cb.addItem(str(value), value)
                    idx = cb.count() - 1
                cb.setCurrentIndex(max(idx, 0))
                table.setCellWidget(r, c, cb)
                if name == "soil" and col["key"] == "behaviour":
                    cb.currentIndexChanged.connect(
                        lambda _i, cb=cb: (self._grey_unused(table, cols, cb),
                                           self._schedule_preview()))
            else:
                text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                if col.get("kind") == "number":
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(r, c, item)
        if name == "soil":
            behaviour_col = next((i for i, c in enumerate(cols) if c["key"] == "behaviour"),
                                 None)
            if behaviour_col is not None:
                self._grey_unused(table, cols, table.cellWidget(r, behaviour_col))

    def _grey_unused(self, table: QTableWidget, cols: list, cb: QComboBox,
                     keep_invalid: bool = False):
        """Greys out the columns that mean nothing for the layer's behaviour."""
        if cb is None:
            return
        row = next((r for r in range(table.rowCount())
                    if table.cellWidget(r, [c["key"] for c in cols].index("behaviour")) is cb),
                   None)
        if row is None:
            return
        spec = self.schema["soil"]
        unused = spec.get("sand_only", []) if cb.currentData() == "cohesive" \
            else spec.get("clay_only", [])
        # colouring a cell must not count as an edit (itemChanged -> validation)
        blocked = table.blockSignals(True)
        try:
            self._paint_unused(table, cols, row, unused, keep_invalid)
        finally:
            table.blockSignals(blocked)

    @staticmethod
    def _paint_unused(table, cols, row, unused, keep_invalid):
        for c, col in enumerate(cols):
            item = table.item(row, c)
            if item is None:
                continue
            if keep_invalid and item.background().color() == INVALID_CELL:
                continue
            item.setBackground(QBrush(UNUSED_CELL) if col["key"] in unused else QBrush())

    @staticmethod
    def _delete_rows(table: QTableWidget):
        rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
        if not rows and table.currentRow() >= 0:
            rows = [table.currentRow()]
        for r in rows:
            table.removeRow(r)

    # ------------------------------------------------------------------ result
    def collect(self) -> dict:
        vals = dict(self.values)
        vals["pile_type"] = self.pile_type()
        for key, widget in self.fields.items():
            try:
                if isinstance(widget, QComboBox):
                    vals[key] = widget.currentData()
                elif isinstance(widget, QCheckBox):
                    vals[key] = widget.isChecked()
                elif isinstance(widget, QSpinBox):
                    vals[key] = int(widget.value())
                elif isinstance(widget, QDoubleSpinBox):
                    vals[key] = widget.value()
                elif isinstance(widget, QLineEdit):
                    vals[key] = widget.text()
            except RuntimeError:
                pass
        for name, table in self.tables.items():
            value_key = TABLE_VALUE_KEYS.get(name, name)
            cols = self.schema.get(name, {}).get("columns", [])
            rows = []
            for r in range(table.rowCount()):
                row = {}
                has = False
                for c, col in enumerate(cols):
                    key = col["key"]
                    kind = col.get("kind", "text")
                    if kind == "select":
                        cb = table.cellWidget(r, c)
                        row[key] = cb.currentData() if isinstance(cb, QComboBox) else ""
                        continue
                    item = table.item(r, c)
                    text = (item.text() if item else "").strip()
                    if kind == "number":
                        try:
                            row[key] = float(text.replace(",", ".")) if text else 0.0
                        except ValueError:
                            row[key] = 0.0
                    else:
                        row[key] = text
                    if text:
                        has = True
                if has:
                    rows.append(row)
            vals[value_key] = rows
        return vals
