"""Long computations off the interface thread, with progress and cancel.

`run_task(parent, title, fn)` runs `fn(progress, is_cancelled)` in a worker
thread behind a progress dialog and returns `(ok, result_or_exception)` once
it is done. The event loop keeps running meanwhile, so the window repaints and
the Cancel button works; only plain Python runs in the worker — every widget
and figure is touched on the interface thread.
"""

from __future__ import annotations

import traceback

from PySide6.QtCore import QEventLoop, QThread, Qt, Signal
from PySide6.QtWidgets import QProgressDialog


class Cancelled(Exception):
    """The user pressed Cancel."""


class Worker(QThread):
    progressed = Signal(int, int)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn
        self.result = None
        self.error = None
        self.trace = ""
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def is_cancelled(self) -> bool:
        return self._cancel

    def run(self):
        try:
            self.result = self.fn(lambda done, total: self.progressed.emit(int(done), int(total)),
                                  self.is_cancelled)
        except Exception as exc:  # handed back to the interface thread
            self.error = exc
            self.trace = traceback.format_exc()


def run_task(parent, title: str, label: str, fn, cancel_text: str = "Cancel",
             delay_ms: int = 400):
    """Runs fn in a worker; returns (True, result), (False, exception) or
    (False, Cancelled()) when the user stopped it."""
    worker = Worker(fn, parent)
    dialog = QProgressDialog(label, cancel_text, 0, 0, parent)
    dialog.setWindowTitle(title)
    dialog.setWindowModality(Qt.WindowModal)
    dialog.setMinimumDuration(delay_ms)
    dialog.setAutoClose(False)
    dialog.setAutoReset(False)

    def on_progress(done, total):
        if total > 0:
            dialog.setMaximum(total)
            dialog.setValue(min(done, total))

    loop = QEventLoop()
    worker.progressed.connect(on_progress)
    dialog.canceled.connect(worker.cancel)
    worker.finished.connect(loop.quit)
    worker.start()
    loop.exec()
    cancelled = worker.is_cancelled()
    # closing a QProgressDialog emits canceled(): disconnect first
    dialog.canceled.disconnect(worker.cancel)
    dialog.close()
    dialog.deleteLater()
    worker.wait()
    worker.deleteLater()
    if cancelled:
        return False, Cancelled()
    if worker.error is not None:
        worker.error.trace = worker.trace
        return False, worker.error
    return True, worker.result
