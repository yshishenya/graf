"""Real filesystem and child-process checks; all mail and decisions are synthetic."""
import asyncio
import copy
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest

from twobrain_rec_server.billing.observation_alerts import (
    HOLD_MARKER,
    AlertJournal,
    ObservationError,
    digest,
)

NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)


@pytest.fixture
def tmp_path():
    # The journal rejects shared writable ancestors such as the CI runner's /tmp.
    with TemporaryDirectory(prefix="graf-billing-observation-test-", dir=Path.home().resolve()) as directory:
        yield Path(directory)


@pytest.fixture
def journal_state(tmp_path):
    directory = tmp_path / "state"
    directory.mkdir(mode=0o700)
    path = directory / "journal.jsonl"
    profile, generation, binding = (str(uuid4()) for _ in range(3))
    AlertJournal.activate(path, source_profile=profile, source_generation=generation,
                          binding_version=binding, role="primary", now=NOW)
    return path, profile, generation, binding


def child(script, path, *args):
    result = subprocess.run([sys.executable, "-c", script, str(path), *args],
                            capture_output=True, timeout=10)
    assert result.stdout == b"" and result.stderr == b""
    return result.returncode


@pytest.mark.parametrize("barrier", [1, 2, 3, 4])
def test_process_death_at_sync_barriers_preserves_the_veto(journal_state, barrier):
    path, *_rest, binding = journal_state
    script = """
import os,sys
from twobrain_rec_server.billing.observation_alerts import AlertJournal
original = os.fsync
calls = 0
def die(fd):
    global calls
    original(fd)
    calls += 1
    if calls == int(sys.argv[2]):
        os._exit(73)
os.fsync = die
with AlertJournal(sys.argv[1]) as journal:
    journal.append('tick', {'completed_at': journal.last_now, 'source_check': 'unavailable',
                            'binding_version': sys.argv[3]})
raise SystemExit(9)
"""
    assert child(script, path, str(barrier), binding) == 73
    if barrier < 4:
        assert path.with_name("journal.jsonl.hold").read_bytes() == HOLD_MARKER
        for read_only in (False, True):
            with pytest.raises(ObservationError), AlertJournal(path, read_only=read_only):
                pass
    else:
        assert not path.with_name("journal.jsonl.hold").exists()
        with AlertJournal(path, read_only=True) as journal:
            assert journal.status()["completed_at"] == NOW.isoformat()


@pytest.mark.parametrize("failure", ["marker_write", "journal_write", "unlink"])
def test_record_io_failure_keeps_history_and_blocks_restart(journal_state, monkeypatch, failure):
    path, *_rest, binding = journal_state
    original = path.read_bytes()
    original_write = os.write
    with AlertJournal(path) as journal:
        def write(fd, data):
            if (failure == "journal_write" and fd == journal.fd) or (
                    failure == "marker_write" and data == HOLD_MARKER):
                raise OSError("synthetic disk full")
            return original_write(fd, data)

        def unlink(_path):
            raise OSError("synthetic unlink failure")

        monkeypatch.setattr(os, "write", write)
        if failure == "unlink":
            monkeypatch.setattr(os, "unlink", unlink)
        with pytest.raises(OSError):
            journal.append("tick", {"completed_at": NOW.isoformat(), "source_check": "unavailable",
                                    "binding_version": binding})
        with pytest.raises(ObservationError):
            journal.status()
    monkeypatch.undo()
    if failure != "unlink":
        assert path.read_bytes() == original
    assert path.with_name("journal.jsonl.hold").exists()
    with pytest.raises(ObservationError), AlertJournal(path):
        pass


