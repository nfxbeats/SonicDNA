from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

from sonicdna.ui.compact_waveform import CompactWaveformWidget


def test_query_waveform_text_size_and_click() -> None:
    application = QApplication.instance() or QApplication([])
    widget = CompactWaveformWidget()
    assert widget.display_text() == "Drop Sample Here"
    widget.set_playback_progress(0.5)
    assert widget.playback_progress() == 0.5
    widget.set_playback_progress(None)
    assert widget.playback_progress() is None
    assert widget.width() == 300
    widget.set_filename("kick.wav")
    assert widget.display_text() == "kick.wav"
    spy = QSignalSpy(widget.clicked)
    widget.show()
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
    assert spy.count() == 1
    widget.close()
    application.processEvents()
