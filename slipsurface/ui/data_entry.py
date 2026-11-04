"""Data entry dialog for SlipSurfaceIQ Pile (separate window)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QScrollArea,
    QFormLayout, QGroupBox, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QCheckBox, QPushButton, QTableWidget, QTableWidgetItem,
    QDialogButtonBox, QWidget,
)

from slipsurface.pile.forms import schema, defaults

#: Schema table name -> flat key the values dictionary uses
TABLE_VALUE_KEYS = {"soil": "soil_profile", "study_vars": "study_variables"}


class DataEntryDialog(QDialog):
    def __init__(self, parent=None, lang: str = "en", values: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Data Entry — SlipSurfaceIQ Pile")
        self.resize(900, 700)
        self.lang = lang
        self.values = values or defaults(lang)
        self.fields: dict = {}
        self.tables: dict = {}

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._build_tabs()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_tabs(self):
        sch = schema(self.lang)
        if "soil" in sch and "columns" in sch["soil"]:
            self.tabs.addTab(self._make_table_page("soil", sch["soil"]), "Soil Profile")
        for part in ("project", "pile", "options", "socket", "study"):
            if part in sch and "groups" in sch[part]:
                self.tabs.addTab(self._make_groups_page(part, sch[part]), part.capitalize())
        if "study_vars" in sch and "columns" in sch["study_vars"]:
            self.tabs.addTab(self._make_table_page("study_vars", sch["study_vars"]), "Study Variables")

    def _make_table_page(self, name: str, spec: dict) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        lay = QVBoxLayout(w)
        if spec.get("note"):
            note = QLabel(spec["note"])
            note.setWordWrap(True)
            lay.addWidget(note)
        table = QTableWidget()
        cols = spec.get("columns", [])
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels([c.get("label", c["key"]) for c in cols])
        value_key = TABLE_VALUE_KEYS.get(name, name)
        rows = self.values.get(value_key) or spec.get("rows", [])
        table.setRowCount(max(len(rows), 4))
        for r, row in enumerate(rows):
            for c, col in enumerate(cols):
                table.setItem(r, c, QTableWidgetItem(str(row.get(col["key"], ""))))
        lay.addWidget(table)
        add = QPushButton("+ Add row")
        add.clicked.connect(lambda: table.insertRow(table.rowCount()))
        lay.addWidget(add)
        scroll.setWidget(w)
        self.tables[name] = table
        return scroll

    def _make_groups_page(self, name: str, part: dict) -> QWidget:
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
        return scroll

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
            sp = QDoubleSpinBox()
            sp.setDecimals(field.get("dec", 2))
            sp.setRange(field.get("lo", -1e9), field.get("hi", 1e9))
            sp.setValue(float(default or 0))
            return sp
        return QLineEdit(str(default or ""))

    def collect(self) -> dict:
        vals = dict(self.values)
        for key, widget in self.fields.items():
            try:
                if isinstance(widget, QComboBox):
                    vals[key] = widget.currentData()
                elif isinstance(widget, QCheckBox):
                    vals[key] = widget.isChecked()
                elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                    vals[key] = widget.value()
                elif isinstance(widget, QLineEdit):
                    vals[key] = widget.text()
            except RuntimeError:
                pass
        for name, table in self.tables.items():
            value_key = TABLE_VALUE_KEYS.get(name, name)
            sch = schema(self.lang).get(name, {})
            cols = sch.get("columns", [])
            rows = []
            for r in range(table.rowCount()):
                row = {}
                has = False
                for c, col in enumerate(cols):
                    item = table.item(r, c)
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
                        has = True
                if has:
                    rows.append(row)
            vals[value_key] = rows
        return vals
