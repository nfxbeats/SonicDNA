"""Results table with local-file drag support."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QMimeData, Signal, Qt, QUrl
from PySide6.QtGui import QColor, QDrag, QMouseEvent
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


class NumericTableWidgetItem(QTableWidgetItem):
    """Display formatted text while sorting by the underlying numeric value."""

    def __init__(self, text: str, value: float) -> None:
        super().__init__(text)
        self.sort_value = value

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, NumericTableWidgetItem):
            return self.sort_value < other.sort_value
        return super().__lt__(other)


class ResultsTable(QTableWidget):
    """Drag selected results into Explorer, Finder, or a compatible DAW."""

    PATH_COLUMN = 3
    selected_row_clicked_again = Signal()

    def __init__(self, rows: int = 0, columns: int = 0, parent=None) -> None:
        super().__init__(rows, columns, parent)
        self._waveform_color = QColor(122, 211, 255, 190)
        self._waveform_background = QColor("#172033")
        self._waveform_text_color = QColor("#ffffff")
        self._waveform_overlay_color = QColor(0, 0, 0, 125)
        self._waveform_outline_color = QColor("#52627a")

    def _set_color(self, attribute: str, value: QColor) -> None:
        color = QColor(value)
        if color.isValid() and color != getattr(self, attribute):
            setattr(self, attribute, color)
            self.viewport().update()

    def get_waveform_color(self) -> QColor:
        return self._waveform_color

    def set_waveform_color(self, value: QColor) -> None:
        self._set_color("_waveform_color", value)

    waveformColor = Property(QColor, get_waveform_color, set_waveform_color)

    def get_waveform_background(self) -> QColor:
        return self._waveform_background

    def set_waveform_background(self, value: QColor) -> None:
        self._set_color("_waveform_background", value)

    waveformBackground = Property(QColor, get_waveform_background, set_waveform_background)

    def get_waveform_text_color(self) -> QColor:
        return self._waveform_text_color

    def set_waveform_text_color(self, value: QColor) -> None:
        self._set_color("_waveform_text_color", value)

    waveformTextColor = Property(QColor, get_waveform_text_color, set_waveform_text_color)

    def get_waveform_overlay_color(self) -> QColor:
        return self._waveform_overlay_color

    def set_waveform_overlay_color(self, value: QColor) -> None:
        self._set_color("_waveform_overlay_color", value)

    waveformOverlayColor = Property(QColor, get_waveform_overlay_color, set_waveform_overlay_color)

    def get_waveform_outline_color(self) -> QColor:
        return self._waveform_outline_color

    def set_waveform_outline_color(self, value: QColor) -> None:
        self._set_color("_waveform_outline_color", value)

    waveformOutlineColor = Property(QColor, get_waveform_outline_color, set_waveform_outline_color)

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
