from pathlib import Path

import numpy as np

from sonicdna.database import IndexDatabase
from sonicdna.feature_schema import FEATURE_VECTOR_LENGTH
from sonicdna.workers import LibraryWorker


def test_search_uses_completed_index_without_folder_discovery(
    tmp_path: Path, monkeypatch
) -> None:
    library = tmp_path / "library"
    library.mkdir()
    sample = library / "kick.wav"
    sample.write_bytes(b"indexed")
    query = tmp_path / "query.wav"
    query.write_bytes(b"query")
    database_path = tmp_path / "index.db"
    vector = np.ones(FEATURE_VECTOR_LENGTH, dtype=np.float32)

    with IndexDatabase(database_path) as database:
        folder_id = database.folder_id(library)
        stat = sample.stat()
        database.store_sample(folder_id, sample, stat.st_mtime_ns, stat.st_size, vector)
        database.finish_scan(folder_id)

    def unexpected_scan(*_args, **_kwargs):
        raise AssertionError("completed libraries must not be scanned during Find Similar")

    monkeypatch.setattr("sonicdna.workers.update_index", unexpected_scan)
    def fake_query_features(_path, progress=None):
        if progress is not None:
            progress("Query fingerprint complete", 6, 6)
        return vector

    monkeypatch.setattr("sonicdna.workers.extract_features", fake_query_features)

    discoveries: list[tuple[str, int]] = []
    cached_batches: list[tuple[object, object]] = []
    result_batches: list[tuple[object, int, float]] = []
    search_updates: list[tuple[str, int, int]] = []
    worker = LibraryWorker(
        [library],
        query,
        database_path=database_path,
        refresh_index=False,
    )
    worker.discovery_progress.connect(
        lambda folder, count: discoveries.append((folder, count))
    )
    worker.samples_ready.connect(
        lambda samples, times: cached_batches.append((samples, times))
    )
    worker.results_ready.connect(
        lambda results, searched, elapsed: result_batches.append(
            (results, searched, elapsed)
        )
    )
    worker.search_progress.connect(
        lambda stage, current, total: search_updates.append((stage, current, total))
    )

    worker.run()

    assert discoveries == []
    assert len(cached_batches) == 1
    assert len(cached_batches[0][0]) == 1
    assert result_batches[0][1] == 1
    assert result_batches[0][2] >= 0
    assert any(
        stage == "Preparing candidate list from 1 cached audio fingerprints"
        for stage, _current, _total in search_updates
    )
    assert any(
        stage == "Preparing matrix for 1 candidates"
        for stage, _current, _total in search_updates
    )
    assert all(
        total == 0
        for stage, _current, total in search_updates
        if not stage.startswith("Analyzing query")
    )
    assert search_updates[-1] == ("Ranking all 1 candidates", 0, 0)