@pytest.mark.parametrize("invalid", ["symlink", "hardlink", "mode", "content", "directory"])
def test_invalid_interlock_is_preserved_even_by_recovery(journal_state, tmp_path, invalid):
    path, *_ = journal_state
    flag = path.with_name("journal.jsonl.hold")
    target = tmp_path / "target"
    target.write_bytes(HOLD_MARKER)
    target.chmod(0o600)
    if invalid == "symlink":
        flag.symlink_to(target)
    elif invalid == "hardlink":
        os.link(target, flag)
    elif invalid == "directory":
        flag.mkdir(mode=0o700)
    else:
        flag.write_bytes(HOLD_MARKER if invalid == "mode" else b"invalid")
        flag.chmod(0o644 if invalid == "mode" else 0o600)
    original = path.read_bytes(), flag.lstat().st_ino
    for recovery in (False, True):
        with pytest.raises((ObservationError, OSError)), AlertJournal(path, recovery=recovery):
            pass
        assert (path.read_bytes(), flag.lstat().st_ino) == original


@pytest.mark.parametrize("startup_delay", [0, 3])
def test_second_process_cannot_remove_the_locked_writers_veto(journal_state, startup_delay):
    path, *_rest, binding = journal_state
    script = """
import sys,time
time.sleep(float(sys.argv[2]))
from twobrain_rec_server.billing.observation_alerts import AlertJournal, ObservationError
# Interpreter startup is outside the journal's lock budget.
started = time.monotonic()
try:
    with AlertJournal(sys.argv[1], recovery=True):
        pass
except ObservationError:
    assert 2 <= time.monotonic() - started < 4
    raise SystemExit(3)
raise SystemExit(9)
"""
    with AlertJournal(path) as journal:
        journal.begin_record()
        assert child(script, path, str(startup_delay)) == 3
        assert path.with_name("journal.jsonl.hold").exists()
        journal.recovery = True
        journal.append("recovery", {"expected_head": journal.head,
                                    "source_generation": journal.activation["source_generation"],
                                    "at": NOW.isoformat(), "evidence_ref": "synthetic:verified"})
        journal.append("tick", {"completed_at": NOW.isoformat(), "source_check": "unavailable",
                                "binding_version": binding})


class SyntheticMail:
    from_address = "sender@example.invalid"

    def __init__(self):
        self.posts = []

    async def _post_message(self, message):
        self.posts.append(message)
        return {"id": "synthetic-receipt"}


def test_storage_recovery_preserves_accepted_consumed_and_deadlines(journal_state, tmp_path):
    path, profile, generation, binding = journal_state
    mail = SyntheticMail()
    sample = {"schema_version": 1, "source_profile": profile, "source_generation": generation,
              "as_of": NOW.isoformat(), "coverage": "partial", "event_count": 2,
              "failed_event_count": 1, "conflicting_attempt_count": 0, "last_event_at": NOW.isoformat()}
    with AlertJournal(path) as journal:
        asyncio.run(journal.tick(source=sample, peer=None, now=NOW, binding_version=binding,
                                 client=mail, recipient="synthetic@example.invalid"))
        incident = journal.current("reconciliation_failure")
        manifest = {"source_profile": profile, "source_generation": generation,
                    "incident_id": incident["incident_id"], "incident_generation": 1,
                    "expected_basis_revision": 1, "basis_hash": incident["basis_hash"],
                    "action": "investigating", "evidence_class": "operational_review",
                    "evidence_ref": "synthetic:review", "message_ref": "synthetic:decision:1",
                    "message_at": NOW.isoformat(), "decision_digest": digest("synthetic decision")}
        journal.transfer(manifest, now=NOW)
        baseline = copy.deepcopy((journal.activation, journal.source, journal.messages,
                                  journal.incidents, journal.consumed))
        expected_head = journal.head
        backup = tmp_path / "backup"
        backup.mkdir(mode=0o700)
        journal.backup(backup / "journal.jsonl")
    flag = path.with_name("journal.jsonl.hold")
    flag.write_bytes(HOLD_MARKER)
    flag.chmod(0o600)
    with AlertJournal(path, recovery=True) as journal:
        assert (backup / "journal.jsonl").read_bytes() == path.read_bytes()
        with pytest.raises(ObservationError):
            journal.append("recovery", {"expected_head": "0" * 64, "source_generation": generation,
                                        "at": NOW.isoformat(), "evidence_ref": "synthetic:verified"})
        assert flag.exists()
        journal.append("recovery", {"expected_head": expected_head, "source_generation": generation,
                                    "at": NOW.isoformat(), "evidence_ref": "synthetic:verified"})
        assert (journal.activation, journal.source, journal.messages, journal.incidents, journal.consumed) == baseline
    assert not flag.exists()
    with AlertJournal(path) as journal:
        assert (journal.activation, journal.source, journal.messages, journal.incidents, journal.consumed) == baseline
        with pytest.raises(ObservationError):
            journal.transfer(manifest, now=NOW)
        asyncio.run(journal.tick(source={**sample, "as_of": (NOW + timedelta(seconds=300)).isoformat()},
                                 peer=None, now=NOW + timedelta(seconds=300), binding_version=binding,
                                 client=mail, recipient="synthetic@example.invalid"))
        assert len(mail.posts) == 1


