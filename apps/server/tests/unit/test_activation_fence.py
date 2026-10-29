"""Real private files and independent processes; no database/provider access."""

import hashlib
import json
import os
import stat
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.product_analytics.activation_fence import (
    DIGEST_FIELDS,
    READY_FIELDS,
    ActivationHold,
    activation_fence,
)

NOW = datetime(2026, 10, 29, 12, tzinfo=UTC)


def private(path, value):
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
    path.chmod(0o600)


@pytest.fixture
def state(tmp_path):
    directory = (tmp_path / "operator").resolve()
    directory.mkdir(mode=0o700)
    path = directory / "state.json"
    lock = directory / "activation.lock"
    private(lock, b"permanent")
    info = lock.stat()
    expected = dict(source_sha="a" * 40, image_id="sha256:" + "b" * 64,
                    cluster_id="123456789", db_name="synthetic", db_oid=123,
                    schema_revision="0106_activation_milestones")
    initial = dict(version=1, started_at=(NOW - timedelta(days=1)).isoformat(),
                   lock_dev=info.st_dev, lock_ino=info.st_ino, history_proof_sha256="c" * 64)
    private(directory / "initial.json", initial)
    record = dict.fromkeys(READY_FIELDS)
    record.update({key: "c" * 64 for key in DIGEST_FIELDS})
    record.update(expected)
    record.update(initial)
    record.update(status="ready", mode="local_only", verified_at=NOW.isoformat(),
                  backup_finished_at=NOW.isoformat(), restore_verified_at=NOW.isoformat(),
                  retention_verified_at=NOW.isoformat(), resource_verified_at=NOW.isoformat(),
                  initial_receipt_sha256=hashlib.sha256((directory / "initial.json").read_bytes()).hexdigest(),
                  reason="verified")
    private(path, record)
    return path, record, expected


def test_ready_requires_exact_binding_initial_and_private_readonly_installation(state):
    path, record, expected = state
    with (pytest.raises(ActivationHold, match="mount_writable"),
          activation_fence(path, owner_uid=os.geteuid())):
        pass
    with activation_fence(path, owner_uid=os.geteuid(), readonly=False) as fence:
        assert fence.read_ready(expected=expected, now=NOW) == record
        with pytest.raises(ActivationHold, match="binding_mismatch"):
            fence.read_ready(expected={**expected, "db_oid": 124}, now=NOW)
        with pytest.raises(ActivationHold, match="exclusive_required"):
            fence.revoke()
        # A valid-looking ready file cannot replace the immutable initial.
        (path.parent / "initial.json").unlink()
        with pytest.raises(FileNotFoundError):
            fence.read_ready(expected=expected, now=NOW)
    assert not (path.parent / "initial.json").exists()


@pytest.mark.parametrize("key,value,reason", [
    ("version", True, "receipt_invalid"), ("db_oid", True, "binding_invalid"),
    ("status", "revoked", "not_ready"), ("mode", "live_safe", "not_ready"),
    ("reason", "manual_pass", "not_ready"), ("source_sha", "a", "binding_invalid"),
    ("roles_sha256", "", "digest_invalid"), ("unexpected", "secret", "receipt_invalid"),
    ("started_at", None, "timestamp_invalid"),
    ("verified_at", "2026-10-30T12:00:00Z", "timestamp_invalid"),
    ("backup_finished_at", "2026-10-28T10:00:00Z", "evidence_stale"),
    ("backup_finished_at", "2026-10-29T12:00:01Z", "evidence_stale"),
    ("retention_verified_at", "2026-10-28T10:00:00Z", "evidence_stale"),
    ("resource_verified_at", "2026-10-28T10:00:00Z", "evidence_stale"),
    ("restore_verified_at", "2026-09-29T11:59:59Z", "evidence_stale"),
    ("lock_ino", 0, "lock_changed"), ("initial_receipt_sha256", "e" * 64, "initial_mismatch"),
])
def test_unknown_malformed_future_stale_or_changed_evidence_never_opens(state, key, value, reason):
    path, record, expected = state
    record[key] = value
    private(path, record)
    with (activation_fence(path, owner_uid=os.geteuid(), readonly=False) as fence,
          pytest.raises(ActivationHold, match=reason)):
        fence.read_ready(expected=expected, now=NOW)


