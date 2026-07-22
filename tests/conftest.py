from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_application_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent UI tests from changing the developer's real SonicDNA preferences."""
    monkeypatch.setenv("SONICDNA_SETTINGS_FILE", str(tmp_path / "settings.ini"))
    monkeypatch.setenv("SONICDNA_THEME_DIR", str(tmp_path / "themes"))
