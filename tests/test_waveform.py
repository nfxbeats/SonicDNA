from pathlib import Path

import numpy as np
import soundfile as sf

from sonicdna.waveform import waveform_envelope


def test_waveform_envelope_is_bounded_and_downsampled(tmp_path: Path) -> None:
    path = tmp_path / "wave.wav"
    time = np.linspace(0, 1, 44_100, endpoint=False)
    audio = np.sin(2 * np.pi * 80 * time).astype(np.float32)
    sf.write(path, audio, 44_100)

    points = waveform_envelope(path, bins=120)

    assert len(points) == 120
    assert all(-1.0 <= minimum <= maximum <= 1.0 for minimum, maximum in points)
