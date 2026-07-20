from pathlib import Path

from sonicdna import platform_actions


def test_windows_reveal_uses_shell_selection_api(tmp_path: Path, monkeypatch) -> None:
    sample = tmp_path / "folder with spaces" / "kick drum.wav"
    sample.parent.mkdir()
    sample.write_bytes(b"audio")
    calls: list[Path] = []
    monkeypatch.setattr(platform_actions.sys, "platform", "win32")
    monkeypatch.setattr(platform_actions, "_reveal_windows", calls.append)

    platform_actions.reveal_file(sample)

    assert calls == [sample.resolve()]
