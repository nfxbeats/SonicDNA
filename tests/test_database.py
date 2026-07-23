from pathlib import Path

import numpy as np

from sonicdna.database import IndexDatabase
from sonicdna.feature_schema import FEATURE_VECTOR_LENGTH


def test_vector_round_trip(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    sample = library / "kick.wav"
    sample.write_bytes(b"fixture")
    vector = np.arange(FEATURE_VECTOR_LENGTH, dtype=np.float32)

    with IndexDatabase(tmp_path / "index.db") as database:
        folder_id = database.folder_id(library)
        stat = sample.stat()
        database.store_sample(folder_id, sample, stat.st_mtime_ns, stat.st_size, vector)
        load_progress: list[tuple[int, int]] = []
        restored = database.samples_for_folder(
            folder_id,
            progress=lambda current, total: load_progress.append((current, total)),
            batch_size=1,
        )

    assert len(restored) == 1
    assert restored[0].path == sample.resolve()
    np.testing.assert_array_equal(restored[0].vector, vector)
    assert load_progress[-1] == (1, 1)


def test_remove_library_deletes_cached_samples_and_registration(tmp_path: Path) -> None:
    library = tmp_path / "temporary library"
    library.mkdir()
    sample = library / "snare.wav"
    sample.write_bytes(b"fixture")
    vector = np.ones(FEATURE_VECTOR_LENGTH, dtype=np.float32)

    with IndexDatabase(tmp_path / "index.db") as database:
        folder_id = database.folder_id(library)
        stat = sample.stat()
        database.store_sample(folder_id, sample, stat.st_mtime_ns, stat.st_size, vector)

        assert database.remove_library(library) == 1
        assert database.samples_for_folder(folder_id) == []
        assert database.remove_library(library) == 0
        new_folder_id = database.folder_id(library)

    assert isinstance(new_folder_id, int)


def test_library_status_tracks_completed_index(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()

    with IndexDatabase(tmp_path / "index.db") as database:
        missing = database.library_status(library)
        assert missing.folder_id is None
        assert missing.needs_scan

        folder_id = database.folder_id(library)
        incomplete = database.library_status(library)
        assert incomplete.folder_id == folder_id
        assert incomplete.last_scan_at is None
        assert incomplete.needs_scan

        database.finish_scan(folder_id)
        complete = database.library_status(library)
        assert complete.last_scan_at is not None
        assert not complete.needs_scan
