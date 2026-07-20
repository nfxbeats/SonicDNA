import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QGroupBox

from sonicdna.ui.main_window import MainWindow


def test_main_window_launches() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle() == "SonicDNA"
    assert window.results.columnCount() == 4
    layout = window.centralWidget().layout()
    query = window.findChild(QGroupBox, "query_group")
    library = window.findChild(QGroupBox, "library_group")
    assert layout.indexOf(query) < layout.indexOf(window.results) < layout.indexOf(library)
    window.close()
    application.processEvents()
