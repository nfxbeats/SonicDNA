from PySide6.QtWidgets import QApplication

from sonicdna.ui.weights_dialog import WeightsDialog
from sonicdna.weighting import BUILTIN_PRESETS, DEFAULT_WEIGHTS


def test_reset_restores_kick_defaults() -> None:
    application = QApplication.instance() or QApplication([])
    dialog = WeightsDialog({key: 0.0 for key in DEFAULT_WEIGHTS})
    dialog.reset_defaults()
    assert dialog.values() == DEFAULT_WEIGHTS
    dialog.close()
    application.processEvents()


def test_builtin_profiles_load_and_custom_state_can_be_saved() -> None:
    application = QApplication.instance() or QApplication([])
    dialog = WeightsDialog(DEFAULT_WEIGHTS)
    for name, expected in BUILTIN_PRESETS.items():
        dialog.load_preset(name)
        assert dialog.values() == expected

    dialog.sliders["attack"].setValue(12)
    assert dialog.save_named_preset("My Soft Hits")
    assert dialog.saved_presets()["My Soft Hits"]["attack"] == 0.12
    dialog.load_preset("Kick")
    dialog.load_preset("My Soft Hits")
    assert dialog.values()["attack"] == 0.12
    dialog.close()
    application.processEvents()
