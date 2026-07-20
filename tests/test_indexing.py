from pathlib import Path

import numpy as np

from sonicdna.database import IndexDatabase
from sonicdna.feature_schema import FEATURE_VECTOR_LENGTH
from sonicdna.indexing import update_index


def test_incremental_scan_and_missing_cleanup(tmp_path: Path, monkeypatch) -> None:
    library = tmp_path / "library"
    library.mkdir()
    sample = library / "kick.wav"
    sample.write_bytes(b"fixture")
    calls: list[Path] = []
    progress_updates: list[tuple[Path, int, int]] = []

    def fake_extract(path: Path) -> np.ndarray:
        calls.append(path)
        return np.ones(FEATURE_VECTOR_LENGTH, dtype=np.float32)

    monkeypatch.setattr("sonicdna.indexing.extract_features", fake_extract)
    with IndexDatabase(tmp_path / "index.db") as database:
        folder_id, first = update_index(database, library)
        _, second = update_index(
            database,
            library,
            progress=lambda path, current, total: progress_updates.append(
                (path, current, total)
            ),
        )
        sample.unlink()
        _, third = update_index(database, library)
        remaining = database.samples_for_folder(folder_id)

    assert first.indexed == 1
    assert second.indexed == 0
    assert second.unchanged == 1
    assert progress_updates == [(sample, 1, 1)]
    assert calls == [sample]
    assert third.removed == 1
    assert remaining == []
