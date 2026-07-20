"""Nearest-neighbor search over indexed feature vectors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping

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


def audio_files(folder: Path) -> list[Path]:
    return sorted(
        path for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def search_index(
    query_vector: np.ndarray,
    query: Path,
    samples: list[IndexedSample],
    limit: int = 10,
    weights: Mapping[str, float] | None = None,
) -> list[SearchResult]:
    """Rank indexed samples by standardized cosine distance."""
    query_resolved = query.resolve()
    candidates = [sample for sample in samples if sample.path.resolve() != query_resolved]
    if not candidates:
        return []
    matrix = np.vstack([sample.vector for sample in candidates])
    scaler = StandardScaler().fit(matrix)
    indexed = scaler.transform(matrix)
    needle = scaler.transform(query_vector.reshape(1, -1))[0]
    expanded_weights = feature_weight_vector(weights)
    indexed *= expanded_weights
    needle *= expanded_weights
    norms = np.linalg.norm(indexed, axis=1) * np.linalg.norm(needle)
    similarities = np.divide(indexed @ needle, norms, out=np.zeros(len(candidates)), where=norms > 0)
    distances = 1.0 - np.clip(similarities, -1.0, 1.0)
    order = np.argsort(distances)[:limit]
    return [
        SearchResult(candidates[i].path,
                     float(np.clip((1.0 - distances[i] / 2.0) * 100.0, 0, 100)),
                     float(distances[i]))
        for i in order
    ]
