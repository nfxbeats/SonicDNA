"""Render a centered Font Awesome play glyph for the current result row."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem


def without_selection(option: QStyleOptionViewItem) -> QStyleOptionViewItem:
    """Copy an item option without selection or keyboard-focus decoration."""
    clean = QStyleOptionViewItem(option)
    clean.state &= ~QStyle.StateFlag.State_Selected
    clean.state &= ~QStyle.StateFlag.State_HasFocus
    return clean


class UnhighlightedItemDelegate(QStyledItemDelegate):
    """Render selected result cells with their normal colors."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        clean = without_selection(option)
        painter.fillRect(clean.rect, clean.palette.brush(QPalette.ColorRole.Base))
        super().paint(painter, clean, index)


class PlayIndicatorDelegate(QStyledItemDelegate):
    """Paint a play marker only in the table's current row."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        clean = without_selection(option)
        painter.fillRect(clean.rect, clean.palette.brush(QPalette.ColorRole.Base))
        super().paint(painter, clean, index)
        table = self.parent()
        if table is None or index.row() != table.currentRow():
            return

        color = clean.palette.color(QPalette.ColorRole.Text)
        icon = qta.icon("fa6s.play", color=color)
        size = min(14, option.rect.width() - 6, option.rect.height() - 6)
        if size <= 0:
            return
        target = QRect(0, 0, size, size)
        target.moveCenter(option.rect.center())
        icon.paint(painter, target)

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        hint = super().sizeHint(option, index)
        return QSize(max(28, hint.width()), hint.height())
