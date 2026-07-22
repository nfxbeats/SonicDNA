"""A checkbox whose indicator colors are controlled by Qt theme properties."""

from __future__ import annotations

from PySide6.QtCore import Property, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton


class ThemedCheckBox(QCheckBox):
    """Draw a consistently visible indicator across light and dark themes."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self._checkbox_background = QColor("#ffffff")
        self._checkbox_border = QColor("#6b7280")
        self._checkbox_checked = QColor("#2563eb")
        self._checkbox_check = QColor("#ffffff")

    def _set_color(self, attribute: str, value: QColor) -> None:
        color = QColor(value)
        if color.isValid() and color != getattr(self, attribute):
            setattr(self, attribute, color)
            self.update()

    def get_checkbox_background(self) -> QColor:
        return self._checkbox_background

    def set_checkbox_background(self, value: QColor) -> None:
        self._set_color("_checkbox_background", value)

    checkboxBackground = Property(QColor, get_checkbox_background, set_checkbox_background)

    def get_checkbox_border(self) -> QColor:
        return self._checkbox_border

    def set_checkbox_border(self, value: QColor) -> None:
        self._set_color("_checkbox_border", value)

    checkboxBorder = Property(QColor, get_checkbox_border, set_checkbox_border)

    def get_checkbox_checked(self) -> QColor:
        return self._checkbox_checked

    def set_checkbox_checked(self, value: QColor) -> None:
        self._set_color("_checkbox_checked", value)

    checkboxChecked = Property(QColor, get_checkbox_checked, set_checkbox_checked)

    def get_checkbox_check(self) -> QColor:
        return self._checkbox_check

    def set_checkbox_check(self, value: QColor) -> None:
        self._set_color("_checkbox_check", value)

    checkboxCheck = Property(QColor, get_checkbox_check, set_checkbox_check)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        option = QStyleOptionButton()
        self.initStyleOption(option)
        indicator = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, option, self
        )
        contents = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxContents, option, self
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        checked = self.isChecked()
        painter.setPen(QPen(self._checkbox_border, 1.0))
        painter.setBrush(self._checkbox_checked if checked else self._checkbox_background)
        painter.drawRoundedRect(indicator.adjusted(1, 1, -1, -1), 3, 3)

        if checked:
            box = indicator.adjusted(3, 3, -3, -3)
            check = QPainterPath()
            check.moveTo(box.left(), box.center().y())
            check.lineTo(box.center().x() - 1, box.bottom())
            check.lineTo(box.right(), box.top())
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self._checkbox_check, 2.0))
            painter.drawPath(check)

        painter.setPen(option.palette.windowText().color())
        painter.drawText(
            contents,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.text(),
        )
