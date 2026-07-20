"""Cross-platform adapters for opening and revealing local files."""

from __future__ import annotations

import os
import subprocess
import sys
import ctypes
from pathlib import Path


def _raise_for_hresult(result: int, operation: str) -> None:
    if result < 0:
        raise OSError(f"{operation} failed with HRESULT 0x{result & 0xFFFFFFFF:08X}")


def _reveal_windows(path: Path) -> None:
    """Select a file through the Windows Shell API, avoiding Explorer CLI parsing."""
    shell32 = ctypes.windll.shell32  # type: ignore[attr-defined]
    ole32 = ctypes.windll.ole32  # type: ignore[attr-defined]
    shell32.SHParseDisplayName.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    shell32.SHParseDisplayName.restype = ctypes.c_long
    shell32.SHOpenFolderAndSelectItems.argtypes = [
        ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_ulong
    ]
    shell32.SHOpenFolderAndSelectItems.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    item_id_list = ctypes.c_void_p()
    attributes = ctypes.c_ulong()
    initialized = ole32.CoInitialize(None) in (0, 1)
    try:
        parse_result = shell32.SHParseDisplayName(
            str(path), None, ctypes.byref(item_id_list), 0, ctypes.byref(attributes)
        )
        _raise_for_hresult(parse_result, "Resolving the sample path")
        try:
            select_result = shell32.SHOpenFolderAndSelectItems(item_id_list, 0, None, 0)
            _raise_for_hresult(select_result, "Revealing the sample")
        finally:
            ole32.CoTaskMemFree(item_id_list)
    finally:
        if initialized:
            ole32.CoUninitialize()


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
        _reveal_windows(resolved)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(resolved)])
    else:
        subprocess.Popen(["xdg-open", str(resolved.parent)])
