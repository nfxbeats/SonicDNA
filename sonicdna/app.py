"""PySide6 application bootstrap."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sonicdna.ui.main_window import MainWindow


def run() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("SonicDNA")
    application.setOrganizationName("SonicDNA")
    window = MainWindow()
    window.show()
    return application.exec()

