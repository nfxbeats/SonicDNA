"""Cross-platform, replaceable audio-preview backends."""

from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Protocol

import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from scipy.signal import resample_poly


class AudioPlayer(Protocol):
    playing_changed: Signal
    progress_changed: Signal

    def play(self, path: Path) -> None: ...
    def stop(self) -> None: ...
    def set_volume(self, value: float) -> None: ...
    def close(self) -> None: ...


def prepare_audio(
    path: Path, target_rate: int, channels: int, fade_frames: int
) -> np.ndarray:
    """Decode and prepare a sample for the persistent output stream."""
    data, source_rate = sf.read(path, dtype="float32", always_2d=True)
    if data.size == 0:
        raise ValueError("audio file is empty")
    if source_rate != target_rate:
        divisor = int(np.gcd(source_rate, target_rate))
        data = resample_poly(
            data, target_rate // divisor, source_rate // divisor, axis=0
        ).astype(np.float32)
    if channels == 1:
        data = np.mean(data, axis=1, keepdims=True)
    elif data.shape[1] == 1:
        data = np.repeat(data, channels, axis=1)
    elif data.shape[1] > channels:
        data = data[:, :channels]
    fade = min(fade_frames, max(1, data.shape[0] // 2))
    ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)[:, None]
    data[:fade] *= ramp
    data[-fade:] *= ramp[::-1]
    return np.ascontiguousarray(data, dtype=np.float32)


class SoundDevicePlayer(QObject):
    """Persistent PortAudio stream with click-resistant sample transitions."""

    playing_changed = Signal(bool)
    progress_changed = Signal(float)

    def __init__(self, volume: float = 0.8, parent: QObject | None = None) -> None:
        super().__init__(parent)
        device = sd.query_devices(kind="output")
        self.sample_rate = int(round(float(device["default_samplerate"])))
        self.channels = min(2, int(device["max_output_channels"]))
        if self.channels < 1:
            raise RuntimeError("No audio output channels are available")
        self._volume = float(np.clip(volume, 0.0, 1.0))
        self._lock = RLock()
        self._current: np.ndarray | None = None
        self._position = 0
        self._pending: np.ndarray | None = None
        self._stop_requested = False
        self._is_playing = False
        self._total_frames = 0
        self._last_progress = -1.0
        self._fade_frames = max(16, round(self.sample_rate * 0.005))
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=512,
            callback=self._audio_callback,
        )
        self._stream.start()

    def _prepare(self, path: Path) -> np.ndarray:
        return prepare_audio(path, self.sample_rate, self.channels, self._fade_frames)

    def play(self, path: Path) -> None:
        data = self._prepare(path)
        with self._lock:
            self._pending = data
            self._total_frames = data.shape[0]
            self._last_progress = 0.0
            self._stop_requested = False
            if not self._is_playing:
                self._is_playing = True
                self.playing_changed.emit(True)
        self.progress_changed.emit(0.0)

    def stop(self) -> None:
        with self._lock:
            if self._current is not None or self._pending is not None:
                self._stop_requested = True
                self._pending = None

    def set_volume(self, value: float) -> None:
        with self._lock:
            self._volume = float(np.clip(value, 0.0, 1.0))

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()

    def _take_current(self, count: int) -> np.ndarray:
        output = np.zeros((count, self.channels), dtype=np.float32)
        if self._current is None:
            return output
        available = min(count, self._current.shape[0] - self._position)
        if available > 0:
            output[:available] = self._current[self._position:self._position + available]
            self._position += available
        if self._position >= self._current.shape[0]:
            self._current = None
            self._position = 0
        return output

    def _audio_callback(self, outdata: np.ndarray, frames: int, _time, _status) -> None:
        ended = False
        progress: float | None = None
        with self._lock:
            if self._pending is not None:
                incoming = self._pending
                self._pending = None
                transition = min(self._fade_frames, frames, incoming.shape[0])
                old = self._take_current(transition)
                ramp = np.linspace(0.0, 1.0, transition, dtype=np.float32)[:, None]
                outdata[:transition] = old * (1.0 - ramp) + incoming[:transition] * ramp
                self._current = incoming
                self._position = transition
                if transition < frames:
                    outdata[transition:] = self._take_current(frames - transition)
            elif self._stop_requested:
                transition = min(self._fade_frames, frames)
                old = self._take_current(transition)
                ramp = np.linspace(1.0, 0.0, transition, dtype=np.float32)[:, None]
                outdata[:transition] = old * ramp
                outdata[transition:] = 0
                self._current = None
                self._position = 0
                self._stop_requested = False
            else:
                outdata[:] = self._take_current(frames)
            outdata *= self._volume
            if self._current is None and self._pending is None and self._is_playing:
                self._is_playing = False
                ended = True
                progress = 1.0
            elif self._current is not None and self._total_frames > 0:
                current_progress = min(1.0, self._position / self._total_frames)
                if current_progress - self._last_progress >= 0.01:
                    self._last_progress = current_progress
                    progress = current_progress
        if progress is not None:
            self.progress_changed.emit(progress)
        if ended:
            self.playing_changed.emit(False)


class QtAudioPlayer(QObject):
    """Qt Multimedia fallback when PortAudio is unavailable."""

    playing_changed = Signal(bool)
    progress_changed = Signal(float)

    def __init__(self, volume: float = 0.8, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.output = QAudioOutput(self)
        self.output.setVolume(volume)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.output)
        self.player.playbackStateChanged.connect(
            lambda state: self.playing_changed.emit(
                state == QMediaPlayer.PlaybackState.PlayingState
            )
        )
        self.player.positionChanged.connect(self._position_changed)

    def play(self, path: Path) -> None:
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.progress_changed.emit(0.0)
        self.player.play()

    def stop(self) -> None:
        self.player.stop()

    def set_volume(self, value: float) -> None:
        self.output.setVolume(value)

    def close(self) -> None:
        self.player.stop()

    def _position_changed(self, position: int) -> None:
        duration = self.player.duration()
        if duration > 0:
            self.progress_changed.emit(min(1.0, max(0.0, position / duration)))


def create_audio_player(volume: float, parent: QObject | None = None) -> tuple[AudioPlayer, str]:
    """Create the low-latency backend, falling back to Qt when necessary."""
    try:
        return SoundDevicePlayer(volume, parent), "sounddevice"
    except (sd.PortAudioError, OSError, RuntimeError, ValueError):
        return QtAudioPlayer(volume, parent), "Qt Multimedia"