def test_restore_boundary_and_duplicate_json_keys(state):
    path, record, expected = state
    record["restore_verified_at"] = (NOW - timedelta(days=30)).isoformat()
    private(path, record)
    with activation_fence(path, owner_uid=os.geteuid(), readonly=False) as fence:
        assert fence.read_ready(expected=expected, now=NOW)["status"] == "ready"
        private(path, path.read_bytes()[:-1] + b',"status":"ready"}')
        with pytest.raises(ActivationHold, match="duplicate_key"):
            fence.read_ready(expected=expected, now=NOW)


@pytest.mark.parametrize("target", ["state.json", "initial.json", "activation.lock"])
@pytest.mark.parametrize("change", ["permissions", "hardlink", "symlink"])
def test_untrusted_files_never_open(state, target, change):
    path, _, expected = state
    victim = path.parent / target
    if change == "permissions":
        victim.chmod(0o644)
    elif change == "hardlink":
        os.link(victim, path.parent / "other")
    else:
        victim.rename(path.parent / "other")
        victim.symlink_to("other")
    with (pytest.raises((ActivationHold, OSError)),
          activation_fence(path, owner_uid=os.geteuid(), readonly=False) as fence):
        fence.read_ready(expected=expected, now=NOW)


def test_inode_and_directory_replacement_are_detected_while_held(state):
    path, _, expected = state
    with activation_fence(path, owner_uid=os.geteuid(), readonly=False) as fence:
        lock = path.parent / "activation.lock"
        lock.rename(path.parent / "retired.lock")
        private(lock, b"replacement")
        with pytest.raises(ActivationHold, match="lock_changed"):
            fence.read_ready(expected=expected, now=NOW)
    lock.unlink()
    (path.parent / "retired.lock").rename(lock)
    with activation_fence(path, owner_uid=os.geteuid(), readonly=False) as fence:
        path.parent.rename(path.parent.with_name("retired"))
        path.parent.mkdir(mode=0o700)
        with pytest.raises(ActivationHold, match="directory_changed"):
            fence.identity()


@pytest.mark.parametrize("failure_at", ["file", "directory"])
def test_exclusive_revoke_is_durable_and_keeps_initial_and_lock(state, monkeypatch, failure_at):
    path, record, expected = state
    initial = (path.parent / "initial.json").read_bytes()
    inode = (path.parent / "activation.lock").stat().st_ino
    with activation_fence(path, owner_uid=os.geteuid(), exclusive=True) as fence:
        fence.revoke()
        revoked = json.loads(path.read_bytes())
        assert set(revoked) == READY_FIELDS
        assert revoked["started_at"] == record["started_at"]
        assert revoked["status"] == "revoked"
        with pytest.raises(ActivationHold, match="not_ready"):
            fence.read_ready(expected=expected, now=NOW)
        private(path, record)
        fsync = os.fsync
        def failed(fd):
            is_directory = stat.S_ISDIR(os.fstat(fd).st_mode)
            if is_directory == (failure_at == "directory"):
                raise OSError("synthetic fsync failure")
            fsync(fd)
        monkeypatch.setattr(os, "fsync", failed)
        with pytest.raises(OSError, match="fsync"):
            fence.revoke()
        assert json.loads(path.read_bytes())["status"] == (
            "revoked" if failure_at == "directory" else "ready")
    assert (path.parent / "initial.json").read_bytes() == initial
    assert (path.parent / "activation.lock").stat().st_ino == inode
    assert not list(path.parent.glob(".revoke-*"))


def test_separate_processes_share_one_lock_with_bounded_refusal_and_release(state):
    path, _, _ = state
    code = """
import os,sys
from pathlib import Path
from twobrain_rec_server.product_analytics.activation_fence import activation_fence,ActivationHold
try:
    with activation_fence(Path(sys.argv[1]), owner_uid=os.geteuid(), exclusive=sys.argv[2]=='EX',
                          timeout=.05, readonly=False): print('locked')
except ActivationHold as e: print(str(e))
"""
    def child(mode):
        result = subprocess.run([sys.executable, "-c", code, str(path), mode],
                                capture_output=True, text=True, timeout=5, check=True)
        return result.stdout.strip()
    with activation_fence(path, owner_uid=os.geteuid(), readonly=False):
        assert child("SH") == "locked"
        assert child("EX") == "activation_lock_busy"
    with activation_fence(path, owner_uid=os.geteuid(), exclusive=True):
        assert child("SH") == child("EX") == "activation_lock_busy"
    assert child("EX") == "locked"
