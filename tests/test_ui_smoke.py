import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QGroupBox, QPushButton, QStyle, QStyleOptionViewItem

from sonicdna.ui.main_window import (
    DONATE_URL,
    MainWindow,
    REPOSITORY_URL,
    format_file_size,
)
from sonicdna.ui.play_indicator_delegate import (
    PlayIndicatorDelegate,
    UnhighlightedItemDelegate,
    without_selection,
)


def test_main_window_launches() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle() == "Warbeats SonicDNA"
    assert window.results.columnCount() == 5
    assert window.results.horizontalHeaderItem(0).text() == ""
    assert isinstance(window.results.itemDelegate(), UnhighlightedItemDelegate)
    assert isinstance(window.results.itemDelegateForColumn(0), PlayIndicatorDelegate)
    assert window.results.verticalHeader().isHidden()
    assert window.results.horizontalHeader().sortIndicatorSection() == 1
    assert (
        window.results.horizontalHeader().sortIndicatorOrder() == Qt.SortOrder.AscendingOrder
    )
    assert window.query_waveform.height() == 46
    assert window.query_waveform.width() == 300
    assert window.query_waveform.display_text() == "Drop Sample Here"
    assert window.find_button.styleSheet() == ""
    assert window.find_button.minimumWidth() == 170
    browse_button = window.findChild(QPushButton, "browse_query")
    assert browse_button is not None
    assert browse_button.width() == browse_button.height() == 34
    assert window.query_playback_button.width() == window.query_playback_button.height() == 34
    assert window.query_playback_button.toolTip() == "Play query sample"
    assert window.result_count.width() == 84
    layout = window.centralWidget().layout()
    query = window.findChild(QGroupBox, "query_group")
    library = window.findChild(QGroupBox, "library_group")
    assert layout.indexOf(query) < layout.indexOf(window.results) < layout.indexOf(library)
    assert REPOSITORY_URL == "https://github.com/nfxbeats/SonicDNA/tree/main#"
    assert DONATE_URL == "https://www.paypal.com/donate/?hosted_button_id=KXJEA3SNE5PXC"
    assert window.theme_combo.currentData() == "Cyber"
    assert "drop-down { width: 16px" in window.theme_combo.styleSheet()
    window._on_search_progress(
        "Preparing candidate list from 10,000 cached audio fingerprints", 0, 0
    )
    assert window.progress.minimum() == 0
    assert window.progress.maximum() == 0
    assert window.status.text().endswith("…")
    window.move(-500, -300)
    window._ensure_window_position_visible()
    assert window.x() >= 0
    assert window.y() >= 0
    window.move(100_000, 100_000)
    window._ensure_window_position_visible()
    available = application.primaryScreen().availableGeometry()
    assert available.contains(window.pos())
    window.close()
    application.processEvents()


def test_result_delegate_removes_selection_and_focus_states() -> None:
    option = QStyleOptionViewItem()
    option.state |= QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus
    clean = without_selection(option)
    assert not clean.state & QStyle.StateFlag.State_Selected
    assert not clean.state & QStyle.StateFlag.State_HasFocus


def test_file_size_status_formatting() -> None:
    assert format_file_size(0) == "0 bytes"
    assert format_file_size(1536) == "1.5 KB"
    assert format_file_size(5 * 1024 * 1024) == "5.0 MB"
