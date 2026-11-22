import fcntl
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

import twobrain_rec_server.storage.recovery as recovery
from twobrain_rec_server.config import Settings


def test_recovery_record_requires_bound_scope_and_live_shared_lock(tmp_path):
    path = tmp_path / "recovery"
    sidecar = path.with_name("recovery.lock")
    expected = uuid4()
    settings = Settings(
        strict_storage_scope="scope", strict_storage_recovery_file=path,
        strict_storage_recovery_id=expected,
    )
    recovery_id = str(expected)
    record = {"schema": 1, "scope": "scope", "recovery_id": recovery_id, "state": "reconciled"}
    path.write_text(json.dumps(record), encoding="utf-8")
    assert recovery.storage_recovery_token(settings) is None

    with sidecar.open("w+") as operator:
        fcntl.flock(operator, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert recovery.storage_recovery_token(settings) is None
        fcntl.flock(operator, fcntl.LOCK_UN)
        assert recovery.storage_recovery_token(settings) == recovery_id
        with recovery.storage_recovery_snapshot(settings) as token:
            assert token == recovery_id
            try:
                fcntl.flock(operator, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise AssertionError("Operator must not change the state during publication")

    for change in (
        {"scope": "other-bucket"},
        {"recovery_id": "stale-or-invalid"},
        {"recovery_id": str(uuid4())},
        {"schema": True},
        {"state": "recovery_unknown"},
    ):
        path.write_text(json.dumps(record | change), encoding="utf-8")
        assert recovery.storage_recovery_token(settings) is None
    path.write_text("{", encoding="utf-8")
    assert recovery.storage_recovery_token(settings) is None


@pytest.mark.parametrize("field,conflict", [
    ("schema", 0), ("scope", "other"), ("recovery_id", "stale"), ("state", "recovery_unknown"),
])
def test_duplicate_recovery_fields_never_admit_publication(tmp_path, field, conflict):
    path = tmp_path / "recovery"
    path.with_name("recovery.lock").touch()
    expected = uuid4()
    settings = Settings(
        strict_storage_scope="scope", strict_storage_recovery_file=path,
        strict_storage_recovery_id=expected,
    )
    record = {"schema": 1, "scope": "scope", "recovery_id": str(expected), "state": "reconciled"}
    payload = json.dumps({field: conflict})[:-1] + "," + json.dumps(record)[1:]
    path.write_text(payload, encoding="utf-8")
    assert recovery.storage_recovery_token(settings) is None


def test_managed_recovery_directory_refuses_legacy_after_operator_provisions_lock(tmp_path):
    directory = tmp_path / "managed"
    unbound = Settings(strict_storage_recovery_directory=directory)
    assert recovery.storage_recovery_token(unbound) is None
    directory.mkdir()
    assert recovery.storage_recovery_token(unbound) is None
    legacy = unbound.model_copy(update={"strict_storage_recovery_allow_legacy": True})
    assert recovery.storage_recovery_token(legacy) == "legacy"
    path = directory / "state.json"
    operation = uuid4()
    partial = unbound.model_copy(update={"strict_storage_scope": "scope"})
    assert recovery.storage_recovery_token(partial) is None
    path.with_suffix(".json.lock").touch()
    assert recovery.storage_recovery_token(unbound) is None
    assert recovery.storage_recovery_token(legacy) is None
    recovery.mark_storage_recovery_unknown(path, scope="scope", recovery_id=operation, previous_id=None)
    bound = partial.model_copy(update={"strict_storage_recovery_id": operation})
    assert recovery.storage_recovery_token(bound) is None
    record = json.loads(path.read_bytes())
    path.write_text(json.dumps(record | {"state": "reconciled"}), encoding="utf-8")
    assert recovery.storage_recovery_token(bound) == str(operation)
    assert recovery.storage_recovery_token(unbound) is None
    alternate = bound.model_copy(update={"strict_storage_recovery_file": path})
    assert recovery.storage_recovery_token(alternate) is None
    path.unlink()
    assert recovery.storage_recovery_token(unbound) is None
    assert recovery.storage_recovery_token(legacy) is None


def test_operator_marks_new_restore_without_replacing_the_shared_lock(tmp_path):
    path = tmp_path / "recovery"
    lock = tmp_path / "recovery.lock"
    lock.touch()
    lock_inode = lock.stat().st_ino
    previous, current = uuid4(), uuid4()
    settings = Settings(
        strict_storage_scope="scope", strict_storage_recovery_file=path,
        strict_storage_recovery_id=previous,
    )
    recovery.mark_storage_recovery_unknown(path, scope="scope", recovery_id=previous, previous_id=None)
    record = json.loads(path.read_bytes())
    assert record["schema"] == 1 and record["scope"] == "scope"
    assert record["recovery_id"] == str(previous) and record["state"] == "recovery_unknown"
    assert recovery.storage_recovery_token(settings) is None

    # Represents an already reconciled operation, published by the reconciliation owner.
    path.write_text(json.dumps(record | {"state": "reconciled"}), encoding="utf-8")
    assert recovery.storage_recovery_token(settings) == str(previous)
    with recovery.storage_recovery_snapshot(settings), pytest.raises(BlockingIOError):
        recovery.mark_storage_recovery_unknown(path, scope="scope", recovery_id=current, previous_id=previous)
    with pytest.raises(ValueError):
        recovery.mark_storage_recovery_unknown(path, scope="other", recovery_id=current, previous_id=previous)
    with pytest.raises(ValueError):
        recovery.mark_storage_recovery_unknown(path, scope="scope", recovery_id=current, previous_id=uuid4())
    with pytest.raises(ValueError):
        recovery.mark_storage_recovery_unknown(path, scope="scope", recovery_id=previous, previous_id=None)
    assert recovery.storage_recovery_token(settings) == str(previous)

    recovery.mark_storage_recovery_unknown(path, scope="scope", recovery_id=current, previous_id=previous)
    assert lock.stat().st_ino == lock_inode
    assert recovery.storage_recovery_token(settings) is None
    settings.strict_storage_recovery_id = current
    assert recovery.storage_recovery_token(settings) is None
    published_inode = path.stat().st_ino
    for wrong_previous in (None, uuid4()):
        with pytest.raises(ValueError):
            recovery.mark_storage_recovery_unknown(path, scope="scope", recovery_id=current, previous_id=wrong_previous)
    recovery.mark_storage_recovery_unknown(path, scope="scope", recovery_id=current, previous_id=previous)
    assert path.stat().st_ino == published_inode


@pytest.mark.parametrize("fail_on_directory", [False, True])
def test_operator_requires_durable_publication_and_can_retry_io_failure(tmp_path, monkeypatch, fail_on_directory):
    path = tmp_path / "recovery"
    (tmp_path / "recovery.lock").touch()
    current = uuid4()
    fsync = os.fsync

    def fail_at_boundary(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode) == fail_on_directory:
            raise OSError("synthetic fsync failure")
        fsync(fd)

    with monkeypatch.context() as scoped:
        scoped.setattr(recovery.os, "fsync", fail_at_boundary)
        with pytest.raises(OSError, match="synthetic fsync failure"):
            recovery.mark_storage_recovery_unknown(path, scope="scope", recovery_id=current, previous_id=None)
    assert path.exists() is fail_on_directory
    recovery.mark_storage_recovery_unknown(path, scope="scope", recovery_id=current, previous_id=None)
    assert json.loads(path.read_bytes())["state"] == "recovery_unknown"
    assert sorted(entry.name for entry in tmp_path.iterdir()) == ["recovery", "recovery.lock"]


def test_operator_cli_shares_deployment_lock_and_preserves_parent_ownership(tmp_path):
    server = Path(__file__).parents[2]
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    lock_name = subprocess.check_output(
        ["git", "rev-parse", "--git-path", "twobrain-rec-deploy.lock"], cwd=tmp_path, text=True,
    ).strip()
    state = tmp_path / "state.json"
    state.with_suffix(".json.lock").touch()
    recovery_id = uuid4()
    command = [
        sys.executable, str(server / "scripts/mark_storage_recovery_unknown.py"),
        "--file", str(state), "--scope", "test", "--recovery-id", str(recovery_id),
    ]

    def invoke(fd):
        return subprocess.run(
            [*command, "--deployment-lock-fd", str(fd)], cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(server / "src")},
            pass_fds=(fd,), capture_output=True, text=True,
        )

    with (tmp_path / lock_name).open("ab") as operator, (tmp_path / lock_name).open("ab") as other:
        fcntl.flock(operator, fcntl.LOCK_EX | fcntl.LOCK_NB)
        busy = invoke(other.fileno())
        assert busy.returncode == 1 and "deployment_lock_busy" in busy.stderr
        with (tmp_path / "foreign.lock").open("ab") as foreign:
            invalid = invoke(foreign.fileno())
        assert invalid.returncode == 1 and "deployment_lock_unverified" in invalid.stderr
        assert not state.exists()

        published = invoke(operator.fileno())
        assert published.returncode == 0, published.stderr
        assert published.stdout.strip() == "storage_recovery=recovery_unknown"
        assert json.loads(state.read_bytes())["recovery_id"] == str(recovery_id)
        with pytest.raises(BlockingIOError):
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(operator, fcntl.LOCK_UN)
        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
