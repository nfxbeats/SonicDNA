from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from sonicdna.ui.results_table import ResultsTable


def test_drag_contains_local_file_url(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    sample = tmp_path / "kick drum.wav"
    sample.write_bytes(b"audio")
    table = ResultsTable(1, 4)
    path_item = QTableWidgetItem(str(sample))
    path_item.setData(Qt.ItemDataRole.UserRole, str(sample))
    table.setItem(0, 3, path_item)
    table.selectRow(0)

    urls = table.mime_data_for_selection().urls()

    assert len(urls) == 1
    assert Path(urls[0].toLocalFile()) == sample
    table.close()
    application.processEvents()
