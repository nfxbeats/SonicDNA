from PySide6.QtGui import QIcon

from sonicdna.resources import logo_path


def test_logo_is_available_and_readable() -> None:
    path = logo_path()
    assert path.is_file()
    assert not QIcon(str(path)).isNull()
