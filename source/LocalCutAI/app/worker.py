from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal


class TaskWorker(QThread):
    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, function: Callable[..., Any], parent=None):
        super().__init__(parent)
        self.function = function

    def run(self) -> None:
        try:
            result = self.function(self.progress.emit)
            self.succeeded.emit(result)
        except Exception as exc:
            self.failed.emit(f"{exc}\n\nSzczegóły techniczne:\n{traceback.format_exc()}")