def test_crash_inside_post_replays_unknown_without_storage_hold(journal_state):
    path, profile, generation, binding = journal_state
    sample = {"schema_version": 1, "source_profile": profile, "source_generation": generation,
              "as_of": NOW.isoformat(), "coverage": "partial", "event_count": 2,
              "failed_event_count": 1, "conflicting_attempt_count": 0, "last_event_at": NOW.isoformat()}
    script = """
import asyncio,json,os,sys
from datetime import datetime
from twobrain_rec_server.billing.observation_alerts import AlertJournal
class Mail:
    from_address = 'sender@example.invalid'
    async def _post_message(self, message):
        os._exit(74)
with AlertJournal(sys.argv[1]) as journal:
    sample = json.loads(sys.argv[2])
    asyncio.run(journal.tick(source=sample, peer=None, now=datetime.fromisoformat(sample['as_of']),
                            binding_version=sys.argv[3], client=Mail(), recipient='synthetic@example.invalid'))
raise SystemExit(9)
"""
    assert child(script, path, json.dumps(sample), binding) == 74
    assert not path.with_name("journal.jsonl.hold").exists()
    mail = SyntheticMail()
    with AlertJournal(path) as journal:
        assert next(iter(journal.messages.values()))["outcome"] == "unknown"
        assert journal.current("reconciliation_failure")["next_allowed_at"] == (NOW + timedelta(seconds=300)).isoformat()
        for seconds in (299, 300):
            now = NOW + timedelta(seconds=seconds)
            asyncio.run(journal.tick(source={**sample, "as_of": now.isoformat()}, peer=None, now=now,
                                     binding_version=binding, client=mail, recipient="synthetic@example.invalid"))
            assert len(mail.posts) == int(seconds == 300)


