"""Operator-owned activation fence; reading a receipt never creates readiness.

The operator provisions the directory and permanent lock outside DB backups.
Runtime callers must hold SH through transaction completion and connection close.
Only the trusted full verifier may issue ready/initial receipts; this module has
no initialise command, pass-file input or fallback that can open admission.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

READY_FIELDS = frozenset({
    "version", "status", "mode", "started_at", "verified_at", "source_sha", "image_id",
    "cluster_id", "db_name", "db_oid", "schema_revision", "ledger_invariants_sha256",
    "roles_sha256", "lock_dev", "lock_ino", "initial_receipt_sha256", "history_proof_sha256",
    "backup_manifest_sha256", "backup_finished_at", "restore_receipt_sha256",
    "restore_verified_at", "disposition_coverage_sha256", "retention_receipt_sha256",
    "retention_verified_at", "resource_guard_sha256", "resource_verified_at", "reason",
})
INITIAL_FIELDS = frozenset({
    "version", "started_at", "lock_dev", "lock_ino", "history_proof_sha256",
})
DIGEST_FIELDS = tuple(sorted(key for key in READY_FIELDS if key.endswith("_sha256")))
TIME_LIMITS = {"backup_finished_at": 26 * 3600, "restore_verified_at": 30 * 86400,
               "retention_verified_at": 26 * 3600, "resource_verified_at": 26 * 3600}


class ActivationHold(PermissionError):
    """A finite metadata-only reason; never include a path, payload or SQL error."""


def _require(value: bool, reason: str) -> None:
    if not value:
        raise ActivationHold(reason)


def _object(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "activation_receipt_duplicate_key")
            result[key] = value
        return result

    try:
        result = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise ActivationHold("activation_receipt_invalid") from None
    _require(isinstance(result, dict), "activation_receipt_invalid")
    return result


def _timestamp(value: object) -> datetime:
    _require(isinstance(value, str), "activation_timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ActivationHold("activation_timestamp_invalid") from None
    _require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0,
             "activation_timestamp_invalid")
    return parsed


@dataclass(slots=True)
class ActivationFence:
    directory: int
    descriptor: int
    owner_uid: int
    state_name: str
    exclusive: bool
    path: Path

    def _file(self, name: str) -> bytes:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.directory)
        try:
            before = os.fstat(fd)
            _require(stat.S_ISREG(before.st_mode) and before.st_uid == self.owner_uid
                     and stat.S_IMODE(before.st_mode) == 0o600 and before.st_nlink == 1
                     and 0 < before.st_size <= 16384, "activation_file_untrusted")
            raw = os.read(fd, 16385)
            after = os.fstat(fd)
            _require(len(raw) == before.st_size
                     and (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                     == (after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                     "activation_file_changed")
            return raw
        finally:
            os.close(fd)

    def identity(self) -> tuple[int, int]:
        """Do not silently lock a replaced inode or renamed operator directory."""
        before = os.fstat(self.descriptor)
        directory = os.fstat(self.directory)
        current = self.path.parent.lstat()
        _require(stat.S_ISDIR(current.st_mode) and current.st_uid == self.owner_uid
                 and stat.S_IMODE(current.st_mode) == 0o700
                 and (directory.st_dev, directory.st_ino) == (current.st_dev, current.st_ino),
                 "activation_directory_changed")
        after = os.stat("activation.lock", dir_fd=self.directory, follow_symlinks=False)
        _require(before.st_dev == after.st_dev and before.st_ino == after.st_ino
                 and stat.S_ISREG(after.st_mode) and after.st_uid == self.owner_uid
                 and stat.S_IMODE(after.st_mode) == 0o600 and after.st_nlink == 1,
                 "activation_lock_changed")
        return before.st_dev, before.st_ino

    def read_ready(self, *, expected: Mapping[str, object], now: datetime | None = None) -> dict:
        """Consume the trusted verifier's result, bound to this lock and runtime.

        expected is supplied by the server/operator, never an HTTP request.
        Actual DB/schema checks and the fresh legal/resource gates are additional
        requirements at the insertion boundary, not inferred from JSON here.
        """
        moment = now or datetime.now(UTC)
        _require(moment.tzinfo is not None, "activation_timestamp_invalid")
        record = _object(self._file(self.state_name))
        _require(set(record) == READY_FIELDS and type(record["version"]) is int
                 and record["version"] == 1, "activation_receipt_invalid")
        _require(record["status"] == "ready" and record["mode"] == "local_only"
                 and record["reason"] == "verified", "activation_not_ready")
        for key in DIGEST_FIELDS:
            _require(isinstance(record[key], str) and re.fullmatch(r"[0-9a-f]{64}", record[key])
                     is not None, "activation_digest_invalid")
        _require(isinstance(record["source_sha"], str)
                 and re.fullmatch(r"[0-9a-f]{40}", record["source_sha"]) is not None
                 and isinstance(record["image_id"], str)
                 and re.fullmatch(r"sha256:[0-9a-f]{64}", record["image_id"]) is not None
                 and isinstance(record["cluster_id"], str)
                 and re.fullmatch(r"[0-9]{1,20}", record["cluster_id"]) is not None
                 and isinstance(record["db_name"], str)
                 and re.fullmatch(r"[a-z][a-z0-9_]{0,62}", record["db_name"]) is not None
                 and type(record["db_oid"]) is int and record["db_oid"] > 0
                 and isinstance(record["schema_revision"], str)
                 and re.fullmatch(r"[0-9]{4}_[a-z0-9_]{1,90}", record["schema_revision"])
                 is not None, "activation_binding_invalid")
        binding = {"source_sha", "image_id", "cluster_id", "db_name", "db_oid", "schema_revision"}
        _require(set(expected) == binding and all(type(expected[k]) is type(record[k])
                 and record[k] == expected[k] for k in binding), "activation_binding_mismatch")
        dev, ino = self.identity()
        _require(type(record["lock_dev"]) is int and type(record["lock_ino"]) is int
                 and (record["lock_dev"], record["lock_ino"]) == (dev, ino),
                 "activation_lock_changed")
        started = _timestamp(record["started_at"])
        verified = _timestamp(record["verified_at"])
        _require(started <= verified <= moment, "activation_timestamp_invalid")
        for key, maximum in TIME_LIMITS.items():
            age = (moment - _timestamp(record[key])).total_seconds()
            _require(0 <= age < maximum or (key == "restore_verified_at" and age == maximum),
                     "activation_evidence_stale")
        initial_raw = self._file("initial.json")
        _require(hashlib.sha256(initial_raw).hexdigest() == record["initial_receipt_sha256"],
                 "activation_initial_mismatch")
        initial = _object(initial_raw)
        _require(set(initial) == INITIAL_FIELDS and type(initial["version"]) is int
                 and initial["version"] == 1 and all(type(initial[key]) is type(record[key])
                 and initial[key] == record[key] for key in INITIAL_FIELDS - {"version"}),
                 "activation_initial_mismatch")
        self.identity()
        return record

    def revoke(self) -> None:
        """Durably close admission even when the old receipt is absent/invalid.

        No initial receipt is created, replaced or removed. The tombstone cannot
        pass read_ready; the full verifier must rebuild readiness for that same
        initial period. A failed fsync is an error, never permission to restore.
        """
        _require(self.exclusive, "activation_exclusive_required")
        dev, ino = self.identity()
        temporary = ".revoke-" + uuid4().hex
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=self.directory)
        try:
            record = dict.fromkeys(READY_FIELDS)
            record.update(version=1, status="revoked", mode="local_only",
                          lock_dev=dev, lock_ino=ino, reason="operator_revoked")
            try:
                initial = _object(self._file("initial.json"))
                if set(initial) == INITIAL_FIELDS:
                    record["started_at"] = initial["started_at"]
            except (OSError, ActivationHold):
                pass  # Lost initial cannot open a new period; still revoke now.
            raw = (json.dumps(record, sort_keys=True) + "\n").encode()
            _require(os.write(fd, raw) == len(raw), "activation_revoke_failed")
            os.fchmod(fd, 0o600)
            if os.fstat(fd).st_uid != self.owner_uid:
                os.fchown(fd, self.owner_uid, -1)
            os.fsync(fd)
            os.replace(temporary, self.state_name, src_dir_fd=self.directory,
                       dst_dir_fd=self.directory)
            os.fsync(self.directory)
            self.identity()
            _require(self._file(self.state_name) == raw, "activation_revoke_failed")
        finally:
            os.close(fd)
            with suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=self.directory)


@contextmanager
def activation_fence(state_file: Path, *, owner_uid: int, exclusive: bool = False,
                     timeout: float = 30, readonly: bool = True) -> Iterator[ActivationFence]:
    """Open only an existing permanent inode. Runtime SH never waits."""
    _require(type(owner_uid) is int and owner_uid >= 0 and state_file.is_absolute()
             and state_file.name not in {"activation.lock", "initial.json", ".", ".."}
             and isinstance(timeout, (int, float)) and 0 <= timeout <= 30,
             "activation_configuration_invalid")
    directory = os.open(state_file.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptor = None
    try:
        info = os.fstat(directory)
        _require(info.st_uid == owner_uid and stat.S_IMODE(info.st_mode) == 0o700,
                 "activation_directory_untrusted")
        if readonly and not exclusive:
            _require(bool(os.fstatvfs(directory).f_flag & os.ST_RDONLY),
                     "activation_mount_writable")
            # Mount the stable outer parent, never this replaceable directory:
            # a direct bind pins its old inode after a host rename.
            parent = os.open(state_file.parent.parent,
                             os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                mount_ids = []
                for fd in (parent, directory):
                    matches = re.findall(r"^mnt_id:\s+([0-9]+)$",
                                         Path(f"/proc/self/fdinfo/{fd}").read_text(), re.M)
                    _require(len(matches) == 1, "activation_mount_unverified")
                    mount_ids.append(matches[0])
                _require(mount_ids[0] == mount_ids[1], "activation_direct_mount")
            finally:
                os.close(parent)
        descriptor = os.open("activation.lock", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        fence = ActivationFence(directory, descriptor, owner_uid, state_file.name, exclusive, state_file)
        fence.identity()
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(descriptor, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                            | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if not exclusive or time.monotonic() >= deadline:
                    raise ActivationHold("activation_lock_busy") from None
                time.sleep(min(.01, max(0, deadline - time.monotonic())))
        fence.identity()
        yield fence
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)
