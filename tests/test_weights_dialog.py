from PySide6.QtWidgets import QApplication

from sonicdna.ui.weights_dialog import WeightsDialog
from sonicdna.weighting import DEFAULT_WEIGHTS


def test_reset_restores_kick_defaults() -> None:
    application = QApplication.instance() or QApplication([])
    dialog = WeightsDialog({key: 0.0 for key in DEFAULT_WEIGHTS})
    dialog.reset_defaults()
    assert dialog.values() == DEFAULT_WEIGHTS
    dialog.close()
    application.processEvents()
