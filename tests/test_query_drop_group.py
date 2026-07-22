from pathlib import Path

from PySide6.QtCore import QMimeData, QUrl

from sonicdna.ui.query_drop_group import QueryDropGroupBox


def test_query_drop_accepts_files_but_not_folders(tmp_path: Path) -> None:
    sample = tmp_path / "kick.wav"
    sample.write_bytes(b"audio")
    folder = tmp_path / "library"
    folder.mkdir()
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(folder)), QUrl.fromLocalFile(str(sample))])

    assert QueryDropGroupBox.files_from_mime(mime_data) == [sample.resolve()]
