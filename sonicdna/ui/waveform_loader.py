"""Qt thread-pool tasks for result waveform previews."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from sonicdna.waveform import waveform_envelope


class WaveformTaskSignals(QObject):
    loaded = Signal(int, str, object)


class WaveformTask(QRunnable):
    def __init__(self, row: int, path: Path, bins: int = 160) -> None:
        super().__init__()
        self.row = row
        self.path = path
        self.bins = bins
        self.signals = WaveformTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            points = waveform_envelope(self.path, self.bins)
        except (OSError, RuntimeError, ValueError):
            points = []
        self.signals.loaded.emit(self.row, str(self.path), points)

