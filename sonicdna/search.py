"""Nearest-neighbor search over indexed feature vectors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Mapping
import os

import numpy as np
from sklearn.preprocessing import StandardScaler

from sonicdna.database import IndexedSample
from sonicdna.features import SUPPORTED_EXTENSIONS
from sonicdna.weighting import feature_weight_vector


@dataclass(frozen=True, slots=True)
class SearchResult:
    path: Path
    similarity_score: float
    raw_distance: float


def audio_files(
    folder: Path,
    discovery_progress: Callable[[int], None] | None = None,
) -> list[Path]:
    """Recursively collect supported files and report the growing audio-file count."""
    discovered: list[Path] = []
    for root, _directories, filenames in os.walk(folder):
        root_path = Path(root)
        discovered.extend(
            root_path / filename
            for filename in filenames
            if Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if discovery_progress is not None:
            discovery_progress(len(discovered))
    return sorted(discovered)


def search_index(
    query_vector: np.ndarray,
    query: Path,
    samples: list[IndexedSample],
    limit: int = 10,
    weights: Mapping[str, float] | None = None,
    progress: Callable[[str, int, int], None] | None = None,
) -> list[SearchResult]:
    """Rank indexed samples by standardized cosine distance."""
    if progress is not None:
        progress(
            f"Preparing candidate list from {len(samples):,} cached audio fingerprints",
            0,
            0,
        )
    query_resolved = query.resolve()
    candidates = [sample for sample in samples if sample.path.resolve() != query_resolved]
    if not candidates:
        return []
    candidate_count = len(candidates)
    if progress is not None:
        progress(f"Preparing matrix for {candidate_count:,} candidates", 0, 0)
    matrix = np.vstack([sample.vector for sample in candidates])
    if progress is not None:
        progress(f"Standardizing {query_vector.size:,} fingerprint dimensions", 0, 0)
    scaler = StandardScaler().fit(matrix)
    indexed = scaler.transform(matrix)
    needle = scaler.transform(query_vector.reshape(1, -1))[0]
    if progress is not None:
        progress("Applying 7 similarity weight groups", 0, 0)
    expanded_weights = feature_weight_vector(weights)
    indexed *= expanded_weights
    needle *= expanded_weights
    if progress is not None:
        progress(f"Comparing {candidate_count:,} candidate samples", 0, 0)
    norms = np.linalg.norm(indexed, axis=1) * np.linalg.norm(needle)
    similarities = np.divide(indexed @ needle, norms, out=np.zeros(len(candidates)), where=norms > 0)
    distances = 1.0 - np.clip(similarities, -1.0, 1.0)
    if progress is not None:
        progress(f"Ranking all {candidate_count:,} candidates", 0, 0)
    order = np.argsort(distances)[:limit]
    return [
        SearchResult(candidates[i].path,
                     float(np.clip((1.0 - distances[i] / 2.0) * 100.0, 0, 100)),
                     float(distances[i]))
        for i in order
    ]
