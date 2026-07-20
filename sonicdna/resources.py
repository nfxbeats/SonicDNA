"""Locate application resources in source and packaged builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(filename: str) -> Path:
    """Resolve a bundled resource under PyInstaller or the source checkout."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root is not None:
        return Path(bundle_root) / filename
    return Path(__file__).resolve().parent.parent / filename


def logo_path() -> Path:
    return resource_path("sonicdna-logo.png")

