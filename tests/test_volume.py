from PySide6.QtWidgets import QApplication

from sonicdna.ui.main_window import MainWindow


def test_volume_slider_updates_player() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    values: list[float] = []
    window.player.set_volume = values.append  # type: ignore[method-assign]

    target = 37 if window.volume_slider.value() != 37 else 38
    window.volume_slider.setValue(target)

    assert values[-1] == target / 100.0
    window.close()
    application.processEvents()
