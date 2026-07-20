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
        restored = database.samples_for_folder(folder_id)

    assert len(restored) == 1
    assert restored[0].path == sample.resolve()
    np.testing.assert_array_equal(restored[0].vector, vector)

