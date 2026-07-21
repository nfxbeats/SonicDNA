from PySide6.QtWidgets import QApplication

from sonicdna.ui.main_window import MainWindow


def test_volume_and_auto_play_survive_restart() -> None:
    application = QApplication.instance() or QApplication([])
    first = MainWindow()
    first.auto_audition.setChecked(False)
    first.volume_slider.setValue(43)
    first.close()
    application.processEvents()

    second = MainWindow()
    assert not second.auto_audition.isChecked()
    assert second.volume_slider.value() == 43
    second.close()
    application.processEvents()
