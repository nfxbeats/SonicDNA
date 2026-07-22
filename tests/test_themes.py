from pathlib import Path

from PySide6.QtWidgets import QApplication

from sonicdna.themes import apply_theme, available_themes, ensure_default_themes
from sonicdna.ui.compact_waveform import CompactWaveformWidget
from sonicdna.ui.results_table import ResultsTable
from sonicdna.ui.themed_icon_button import ThemedIconButton


def test_builtin_themes_are_local_files_and_apply() -> None:
    application = QApplication.instance() or QApplication([])
    directory = ensure_default_themes()
    assert directory.is_dir()
    themes = available_themes()
    assert list(themes)[:4] == ["System", "Dark", "Autumn", "Cyber"]
    assert all(isinstance(path, Path) and path.is_file() for path in themes.values())

    assert apply_theme("Dark") == "Dark"
    assert "#111827" in application.styleSheet()
    assert apply_theme("Autumn") == "Autumn"
    assert "#2b2118" in application.styleSheet()
    assert "QPushButton#find_similar" in application.styleSheet()
    assert "background-color: #c2410c" in application.styleSheet()
    query_waveform = CompactWaveformWidget()
    result_table = ResultsTable()
    icon_button = ThemedIconButton("fa6s.play")
    query_waveform.ensurePolished()
    result_table.ensurePolished()
    icon_button.ensurePolished()
    assert query_waveform.get_waveform_color().name() == "#f59e0b"
    assert result_table.get_waveform_background().name() == "#3a2418"
    assert icon_button.get_icon_color().name() == "#ffcc80"
    assert apply_theme("Cyber") == "Cyber"
    assert "#070b1a" in application.styleSheet()
    assert "background-color: #0891b2" in application.styleSheet()
    query_waveform.ensurePolished()
    result_table.ensurePolished()
    icon_button.ensurePolished()
    assert query_waveform.get_waveform_color().name() == "#22d3ee"
    assert result_table.get_waveform_background().name() == "#050816"
    assert query_waveform.get_waveform_outline_color().name() == "#f72585"
    assert result_table.get_waveform_outline_color().name() == "#f72585"
    assert icon_button.get_icon_color().name() == "#67e8f9"
    query_waveform.close()
    result_table.close()
    icon_button.close()
    assert apply_theme("System") == "System"
