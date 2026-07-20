import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from sonicdna.ui.main_window import MainWindow


def test_main_window_launches() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle() == "SonicDNA"
    assert window.results.columnCount() == 5
    window.close()
    application.processEvents()
