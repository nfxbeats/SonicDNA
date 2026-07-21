import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QGroupBox

from sonicdna.ui.main_window import DONATE_URL, MainWindow, REPOSITORY_URL


def test_main_window_launches() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle() == "Warbeats SonicDNA"
    assert window.results.columnCount() == 4
    layout = window.centralWidget().layout()
    query = window.findChild(QGroupBox, "query_group")
    library = window.findChild(QGroupBox, "library_group")
    assert layout.indexOf(query) < layout.indexOf(window.results) < layout.indexOf(library)
    assert REPOSITORY_URL == "https://github.com/nfxbeats/SonicDNA/tree/main#"
    assert DONATE_URL == "https://www.paypal.com/donate/?hosted_button_id=KXJEA3SNE5PXC"
    window.close()
    application.processEvents()
