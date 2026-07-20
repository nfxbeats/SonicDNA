from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from sonicdna.search import SearchResult
from sonicdna.ui.main_window import MainWindow


def test_selection_change_updates_playing_row(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    first.write_bytes(b"not real audio")
    second.write_bytes(b"not real audio")
    window = MainWindow()
    window.auto_audition.setChecked(True)
    window._show_results([
        SearchResult(first, 90.0, 0.2),
        SearchResult(second, 80.0, 0.4),
    ])
    window.play_path = lambda _path: None  # type: ignore[method-assign]

    window.results.setCurrentCell(0, 0)
    assert window.playing_row == 0
    window.results.setCurrentCell(1, 0)
    assert window.playing_row == 1
    application.processEvents()
    selected_columns = {
        index.column() for index in window.results.selectedIndexes() if index.row() == 1
    }
    assert selected_columns == set(range(window.results.columnCount()))

    window.close()
    application.processEvents()


def test_clicking_selected_row_restarts_playback(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    sample = tmp_path / "kick.wav"
    sample.write_bytes(b"not real audio")
    window = MainWindow()
    window.auto_audition.setChecked(False)
    window._show_results([SearchResult(sample, 90.0, 0.2)])
    window.results.setCurrentCell(0, 0)
    played: list[Path] = []
    window.play_path = played.append  # type: ignore[method-assign]
    window.show()
    application.processEvents()

    cell = window.results.visualItemRect(window.results.item(0, 0)).center()
    QTest.mouseClick(window.results.viewport(), Qt.MouseButton.LeftButton, pos=cell)

    assert played == [sample]
    window.close()
    application.processEvents()
