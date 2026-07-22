from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from sonicdna.search import SearchResult
from sonicdna.ui.main_window import MainWindow
from sonicdna.ui.results_table import NumericTableWidgetItem, ResultsTable


def test_numeric_columns_sort_by_value() -> None:
    application = QApplication.instance() or QApplication([])
    table = ResultsTable(3, 1)
    for row, value in enumerate((2.0, 10.0, 1.0)):
        table.setItem(row, 0, NumericTableWidgetItem(str(value), value))
    table.setSortingEnabled(True)
    table.sortItems(0, Qt.SortOrder.AscendingOrder)

    assert [table.item(row, 0).sort_value for row in range(3)] == [1.0, 2.0, 10.0]
    table.close()
    application.processEvents()


def test_new_search_resets_to_best_rank_first() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    results = [
        SearchResult(Path("first.wav"), 95.0, 0.1),
        SearchResult(Path("second.wav"), 85.0, 0.3),
        SearchResult(Path("third.wav"), 75.0, 0.5),
    ]
    window._show_results(results)
    window.results.sortItems(0, Qt.SortOrder.DescendingOrder)
    assert window.results.item(0, 0).text() == "3"

    window._show_results(results)

    assert window.results.item(0, 0).text() == "1"
    assert window.results.horizontalHeader().sortIndicatorSection() == 0
    assert window.results.horizontalHeader().sortIndicatorOrder() == Qt.SortOrder.AscendingOrder
    window.close()
    application.processEvents()
