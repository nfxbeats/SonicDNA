"""Paint compact result waveforms with filename overlays."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

WAVEFORM_ROLE = Qt.ItemDataRole.UserRole + 1


class WaveformDelegate(QStyledItemDelegate):
    """Render an envelope behind a readable, centered filename."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        rect = QRectF(option.rect.adjusted(3, 3, -3, -3))
        painter.setPen(Qt.PenStyle.NoPen)
        # Keep waveform rendering stable while the other cells show row selection.
        painter.setBrush(QColor("#172033"))
        painter.drawRoundedRect(rect, 4, 4)

        points = index.data(WAVEFORM_ROLE) or []
        if points:
            center = rect.center().y()
            half_height = max(1.0, rect.height() * 0.40)
            width_step = rect.width() / max(1, len(points) - 1)
            path = QPainterPath()
            for position, (minimum, maximum) in enumerate(points):
                x = rect.left() + position * width_step
                top = center - float(maximum) * half_height
                bottom = center - float(minimum) * half_height
                path.moveTo(QPointF(x, top))
                path.lineTo(QPointF(x, bottom))
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            painter.setPen(QPen(QColor(122, 211, 255, 190), 1.0))
            painter.drawPath(path)

        # A translucent strip keeps filenames legible over dense waveforms.
        text_rect = QRectF(rect.left(), rect.center().y() - 10, rect.width(), 20)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 125))
        painter.drawRect(text_rect)
        painter.setPen(QColor("white"))
        elided = option.fontMetrics.elidedText(
            str(index.data(Qt.ItemDataRole.DisplayRole)),
            Qt.TextElideMode.ElideMiddle,
            int(text_rect.width()) - 8,
        )
        painter.drawText(text_rect.adjusted(4, 0, -4, 0), Qt.AlignmentFlag.AlignCenter, elided)
        painter.restore()
