from pathlib import Path

import numpy as np
import soundfile as sf

from sonicdna.playback import prepare_audio


def test_prepare_resamples_channels_and_fades(tmp_path: Path) -> None:
    path = tmp_path / "sample.wav"
    sf.write(path, np.ones(1000, dtype=np.float32) * 0.5, 22_050)
    prepared = prepare_audio(path, target_rate=44_100, channels=2, fade_frames=100)

    assert prepared.shape[1] == 2
    assert 1900 <= prepared.shape[0] <= 2100
    assert abs(float(prepared[0, 0])) < 0.001
    assert abs(float(prepared[-1, 0])) < 0.001
