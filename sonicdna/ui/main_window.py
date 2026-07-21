"""Main SonicDNA desktop window."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, QSettings, QThread, QTimer, Qt
from PySide6.QtGui import (
    QAction,
    QBrush,
    QCloseEvent,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sonicdna.database import default_database_path
from sonicdna.features import SUPPORTED_EXTENSIONS
from sonicdna.indexing import ScanSummary
from sonicdna.platform_actions import open_file, reveal_file
from sonicdna.playback import create_audio_player
from sonicdna.search import SearchResult
from sonicdna.ui.results_table import ResultsTable
from sonicdna.ui.library_list import LibraryListWidget
from sonicdna.ui.weights_dialog import WeightsDialog
from sonicdna.weighting import BUILTIN_PRESETS, DEFAULT_WEIGHTS, normalize_weights, weights_match
from sonicdna.workers import LibraryWorker


class MainWindow(QMainWindow):
    """Library, query, and search workflow for the Phase 3 application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SonicDNA")
        self.setMinimumSize(760, 560)
        self.resize(1024, 700)
        self.setAcceptDrops(True)
        self.settings = QSettings("SonicDNA", "SonicDNA")
        self.worker_thread: QThread | None = None
        self.worker: LibraryWorker | None = None
        self.query_path: Path | None = None
        self.current_results: list[SearchResult] = []
        self.playing_row = -1
        self._close_pending = False
        self._build_ui()
        self._build_audio()
        self._restore_settings()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        library_group = QGroupBox("Sample Libraries")
        library_group.setObjectName("library_group")
        library_layout = QGridLayout(library_group)
        self.folder_list = LibraryListWidget()
        self.folder_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.folder_list.folders_dropped.connect(self.add_library_paths)
        library_layout.addWidget(self.folder_list, 0, 0, 4, 1)
        add_button = QPushButton("Add Folder")
        add_button.clicked.connect(self.add_folder)
        remove_button = QPushButton("Remove Folder")
        remove_button.clicked.connect(self.remove_folders)
        self.scan_button = QPushButton("Scan / Update")
        self.scan_button.clicked.connect(self.scan)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_work)
        library_layout.addWidget(add_button, 0, 1)
        library_layout.addWidget(remove_button, 1, 1)
        library_layout.addWidget(self.scan_button, 2, 1)
        library_layout.addWidget(self.cancel_button, 3, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.status = QLabel(f"Index: {default_database_path()}")
        library_layout.addWidget(self.progress, 4, 0, 1, 2)
        library_layout.addWidget(self.status, 5, 0, 1, 2)
        query_group = QGroupBox("Query Sample (or drop an audio file anywhere)")
        query_group.setObjectName("query_group")
        query_layout = QVBoxLayout(query_group)
        self.query_label = QLabel("No query selected")
        self.query_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.query_label.setMinimumWidth(0)
        self.query_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        query_layout.addWidget(self.query_label)
        query_controls = QHBoxLayout()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_query)
        play_query = QPushButton("Play")
        play_query.clicked.connect(self.play_query)
        stop_button = QPushButton("Stop")
        stop_button.clicked.connect(self.stop_audio)
        self.find_button = QPushButton("Find Similar")
        self.find_button.clicked.connect(self.find_similar)
        self.result_count = QSpinBox()
        self.result_count.setRange(1, 1000)
        self.result_count.setValue(25)
        query_controls.addWidget(browse_button)
        query_controls.addWidget(play_query)
        query_controls.addWidget(stop_button)
        query_controls.addStretch(1)
        query_controls.addWidget(QLabel("Results:"))
        query_controls.addWidget(self.result_count)
        query_controls.addWidget(self.find_button)
        query_layout.addLayout(query_controls)
        layout.addWidget(query_group)

        result_controls = QHBoxLayout()
        play_result = QPushButton("Play Selected")
        play_result.clicked.connect(self.play_selected_result)
        stop_result = QPushButton("Stop")
        stop_result.clicked.connect(self.stop_audio)
        export_button = QPushButton("Export Results to CSV")
        export_button.clicked.connect(self.export_csv)
        self.auto_audition = QCheckBox("Auto-play selection")
        self.auto_audition.setChecked(True)
        self.auto_audition.toggled.connect(self._save_auto_audition)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("preview_volume")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setMaximumWidth(120)
        self.volume_slider.setToolTip("Preview volume")
        self.volume_slider.setValue(
            round(float(self.settings.value("preview_volume", 0.8)) * 100)
        )
        self.volume_slider.valueChanged.connect(self._volume_changed)
        self.weights_button = QPushButton()
        self.weights_button.clicked.connect(self.open_weights_dialog)
        self._update_weights_button()
        result_controls.addWidget(play_result)
        result_controls.addWidget(stop_result)
        result_controls.addWidget(self.auto_audition)
        result_controls.addWidget(QLabel("Volume:"))
        result_controls.addWidget(self.volume_slider)
        result_controls.addWidget(self.weights_button)
        result_controls.addStretch(1)
        result_controls.addWidget(export_button)
        layout.addLayout(result_controls)

        self.results = ResultsTable(0, 4)
        self.results.setObjectName("results_table")
        self.results.setHorizontalHeaderLabels(
            ["Rank", "Similarity", "Filename", "Full path"]
        )
        self.results.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results.setStyleSheet(
            "QTableWidget::item:selected { background-color: #2563eb; color: white; }"
        )
        self.results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results.setDragEnabled(True)
        self.results.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.results.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.results.setSortingEnabled(False)
        self.results.doubleClicked.connect(self.play_selected_result)
        self.results.currentCellChanged.connect(self._result_selection_changed)
        self.results.selected_row_clicked_again.connect(self.play_selected_result)
        self.results.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results.customContextMenuRequested.connect(self.show_result_menu)
        self.results.horizontalHeader().setStretchLastSection(True)
        self.results.setColumnWidth(0, 60)
        self.results.setColumnWidth(1, 90)
        self.results.setColumnWidth(2, 250)
        layout.addWidget(self.results, 1)
        layout.addWidget(library_group)
        self.setCentralWidget(root)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self.play_selected_result)

    def _build_audio(self) -> None:
        volume = self.volume_slider.value() / 100.0
        self.player, self.playback_backend = create_audio_player(volume, self)
        self.player.playing_changed.connect(self._playback_state_changed)

    def _restore_settings(self) -> None:
        geometry = self.settings.value("window_geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        folders = self.settings.value("library_folders", [])
        if isinstance(folders, str):
            folders = [folders]
        for folder in folders:
            if Path(folder).is_dir():
                self.folder_list.addItem(folder)
        self.result_count.setValue(int(self.settings.value("result_count", 25)))
        self.auto_audition.setChecked(
            self.settings.value("auto_audition", True, type=bool)
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.worker_thread is not None and self.worker_thread.isRunning():
            self._close_pending = True
            self.cancel_work()
            event.ignore()
            return
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("library_folders", [
            self.folder_list.item(row).text() for row in range(self.folder_list.count())
        ])
        self.settings.setValue("result_count", self.result_count.value())
        self.settings.setValue("auto_audition", self.auto_audition.isChecked())
        self.settings.setValue("preview_volume", self.volume_slider.value() / 100.0)
        self.stop_audio()
        self.player.close()
        self.cancel_work()
        event.accept()

    def folders(self) -> list[Path]:
        return [Path(self.folder_list.item(row).text()) for row in range(self.folder_list.count())]

    def add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add Sample Library")
        if folder:
            self.add_library_paths([Path(folder)])

    def add_library_paths(self, paths: list[Path]) -> None:
        existing = {path.resolve() for path in self.folders()}
        for path in paths:
            resolved = path.resolve()
            if resolved.is_dir() and resolved not in existing:
                self.folder_list.addItem(str(resolved))
                existing.add(resolved)

    def remove_folders(self) -> None:
        for item in self.folder_list.selectedItems():
            self.folder_list.takeItem(self.folder_list.row(item))

    def browse_query(self) -> None:
        pattern = "Audio files (*.wav *.flac *.aiff *.aif *.ogg *.mp3);;All files (*)"
        filename, _ = QFileDialog.getOpenFileName(self, "Select Query Sample", "", pattern)
        if filename:
            self.set_query(Path(filename))

    def set_query(self, path: Path) -> None:
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            self.query_path = path.resolve()
            self.query_label.setText(str(self.query_path))
            self.query_label.setToolTip(str(self.query_path))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if urls:
            self.set_query(Path(urls[0].toLocalFile()))
            event.acceptProposedAction()

    def scan(self) -> None:
        if not self.folders():
            QMessageBox.information(self, "SonicDNA", "Add at least one library folder first.")
            return
        self._start_worker(None)

    def find_similar(self) -> None:
        if self.query_path is None:
            QMessageBox.information(self, "SonicDNA", "Select or drop a query sample first.")
            return
        if not self.folders():
            QMessageBox.information(self, "SonicDNA", "Add at least one library folder first.")
            return
        self._start_worker(self.query_path)

    def _start_worker(self, query: Path | None) -> None:
        if self.worker_thread is not None:
            return
        self.progress.setValue(0)
        self.status.setText("Starting scan…")
        self.scan_button.setEnabled(False)
        self.find_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.worker_thread = QThread(self)
        self.worker = LibraryWorker(
            self.folders(),
            query,
            self.result_count.value(),
            weights=self.similarity_weights(),
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.folder_complete.connect(self._on_folder_complete)
        self.worker.results_ready.connect(self._show_results)
        self.worker.failed.connect(self._show_error)
        self.worker.finished.connect(self._work_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self._thread_finished)
        self.worker_thread.start()

    def cancel_work(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.status.setText("Cancelling after the current file…")

    def _on_progress(self, path: str, current: int, total: int) -> None:
        self.progress.setValue(round(current / max(total, 1) * 100))
        self.status.setText(f"Scanning {current}/{total}: {Path(path).name}")

    def _on_folder_complete(self, folder: str, summary: ScanSummary) -> None:
        self.status.setText(
            f"{Path(folder).name}: {summary.indexed} indexed, "
            f"{summary.unchanged} unchanged, {len(summary.errors)} skipped"
        )

    def _show_results(self, results: list[SearchResult]) -> None:
        self.current_results = results
        self.playing_row = -1
        self.results.setRowCount(len(results))
        for row, result in enumerate(results):
            rank = QTableWidgetItem(str(row + 1))
            score = QTableWidgetItem(f"{result.similarity_score:.2f}")
            filename = QTableWidgetItem(result.path.name)
            full_path = QTableWidgetItem(str(result.path))
            full_path.setData(Qt.ItemDataRole.UserRole, str(result.path))
            for column, item in enumerate((rank, score, filename, full_path)):
                self.results.setItem(row, column, item)
        self.status.setText(f"Found {len(results)} similar sample(s).")

    def _show_error(self, message: str) -> None:
        self.status.setText("Operation failed")
        QMessageBox.critical(self, "SonicDNA Error", message)

    def _work_finished(self, cancelled: bool) -> None:
        if cancelled:
            self.status.setText("Operation cancelled; completed records were preserved.")
        else:
            self.progress.setValue(100)
        self.scan_button.setEnabled(True)
        self.find_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def _thread_finished(self) -> None:
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
        self.worker_thread = None
        self.worker = None
        if self._close_pending:
            QTimer.singleShot(0, self.close)

    def play_path(self, path: Path) -> None:
        if not path.is_file():
            QMessageBox.warning(self, "SonicDNA", f"File no longer exists:\n{path}")
            return
        self.player.stop()
        try:
            self.player.play(path)
            self.status.setText(f"Playing {path.name} via {self.playback_backend}")
        except (OSError, RuntimeError, ValueError) as exc:
            QMessageBox.warning(self, "SonicDNA Playback", str(exc))

    def play_query(self) -> None:
        if self.query_path is not None:
            self.playing_row = -1
            self.play_path(self.query_path)

    def play_selected_result(self) -> None:
        row = self.results.currentRow()
        if row >= 0:
            item = self.results.item(row, 3)
            self.playing_row = row
            self.play_path(Path(item.data(Qt.ItemDataRole.UserRole)))

    def _result_selection_changed(
        self, current_row: int, _current_column: int, previous_row: int, _previous_column: int
    ) -> None:
        if current_row >= 0:
            QTimer.singleShot(0, self._ensure_current_row_selected)
        if current_row >= 0 and current_row != previous_row and self.auto_audition.isChecked():
            self.play_selected_result()

    def _ensure_current_row_selected(self) -> None:
        """Expand keyboard/current-cell changes to a visible full-row selection."""
        row = self.results.currentRow()
        if row < 0:
            return
        selected_columns = {
            index.column() for index in self.results.selectedIndexes() if index.row() == row
        }
        if len(selected_columns) != self.results.columnCount():
            self.results.selectionModel().select(
                self.results.currentIndex(),
                QItemSelectionModel.SelectionFlag.ClearAndSelect
                | QItemSelectionModel.SelectionFlag.Rows,
            )

    def stop_audio(self) -> None:
        self.player.stop()

    def _playback_state_changed(self, playing_now: bool) -> None:
        for row in range(self.results.rowCount()):
            playing = row == self.playing_row and playing_now
            brush = QBrush(QColor("#d8f3dc")) if playing else QBrush()
            for column in range(self.results.columnCount()):
                item = self.results.item(row, column)
                if item is not None:
                    item.setBackground(brush)

    def selected_result_path(self) -> Path | None:
        paths = self.results.selected_paths()
        return paths[0] if paths else None

    def show_result_menu(self, position) -> None:
        clicked = self.results.itemAt(position)
        if clicked is not None and clicked.row() not in {
            index.row() for index in self.results.selectedIndexes()
        }:
            self.results.selectRow(clicked.row())
        path = self.selected_result_path()
        if path is None:
            return
        menu = QMenu(self)
        play_action = QAction("Play", self)
        play_action.triggered.connect(self.play_selected_result)
        reveal_action = QAction("Reveal in File Manager", self)
        reveal_action.triggered.connect(lambda: self._file_action(reveal_file, path))
        open_action = QAction("Open with Default Application", self)
        open_action.triggered.connect(lambda: self._file_action(open_file, path))
        copy_path_action = QAction("Copy Full Path", self)
        copy_path_action.triggered.connect(
            lambda: self._copy_text(str(path))
        )
        copy_name_action = QAction("Copy Filename", self)
        copy_name_action.triggered.connect(lambda: self._copy_text(path.name))
        menu.addActions([play_action, reveal_action, open_action])
        menu.addSeparator()
        menu.addActions([copy_path_action, copy_name_action])
        menu.exec(self.results.viewport().mapToGlobal(position))

    def _file_action(self, action, path: Path) -> None:
        try:
            action(path)
        except (OSError, RuntimeError) as exc:
            QMessageBox.warning(self, "SonicDNA", str(exc))

    def _copy_text(self, text: str) -> None:
        QApplication.clipboard().setText(text)

    def _save_auto_audition(self, checked: bool) -> None:
        """Persist immediately so the preference survives abnormal shutdowns."""
        self.settings.setValue("auto_audition", checked)
        self.settings.sync()

    def _volume_changed(self, value: int) -> None:
        volume = value / 100.0
        if hasattr(self, "player"):
            self.player.set_volume(volume)
        self.settings.setValue("preview_volume", volume)
        self.settings.sync()

    def similarity_weights(self) -> dict[str, float]:
        values = {
            key: float(self.settings.value(f"similarity_weights/{key}", default))
            for key, default in DEFAULT_WEIGHTS.items()
        }
        return normalize_weights(values)

    def open_weights_dialog(self) -> None:
        dialog = WeightsDialog(
            self.similarity_weights(),
            self.custom_weight_presets(),
            active_preset=self.active_weight_preset(),
            parent=self,
        )
        result = dialog.exec()
        self.settings.setValue(
            "similarity_weight_presets",
            json.dumps(dialog.saved_presets(), sort_keys=True),
        )
        self.settings.sync()
        if result != QDialog.DialogCode.Accepted:
            self._update_weights_button()
            return
        for key, value in dialog.values().items():
            self.settings.setValue(f"similarity_weights/{key}", value)
        self.settings.setValue("similarity_weight_active_preset", dialog.active_preset_name())
        self.settings.sync()
        self._update_weights_button()
        self.status.setText("Similarity weights updated; run Find Similar to apply them.")

    def custom_weight_presets(self) -> dict[str, dict[str, float]]:
        raw = str(self.settings.value("similarity_weight_presets", "{}"))
        try:
            values = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(values, dict):
            return {}
        return {
            str(name): normalize_weights(weights)
            for name, weights in values.items()
            if isinstance(weights, dict)
        }

    def active_weight_preset(self) -> str:
        available = {**BUILTIN_PRESETS, **self.custom_weight_presets()}
        saved = str(self.settings.value("similarity_weight_active_preset", ""))
        if saved in available:
            return saved
        current = self.similarity_weights()
        return next(
            (name for name, values in available.items() if weights_match(current, values)),
            "Kick",
        )

    def _update_weights_button(self) -> None:
        name = self.active_weight_preset()
        available = {**BUILTIN_PRESETS, **self.custom_weight_presets()}
        baseline = available.get(name, BUILTIN_PRESETS["Kick"])
        marker = "*" if not weights_match(self.similarity_weights(), baseline) else ""
        self.weights_button.setText(f"Similarity Weights: {name}{marker}…")

    def export_csv(self) -> None:
        if not self.current_results:
            QMessageBox.information(self, "SonicDNA", "There are no results to export.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export SonicDNA Results", "sonicdna-results.csv", "CSV files (*.csv)"
        )
        if not filename:
            return
        try:
            with Path(filename).open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Rank", "Similarity", "Filename", "Full path"])
                for rank, result in enumerate(self.current_results, 1):
                    writer.writerow([
                        rank, f"{result.similarity_score:.2f}", result.path.name, result.path
                    ])
            self.status.setText(f"Exported {len(self.current_results)} results to {filename}")
        except OSError as exc:
            QMessageBox.warning(self, "SonicDNA", f"Could not export results:\n{exc}")
