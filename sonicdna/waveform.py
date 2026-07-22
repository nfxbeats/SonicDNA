"""Small, display-oriented waveform envelopes."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def waveform_envelope(path: Path, bins: int = 160) -> list[tuple[float, float]]:
    """Return normalized minimum/maximum pairs for a compact waveform preview."""
    if bins < 1:
        raise ValueError("bins must be positive")
    audio, _sample_rate = sf.read(path, dtype="float32", always_2d=True)
    if audio.size == 0:
        return []
    mono = np.mean(audio, axis=1)
    peak = float(np.max(np.abs(mono)))
    if not np.isfinite(peak) or peak <= np.finfo(np.float32).eps:
        return [(0.0, 0.0)] * min(bins, max(1, mono.size))
    mono = mono / peak
    edges = np.linspace(0, mono.size, min(bins, mono.size) + 1, dtype=np.int64)
    return [
        (float(np.min(mono[start:end])), float(np.max(mono[start:end])))
        for start, end in zip(edges[:-1], edges[1:], strict=True)
        if end > start
    ]

