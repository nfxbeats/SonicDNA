"""Results table with local-file drag support."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, Signal, Qt, QUrl
from PySide6.QtGui import QDrag, QMouseEvent
from PySide6.QtWidgets import QTableWidget


class ResultsTable(QTableWidget):
    """Drag selected results into Explorer, Finder, or a compatible DAW."""

    PATH_COLUMN = 3
    selected_row_clicked_again = Signal()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        index = self.indexAt(event.position().toPoint())
        replay = (
            event.button() == Qt.MouseButton.LeftButton
            and index.isValid()
            and index.row() == self.currentRow()
        )
        super().mousePressEvent(event)
        if replay:
            self.selected_row_clicked_again.emit()

    def selected_paths(self) -> list[Path]:
        rows = sorted({index.row() for index in self.selectedIndexes()})
        paths: list[Path] = []
        for row in rows:
            item = self.item(row, self.PATH_COLUMN)
            if item is not None:
                value = item.data(Qt.ItemDataRole.UserRole)
                if value:
                    paths.append(Path(value))
        return paths

    def mime_data_for_selection(self) -> QMimeData:
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(path)) for path in self.selected_paths()])
        return mime_data

    def startDrag(self, supported_actions: Qt.DropAction) -> None:  # noqa: N802
        if not self.selected_paths():
            return
        drag = QDrag(self)
        drag.setMimeData(self.mime_data_for_selection())
        drag.exec(Qt.DropAction.CopyAction)
