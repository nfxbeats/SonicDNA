"""Stable, versioned layout of SonicDNA feature vectors."""

from __future__ import annotations

from collections.abc import Mapping

FEATURE_VERSION = 1

# Each tuple is a half-open [start, end) range.
FEATURE_SCHEMA: Mapping[str, tuple[int, int]] = {
    "timbre": (0, 100),          # 20 MFCCs x 5 statistics
    "mel_spectrum": (100, 132),  # 32 mel-band means
    "brightness": (132, 147),    # centroid, bandwidth, rolloff x 5
    "noise": (147, 157),         # flatness and ZCR x 5
    "energy": (157, 162),        # RMS x 5
    "attack": (162, 164),        # attack and transient/body ratio
    "decay": (164, 167),         # peak-to-50%, 20%, and 5%
    "low_frequency_body": (167, 176),  # dominant frequency + 8 bands
    "duration": (176, 177),
}
FEATURE_VECTOR_LENGTH = 177


def validate_schema() -> None:
    """Raise ValueError if the feature ranges are not contiguous and complete."""
    position = 0
    for name, (start, end) in FEATURE_SCHEMA.items():
        if start != position or end <= start:
            raise ValueError(f"Invalid feature range for {name}: {(start, end)}")
        position = end
    if position != FEATURE_VECTOR_LENGTH:
        raise ValueError(f"Schema ends at {position}, expected {FEATURE_VECTOR_LENGTH}")