@pytest.mark.parametrize("limit", ["records", "bytes"])
def test_full_journal_replays_within_the_tick_budget(journal_state, limit):
    import time

    from twobrain_rec_server.billing.observation_alerts import (
        MAX_JOURNAL,
        MAX_RECORD,
        MAX_RECORDS,
        canonical,
    )

    path, profile, generation, binding = journal_state
    with AlertJournal(path) as journal:
        sequence, head = journal.sequence, journal.head
    with path.open("ab") as stream:
        def record(kind, data, target_size=None):
            nonlocal sequence, head
            sequence += 1
            value = {"sequence": sequence, "prev_sha256": head, "kind": kind, "data": data}
            if target_size is not None:
                data["at"] = "20261103T13." + "0" * 2 + "Z"
                raw = canonical(value | {"record_sha256": "0" * 64}) + b"\n"
                data["at"] = "20261103T13." + "0" * (2 + target_size - len(raw)) + "Z"
            head = digest(value)
            raw = canonical(value | {"record_sha256": head}) + b"\n"
            assert len(raw) <= MAX_RECORD
            if target_size is not None:
                assert len(raw) == target_size
            stream.write(raw)

        generations = 500 if limit == "bytes" else 1
        incident_id, basis = None, None
        for index in range(generations):
            if index:
                manifest = {"source_profile": profile, "source_generation": generation,
                    "incident_id": incident_id, "incident_generation": index, "expected_basis_revision": 1,
                    "basis_hash": digest(basis), "evidence_class": "operational_review",
                    "evidence_ref": "synthetic:verified", "message_at": NOW.isoformat(),
                    "decision_digest": digest("synthetic decision")}
                for action in ("investigating", "resolved"):
                    decision = {**manifest, "action": action, "message_ref": f"synthetic:{index}:{action}"}
                    record("transfer", {**decision, "transferred_at": NOW.isoformat(), "manifest_digest": digest(decision)})
                generation = str(uuid4())
                record("recovery", {"expected_head": head, "source_generation": generation,
                                    "at": NOW.isoformat(), "evidence_ref": "synthetic:verified"})
            basis = {"source_profile": profile, "source_generation": generation,
                     "kind": "reconciliation_failure", "count": 1}
            incident_id = str(uuid4())
            record("incident", {"incident_id": incident_id, "kind": "reconciliation_failure",
                "incident_generation": index + 1, "basis_revision": 1, "basis": basis,
                "basis_hash": digest(basis), "detected_at": NOW.isoformat(),
                "initial_deadline": (NOW + timedelta(seconds=300)).isoformat()})
        stream.flush()
        with AlertJournal(path) as journal:
            assert len(journal.incidents) == generations
            if generations == 500:
                before_limit = path.stat().st_size, journal.head
                with pytest.raises(ObservationError):
                    journal.detect("reconciliation_conflict", {"count": 1}, NOW)
                assert (path.stat().st_size, journal.head) == before_limit
        target_count = MAX_RECORDS if limit == "records" else MAX_RECORDS - 4096
        while sequence < target_count:
            data = {"at": "20261103T13Z", "source": None, "peer": None}
            target_size = None
            if limit == "bytes" and target_count - sequence <= 256:
                stream.flush()
                remaining = target_count - sequence
                target_size = (MAX_JOURNAL - stream.tell()) // remaining
                assert 260 <= target_size <= MAX_RECORD
            record("sample", data, target_size)
    size = path.stat().st_size
    assert size <= MAX_JOURNAL and (limit != "bytes" or size == MAX_JOURNAL)
    assert sequence == target_count
    started = time.monotonic()
    before = path.stat().st_size, head
    try:
        with AlertJournal(path) as journal:
            assert len(journal.incidents) == generations and journal.sequence == target_count and journal.head == head
            assert all(incident["breached"] for incident in journal.incidents.values())
            with pytest.raises(ObservationError):
                journal.append("tick", {"completed_at": (NOW + timedelta(hours=1)).isoformat(), "source_check": "unavailable",
                                        "binding_version": binding})
            assert (path.stat().st_size, journal.head) == before
        assert time.monotonic() - started < 60
        if limit == "records":
            value = {"sequence": sequence + 1, "prev_sha256": head, "kind": "sample",
                     "data": {"at": "20261103T13Z", "source": None, "peer": None}}
            extra = canonical(value | {"record_sha256": digest(value)}) + b"\n"
        else:
            extra = b"\n"
        with path.open("ab") as stream:
            stream.write(extra)
        oversize = path.stat().st_size
        with pytest.raises(ObservationError), AlertJournal(path):
            pass
        assert path.stat().st_size == oversize
    finally:
        path.unlink()


