"""Application settings factory with an isolated test/development override."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSettings


def create_settings() -> QSettings:
    """Return native user settings, or an explicit INI file when configured."""
    override = os.environ.get("SONICDNA_SETTINGS_FILE")
    if override:
        path = Path(override).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return QSettings(str(path), QSettings.Format.IniFormat)
    return QSettings("SonicDNA", "SonicDNA")

