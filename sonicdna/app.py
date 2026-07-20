"""PySide6 application bootstrap."""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from sonicdna.resources import logo_path
from sonicdna.ui.main_window import MainWindow


def run() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("SonicDNA")
    application.setOrganizationName("SonicDNA")
    icon = QIcon(str(logo_path()))
    application.setWindowIcon(icon)
    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    return application.exec()
