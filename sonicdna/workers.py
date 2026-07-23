"""Background Qt workers for indexing and similarity search."""

from __future__ import annotations

from pathlib import Path
from threading import Event
from time import perf_counter
from collections.abc import Mapping

from PySide6.QtCore import QObject, Signal, Slot

from sonicdna.database import IndexedSample, IndexDatabase, default_database_path
from sonicdna.features import extract_features
from sonicdna.indexing import update_index
from sonicdna.search import SearchResult, search_index


class LibraryWorker(QObject):
    """Scan one or more libraries and optionally perform a query."""

    progress = Signal(str, int, int)
    discovery_progress = Signal(str, int)
    folder_complete = Signal(str, object)
    fingerprint_loading = Signal(int, int)
    search_progress = Signal(str, int, int)
    samples_ready = Signal(object, object)
    results_ready = Signal(object, int, float)
    failed = Signal(str)
    finished = Signal(bool)

    def __init__(
        self,
        folders: list[Path],
        query: Path | None = None,
        limit: int = 25,
        rebuild: bool = False,
        database_path: Path | None = None,
        weights: Mapping[str, float] | None = None,
        refresh_index: bool = True,
        cached_samples: list[IndexedSample] | None = None,
        cached_scan_times: dict[str, str | None] | None = None,
    ) -> None:
        super().__init__()
        self.folders = folders
        self.query = query
        self.limit = limit
        self.rebuild = rebuild
        self.database_path = database_path or default_database_path()
        self.weights = dict(weights or {})
        self.refresh_index = refresh_index
        self.cached_samples = cached_samples
        self.cached_scan_times = dict(cached_scan_times or {})
        self._cancelled = Event()

    @Slot()
    def cancel(self) -> None:
        self._cancelled.set()

    @Slot()
    def run(self) -> None:
        try:
            samples = list(self.cached_samples) if self.cached_samples is not None else []
            scan_times = dict(self.cached_scan_times)
            if self.cached_samples is None:
                with IndexDatabase(self.database_path) as database:
                    folder_ids: list[int] = []
                    for folder in self.folders:
                        if self._cancelled.is_set():
                            break
                        status = database.library_status(folder)
                        if self.refresh_index or status.needs_scan:
                            self.discovery_progress.emit(str(folder), 0)
                            folder_id, summary = update_index(
                                database,
                                folder,
                                rebuild=self.rebuild,
                                discovery_progress=lambda count, folder=folder: (
                                    self.discovery_progress.emit(str(folder), count)
                                ),
                                progress=lambda path, current, total: self.progress.emit(
                                    str(path), current, total
                                ),
                                is_cancelled=self._cancelled.is_set,
                            )
                            self.folder_complete.emit(str(folder), summary)
                            status = database.library_status(folder)
                        else:
                            folder_id = status.folder_id
                        if folder_id is not None:
                            folder_ids.append(folder_id)
                        scan_times[str(folder.resolve())] = status.last_scan_at
                    total_samples = sum(
                        database.sample_count_for_folder(folder_id)
                        for folder_id in folder_ids
                    )
                    loaded_samples = 0
                    self.fingerprint_loading.emit(0, total_samples)
                    for folder_id in folder_ids:
                        folder_samples = database.samples_for_folder(
                            folder_id,
                            progress=lambda current, _folder_total, offset=loaded_samples: (
                                self.fingerprint_loading.emit(
                                    offset + current, total_samples
                                )
                            ),
                        )
                        samples.extend(folder_samples)
                        loaded_samples += len(folder_samples)
                if not self._cancelled.is_set():
                    self.samples_ready.emit(samples, scan_times)
            if self.query is not None and not self._cancelled.is_set():
                search_started = perf_counter()
                query_vector = extract_features(
                    self.query,
                    progress=lambda stage, current, total: self.search_progress.emit(
                        f"Analyzing query — {stage}", current, total
                    ),
                )
                results: list[SearchResult] = search_index(
                    query_vector,
                    self.query,
                    samples,
                    self.limit,
                    self.weights,
                    progress=lambda stage, current, total: self.search_progress.emit(
                        stage, current, total
                    ),
                )
                query_resolved = self.query.resolve()
                searched_files = sum(
                    sample.path.resolve() != query_resolved for sample in samples
                )
                self.results_ready.emit(
                    results, searched_files, perf_counter() - search_started
                )
        except Exception as exc:  # Worker boundary: present failures without crashing Qt.
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.finished.emit(self._cancelled.is_set())
