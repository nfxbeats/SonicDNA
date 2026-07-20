"""Popup editor for similarity feature-group weights."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from sonicdna.weighting import (
    BUILTIN_PRESETS,
    DEFAULT_WEIGHTS,
    WEIGHT_LABELS,
    normalize_weights,
)


class WeightsDialog(QDialog):
    """Edit the seven high-level similarity weights without crowding the main UI."""

    def __init__(
        self,
        weights: Mapping[str, float],
        custom_presets: Mapping[str, Mapping[str, float]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Similarity Weights")
        self.setMinimumWidth(460)
        root = QVBoxLayout(self)
        explanation = QLabel(
            "Higher values make that characteristic more influential in the ranking."
        )
        explanation.setWordWrap(True)
        root.addWidget(explanation)
        self.custom_presets = {
            name: normalize_weights(values) for name, values in (custom_presets or {}).items()
        }
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("weight_preset")
        preset_row.addWidget(self.preset_combo, 1)
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_selected_preset)
        save_button = QPushButton("Save Current As…")
        save_button.clicked.connect(self.save_current_as)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_selected_preset)
        preset_row.addWidget(load_button)
        preset_row.addWidget(save_button)
        preset_row.addWidget(self.delete_button)
        root.addLayout(preset_row)
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
        self._refresh_presets()
        self.preset_combo.currentIndexChanged.connect(self._update_delete_button)

    def values(self) -> dict[str, float]:
        return {key: slider.value() / 100.0 for key, slider in self.sliders.items()}

    def reset_defaults(self) -> None:
        for key, value in DEFAULT_WEIGHTS.items():
            self.sliders[key].setValue(round(value * 100))

    def _refresh_presets(self, selected: str = "Kick") -> None:
        self.preset_combo.clear()
        for name in BUILTIN_PRESETS:
            self.preset_combo.addItem(f"{name} (Built-in)", name)
        for name in sorted(self.custom_presets, key=str.casefold):
            self.preset_combo.addItem(name, name)
        index = self.preset_combo.findData(selected)
        self.preset_combo.setCurrentIndex(max(0, index))
        self._update_delete_button()

    def _update_delete_button(self) -> None:
        self.delete_button.setEnabled(self.preset_combo.currentData() in self.custom_presets)

    def load_selected_preset(self) -> None:
        self.load_preset(str(self.preset_combo.currentData()))

    def load_preset(self, name: str) -> None:
        values = BUILTIN_PRESETS.get(name) or self.custom_presets.get(name)
        if values is None:
            raise KeyError(f"unknown weight preset: {name}")
        for key, value in values.items():
            self.sliders[key].setValue(round(value * 100))

    def save_current_as(self) -> None:
        name, accepted = QInputDialog.getText(self, "Save Weight Preset", "Preset name:")
        if accepted and name.strip():
            self.save_named_preset(name.strip())

    def save_named_preset(self, name: str) -> bool:
        if any(name.casefold() == builtin.casefold() for builtin in BUILTIN_PRESETS):
            QMessageBox.warning(self, "Similarity Weights", "Built-in presets cannot be replaced.")
            return False
        existing = next(
            (saved for saved in self.custom_presets if saved.casefold() == name.casefold()), None
        )
        if existing is not None and existing != name:
            del self.custom_presets[existing]
        self.custom_presets[name] = self.values()
        self._refresh_presets(name)
        return True

    def delete_selected_preset(self) -> None:
        name = str(self.preset_combo.currentData())
        if name in self.custom_presets:
            del self.custom_presets[name]
            self._refresh_presets()

    def saved_presets(self) -> dict[str, dict[str, float]]:
        return {name: dict(values) for name, values in self.custom_presets.items()}
