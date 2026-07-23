"""Main SonicDNA desktop window."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QItemSelectionModel,
    QPoint,
    QSignalBlocker,
    QThread,
    QThreadPool,
    QTimer,
    Qt,
    QUrl,
)
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDesktopServices,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
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

from sonicdna.database import IndexedSample, IndexDatabase, default_database_path
from sonicdna.features import SUPPORTED_EXTENSIONS
from sonicdna.indexing import ScanSummary
from sonicdna.platform_actions import open_file, reveal_file
from sonicdna.playback import create_audio_player
from sonicdna.search import SearchResult
from sonicdna.settings import create_settings
from sonicdna.ui.results_table import NumericTableWidgetItem, ResultsTable
from sonicdna.ui.play_indicator_delegate import PlayIndicatorDelegate, UnhighlightedItemDelegate
from sonicdna.ui.themed_icon_button import ThemedIconButton
from sonicdna.ui.themed_checkbox import ThemedCheckBox
from sonicdna.ui.library_list import LibraryListWidget
from sonicdna.ui.compact_waveform import CompactWaveformWidget
from sonicdna.ui.query_drop_group import QueryDropGroupBox
from sonicdna.ui.weights_dialog import WeightsDialog
from sonicdna.ui.waveform_delegate import (
    PLAYBACK_PROGRESS_ROLE,
    WAVEFORM_ROLE,
    WaveformDelegate,
)
from sonicdna.ui.waveform_loader import WaveformTask
from sonicdna.weighting import BUILTIN_PRESETS, DEFAULT_WEIGHTS, normalize_weights, weights_match
from sonicdna.themes import apply_theme, available_themes, theme_directory
from sonicdna.workers import LibraryWorker

REPOSITORY_URL = "https://github.com/nfxbeats/SonicDNA/tree/main#"
DONATE_URL = "https://www.paypal.com/donate/?hosted_button_id=KXJEA3SNE5PXC"


class MainWindow(QMainWindow):
    """Library, query, and search workflow for the Phase 3 application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Warbeats SonicDNA")
        self.setMinimumSize(760, 560)
        self.resize(1024, 700)
        self.settings = create_settings()
        self.worker_thread: QThread | None = None
        self.worker: LibraryWorker | None = None
        self.query_path: Path | None = None
        self.current_results: list[SearchResult] = []
        self.playing_row = -1
        self.playing_path: Path | None = None
        self._audio_is_playing = False
        self._close_pending = False
        self._waveform_pending: set[str] = set()
        self._sample_cache: list[IndexedSample] | None = None
        self._sample_cache_folders: tuple[str, ...] = ()
        self._sample_cache_scan_times: dict[str, str | None] = {}
        self._worker_folder_key: tuple[str, ...] = ()
        self._active_index_scan_times: dict[str, str | None] = {}
        self._operation_failed = False
        self.waveform_pool = QThreadPool(self)
        self.waveform_pool.setMaxThreadCount(2)
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
        query_group = QueryDropGroupBox("Query Sample (drop an audio file in this panel)")
        query_group.setObjectName("query_group")
        query_group.file_dropped.connect(lambda path: self.set_query(Path(path)))
        query_layout = QVBoxLayout(query_group)
        self.query_label = QLabel("No query selected")
        self.query_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.query_label.setMinimumWidth(0)
        self.query_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        query_top_row = QHBoxLayout()
        self.query_waveform = CompactWaveformWidget()
        self.query_waveform.clicked.connect(self.play_query)
        self.query_waveform.file_dropped.connect(lambda path: self.set_query(Path(path)))
        query_top_row.addWidget(self.query_waveform)
        browse_button = ThemedIconButton("fa6s.folder-open")
        browse_button.setObjectName("browse_query")
        browse_button.setFixedSize(34, 34)
        browse_button.setToolTip("Browse for query sample")
        browse_button.setAccessibleName("Browse for query sample")
        browse_button.clicked.connect(self.browse_query)
        self.query_playback_button = ThemedIconButton("fa6s.play")
        self.query_playback_button.setObjectName("query_playback")
        self.query_playback_button.setFixedSize(34, 34)
        self.query_playback_button.clicked.connect(self.toggle_query_playback)
        self._set_query_playback_button_state(False)
        self.result_count = QSpinBox()
        self.result_count.setRange(1, 1000)
        self.result_count.setValue(25)
        self.result_count.setFixedWidth(84)
        query_top_row.addWidget(browse_button)
        query_top_row.addWidget(self.query_playback_button)
        results_label = QLabel("Results:")
        results_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        query_top_row.addWidget(results_label)
        query_top_row.addWidget(self.result_count)
        self.find_button = QPushButton("Find Similar")
        self.find_button.setObjectName("find_similar")
        self.find_button.setMinimumWidth(170)
        self.find_button.clicked.connect(self.find_similar)
        query_top_row.addWidget(self.find_button)
        query_layout.addLayout(query_top_row)
        query_layout.addWidget(self.query_label)
        layout.addWidget(query_group)

        result_controls = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("theme_selector")
        self.theme_combo.setMinimumWidth(120)
        self.theme_combo.setStyleSheet(
            "QComboBox#theme_selector { padding-right: 18px; }"
            "QComboBox#theme_selector::drop-down { width: 16px; border: 0; }"
            "QComboBox#theme_selector::down-arrow { width: 8px; height: 8px; }"
        )
        self._populate_theme_combo()
        self.theme_combo.currentIndexChanged.connect(self._theme_combo_changed)
        export_button = QPushButton("Export")
        export_button.clicked.connect(self.export_csv)
        repository_button = QPushButton("Github Repo")
        repository_button.setToolTip(REPOSITORY_URL)
        repository_button.clicked.connect(self.open_repository)
        donate_button = QPushButton("Donate")
        donate_button.setToolTip(DONATE_URL)
        donate_button.clicked.connect(self.open_donate)
        self.auto_audition = ThemedCheckBox("Auto-play")
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
        result_controls.addWidget(QLabel("Theme:"))
        result_controls.addWidget(self.theme_combo)
        result_controls.addSpacing(8)
        result_controls.addWidget(self.auto_audition)
        result_controls.addWidget(QLabel("Volume:"))
        result_controls.addWidget(self.volume_slider)
        result_controls.addSpacing(8)
        result_controls.addWidget(self.weights_button)
        result_controls.addStretch(1)
        result_controls.addWidget(export_button)
        result_controls.addWidget(donate_button)
        result_controls.addWidget(repository_button)
        layout.addLayout(result_controls)

        self.results = ResultsTable(0, 5)
        self.results.setObjectName("results_table")
        self.results.setHorizontalHeaderLabels(
            ["", "Rank", "Similarity", "Sample", "Full path"]
        )
        self.results.verticalHeader().setVisible(False)
        self.results.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results.setStyleSheet("ResultsTable { outline: 0; }")
        self.results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results.setDragEnabled(True)
        self.results.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.results.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.results.setSortingEnabled(False)
        self.results.horizontalHeader().setSortIndicator(1, Qt.SortOrder.AscendingOrder)
        self.results.doubleClicked.connect(self.play_selected_result)
        self.results.currentCellChanged.connect(self._result_selection_changed)
        self.results.selected_row_clicked_again.connect(self.play_selected_result)
        self.results.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results.customContextMenuRequested.connect(self.show_result_menu)
        self.results.horizontalHeader().setStretchLastSection(True)
        self.results.setColumnWidth(0, 30)
        self.results.setColumnWidth(1, 60)
        self.results.setColumnWidth(2, 90)
        self.results.setColumnWidth(3, 250)
        self.results.verticalHeader().setDefaultSectionSize(46)
        self.results.setItemDelegate(UnhighlightedItemDelegate(self.results))
        self.results.setItemDelegateForColumn(0, PlayIndicatorDelegate(self.results))
        self.results.setItemDelegateForColumn(3, WaveformDelegate(self.results))
        self.results.verticalScrollBar().valueChanged.connect(self._schedule_visible_waveforms)
        self.results.horizontalHeader().sortIndicatorChanged.connect(
            self._results_sort_changed
        )
        layout.addWidget(self.results, 1)
        layout.addWidget(library_group)
        self.setCentralWidget(root)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self.play_selected_result)

    def _populate_theme_combo(self) -> None:
        selected = str(self.settings.value("theme", "Cyber"))
        themes = available_themes()
        if selected not in themes:
            selected = "System"
        with QSignalBlocker(self.theme_combo):
            self.theme_combo.clear()
            for name in themes:
                self.theme_combo.addItem(name, name)
            selected_index = self.theme_combo.findData(selected)
            self.theme_combo.setCurrentIndex(max(0, selected_index))
            self.theme_combo.insertSeparator(self.theme_combo.count())
            self.theme_combo.addItem("Refresh Themes…", "__refresh__")
            self.theme_combo.addItem("Open Theme Folder…", "__open__")

    def _theme_combo_changed(self, index: int) -> None:
        choice = self.theme_combo.itemData(index)
        if choice == "__refresh__":
            self._populate_theme_combo()
            self.status.setText("Theme list refreshed.")
        elif choice == "__open__":
            self.open_theme_folder()
            self._populate_theme_combo()
        elif isinstance(choice, str):
            self.set_theme(choice)

    def set_theme(self, name: str) -> None:
        resolved = apply_theme(name)
        self.settings.setValue("theme", resolved)
        self.settings.sync()
        self.status.setText(f"Theme: {resolved}")

    def open_theme_folder(self) -> None:
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(theme_directory()))):
            QMessageBox.warning(self, "Warbeats SonicDNA", "Could not open the theme folder.")

    def _build_audio(self) -> None:
        volume = self.volume_slider.value() / 100.0
        self.player, self.playback_backend = create_audio_player(volume, self)
        self.player.playing_changed.connect(self._playback_state_changed)
        self.player.progress_changed.connect(self._playback_progress_changed)

    def _restore_settings(self) -> None:
        geometry = self.settings.value("window_geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self._ensure_window_position_visible()
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

    def _ensure_window_position_visible(self) -> None:
        """Keep restored geometry on-screen and out of negative coordinates."""
        frame = self.frameGeometry()
        screen = QApplication.screenAt(frame.center())
        if screen is None or screen.availableGeometry().right() < 0:
            screen = QApplication.primaryScreen()
        if screen is None:
            self.move(max(0, self.x()), max(0, self.y()))
            return

        available = screen.availableGeometry()
        left = max(0, available.left())
        top = max(0, available.top())
        max_x = max(left, available.right() - frame.width() + 1)
        max_y = max(top, available.bottom() - frame.height() + 1)
        self.move(
            min(max(left, self.x()), max_x),
            min(max(top, self.y()), max_y),
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
                self._invalidate_sample_cache()

    def remove_folders(self) -> None:
        selected = self.folder_list.selectedItems()
        if not selected:
            return
        if self.worker_thread is not None and self.worker_thread.isRunning():
            QMessageBox.information(
                self,
                "Operation in Progress",
                "Wait for the current scan or search to finish, or cancel it, before removing "
                "a Sample Library.",
            )
            return
        noun = "library" if len(selected) == 1 else "libraries"
        choice = QMessageBox.question(
            self,
            "Remove Sample Libraries",
            f"Remove the selected {noun} from SonicDNA?\n\n"
            "Choose Yes to also delete its cached audio fingerprints. Re-adding it will require "
            "a full scan.\n\n"
            "Choose No to keep the cache for faster re-adding later. Source audio files are "
            "never deleted.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if choice == QMessageBox.StandardButton.Cancel:
            return

        removed_entries = 0
        if choice == QMessageBox.StandardButton.Yes:
            try:
                with IndexDatabase() as database:
                    for item in selected:
                        removed_entries += database.remove_library(Path(item.text()))
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Database Cleanup Failed",
                    f"The libraries were not removed because their cached audio fingerprints "
                    f"could not "
                    f"be deleted:\n\n{type(exc).__name__}: {exc}",
                )
                return

        for item in selected:
            self.folder_list.takeItem(self.folder_list.row(item))
        self._invalidate_sample_cache()
        if choice == QMessageBox.StandardButton.Yes:
            self.status.setText(
                f"Removed {len(selected)} {noun} and {removed_entries} cached audio fingerprints."
            )
        else:
            self.status.setText(
                f"Removed {len(selected)} {noun}; cached audio fingerprints were retained."
            )

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
            self.query_waveform.clear()
            self.query_waveform.set_filename(self.query_path.name)
            task = WaveformTask(-1, self.query_path, bins=320)
            task.signals.loaded.connect(self._query_waveform_loaded)
            self.waveform_pool.start(task)

    def _query_waveform_loaded(self, _row: int, path: str, points: object) -> None:
        if self.query_path is None or str(self.query_path) != path:
            return
        self.query_waveform.set_points(list(points))

    def scan(self) -> None:
        if not self.folders():
            QMessageBox.information(self, "SonicDNA", "Add at least one library folder first.")
            return
        self._start_worker(None, refresh_index=True)

    def find_similar(self) -> None:
        if self.query_path is None:
            QMessageBox.information(self, "SonicDNA", "Select or drop a query sample first.")
            return
        if not self.folders():
            QMessageBox.information(self, "SonicDNA", "Add at least one library folder first.")
            return
        self._start_worker(self.query_path, refresh_index=False)

    def _start_worker(self, query: Path | None, refresh_index: bool) -> None:
        if self.worker_thread is not None:
            return
        if refresh_index:
            self._invalidate_sample_cache()
        folders = self.folders()
        folder_key = tuple(str(folder.resolve()) for folder in folders)
        use_cache = (
            query is not None
            and not refresh_index
            and self._sample_cache is not None
            and folder_key == self._sample_cache_folders
        )
        self.progress.setValue(0)
        self.progress.setRange(0, 100)
        self._operation_failed = False
        if refresh_index:
            self.status.setText("Starting library scan…")
        elif use_cache:
            self.status.setText("Searching cached audio fingerprints…")
        else:
            self.status.setText("Loading cached audio fingerprints…")
            self.progress.setRange(0, 0)
        self.scan_button.setEnabled(False)
        self.find_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.worker_thread = QThread(self)
        self._worker_folder_key = folder_key
        self._active_index_scan_times = (
            dict(self._sample_cache_scan_times) if use_cache else {}
        )
        self.worker = LibraryWorker(
            folders,
            query,
            self.result_count.value(),
            weights=self.similarity_weights(),
            refresh_index=refresh_index,
            cached_samples=self._sample_cache if use_cache else None,
            cached_scan_times=self._sample_cache_scan_times if use_cache else None,
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.discovery_progress.connect(self._on_discovery_progress)
        self.worker.progress.connect(self._on_progress)
        self.worker.folder_complete.connect(self._on_folder_complete)
        self.worker.fingerprint_loading.connect(self._on_fingerprint_loading)
        self.worker.search_progress.connect(self._on_search_progress)
        self.worker.samples_ready.connect(self._cache_worker_samples)
        self.worker.results_ready.connect(self._show_results)
        self.worker.failed.connect(self._show_error)
        self.worker.finished.connect(self._work_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self._thread_finished)
        self.worker_thread.start()

    def _invalidate_sample_cache(self) -> None:
        self._sample_cache = None
        self._sample_cache_folders = ()
        self._sample_cache_scan_times = {}

    def _cache_worker_samples(
        self,
        samples: list[IndexedSample],
        scan_times: dict[str, str | None],
    ) -> None:
        current_key = tuple(str(folder.resolve()) for folder in self.folders())
        if self._worker_folder_key != current_key:
            return
        self._sample_cache = list(samples)
        self._sample_cache_folders = self._worker_folder_key
        self._sample_cache_scan_times = dict(scan_times)
        self._active_index_scan_times = dict(scan_times)

    def _index_freshness_text(self) -> str:
        timestamps: list[datetime] = []
        for value in self._active_index_scan_times.values():
            if not value:
                continue
            try:
                timestamps.append(datetime.fromisoformat(value).astimezone())
            except ValueError:
                continue
        if not timestamps:
            return ""
        oldest = min(timestamps)
        formatted = oldest.strftime("%b %d, %Y at %I:%M %p").replace(" 0", " ")
        suffix = " (oldest library)" if len(timestamps) > 1 else ""
        return f"Index last updated {formatted}{suffix}."

    def cancel_work(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.status.setText("Cancelling after the current file…")

    def _on_progress(self, path: str, current: int, total: int) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(round(current / max(total, 1) * 100))
        self.status.setText(f"Scanning {current}/{total}: {Path(path).name}")

    def _on_discovery_progress(self, folder: str, discovered: int) -> None:
        folder_path = Path(folder)
        folder_name = folder_path.name or str(folder_path)
        self.progress.setRange(0, 0)
        self.status.setText(
            f"Building file list for {folder_name}: {discovered} audio file(s) found…"
        )

    def _on_fingerprint_loading(self, loaded: int, total: int) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(loaded if total else 1)
        self.status.setText(
            f"Loading cached audio fingerprints: {loaded:,} / {total:,}"
        )

    def _on_search_progress(self, stage: str, current: int, total: int) -> None:
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(current)
            self.status.setText(f"{stage}: {current:,} / {total:,}")
        else:
            self.progress.setRange(0, 0)
            self.status.setText(f"{stage}…")

    def _on_folder_complete(self, folder: str, summary: ScanSummary) -> None:
        self.progress.setRange(0, 100)
        self.status.setText(
            f"{Path(folder).name}: {summary.indexed} indexed, "
            f"{summary.unchanged} unchanged, {len(summary.errors)} skipped"
        )

    def _show_results(
        self,
        results: list[SearchResult],
        searched_files: int | None = None,
        elapsed_seconds: float | None = None,
    ) -> None:
        self.progress.setRange(0, 100)
        self.current_results = results
        self.playing_row = -1
        self.playing_path = None
        self._waveform_pending.clear()
        self.results.setSortingEnabled(False)
        self.results.horizontalHeader().setSortIndicator(1, Qt.SortOrder.AscendingOrder)
        self.results.setRowCount(len(results))
        for row, result in enumerate(results):
            rank = NumericTableWidgetItem(str(row + 1), row + 1)
            score = NumericTableWidgetItem(
                f"{result.similarity_score:.2f}", result.similarity_score
            )
            filename = QTableWidgetItem(result.path.name)
            full_path = QTableWidgetItem(str(result.path))
            full_path.setData(Qt.ItemDataRole.UserRole, str(result.path))
            indicator = NumericTableWidgetItem("", row + 1)
            for column, item in enumerate((indicator, rank, score, filename, full_path)):
                self.results.setItem(row, column, item)
        self.results.setSortingEnabled(True)
        self.results.sortItems(1, Qt.SortOrder.AscendingOrder)
        status = f"Found {len(results)} similar sample(s)."
        if searched_files is not None and elapsed_seconds is not None:
            status += f" Searched {searched_files} files in {elapsed_seconds:.2f} seconds."
        freshness = self._index_freshness_text()
        if freshness:
            status += f" {freshness}"
        self.status.setText(status)
        QTimer.singleShot(0, self._schedule_visible_waveforms)

    def _schedule_visible_waveforms(self) -> None:
        if self.results.rowCount() == 0:
            return
        first = self.results.indexAt(QPoint(0, 0)).row()
        last = self.results.indexAt(QPoint(0, self.results.viewport().height() - 1)).row()
        first = max(0, first if first >= 0 else 0)
        last = min(self.results.rowCount() - 1, last if last >= 0 else first + 20)
        for row in range(first, last + 1):
            waveform_item = self.results.item(row, 3)
            path_item = self.results.item(row, 4)
            if waveform_item is None or path_item is None:
                continue
            path_text = str(path_item.data(Qt.ItemDataRole.UserRole))
            if waveform_item.data(WAVEFORM_ROLE) is not None or path_text in self._waveform_pending:
                continue
            self._waveform_pending.add(path_text)
            task = WaveformTask(row, Path(path_text))
            task.signals.loaded.connect(self._waveform_loaded)
            self.waveform_pool.start(task)

    def _results_sort_changed(self, _column: int, _order: Qt.SortOrder) -> None:
        # Sorting changes which paths are visible without necessarily moving the scrollbar.
        QTimer.singleShot(0, self._schedule_visible_waveforms)

    def _waveform_loaded(self, row: int, path: str, points: object) -> None:
        self._waveform_pending.discard(path)
        matching_row = row if row < self.results.rowCount() else -1
        if matching_row >= 0:
            candidate = self.results.item(matching_row, 4)
            if candidate is None or str(candidate.data(Qt.ItemDataRole.UserRole)) != path:
                matching_row = -1
        if matching_row < 0:
            for candidate_row in range(self.results.rowCount()):
                candidate = self.results.item(candidate_row, 4)
                if candidate is not None and str(candidate.data(Qt.ItemDataRole.UserRole)) == path:
                    matching_row = candidate_row
                    break
        if matching_row < 0:
            return
        waveform_item = self.results.item(matching_row, 3)
        if waveform_item is None:
            return
        waveform_item.setData(WAVEFORM_ROLE, points)
        self.results.viewport().update(self.results.visualItemRect(waveform_item))

    def _show_error(self, message: str) -> None:
        self.progress.setRange(0, 100)
        self._operation_failed = True
        self.status.setText("Operation failed")
        QMessageBox.critical(self, "SonicDNA Error", message)

    def _work_finished(self, cancelled: bool) -> None:
        self.progress.setRange(0, 100)
        if cancelled:
            self.status.setText("Operation cancelled; completed records were preserved.")
        else:
            self.progress.setValue(100)
            if (
                not self._operation_failed
                and self.worker is not None
                and self.worker.query is None
            ):
                freshness = self._index_freshness_text()
                self.status.setText(
                    f"Library scan complete. {freshness}".rstrip()
                )
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
            self.playing_path = None
            self.play_path(self.query_path)

    def toggle_query_playback(self) -> None:
        """Play the query, or stop whichever sample is currently playing."""
        if self._audio_is_playing:
            self.stop_audio()
        else:
            self.play_query()

    def _set_query_playback_button_state(self, playing: bool) -> None:
        glyph = "fa6s.stop" if playing else "fa6s.play"
        action = "Stop playback" if playing else "Play query sample"
        self.query_playback_button.set_glyph(glyph)
        self.query_playback_button.setToolTip(action)
        self.query_playback_button.setAccessibleName(action)

    def play_selected_result(self) -> None:
        row = self.results.currentRow()
        if row >= 0:
            item = self.results.item(row, 4)
            self.playing_row = row
            self.playing_path = Path(item.data(Qt.ItemDataRole.UserRole))
            self.play_path(self.playing_path)

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
        self._audio_is_playing = playing_now
        self._set_query_playback_button_state(playing_now)
        if not playing_now:
            self._clear_playback_progress()

    def _playback_progress_changed(self, progress: float) -> None:
        if not self._audio_is_playing:
            return
        if self.playing_path is None:
            self.query_waveform.set_playback_progress(progress)
            return
        for row in range(self.results.rowCount()):
            path_item = self.results.item(row, 4)
            row_path = (
                Path(path_item.data(Qt.ItemDataRole.UserRole)) if path_item is not None else None
            )
            waveform_item = self.results.item(row, 3)
            if waveform_item is not None:
                waveform_item.setData(
                    PLAYBACK_PROGRESS_ROLE,
                    progress if row_path == self.playing_path else None,
                )
        self.results.viewport().update()

    def _clear_playback_progress(self) -> None:
        self.query_waveform.set_playback_progress(None)
        for row in range(self.results.rowCount()):
            waveform_item = self.results.item(row, 3)
            if waveform_item is not None:
                waveform_item.setData(PLAYBACK_PROGRESS_ROLE, None)
        self.results.viewport().update()

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
            "Closest",
        )

    def _update_weights_button(self) -> None:
        name = self.active_weight_preset()
        available = {**BUILTIN_PRESETS, **self.custom_weight_presets()}
        baseline = available.get(name, BUILTIN_PRESETS["Closest"])
        marker = "*" if not weights_match(self.similarity_weights(), baseline) else ""
        self.weights_button.setText(f"Weights: {name}{marker}…")

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

    def open_repository(self) -> None:
        self._open_external_url(REPOSITORY_URL, "repository")

    def open_donate(self) -> None:
        self._open_external_url(DONATE_URL, "donation page")

    def _open_external_url(self, url: str, description: str) -> None:
        if not QDesktopServices.openUrl(QUrl(url)):
            QMessageBox.warning(
                self, "Warbeats SonicDNA", f"Could not open the {description}."
            )
