from pathlib import Path
import zipfile

import pytest

import update


def make_project_archive(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "SonicDNA-main/pyproject.toml",
            '[project]\nname = "sonicdna"\nversion = "1.0.0"\n',
        )
        archive.writestr("SonicDNA-main/sonicdna/__init__.py", "")


@pytest.mark.parametrize(
    "remote",
    [
        "https://github.com/nfxbeats/SonicDNA.git",
        "git@github.com:nfxbeats/SonicDNA.git",
        "ssh://git@github.com/nfxbeats/SonicDNA",
    ],
)
def test_supported_git_remotes_normalize_to_repository_slug(remote: str) -> None:
    assert update.normalized_remote(remote) == update.REPOSITORY_SLUG


def test_extract_archive_validates_sonicdna_project(tmp_path: Path) -> None:
    archive = tmp_path / "update.zip"
    destination = tmp_path / "extracted"
    destination.mkdir()
    make_project_archive(archive)

    source = update.extract_archive(archive, destination)

    assert source.name == "SonicDNA-main"
    assert (source / "sonicdna").is_dir()


def test_extract_archive_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    destination = tmp_path / "extracted"
    destination.mkdir()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../outside.txt", "unsafe")

    with pytest.raises(RuntimeError, match="Unsafe path"):
        update.extract_archive(archive, destination)


def test_zip_replacement_preserves_local_files_and_can_restore(tmp_path: Path) -> None:
    root = tmp_path / "SonicDNA"
    source = tmp_path / "download" / "SonicDNA-main"
    backup = tmp_path / "backup"
    root.mkdir()
    source.mkdir(parents=True)
    backup.mkdir()
    (root / "sonicdna").mkdir()
    (source / "sonicdna").mkdir()
    (root / "sonicdna" / "version.txt").write_text("old", encoding="utf-8")
    (source / "sonicdna" / "version.txt").write_text("new", encoding="utf-8")
    (root / "README.md").write_text("old readme", encoding="utf-8")
    (source / "README.md").write_text("new readme", encoding="utf-8")
    (root / "presentation.md").write_text("local narration", encoding="utf-8")
    (root / ".venv").mkdir()

    backed_up = update.backup_managed_files(root, source, backup)
    update.replace_managed_files(root, source)

    assert (root / "sonicdna" / "version.txt").read_text(encoding="utf-8") == "new"
    assert (root / "README.md").read_text(encoding="utf-8") == "new readme"
    assert (root / "presentation.md").read_text(encoding="utf-8") == "local narration"
    assert (root / ".venv").is_dir()

    update.restore_backup(root, source, backup, backed_up)

    assert (root / "sonicdna" / "version.txt").read_text(encoding="utf-8") == "old"
    assert (root / "README.md").read_text(encoding="utf-8") == "old readme"
