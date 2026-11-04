"""
Headless smoke tests of the desktop interface (Qt's offscreen platform).

They drive the real windows the way a user would — pick the pile type,
analyse, draw every figure, run a study — and pin the GUI bugs found so far:
a progress dialog that reported every finished task as cancelled, figures
that failed to draw, inputs of the wrong pile type shown in Data Entry.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(app, monkeypatch, tmp_path):
    # no modal box may block a headless run; no settings leak between tests
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question",
                        staticmethod(lambda *a, **k: QtWidgets.QMessageBox.Discard))
    from PySide6.QtCore import QSettings
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    from slipsurface.ui.app import PileWindow
    w = PileWindow()
    w.settings = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    yield w
    w._dirty = False
    w.close()


def _texts(fig):
    return [t.get_text() for ax in fig.axes for t in ax.texts]


def test_a_finished_task_is_not_reported_as_cancelled(app):
    from slipsurface.ui.tasks import run_task
    ok, result = run_task(None, "t", "l", lambda progress, cancelled: 42)
    assert ok and result == 42


def test_every_pile_type_analyses_and_draws_every_figure(window, app):
    for pile_type in ("bored", "driven", "socket"):
        window.set_pile_type(pile_type)
        assert window.run_analysis() is not False
        assert window._current_analysis() is not None, pile_type
        assert window.cards.grid.count() > 0
        for dark in (False, True):
            if dark != window._dark:
                window.toggle_dark()
            for i in range(window.plot_combo.count()):
                window.plot_combo.setCurrentIndex(i)
                app.processEvents()
                assert not any("could not be drawn" in x for x in _texts(window.fig)), \
                    (pile_type, window.plot_combo.itemData(i))


def test_socket_hides_the_bored_only_commands(window):
    window.set_pile_type("socket")
    assert not window.btn_study.isEnabled() and not window.act_opt.isEnabled()
    assert not window.btn_cost.isEnabled() and not window.act_cost.isEnabled()
    window.set_pile_type("bored")
    assert window.btn_study.isEnabled()


def test_a_study_adds_its_figures(window, app):
    window.values.update(study_method="lhs", study_n=12, study_variables=[
        {"path": "loading.Q", "mode": "dist", "dist": "normal", "mean": 10000, "cov": 0.1}])
    window.run_study()
    keys = [window.plot_combo.itemData(i) for i in range(window.plot_combo.count())]
    assert {"study_hist", "study_scatter", "study_tornado"} <= set(keys)
    assert "β = inf" not in window.results.toPlainText()
    for key in ("study_hist", "study_scatter", "study_tornado"):
        window.plot_combo.setCurrentIndex(keys.index(key))
        app.processEvents()
        assert not any("could not be drawn" in x for x in _texts(window.fig)), key


def test_data_entry_shows_only_the_inputs_of_the_pile_type(window, app):
    from slipsurface.ui.data_entry import DataEntryDialog
    d = DataEntryDialog(window, "en", window.values)

    def tabs():
        return {d.tabs.tabText(i).replace("&&", "&") for i in range(d.tabs.count())
                if d.tabs.isTabVisible(i)}

    assert {"Soil Profile", "Pile & Loads"} <= tabs() and "Socket & Rock" not in tabs()
    d.type_buttons["socket"].setChecked(True)
    app.processEvents()
    assert tabs() == {"Project", "Socket & Rock"}
    assert d.collect()["pile_type"] == "socket"


def test_invalid_soil_cells_are_flagged(window):
    from slipsurface.ui.data_entry import DataEntryDialog
    d = DataEntryDialog(window, "en", window.values)
    table = d.tables["soil"]
    cols = [c["key"] for c in d.schema["soil"]["columns"]]
    table.item(0, cols.index("phi")).setText("abc")
    table.item(1, cols.index("nu")).setText("0.7")
    assert len(d._validate_table("soil")) == 2


def test_a_saved_project_reopens_with_its_pile_type(window, tmp_path):
    window.set_pile_type("socket")
    path = str(tmp_path / "p.pile.json")
    assert window._write(path) and not window._dirty
    window.set_pile_type("bored")
    window._dirty = False
    window.open_project(path)
    assert window.pile_type == "socket" and window._path == path


def test_a_driven_pile_asks_how_it_is_installed(window, app):
    from slipsurface.ui.data_entry import DataEntryDialog
    d = DataEntryDialog(window, "en", window.values)
    row_visible = {w: form.isRowVisible(w) for w, form, _ in d._conditional_fields}
    assert not row_visible[d.fields["installation"]]          # bored by default
    d.type_buttons["driven"].setChecked(True)
    app.processEvents()
    form = next(f for w, f, _ in d._conditional_fields if w is d.fields["installation"])
    assert form.isRowVisible(d.fields["installation"])
    assert d.collect()["pile_type"] == "driven"


def test_a_socket_shows_the_soil_table_when_its_overburden_counts(window, app):
    from slipsurface.ui.data_entry import DataEntryDialog
    window.values["pile_type"] = "socket"
    d = DataEntryDialog(window, "en", window.values)
    soil = next(i for i, name, _ in d._tab_parts if name == "soil")
    assert not d.tabs.isTabVisible(soil)
    combo = d.fields["overburden_friction"]
    combo.setCurrentIndex(combo.findData("soil"))
    app.processEvents()
    assert d.tabs.isTabVisible(soil)


def test_cost_optimization_writes_back_a_safe_design(window):
    window.set_pile_type("bored")
    window.run_optimize_cost(dict(L_bounds=(5.0, 40.0), D_bounds=(0.4, 1.5),
                                  cost_a=1.0, cost_b=0.1, popsize=5, maxiter=5))
    text = window.results.toPlainText()
    assert "Cost Optimization" in text
    if "Success: True" in text:
        assert 5.0 <= window.values["L"] <= 40.0
        assert 0.4 <= window.values["D"] <= 1.5
        assert window._dirty
