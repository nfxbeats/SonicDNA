"""Popup editor for similarity feature-group weights."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import QSignalBlocker, Qt
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
    WEIGHT_LABELS,
    normalize_weights,
    weights_match,
)


class WeightsDialog(QDialog):
    """Edit the seven high-level similarity weights without crowding the main UI."""

    def __init__(
        self,
        weights: Mapping[str, float],
        custom_presets: Mapping[str, Mapping[str, float]] | None = None,
        active_preset: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Weights")
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
        initial_values = normalize_weights(weights)
        available = {**BUILTIN_PRESETS, **self.custom_presets}
        matching = next(
            (name for name, values in available.items() if weights_match(initial_values, values)),
            None,
        )
        self.base_preset = active_preset if active_preset in available else matching or "Closest"
        self._loading_preset = False
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("weight_preset")
        self.preset_combo.setEditable(True)
        self.preset_combo.lineEdit().setReadOnly(True)
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
        values = initial_values
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
            slider.valueChanged.connect(self._weights_changed)
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
        self._refresh_presets(self.base_preset)
        self.preset_combo.currentIndexChanged.connect(self._preset_changed)
        self._update_preset_display()

    def values(self) -> dict[str, float]:
        return {key: slider.value() / 100.0 for key, slider in self.sliders.items()}

    def reset_defaults(self) -> None:
        self.load_preset("Closest")

    def _refresh_presets(self, selected: str) -> None:
        with QSignalBlocker(self.preset_combo):
            self.preset_combo.clear()
            for name in BUILTIN_PRESETS:
                self.preset_combo.addItem(name, name)
            for name in sorted(self.custom_presets, key=str.casefold):
                self.preset_combo.addItem(name, name)
            index = self.preset_combo.findData(selected)
            self.preset_combo.setCurrentIndex(max(0, index))
        self._update_delete_button()
        self._update_preset_display()

    def _preset_changed(self) -> None:
        if self._loading_preset:
            return
        self._update_delete_button()
        name = self.preset_combo.currentData()
        if isinstance(name, str):
            self.load_preset(name)

    def _weights_changed(self) -> None:
        if not self._loading_preset:
            self._update_preset_display()

    def _preset_values(self, name: str) -> Mapping[str, float] | None:
        return BUILTIN_PRESETS.get(name) or self.custom_presets.get(name)

    def is_modified(self) -> bool:
        baseline = self._preset_values(self.base_preset)
        return baseline is None or not weights_match(self.values(), baseline)

    def _update_preset_display(self) -> None:
        marker = "*" if self.is_modified() else ""
        self.preset_combo.setEditText(f"{self.base_preset}{marker}")

    def _update_delete_button(self) -> None:
        self.delete_button.setEnabled(self.preset_combo.currentData() in self.custom_presets)

    def load_selected_preset(self) -> None:
        name = self.preset_combo.currentData()
        if isinstance(name, str):
            self.load_preset(name)

    def load_preset(self, name: str) -> None:
        values = self._preset_values(name)
        if values is None:
            raise KeyError(f"unknown weight preset: {name}")
        self._loading_preset = True
        try:
            self.base_preset = name
            with QSignalBlocker(self.preset_combo):
                self.preset_combo.setCurrentIndex(self.preset_combo.findData(name))
            for key, value in values.items():
                self.sliders[key].setValue(round(value * 100))
        finally:
            self._loading_preset = False
        self._update_delete_button()
        self._update_preset_display()

    def save_current_as(self) -> None:
        name, accepted = QInputDialog.getText(self, "Save Weight Preset", "Preset name:")
        if accepted and name.strip():
            self.save_named_preset(name.strip())

    def save_named_preset(self, name: str) -> bool:
        if any(name.casefold() == builtin.casefold() for builtin in BUILTIN_PRESETS):
            QMessageBox.warning(self, "Weights", "Built-in presets cannot be replaced.")
            return False
        existing = next(
            (saved for saved in self.custom_presets if saved.casefold() == name.casefold()), None
        )
        if existing is not None and existing != name:
            del self.custom_presets[existing]
        self.custom_presets[name] = self.values()
        self.base_preset = name
        self._refresh_presets(name)
        return True

    def delete_selected_preset(self) -> None:
        name = str(self.preset_combo.currentData())
        if name in self.custom_presets:
            del self.custom_presets[name]
            self.base_preset = "Closest"
            self._refresh_presets("Closest")
            self.load_preset("Closest")

    def saved_presets(self) -> dict[str, dict[str, float]]:
        return {name: dict(values) for name, values in self.custom_presets.items()}

    def active_preset_name(self) -> str:
        return self.base_preset
