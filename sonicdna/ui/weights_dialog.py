"""Popup editor for similarity feature-group weights."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from sonicdna.weighting import DEFAULT_WEIGHTS, WEIGHT_LABELS, normalize_weights


class WeightsDialog(QDialog):
    """Edit the seven high-level similarity weights without crowding the main UI."""

    def __init__(self, weights: Mapping[str, float], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Similarity Weights")
        self.setMinimumWidth(460)
        root = QVBoxLayout(self)
        explanation = QLabel(
            "Higher values make that characteristic more influential in the ranking."
        )
        explanation.setWordWrap(True)
        root.addWidget(explanation)
        grid = QGridLayout()
        self.sliders: dict[str, QSlider] = {}
        self.value_labels: dict[str, QLabel] = {}
        values = normalize_weights(weights)
        for row, (key, label) in enumerate(WEIGHT_LABELS.items()):
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setObjectName(f"weight_{key}")
            slider.setRange(0, 100)
            slider.setSingleStep(1)
            slider.setValue(round(values[key] * 100))
            value_label = QLabel()
            value_label.setMinimumWidth(38)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            slider.valueChanged.connect(
                lambda value, target=value_label: target.setText(f"{value / 100:.2f}")
            )
            value_label.setText(f"{slider.value() / 100:.2f}")
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(slider, row, 1)
            grid.addWidget(value_label, row, 2)
            self.sliders[key] = slider
            self.value_labels[key] = value_label
        root.addLayout(grid)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        reset = QPushButton("Reset Defaults")
        reset.setObjectName("reset_defaults")
        reset.clicked.connect(self.reset_defaults)
        buttons.addButton(reset, QDialogButtonBox.ButtonRole.ResetRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self) -> dict[str, float]:
        return {key: slider.value() / 100.0 for key, slider in self.sliders.items()}

    def reset_defaults(self) -> None:
        for key, value in DEFAULT_WEIGHTS.items():
            self.sliders[key].setValue(round(value * 100))

