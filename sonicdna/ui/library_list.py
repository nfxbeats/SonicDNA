"""Library-folder list with operating-system folder drop support."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QListWidget


class LibraryListWidget(QListWidget):
    """Accept local directory URLs while rejecting files and remote URLs."""

    folders_dropped = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setToolTip("Drop one or more sample-library folders here")

    @staticmethod
    def directories_from_mime(mime_data: QMimeData) -> list[Path]:
        paths: list[Path] = []
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_dir():
                paths.append(path.resolve())
        return paths

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self.directories_from_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if self.directories_from_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        folders = self.directories_from_mime(event.mimeData())
        if folders:
            self.folders_dropped.emit(folders)
            event.acceptProposedAction()
        else:
            event.ignore()

