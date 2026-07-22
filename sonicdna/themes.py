"""File-backed application theme discovery and activation."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from platformdirs import user_data_path
from PySide6.QtWidgets import QApplication

from sonicdna.resources import resource_path

BUILTIN_THEME_NAMES = ("System", "Dark", "Autumn", "Cyber")


def theme_directory() -> Path:
    override = os.environ.get("SONICDNA_THEME_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return user_data_path("SonicDNA", appauthor=False, ensure_exists=True) / "themes"


def ensure_default_themes() -> Path:
    """Copy missing built-ins without replacing local edits."""
    destination = theme_directory()
    destination.mkdir(parents=True, exist_ok=True)
    source = resource_path("themes")
    for name in BUILTIN_THEME_NAMES:
        target = destination / f"{name}.qss"
        bundled = source / f"{name}.qss"
        if not target.exists() and bundled.is_file():
            shutil.copyfile(bundled, target)
        elif target.is_file() and bundled.is_file():
            # Preserve local edits while migrating older built-ins that predate
            # themeable waveform properties.
            local_text = target.read_text(encoding="utf-8")
            if "qproperty-waveformColor" not in local_text:
                bundled_text = bundled.read_text(encoding="utf-8")
                block_start = bundled_text.rfind("CompactWaveformWidget, ResultsTable {")
                if block_start >= 0:
                    block_end = bundled_text.find("}", block_start)
                    waveform_block = bundled_text[block_start:block_end + 1]
                    target.write_text(
                        f"{local_text.rstrip()}\n\n{waveform_block}\n", encoding="utf-8"
                    )
            elif "qproperty-waveformOutlineColor" not in local_text:
                bundled_text = bundled.read_text(encoding="utf-8")
                outline_line = next(
                    (
                        line
                        for line in bundled_text.splitlines()
                        if "qproperty-waveformOutlineColor" in line
                    ),
                    "",
                )
                block_start = local_text.rfind("CompactWaveformWidget, ResultsTable {")
                block_end = local_text.find("}", block_start)
                if outline_line and block_start >= 0 and block_end >= 0:
                    updated = (
                        local_text[:block_end].rstrip()
                        + f"\n{outline_line}\n"
                        + local_text[block_end:]
                    )
                    target.write_text(updated, encoding="utf-8")
            local_text = target.read_text(encoding="utf-8")
            if "qproperty-iconColor" not in local_text:
                bundled_text = bundled.read_text(encoding="utf-8")
                block_start = bundled_text.rfind("ThemedIconButton {")
                block_end = bundled_text.find("}", block_start)
                if block_start >= 0 and block_end >= 0:
                    icon_block = bundled_text[block_start:block_end + 1]
                    target.write_text(
                        f"{local_text.rstrip()}\n\n{icon_block}\n", encoding="utf-8"
                    )
            local_text = target.read_text(encoding="utf-8")
            if "QPushButton#find_similar" not in local_text:
                bundled_text = bundled.read_text(encoding="utf-8")
                block_start = bundled_text.rfind("QPushButton#find_similar {")
                if block_start >= 0:
                    button_blocks = bundled_text[block_start:].strip()
                    target.write_text(
                        f"{local_text.rstrip()}\n\n{button_blocks}\n", encoding="utf-8"
                    )
    return destination


def available_themes() -> dict[str, Path]:
    directory = ensure_default_themes()
    discovered = {path.stem: path for path in directory.glob("*.qss") if path.is_file()}
    order = {name: position for position, name in enumerate(BUILTIN_THEME_NAMES)}
    return dict(sorted(discovered.items(), key=lambda item: (order.get(item[0], 100), item[0].casefold())))


def apply_theme(name: str) -> str:
    """Apply a named local QSS file and return its resolved name."""
    themes = available_themes()
    resolved = name if name in themes else "System"
    path = themes.get(resolved)
    stylesheet = path.read_text(encoding="utf-8") if path is not None else ""
    application = QApplication.instance()
    if application is None:
        raise RuntimeError("A QApplication is required before applying a theme")
    application.setStyleSheet(stylesheet)
    return resolved
