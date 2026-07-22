"""Font Awesome buttons whose glyph color can be controlled by a Qt theme."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Property
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton, QWidget


class ThemedIconButton(QPushButton):
    """A compact Font Awesome button with a QSS-configurable icon color."""

    def __init__(self, glyph: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._glyph = glyph
        self._icon_color = QColor("#374151")
        self._refresh_icon()

    def set_glyph(self, glyph: str) -> None:
        if self._glyph != glyph:
            self._glyph = glyph
            self._refresh_icon()

    def get_icon_color(self) -> QColor:
        return self._icon_color

    def set_icon_color(self, color: QColor) -> None:
        resolved = QColor(color)
        if resolved.isValid() and resolved != self._icon_color:
            self._icon_color = resolved
            self._refresh_icon()

    iconColor = Property(QColor, get_icon_color, set_icon_color)

    def _refresh_icon(self) -> None:
        self.setIcon(qta.icon(self._glyph, color=self._icon_color))
