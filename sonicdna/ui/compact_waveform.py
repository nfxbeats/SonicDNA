"""Reusable compact waveform widget for the active query sample."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Signal, Qt
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QWidget


class CompactWaveformWidget(QWidget):
    clicked = Signal()
    file_dropped = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("query_waveform")
        self.setFixedHeight(46)
        self.setFixedWidth(300)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptDrops(True)
        self.setToolTip("Drop a query sample here, or click to play the current query")
        self._points: list[tuple[float, float]] = []
        self._display_text = "Drop Sample Here"

    def set_points(self, points: list[tuple[float, float]]) -> None:
        self._points = points
        self.update()

    def clear(self) -> None:
        self.set_points([])

    def set_filename(self, filename: str) -> None:
        self._display_text = filename or "Drop Sample Here"
        self.update()

    def display_text(self) -> str:
        return self._display_text

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.file_dropped.emit(urls[0].toLocalFile())
            event.acceptProposedAction()
        else:
            event.ignore()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        rect = QRectF(self.rect().adjusted(2, 2, -2, -2))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#172033"))
        painter.drawRoundedRect(rect, 4, 4)
        if self._points:
            center = rect.center().y()
            half_height = rect.height() * 0.40
            width_step = rect.width() / max(1, len(self._points) - 1)
            path = QPainterPath()
            for position, (minimum, maximum) in enumerate(self._points):
                x = rect.left() + position * width_step
                path.moveTo(QPointF(x, center - float(maximum) * half_height))
                path.lineTo(QPointF(x, center - float(minimum) * half_height))
            painter.setPen(QPen(QColor(122, 211, 255), 1.0))
            painter.drawPath(path)
        text_rect = QRectF(rect.left(), rect.center().y() - 10, rect.width(), 20)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 125) if self._points else QColor(0, 0, 0, 0))
        painter.drawRect(text_rect)
        painter.setPen(QColor("white") if self._points else QColor("#b7c3d7"))
        elided = painter.fontMetrics().elidedText(
            self._display_text, Qt.TextElideMode.ElideMiddle, int(text_rect.width()) - 8
        )
        painter.drawText(text_rect.adjusted(4, 0, -4, 0), Qt.AlignmentFlag.AlignCenter, elided)
