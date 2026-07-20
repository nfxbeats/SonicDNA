"""Cross-platform adapters for opening and revealing local files."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_file(path: Path) -> None:
    """Open a file with the operating system's default application."""
    resolved = path.resolve(strict=True)
    if sys.platform == "win32":
        os.startfile(resolved)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(resolved)])
    else:
        subprocess.Popen(["xdg-open", str(resolved)])


def reveal_file(path: Path) -> None:
    """Reveal a file in the platform file manager."""
    resolved = path.resolve(strict=True)
    if sys.platform == "win32":
        subprocess.Popen(["explorer.exe", f"/select,{resolved}"])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(resolved)])
    else:
        subprocess.Popen(["xdg-open", str(resolved.parent)])

