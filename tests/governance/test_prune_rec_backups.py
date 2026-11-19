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
    (path / "backup.passed").write_text("pass", encoding="utf-8")
    (path / "postgres.dump").write_text("dump", encoding="utf-8")
    (path / "schema.sql").write_text("schema", encoding="utf-8")
    (path / "inventory.jsonl").write_text("{}\n", encoding="utf-8")
    (path / "checksums.sha256").write_text("checksum", encoding="utf-8")
    (path / "minio-objects").mkdir()
    return path


def partial_backup(root: Path, name: str) -> Path:
    """The real shape after a minio-stage failure: artifacts but no marker."""

    path = root / name
    path.mkdir()
    (path / "postgres.dump").write_text("dump", encoding="utf-8")
    (path / "schema.sql").write_text("schema", encoding="utf-8")
    (path / "inventory.jsonl").write_text("{}\n", encoding="utf-8")
    (path / "checksums.sha256").write_text("checksum", encoding="utf-8")
    (path / "minio-objects").mkdir()
    return path


def unowned_dated(root: Path, name: str) -> Path:
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


def test_dated_foreign_directory_is_not_removed(tmp_path: Path) -> None:
    old_owned = dated(tmp_path, "20200101T000000Z")
    newest_owned = dated(tmp_path, "20210101T000000Z")
    foreign = unowned_dated(tmp_path, "20190101T000000Z")

    result = run("--execute", "--backup-root", str(tmp_path), "--older-than-days", "30")

    assert result.returncode == 0, result.stderr
    assert not old_owned.exists()
    assert newest_owned.is_dir()
    assert foreign.is_dir()
    assert str(tmp_path) not in result.stdout


def test_failed_newest_backup_keeps_newest_verified(tmp_path: Path) -> None:
    oldest = dated(tmp_path, "20190101T000000Z")
    newest_verified = dated(tmp_path, "20200101T000000Z")
    failed_newest = unowned_dated(tmp_path, "20210101T000000Z")

    result = run("--execute", "--backup-root", str(tmp_path), "--older-than-days", "30")

    assert result.returncode == 0, result.stderr
    assert failed_newest.is_dir()
    assert newest_verified.is_dir()
    assert not oldest.exists()


def test_minio_stage_failure_does_not_unlock_last_good_backup(tmp_path: Path) -> None:
    oldest = dated(tmp_path, "20190101T000000Z")
    last_good = dated(tmp_path, "20200101T000000Z")
    partial_newest = partial_backup(tmp_path, "20210101T000000Z")

    result = run("--execute", "--backup-root", str(tmp_path), "--older-than-days", "30")

    assert result.returncode == 0, result.stderr
    assert partial_newest.is_dir()
    assert last_good.is_dir()
    assert not oldest.exists()


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


def test_incomplete_owned_backup_is_never_deleted(tmp_path: Path) -> None:
    complete_old = dated(tmp_path, "20190101T000000Z")
    newest = dated(tmp_path, "20200101T000000Z")
    incomplete_old = dated(tmp_path, "20180101T000000Z")
    (incomplete_old / "schema.sql").unlink()

    result = run("--execute", "--backup-root", str(tmp_path), "--older-than-days", "30")

    assert result.returncode == 0, result.stderr
    assert not complete_old.exists()
    assert newest.is_dir()
    assert incomplete_old.is_dir()


def test_deletion_failure_returns_three(tmp_path: Path) -> None:
    old = dated(tmp_path, "20190101T000000Z")
    newest = dated(tmp_path, "20200101T000000Z")
    # A directory without write permission cannot have its entries unlinked.
    nested = old / "minio-objects"
    nested.mkdir(exist_ok=True)
    (nested / "object").write_text("x", encoding="utf-8")
    old.chmod(0o500)
    try:
        result = run("--execute", "--backup-root", str(tmp_path), "--older-than-days", "30")
    finally:
        old.chmod(0o700)

    assert result.returncode == 3, result.stdout + result.stderr
    assert "prune_result=partial_failure" in result.stdout
    assert old.is_dir()
    assert newest.is_dir()
