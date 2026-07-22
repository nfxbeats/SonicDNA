"""PySide6 application bootstrap."""

from __future__ import annotations

import sys
import ctypes

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from sonicdna.resources import application_icon_path
from sonicdna.settings import create_settings
from sonicdna.themes import apply_theme
from sonicdna.ui.main_window import MainWindow


WINDOWS_APP_USER_MODEL_ID = "SonicDNA.SonicDNA"


def configure_windows_identity() -> None:
    """Prevent Windows from grouping the GUI under the Python interpreter icon."""
    if sys.platform == "win32":
        shell32 = ctypes.windll.shell32  # type: ignore[attr-defined]
        setter = shell32.SetCurrentProcessExplicitAppUserModelID
        setter.argtypes = [ctypes.c_wchar_p]
        setter.restype = ctypes.c_long
        result = setter(WINDOWS_APP_USER_MODEL_ID)
        if result < 0:
            raise OSError(f"Unable to set Windows AppUserModelID: 0x{result & 0xFFFFFFFF:08X}")


def run() -> int:
    configure_windows_identity()
    application = QApplication(sys.argv)
    application.setApplicationName("SonicDNA")
    application.setApplicationDisplayName("Warbeats SonicDNA")
    application.setOrganizationName("SonicDNA")
    settings = create_settings()
    selected_theme = str(settings.value("theme", "System"))
    resolved_theme = apply_theme(selected_theme)
    if resolved_theme != selected_theme:
        settings.setValue("theme", resolved_theme)
        settings.sync()
    icon = QIcon(str(application_icon_path()))
    application.setWindowIcon(icon)
    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    return application.exec()
