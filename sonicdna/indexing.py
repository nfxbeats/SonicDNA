"""Recursive, incremental library indexing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable

from sonicdna.database import IndexDatabase
from sonicdna.feature_schema import FEATURE_VERSION
from sonicdna.features import extract_features
from sonicdna.search import audio_files


@dataclass(slots=True)
class ScanSummary:
    discovered: int = 0
    indexed: int = 0
    unchanged: int = 0
    removed: int = 0
    errors: list[str] = field(default_factory=list)
    cancelled: bool = False


def update_index(
    database: IndexDatabase,
    folder: Path,
    rebuild: bool = False,
    progress: Callable[[Path, int, int], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> tuple[int, ScanSummary]:
    """Index new/changed files, retain unchanged vectors, and remove missing files."""
    folder_id = database.folder_id(folder)
    if rebuild:
        database.rebuild_folder(folder_id)
    known = database.fingerprints(folder_id)
    paths = audio_files(folder)
    present = {str(path.resolve()) for path in paths}
    summary = ScanSummary(discovered=len(paths))
    for position, path in enumerate(paths, 1):
        if is_cancelled is not None and is_cancelled():
            summary.cancelled = True
            break
        canonical = str(path.resolve())
        try:
            stat = path.stat()
            fingerprint = (stat.st_mtime_ns, stat.st_size, FEATURE_VERSION)
            if known.get(canonical) == fingerprint:
                summary.unchanged += 1
                continue
            vector = extract_features(path)
            database.store_sample(folder_id, path, stat.st_mtime_ns, stat.st_size, vector)
            summary.indexed += 1
        except Exception as exc:  # Decoder libraries expose unrelated exception hierarchies.
            database.record_error(folder_id, path, exc)
            summary.errors.append(f"{path}: {type(exc).__name__}: {exc}")
        finally:
            if progress is not None:
                progress(path, position, len(paths))
    if not summary.cancelled:
        summary.removed = database.remove_missing(folder_id, present)
        database.finish_scan(folder_id)
    return folder_id, summary
