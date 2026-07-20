"""User-facing similarity groups mapped onto the versioned feature schema."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from sonicdna.feature_schema import FEATURE_SCHEMA, FEATURE_VECTOR_LENGTH

DEFAULT_WEIGHTS: dict[str, float] = {
    "body_pitch": 0.90,
    "attack": 0.85,
    "decay": 0.70,
    "brightness": 0.50,
    "timbre": 0.70,
    "noise": 0.45,
    "duration": 0.40,
}

WEIGHT_LABELS: dict[str, str] = {
    "body_pitch": "Body / Pitch",
    "attack": "Attack",
    "decay": "Decay",
    "brightness": "Brightness",
    "timbre": "Timbre",
    "noise": "Noise / Distortion",
    "duration": "Duration",
}

WEIGHT_FEATURE_GROUPS: dict[str, tuple[str, ...]] = {
    "body_pitch": ("low_frequency_body",),
    "attack": ("attack",),
    "decay": ("decay",),
    "brightness": ("brightness",),
    "timbre": ("timbre", "mel_spectrum", "energy"),
    "noise": ("noise",),
    "duration": ("duration",),
}


def normalize_weights(weights: Mapping[str, float] | None = None) -> dict[str, float]:
    """Return a complete set of finite values clamped between zero and one."""
    supplied = weights or {}
    normalized: dict[str, float] = {}
    for key, default in DEFAULT_WEIGHTS.items():
        value = float(supplied.get(key, default))
        if not np.isfinite(value):
            value = default
        normalized[key] = float(np.clip(value, 0.0, 1.0))
    return normalized


def feature_weight_vector(weights: Mapping[str, float] | None = None) -> np.ndarray:
    """Expand seven user weights into the deterministic 177-value feature layout."""
    normalized = normalize_weights(weights)
    vector = np.zeros(FEATURE_VECTOR_LENGTH, dtype=np.float32)
    for key, feature_groups in WEIGHT_FEATURE_GROUPS.items():
        for group in feature_groups:
            start, end = FEATURE_SCHEMA[group]
            vector[start:end] = normalized[key]
    if np.any(vector == 0) and all(value > 0 for value in normalized.values()):
        raise ValueError("one or more feature dimensions are not assigned to a weight group")
    return vector

