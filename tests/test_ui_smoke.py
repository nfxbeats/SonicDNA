import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QGroupBox

from sonicdna.ui.main_window import DONATE_URL, MainWindow, REPOSITORY_URL


def test_main_window_launches() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle() == "Warbeats SonicDNA"
    assert window.results.columnCount() == 4
    assert window.results.verticalHeader().isHidden()
    assert window.results.horizontalHeader().sortIndicatorSection() == 0
    assert (
        window.results.horizontalHeader().sortIndicatorOrder() == Qt.SortOrder.AscendingOrder
    )
    assert window.query_waveform.height() == 46
    assert window.query_waveform.width() == 300
    assert window.query_waveform.display_text() == "Drop Sample Here"
    assert "background-color: #2563eb" in window.find_button.styleSheet()
    assert window.find_button.minimumWidth() == 170
    layout = window.centralWidget().layout()
    query = window.findChild(QGroupBox, "query_group")
    library = window.findChild(QGroupBox, "library_group")
    assert layout.indexOf(query) < layout.indexOf(window.results) < layout.indexOf(library)
    assert REPOSITORY_URL == "https://github.com/nfxbeats/SonicDNA/tree/main#"
    assert DONATE_URL == "https://www.paypal.com/donate/?hosted_button_id=KXJEA3SNE5PXC"
    assert window.theme_combo.currentData() == "System"
    window.close()
    application.processEvents()