@pytest.mark.parametrize("stopped", ["primary", "witness", "producer", "source_from_start", "source_after_first"])
def test_two_journals_detect_only_the_missing_witness_at_900_seconds(tmp_path, stopped):
    profile, generation, binding = (str(uuid4()) for _ in range(3))
    paths, statuses, incidents, mail = {}, {"primary": None, "witness": None}, {}, {}
    for role in statuses:
        directory = tmp_path / role
        directory.mkdir(mode=0o700)
        paths[role] = directory / "journal.jsonl"
        AlertJournal.activate(paths[role], source_profile=profile, source_generation=generation,
                              binding_version=binding, role=role, now=NOW)
        mail[role] = 0
    script = """
import asyncio,json,sys
from datetime import datetime
from tests.integration.test_billing_observation_alerts import SyntheticMail
from twobrain_rec_server.billing.observation_alerts import AlertJournal
value=json.load(sys.stdin)
mail=SyntheticMail()
with AlertJournal(sys.argv[1]) as journal:
    status=asyncio.run(journal.tick(source=value['source'],peer=value['peer'],
        now=datetime.fromisoformat(value['now']),binding_version=value['binding'],
        client=mail,recipient='synthetic@example.invalid'))
    print(json.dumps({'status':status,'incidents':sorted({i['kind'] for i in journal.incidents.values()}),
                      'posts':len(mail.posts)}))
"""
    for seconds in (0, 300, 600, 899, 900):
        now = NOW + timedelta(seconds=seconds)
        for role in statuses:
            if seconds and stopped == role:
                continue
            source = {"schema_version": 1, "source_profile": profile, "source_generation": generation,
                "as_of": now.isoformat(), "coverage": "partial", "event_count": 2, "failed_event_count": 0,
                "conflicting_attempt_count": 0, "last_event_at": (NOW if stopped == "producer" else now).isoformat()}
            if role == "witness" or stopped == "source_from_start" or (stopped == "source_after_first" and seconds):
                source = None
            child = subprocess.run([sys.executable, "-c", script, str(paths[role])], input=json.dumps({
                "source": source, "peer": statuses["witness" if role == "primary" else "primary"],
                "now": now.isoformat(), "binding": binding}), capture_output=True, text=True, timeout=5)
            assert child.returncode == 0 and child.stderr == ""
            result = json.loads(child.stdout)
            statuses[role], incidents[role] = result["status"], set(result["incidents"])
            mail[role] += result["posts"]
            if seconds < 900:
                assert not incidents[role]
    expected = {"primary": {"witness": {"observer_gap"}}, "witness": {"primary": {"witness_gap"}},
                "producer": {"primary": {"producer_gap"}},
                "source_from_start": {"primary": {"source_gap", "producer_gap"}},
                "source_after_first": {"primary": {"source_gap", "producer_gap"}}}[stopped]
    for role in statuses:
        assert incidents[role] == expected.get(role, set())
        assert mail[role] == (1 if role in expected else 0)
        with AlertJournal(paths[role], read_only=True) as journal:
            assert journal.status() == statuses[role]
    if stopped.startswith("source"):
        assert statuses["primary"]["completed_at"] == (NOW + timedelta(seconds=900)).isoformat()
        assert statuses["primary"]["source_check"] == "unavailable"


