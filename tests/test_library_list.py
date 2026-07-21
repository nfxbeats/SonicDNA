from pathlib import Path

from PySide6.QtCore import QMimeData, QUrl

from sonicdna.ui.library_list import LibraryListWidget


def test_folder_drop_mime_ignores_files(tmp_path: Path) -> None:
    folder = tmp_path / "Drum Kits"
    folder.mkdir()
    sample = tmp_path / "kick.wav"
    sample.write_bytes(b"audio")
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(folder)), QUrl.fromLocalFile(str(sample))])

    assert LibraryListWidget.directories_from_mime(mime_data) == [folder.resolve()]
