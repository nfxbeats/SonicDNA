"""Safely update a Git clone or ZIP installation of Warbeats SonicDNA."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

REPOSITORY_SLUG = "nfxbeats/sonicdna"
MAIN_ARCHIVE_URL = "https://github.com/nfxbeats/SonicDNA/archive/refs/heads/main.zip"
MANAGED_DIRECTORIES = ("sonicdna", "themes", "tests")
PRESERVED_NAMES = {".git", ".venv", "presentation.md"}


def run_command(arguments: list[str], cwd: Path, capture: bool = False) -> str:
    result = subprocess.run(
        arguments,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout.strip() if capture else ""


def is_git_installation(root: Path) -> bool:
    return (root / ".git").exists()


def normalized_remote(remote: str) -> str:
    value = remote.strip().replace("\\", "/").lower()
    if value.endswith(".git"):
        value = value[:-4]
    if value.startswith("git@github.com:"):
        return value.removeprefix("git@github.com:")
    for prefix in ("https://github.com/", "http://github.com/", "ssh://git@github.com/"):
        if value.startswith(prefix):
            return value.removeprefix(prefix)
    return value


def validate_git_installation(root: Path) -> None:
    if shutil.which("git") is None:
        raise RuntimeError("Git is required to update this cloned installation.")
    inside = run_command(
        ["git", "rev-parse", "--is-inside-work-tree"], root, capture=True
    )
    if inside.lower() != "true":
        raise RuntimeError("The .git entry does not belong to a valid Git worktree.")
    remote = run_command(["git", "remote", "get-url", "origin"], root, capture=True)
    if normalized_remote(remote) != REPOSITORY_SLUG:
        raise RuntimeError(
            "The Git origin is not the Warbeats SonicDNA repository:\n"
            f"  {remote}"
        )
    changes = run_command(["git", "status", "--porcelain"], root, capture=True)
    if changes:
        raise RuntimeError(
            "The Git worktree has local changes. Commit, stash, or discard them before updating."
        )


def dependency_fingerprint(pyproject: Path) -> str:
    with pyproject.open("rb") as stream:
        project = tomllib.load(stream)["project"]
    payload = [project.get("requires-python"), project.get("dependencies", [])]
    encoded = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def virtual_environment_python(root: Path) -> Path | None:
    windows = root / ".venv" / "Scripts" / "python.exe"
    unix = root / ".venv" / "bin" / "python"
    if windows.is_file():
        return windows
    if unix.is_file():
        return unix
    return None


def synchronize_dependencies(root: Path) -> None:
    python = virtual_environment_python(root)
    if python is None:
        print("No .venv was found; the normal start script will install dependencies.")
        return
    stamp = root / ".venv" / ".sonicdna-dependencies.sha256"
    current = dependency_fingerprint(root / "pyproject.toml")
    installed = stamp.read_text(encoding="ascii").strip() if stamp.is_file() else ""
    package_ok = subprocess.run(
        [
            str(python),
            "-c",
            "import importlib.metadata as m; m.version('sonicdna')",
        ],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    environment_ok = subprocess.run(
        [str(python), "-m", "pip", "check"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    if current == installed and package_ok and environment_ok:
        print("Python dependency requirements are already up to date.")
        return
    print("Synchronizing Python dependencies. This can take several minutes...")
    run_command(
        [str(python), "-m", "pip", "install", "--progress-bar", "on", "-e", str(root)],
        root,
    )
    stamp.write_text(f"{current}\n", encoding="ascii")


def validate_archive_member(destination: Path, member: zipfile.ZipInfo) -> None:
    target = (destination / member.filename).resolve()
    try:
        target.relative_to(destination.resolve())
    except ValueError as exc:
        raise RuntimeError(f"Unsafe path in update archive: {member.filename}") from exc


def extract_archive(archive: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            validate_archive_member(destination, member)
        bundle.extractall(destination)
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("The update archive does not contain one project directory.")
    source = roots[0]
    pyproject = source / "pyproject.toml"
    package = source / "sonicdna"
    if not pyproject.is_file() or not package.is_dir():
        raise RuntimeError("The update archive is missing required SonicDNA files.")
    with pyproject.open("rb") as stream:
        project_name = tomllib.load(stream).get("project", {}).get("name")
    if str(project_name).lower() != "sonicdna":
        raise RuntimeError("The downloaded archive is not a SonicDNA project.")
    return source


def root_files(source: Path) -> list[Path]:
    return [
        path
        for path in source.iterdir()
        if path.is_file() and path.name not in PRESERVED_NAMES
    ]


def backup_path(root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = root.parent / "SonicDNA-update-backups" / stamp
    destination.mkdir(parents=True, exist_ok=False)
    return destination


def backup_managed_files(root: Path, source: Path, backup: Path) -> list[str]:
    backed_up: list[str] = []
    for name in MANAGED_DIRECTORIES:
        current = root / name
        if current.exists():
            shutil.copytree(current, backup / name)
            backed_up.append(name)
    for incoming in root_files(source):
        current = root / incoming.name
        if current.is_file():
            shutil.copy2(current, backup / incoming.name)
            backed_up.append(incoming.name)
    return backed_up


def replace_managed_files(root: Path, source: Path) -> None:
    for name in MANAGED_DIRECTORIES:
        current = root / name
        incoming = source / name
        if current.is_dir():
            shutil.rmtree(current)
        if incoming.is_dir():
            shutil.copytree(incoming, current)
    for incoming in root_files(source):
        shutil.copy2(incoming, root / incoming.name)


def restore_backup(root: Path, source: Path, backup: Path, backed_up: list[str]) -> None:
    for name in MANAGED_DIRECTORIES:
        current = root / name
        if current.is_dir():
            shutil.rmtree(current)
        saved = backup / name
        if saved.is_dir():
            shutil.copytree(saved, current)
    for incoming in root_files(source):
        current = root / incoming.name
        saved = backup / incoming.name
        if saved.is_file():
            shutil.copy2(saved, current)
        elif current.is_file() and incoming.name not in backed_up:
            current.unlink()


def update_git_installation(root: Path) -> None:
    print("Git clone detected. Validating repository...")
    validate_git_installation(root)
    print("Downloading fast-forward Git updates...")
    run_command(["git", "pull", "--ff-only"], root)
    synchronize_dependencies(root)


def update_zip_installation(root: Path, archive_url: str) -> None:
    print("ZIP installation detected.")
    with tempfile.TemporaryDirectory(prefix="sonicdna-update-") as temporary:
        temporary_path = Path(temporary)
        archive = temporary_path / "sonicdna-update.zip"
        extracted = temporary_path / "extracted"
        extracted.mkdir()
        print(f"Downloading update from {archive_url}")
        urllib.request.urlretrieve(archive_url, archive)  # noqa: S310
        print("Validating and extracting update...")
        source = extract_archive(archive, extracted)
        backup = backup_path(root)
        print(f"Backing up current application files to {backup}")
        backed_up = backup_managed_files(root, source, backup)
        try:
            replace_managed_files(root, source)
            synchronize_dependencies(root)
        except Exception:
            print("Update failed; restoring the previous application files...")
            restore_backup(root, source, backup, backed_up)
            raise
        print(f"Update complete. Backup retained at {backup}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Update Warbeats SonicDNA safely.")
    result.add_argument(
        "--archive-url",
        default=MAIN_ARCHIVE_URL,
        help=argparse.SUPPRESS,
    )
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    root = Path(__file__).resolve().parent
    try:
        if is_git_installation(root):
            update_git_installation(root)
        else:
            update_zip_installation(root, arguments.archive_url)
    except (OSError, RuntimeError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(f"\nUpdate failed: {exc}", file=sys.stderr)
        return 1
    print("Warbeats SonicDNA is up to date. Run the normal start script to launch it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
