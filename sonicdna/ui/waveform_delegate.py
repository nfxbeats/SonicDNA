"""Paint compact result waveforms with filename overlays."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

WAVEFORM_ROLE = Qt.ItemDataRole.UserRole + 1
PLAYBACK_PROGRESS_ROLE = Qt.ItemDataRole.UserRole + 2


class WaveformDelegate(QStyledItemDelegate):
    """Render an envelope behind a readable, centered filename."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.fillRect(option.rect, option.palette.brush(QPalette.ColorRole.Base))
        rect = QRectF(option.rect.adjusted(3, 3, -3, -3))
        painter.setPen(Qt.PenStyle.NoPen)
        widget = self.parent() or option.widget

        def themed_color(property_name: str, fallback: QColor) -> QColor:
            value = widget.property(property_name) if widget is not None else None
            color = QColor(value) if value is not None else fallback
            return color if color.isValid() else fallback

        background = themed_color("waveformBackground", QColor("#172033"))
        waveform = themed_color("waveformColor", QColor(122, 211, 255, 190))
        text = themed_color("waveformTextColor", QColor("white"))
        outline = themed_color("waveformOutlineColor", QColor("#52627a"))
        # Keep waveform rendering stable while the other cells show row selection.
        painter.setBrush(background)
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
            painter.setPen(QPen(waveform, 1.0))
            painter.drawPath(path)

        playback_progress = index.data(PLAYBACK_PROGRESS_ROLE)
        if playback_progress is not None:
            playhead_x = rect.left() + rect.width() * float(playback_progress)
            painter.setPen(QPen(text, 2.0))
            painter.drawLine(
                QPointF(playhead_x, rect.top()), QPointF(playhead_x, rect.bottom())
            )

        text_rect = rect.adjusted(4, 2, -4, -2)
        painter.setPen(text)
        elided = option.fontMetrics.elidedText(
            str(index.data(Qt.ItemDataRole.DisplayRole)),
            Qt.TextElideMode.ElideMiddle,
            int(text_rect.width()),
        )
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            elided,
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(outline, 1.0))
        painter.drawRoundedRect(rect, 4, 4)
        painter.restore()
