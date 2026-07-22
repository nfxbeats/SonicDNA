"""Drop target restricted to the Query Sample panel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QGroupBox


class QueryDropGroupBox(QGroupBox):
    file_dropped = Signal(str)

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(title, parent)
        self.setAcceptDrops(True)

    @staticmethod
    def files_from_mime(mime_data: QMimeData) -> list[Path]:
        return [
            Path(url.toLocalFile()).resolve()
            for url in mime_data.urls()
            if url.isLocalFile() and Path(url.toLocalFile()).is_file()
        ]

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self.files_from_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        files = self.files_from_mime(event.mimeData())
        if files:
            self.file_dropped.emit(str(files[0]))
            event.acceptProposedAction()
        else:
            event.ignore()

