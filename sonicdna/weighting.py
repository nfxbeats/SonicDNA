"""User-facing similarity groups mapped onto the versioned feature schema."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from sonicdna.feature_schema import FEATURE_SCHEMA, FEATURE_VECTOR_LENGTH

DEFAULT_WEIGHTS: dict[str, float] = {
    "body_pitch": 1.00,
    "attack": 1.00,
    "decay": 1.00,
    "brightness": 1.00,
    "timbre": 1.00,
    "noise": 1.00,
    "duration": 1.00,
}

BUILTIN_PRESETS: dict[str, dict[str, float]] = {
    "Closest": dict(DEFAULT_WEIGHTS),
    "Kick": {
        "body_pitch": 0.90,
        "attack": 0.85,
        "decay": 0.70,
        "brightness": 0.50,
        "timbre": 0.70,
        "noise": 0.45,
        "duration": 0.40,
    },
    "Snare": {
        "body_pitch": 0.45,
        "attack": 0.90,
        "decay": 0.75,
        "brightness": 0.75,
        "timbre": 0.80,
        "noise": 0.75,
        "duration": 0.55,
    },
    "Sub Bass": {
        "body_pitch": 1.00,
        "attack": 0.45,
        "decay": 0.80,
        "brightness": 0.15,
        "timbre": 0.55,
        "noise": 0.20,
        "duration": 0.65,
    },
    "Hi-Hat": {
        "body_pitch": 0.15,
        "attack": 0.90,
        "decay": 0.65,
        "brightness": 0.95,
        "timbre": 0.75,
        "noise": 0.90,
        "duration": 0.55,
    },
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


def weights_match(first: Mapping[str, float], second: Mapping[str, float]) -> bool:
    """Return whether two slider states are equal at the UI's 0.01 precision."""
    left = normalize_weights(first)
    right = normalize_weights(second)
    return all(round(left[key] * 100) == round(right[key] * 100) for key in DEFAULT_WEIGHTS)


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
