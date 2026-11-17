from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "infra/scripts/prune-rec-backups.sh"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def dated(root: Path, name: str) -> Path:
    path = root / name
    path.mkdir()
    (path / "marker").write_text("x", encoding="utf-8")
    return path


def test_dry_run_changes_nothing_and_keeps_newest(tmp_path: Path) -> None:
    old = dated(tmp_path, "20200101T000000Z")
    newest = dated(tmp_path, "20210101T000000Z")

    result = run("--dry-run", "--backup-root", str(tmp_path), "--older-than-days", "30")

    assert result.returncode == 0, result.stderr
    assert "candidate_count=1" in result.stdout
    assert "deleted_count=0" in result.stdout
    assert old.is_dir()
    assert newest.is_dir()


def test_execute_removes_only_old_owned_directory(tmp_path: Path) -> None:
    old = dated(tmp_path, "20200101T000000Z")
    newest = dated(tmp_path, "20210101T000000Z")
    foreign = tmp_path / "not-a-backup"
    foreign.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "20220101T000000Z"
    os.symlink(outside, link)

    result = run("--execute", "--backup-root", str(tmp_path), "--older-than-days", "30")

    assert result.returncode == 0, result.stderr
    assert "deleted_count=1" in result.stdout
    assert not old.exists()
    assert newest.is_dir()
    assert foreign.is_dir()
    assert outside.is_dir()
    assert link.is_symlink()


def test_invalid_root_returns_two(tmp_path: Path) -> None:
    result = run("--dry-run", "--backup-root", str(tmp_path / "missing"))

    assert result.returncode == 2
    assert "prune_result=failed" in result.stderr


def test_symlink_root_is_rejected(tmp_path: Path) -> None:
    real_root = tmp_path / "real-backups"
    real_root.mkdir()
    dated(real_root, "20200101T000000Z")
    link = tmp_path / "backups-link"
    os.symlink(real_root, link)

    result = run("--dry-run", "--backup-root", str(link))

    assert result.returncode == 2
    assert "reason=backup_root_symlink" in result.stderr
    assert (real_root / "20200101T000000Z").is_dir()