@pytest.mark.parametrize("closure", ["resolved", "accepted_risk"])
def test_actual_restore_preserves_history_but_requires_new_lineage_before_send(journal_state, tmp_path, monkeypatch, closure):
    from pathlib import Path

    from twobrain_rec_server.cli import billing_observation_alerts as cli

    path, profile, generation, binding = journal_state
    mail = SyntheticMail()
    source = {"schema_version": 1, "source_profile": profile, "source_generation": generation,
        "as_of": NOW.isoformat(), "coverage": "partial", "event_count": 2,
        "failed_event_count": 1, "conflicting_attempt_count": 0, "last_event_at": NOW.isoformat()}
    backup_dir, restored_dir = tmp_path / "backup", tmp_path / "restored"
    for directory in (backup_dir, restored_dir):
        directory.mkdir(mode=0o700)
    backup, target = backup_dir / "journal.jsonl", restored_dir / "journal.jsonl"
    with AlertJournal(path) as journal:
        asyncio.run(journal.tick(source=source, peer=None, now=NOW, binding_version=binding,
                                 client=mail, recipient="synthetic@example.invalid"))
        incident = journal.current("reconciliation_failure")
        manifest = {"source_profile": profile, "source_generation": generation, "incident_id": incident["incident_id"],
            "incident_generation": 1, "expected_basis_revision": 1, "basis_hash": incident["basis_hash"],
            "action": "investigating", "evidence_class": "operational_review", "evidence_ref": "synthetic:review",
            "message_ref": "synthetic:chat:1", "message_at": NOW.isoformat(), "decision_digest": digest("synthetic decision")}
        journal.transfer(manifest, now=NOW)
        journal.transfer({**manifest, "action": closure, "message_ref": "synthetic:chat:2"}, now=NOW)
        saved = copy.deepcopy((journal.messages, journal.incidents, journal.consumed))
        journal.backup(backup)
        journal.append("tick", {"completed_at": (NOW + timedelta(seconds=1)).isoformat(),
                                "source_check": "unavailable", "binding_version": binding})
        latest_head = journal.head
    source_bytes, backup_bytes = path.read_bytes(), backup.read_bytes()
    monkeypatch.setattr(cli, "JOURNAL", target)
    monkeypatch.setattr(cli, "Path", lambda p: backup if p == "/backup/journal.jsonl" else Path(p))
    cli.restore()
    assert path.read_bytes() == source_bytes and backup.read_bytes() == backup_bytes
    with AlertJournal(target) as journal:
        assert journal.hold and (journal.messages, journal.incidents, journal.consumed) == saved
        with pytest.raises(ObservationError):
            journal.status()
        with pytest.raises(ObservationError):
            asyncio.run(journal.tick(source=source, peer=None, now=NOW, binding_version=binding,
                                     client=mail, recipient="synthetic@example.invalid"))
        with pytest.raises(ObservationError):
            journal.append("recovery", {"expected_head": latest_head, "source_generation": str(uuid4()),
                                        "at": NOW.isoformat(), "evidence_ref": "synthetic:verified"})
        with pytest.raises(ObservationError):
            journal.append("recovery", {"expected_head": journal.head, "source_generation": generation,
                                        "at": NOW.isoformat(), "evidence_ref": "synthetic:verified"})
        next_generation = str(uuid4())
        journal.append("recovery", {"expected_head": journal.head, "source_generation": next_generation,
                                    "at": NOW.isoformat(), "evidence_ref": "synthetic:verified"})
        assert (journal.messages, journal.incidents, journal.consumed) == saved
        with pytest.raises(ObservationError):
            journal.transfer(manifest, now=NOW)
        now = NOW + timedelta(seconds=300)
        asyncio.run(journal.tick(source={**source, "source_generation": next_generation, "as_of": now.isoformat()},
            peer=None, now=now, binding_version=binding, client=mail, recipient="synthetic@example.invalid"))
        assert journal.current("reconciliation_failure")["incident_generation"] == 2
    assert len(mail.posts) == 2
    with AlertJournal(target, read_only=True) as journal:
        assert len(journal.incidents) == 2 and saved[2] <= journal.consumed
        assert all(m["outcome"] == "accepted" for m in journal.messages.values())


@pytest.mark.parametrize("invalid", ["missing", "partial", "hash", "live_target"])
def test_actual_restore_refuses_invalid_backup_without_replacing_history(journal_state, tmp_path, monkeypatch, invalid):
    from pathlib import Path

    from twobrain_rec_server.cli import billing_observation_alerts as cli

    path, *_ = journal_state
    backup_dir, restored_dir = tmp_path / "backup", tmp_path / "restored"
    for directory in (backup_dir, restored_dir):
        directory.mkdir(mode=0o700)
    backup, target = backup_dir / "journal.jsonl", restored_dir / "journal.jsonl"
    if invalid != "missing":
        with AlertJournal(path) as journal:
            journal.backup(backup)
        if invalid == "partial":
            backup.write_bytes(backup.read_bytes()[:-1])
        elif invalid == "hash":
            backup.write_bytes(backup.read_bytes().replace(b'"primary"', b'"witness"'))
        else:
            target = path
    before = path.read_bytes()
    monkeypatch.setattr(cli, "JOURNAL", target)
    monkeypatch.setattr(cli, "Path", lambda p: backup if p == "/backup/journal.jsonl" else Path(p))
    with pytest.raises((ObservationError, OSError)):
        cli.restore()
    assert path.read_bytes() == before
    assert (target == path) or not target.exists()
