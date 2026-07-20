"""Background Qt workers for indexing and similarity search."""

from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from sonicdna.database import IndexDatabase, default_database_path
from sonicdna.features import extract_features
from sonicdna.indexing import update_index
from sonicdna.search import SearchResult, search_index


class LibraryWorker(QObject):
    """Scan one or more libraries and optionally perform a query."""

    progress = Signal(str, int, int)
    folder_complete = Signal(str, object)
    results_ready = Signal(object)
    failed = Signal(str)
    finished = Signal(bool)

    def __init__(
        self,
        folders: list[Path],
        query: Path | None = None,
        limit: int = 25,
        rebuild: bool = False,
        database_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.folders = folders
        self.query = query
        self.limit = limit
        self.rebuild = rebuild
        self.database_path = database_path or default_database_path()
        self._cancelled = Event()

    @Slot()
    def cancel(self) -> None:
        self._cancelled.set()

    @Slot()
    def run(self) -> None:
        try:
            samples = []
            with IndexDatabase(self.database_path) as database:
                for folder in self.folders:
                    if self._cancelled.is_set():
                        break
                    folder_id, summary = update_index(
                        database,
                        folder,
                        rebuild=self.rebuild,
                        progress=lambda path, current, total: self.progress.emit(
                            str(path), current, total
                        ),
                        is_cancelled=self._cancelled.is_set,
                    )
                    self.folder_complete.emit(str(folder), summary)
                    samples.extend(database.samples_for_folder(folder_id))
            if self.query is not None and not self._cancelled.is_set():
                query_vector = extract_features(self.query)
                results: list[SearchResult] = search_index(
                    query_vector, self.query, samples, self.limit
                )
                self.results_ready.emit(results)
        except Exception as exc:  # Worker boundary: present failures without crashing Qt.
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.finished.emit(self._cancelled.is_set())
