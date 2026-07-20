"""SQLite persistence for library folders and acoustic feature vectors."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from platformdirs import user_data_path

from sonicdna.feature_schema import FEATURE_VECTOR_LENGTH, FEATURE_VERSION

DATABASE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class IndexedSample:
    path: Path
    modified_ns: int
    size_bytes: int
    vector: np.ndarray


def default_database_path() -> Path:
    """Return the platform-appropriate persistent index location."""
    return user_data_path("SonicDNA", appauthor=False, ensure_exists=True) / "index.db"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class IndexDatabase:
    """Repository for SonicDNA's persistent SQLite index."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = (path or default_database_path()).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    def __enter__(self) -> IndexDatabase:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS library_folders (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 1,
                added_at TEXT NOT NULL,
                last_scan_at TEXT
            );
            CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                library_folder_id INTEGER,
                filename TEXT NOT NULL,
                extension TEXT NOT NULL,
                modified_ns INTEGER NOT NULL,
                size_bytes INTEGER NOT NULL,
                duration_seconds REAL,
                sample_rate INTEGER,
                channels INTEGER,
                feature_version INTEGER NOT NULL,
                feature_vector BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (library_folder_id) REFERENCES library_folders(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS indexing_errors (
                path TEXT PRIMARY KEY,
                library_folder_id INTEGER NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                FOREIGN KEY (library_folder_id) REFERENCES library_folders(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_samples_path ON samples(path);
            CREATE INDEX IF NOT EXISTS idx_samples_folder ON samples(library_folder_id);
            CREATE INDEX IF NOT EXISTS idx_samples_modified ON samples(modified_ns);
            """
        )
        self.connection.execute(
            "INSERT OR REPLACE INTO app_metadata(key, value) VALUES (?, ?)",
            ("database_schema_version", str(DATABASE_SCHEMA_VERSION)),
        )
        self.connection.commit()

    def folder_id(self, folder: Path) -> int:
        canonical = str(folder.expanduser().resolve())
        self.connection.execute(
            "INSERT OR IGNORE INTO library_folders(path, added_at) VALUES (?, ?)",
            (canonical, utc_now()),
        )
        row = self.connection.execute(
            "SELECT id FROM library_folders WHERE path = ?", (canonical,)
        ).fetchone()
        if row is None:
            raise RuntimeError(f"unable to register library folder: {folder}")
        self.connection.commit()
        return int(row["id"])

    def fingerprints(self, folder_id: int) -> dict[str, tuple[int, int, int]]:
        rows = self.connection.execute(
            "SELECT path, modified_ns, size_bytes, feature_version FROM samples "
            "WHERE library_folder_id = ?",
            (folder_id,),
        )
        return {
            str(row["path"]):
                (int(row["modified_ns"]), int(row["size_bytes"]), int(row["feature_version"]))
            for row in rows
        }

    def store_sample(
        self,
        folder_id: int,
        path: Path,
        modified_ns: int,
        size_bytes: int,
        vector: np.ndarray,
    ) -> None:
        if vector.shape != (FEATURE_VECTOR_LENGTH,):
            raise ValueError(f"unexpected feature vector length: {vector.size}")
        canonical = str(path.resolve())
        now = utc_now()
        blob = vector.astype("<f4", copy=False).tobytes()
        self.connection.execute(
            """
            INSERT INTO samples (
                path, library_folder_id, filename, extension, modified_ns, size_bytes,
                feature_version, feature_vector, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                library_folder_id = excluded.library_folder_id,
                filename = excluded.filename,
                extension = excluded.extension,
                modified_ns = excluded.modified_ns,
                size_bytes = excluded.size_bytes,
                feature_version = excluded.feature_version,
                feature_vector = excluded.feature_vector,
                updated_at = excluded.updated_at
            """,
            (canonical, folder_id, path.name, path.suffix.lower(), modified_ns, size_bytes,
             FEATURE_VERSION, blob, now, now),
        )
        self.connection.execute("DELETE FROM indexing_errors WHERE path = ?", (canonical,))
        self.connection.commit()

    def record_error(self, folder_id: int, path: Path, error: Exception) -> None:
        self.connection.execute(
            """
            INSERT INTO indexing_errors(path, library_folder_id, error_type, error_message, occurred_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET error_type = excluded.error_type,
                error_message = excluded.error_message, occurred_at = excluded.occurred_at
            """,
            (str(path.resolve()), folder_id, type(error).__name__, str(error), utc_now()),
        )
        self.connection.commit()

    def remove_missing(self, folder_id: int, present_paths: set[str]) -> int:
        stored = self.connection.execute(
            "SELECT path FROM samples WHERE library_folder_id = ?", (folder_id,)
        ).fetchall()
        missing = [(str(row["path"]),) for row in stored if str(row["path"]) not in present_paths]
        if missing:
            self.connection.executemany("DELETE FROM samples WHERE path = ?", missing)
            self.connection.commit()
        return len(missing)

    def finish_scan(self, folder_id: int) -> None:
        self.connection.execute(
            "UPDATE library_folders SET last_scan_at = ? WHERE id = ?", (utc_now(), folder_id)
        )
        self.connection.commit()

    def samples_for_folder(self, folder_id: int) -> list[IndexedSample]:
        rows = self.connection.execute(
            "SELECT path, modified_ns, size_bytes, feature_vector FROM samples "
            "WHERE library_folder_id = ? AND feature_version = ? ORDER BY path",
            (folder_id, FEATURE_VERSION),
        ).fetchall()
        samples: list[IndexedSample] = []
        for row in rows:
            vector = np.frombuffer(row["feature_vector"], dtype="<f4").copy()
            if vector.shape == (FEATURE_VECTOR_LENGTH,):
                samples.append(IndexedSample(
                    Path(row["path"]), int(row["modified_ns"]), int(row["size_bytes"]), vector
                ))
        return samples

    def rebuild_folder(self, folder_id: int) -> int:
        with closing(self.connection.execute(
            "SELECT COUNT(*) FROM samples WHERE library_folder_id = ?", (folder_id,)
        )) as cursor:
            count = int(cursor.fetchone()[0])
        self.connection.execute("DELETE FROM samples WHERE library_folder_id = ?", (folder_id,))
        self.connection.execute("DELETE FROM indexing_errors WHERE library_folder_id = ?", (folder_id,))
        self.connection.commit()
        return count

