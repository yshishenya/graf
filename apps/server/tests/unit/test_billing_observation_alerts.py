"""Synthetic requirement regressions for the independent operational journal."""
import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import httpx
import pytest

from twobrain_rec_server.auth.email_delivery import PostalEmailLoginClient

NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)


@pytest.fixture
def tmp_path():
    # The journal rejects shared writable ancestors such as the CI runner's /tmp.
    with TemporaryDirectory(prefix="graf-billing-observation-test-", dir=Path.home().resolve()) as directory:
        yield Path(directory)


def setup_journal(tmp_path, *, role="primary"):
    from twobrain_rec_server.billing.observation_alerts import AlertJournal

    directory = tmp_path / "state"
    directory.mkdir(mode=0o700)
    profile, generation, binding = (str(uuid4()) for _ in range(3))
    path = directory / "journal.jsonl"
    AlertJournal.activate(path, source_profile=profile, source_generation=generation,
                          binding_version=binding, role=role, now=NOW)
    return AlertJournal, path, profile, generation, binding


@pytest.mark.parametrize("mode", [0o777, 0o1777])
def test_activation_rejects_shared_writable_ancestor_without_creating_state(tmp_path, mode):
    from twobrain_rec_server.billing.observation_alerts import ObservationError

    shared = tmp_path / "shared"
    shared.mkdir()
    shared.chmod(mode)
    with pytest.raises(ObservationError):
        setup_journal(shared)
    assert list((shared / "state").iterdir()) == []


def sample(profile, generation, now=NOW, *, events=2, failed=0, conflicts=0):
    return {"schema_version": 1, "source_profile": profile, "source_generation": generation,
            "as_of": now.isoformat(), "coverage": "partial", "event_count": events,
            "failed_event_count": failed, "conflicting_attempt_count": conflicts,
            "last_event_at": now.isoformat() if events else None}


def postal(posts, outcome="success"):
    async def handle(request):
        posts.append(json.loads(request.content))
        if outcome == "unknown":
            raise httpx.ReadTimeout("private transport detail", request=request)
        return httpx.Response(200, json={"status": outcome, "data": {"messages": {
            "synthetic@example.invalid": {"id": "synthetic-acceptance"}}}})

    return PostalEmailLoginClient("https://postal.invalid", "synthetic-key",
                                  "sender@example.invalid", transport=httpx.MockTransport(handle))


def test_bootstrap_success_and_read_only_status_are_not_failure_or_tick(tmp_path):
    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        assert journal.status()["completed_at"] is None
        asyncio.run(journal.tick(source=sample(profile, generation), peer=None, now=NOW,
                                 binding_version=binding, client=postal(posts),
                                 recipient="synthetic@example.invalid"))
        assert journal.incidents == {}
        first = path.read_bytes()
        assert journal.status()["completed_at"] == NOW.isoformat()
        assert journal.status()["completed_at"] == NOW.isoformat()
        assert path.read_bytes() == first and posts == []


def test_current_basis_only_and_accepted_dedup_survive_restart(tmp_path):
    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None,
                                 now=NOW, binding_version=binding, client=postal(posts, "unknown"),
                                 recipient="synthetic@example.invalid"))
        incident = next(iter(journal.incidents.values()))
        original_id = incident["incident_id"]
        original_deadline = incident["initial_deadline"]
        first_key = posts[0]["headers"]["X-2brain-Delivery-Key"]
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=299),
                                               events=3, failed=2), peer=None,
                                 now=NOW + timedelta(seconds=299), binding_version=binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(posts) == 1
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=300),
                                               events=3, failed=2), peer=None,
                                 now=NOW + timedelta(seconds=300), binding_version=binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
        incident = journal.incidents[original_id]
        assert incident["basis_revision"] == 2
        assert incident["initial_deadline"] == original_deadline
        assert len(posts) == 2 and first_key != posts[-1]["headers"]["X-2brain-Delivery-Key"]
        assert journal.messages[first_key]["attempt"] == 1
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=600),
                                               events=4, failed=2), peer=None,
                                 now=NOW + timedelta(seconds=600), binding_version=binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(posts) == 2


def test_partial_tail_is_preserved_and_refused(tmp_path):
    from twobrain_rec_server.billing.observation_alerts import ObservationError

    cls, path, *_ = setup_journal(tmp_path)
    with path.open("ab") as stream:
        stream.write(b'{"partial":')
    original = path.read_bytes()
    with pytest.raises(ObservationError), cls(path):
        pass
    assert path.read_bytes() == original


@pytest.mark.parametrize("outcome", ["unknown", "error"])
def test_queue_gives_second_alert_a_turn_before_old_retry(tmp_path, outcome):
    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1, conflicts=1), peer=None,
                                 now=NOW, binding_version=binding, client=postal(posts, outcome),
                                 recipient="synthetic@example.invalid"))
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=300), failed=1, conflicts=1),
                                 peer=None, now=NOW + timedelta(seconds=300), binding_version=binding,
                                 client=postal(posts, outcome), recipient="synthetic@example.invalid"))
        assert len(posts) == 2
        assert posts[0]["headers"]["X-2brain-Delivery-Key"] != posts[1]["headers"]["X-2brain-Delivery-Key"]
        assert all(message["attempt"] == 1 for message in journal.messages.values())


@pytest.mark.parametrize("outcome", ["unknown", "error"])
def test_binding_change_and_late_old_acceptance_do_not_notify_new_key(tmp_path, outcome):
    from twobrain_rec_server.billing.observation_alerts import digest, stamp

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    new_binding = str(uuid4())
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
                                 binding_version=binding, client=postal(posts, outcome), recipient="synthetic@example.invalid"))
        old_key = posts[0]["headers"]["X-2brain-Delivery-Key"]
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=299), failed=1),
                                 peer=None, now=NOW + timedelta(seconds=299), binding_version=new_binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(posts) == 1
        journal.append("outcome", {"message_key": old_key, "attempt": 1, "outcome": "accepted",
                                   "acceptance_digest": digest("late"), "at": stamp(NOW + timedelta(seconds=299))})
        assert next(iter(journal.incidents.values()))["notified_key"] is None
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=300), failed=1),
                                 peer=None, now=NOW + timedelta(seconds=300), binding_version=new_binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(posts) == 2
        incident = next(iter(journal.incidents.values()))
        assert incident["notified_key"] == posts[-1]["headers"]["X-2brain-Delivery-Key"] != old_key
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=600), failed=1),
                                 peer=None, now=NOW + timedelta(seconds=600), binding_version=new_binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(posts) == 2 and len(journal.messages) == 2


def test_specific_owner_decision_survives_samples_but_not_new_failure(tmp_path):
    from twobrain_rec_server.billing.observation_alerts import ObservationError, digest, stamp

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
                                 binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        incident = next(iter(journal.incidents.values()))
        manifest = {"source_profile": profile, "source_generation": generation, "incident_id": incident["incident_id"],
                    "incident_generation": 1, "expected_basis_revision": 1, "basis_hash": incident["basis_hash"],
                    "action": "investigating", "evidence_class": "operational_review", "evidence_ref": "synthetic:review",
                    "message_ref": "synthetic:chat:1", "message_at": stamp(NOW), "decision_digest": digest("synthetic decision")}
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=300), events=3, failed=1),
                                 peer=None, now=NOW + timedelta(seconds=300), binding_version=binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
        assert incident["basis_revision"] == 1
        journal.transfer(manifest, now=NOW + timedelta(seconds=300))
        risk = {**manifest, "action": "accepted_risk", "message_ref": "synthetic:chat:2"}
        journal.transfer(risk, now=NOW + timedelta(seconds=300))
        with pytest.raises(ObservationError):
            journal.transfer(risk, now=NOW + timedelta(seconds=300))
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=600), events=4, failed=1),
                                 peer=None, now=NOW + timedelta(seconds=600), binding_version=binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(journal.incidents) == 1
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=601), events=5, failed=2),
                                 peer=None, now=NOW + timedelta(seconds=601), binding_version=binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
        current = journal.current("reconciliation_failure")
        assert current["incident_generation"] == 2 and current["basis_revision"] == 1 and current["closure"] is None
        with pytest.raises(ObservationError):
            journal.transfer({**risk, "message_ref": "synthetic:chat:3"}, now=NOW + timedelta(seconds=601))


@pytest.mark.parametrize("age", [899, 900, 901])
def test_empty_source_gap_uses_activation_boundary_without_financial_failure(tmp_path, age):
    cls, path, *_rest, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=None, peer=None, now=NOW + timedelta(seconds=age),
                                 binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        assert set(i["kind"] for i in journal.incidents.values()) == (
            {"source_gap", "producer_gap", "witness_gap"} if age >= 900 else set())
        assert len(posts) == (1 if age >= 900 else 0)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'x' * 16385])
def test_closed_json_input_rejects_ambiguous_or_unbounded_values(raw):
    from twobrain_rec_server.billing.observation_alerts import ObservationError, decode

    with pytest.raises(ObservationError):
        decode(raw)


def test_fsync_failure_with_a_valid_tail_stays_hold_after_restart(tmp_path, monkeypatch):
    import os

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    original_fsync = os.fsync
    posts = []
    with cls(path) as journal:
        def fail(fd):
            if fd == journal.fd:
                raise OSError("synthetic fsync failure")
            return original_fsync(fd)

        monkeypatch.setattr(os, "fsync", fail)
        with pytest.raises(OSError):
            asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None,
                                     now=NOW, binding_version=binding, client=postal(posts),
                                     recipient="synthetic@example.invalid"))
    monkeypatch.setattr(os, "fsync", original_fsync)
    # An intact readable tail is not evidence that the previous fsync succeeded.
    from twobrain_rec_server.billing.observation_alerts import ObservationError

    with pytest.raises(ObservationError), cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, NOW + timedelta(seconds=300), failed=1),
                                 peer=None, now=NOW + timedelta(seconds=300), binding_version=binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
    assert posts == []


@pytest.mark.parametrize("barrier", [1, 2, 3, 4])
def test_record_sync_failure_blocks_a_new_process_and_status(tmp_path, monkeypatch, barrier):
    import os
    import subprocess
    import sys

    cls, path, *_rest, binding = setup_journal(tmp_path)
    original = path.read_bytes()
    original_fsync = os.fsync
    calls = 0
    with cls(path) as journal:
        def fail(fd):
            nonlocal calls
            calls += 1
            if calls == barrier:
                raise OSError("synthetic sync failure")
            return original_fsync(fd)

        monkeypatch.setattr(os, "fsync", fail)
        with pytest.raises(OSError):
            journal.append("tick", {"completed_at": NOW.isoformat(), "source_check": "unavailable",
                                    "binding_version": binding})
    monkeypatch.setattr(os, "fsync", original_fsync)
    assert path.with_name("journal.jsonl.hold").exists()
    if barrier < 3:
        assert path.read_bytes() == original
    else:
        assert len(path.read_bytes().splitlines()) == 2
    script = """
import sys
from twobrain_rec_server.billing.observation_alerts import AlertJournal, ObservationError
try:
    with AlertJournal(sys.argv[1], read_only=True) as journal:
        journal.status()
except (ObservationError, OSError):
    raise SystemExit(3)
raise SystemExit(0)
"""
    result = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True, timeout=10)
    assert result.returncode == 3 and result.stdout == b"" and result.stderr == b""


def test_old_interlock_is_never_claimed_by_a_writer_or_read_only_status(tmp_path):
    from twobrain_rec_server.billing.observation_alerts import ObservationError

    cls, path, *_ = setup_journal(tmp_path)
    flag = path.with_name("journal.jsonl.hold")
    flag.write_bytes(b"GRAF_OBSERVATION_HOLD_V1\n")
    flag.chmod(0o600)
    before = path.read_bytes(), flag.read_bytes(), flag.stat().st_ino
    for read_only in (False, True):
        with pytest.raises(ObservationError), cls(path, read_only=read_only):
            pass
        assert (path.read_bytes(), flag.read_bytes(), flag.stat().st_ino) == before


def test_activation_places_interlock_before_journal_creation(tmp_path, monkeypatch):
    import os

    from twobrain_rec_server.billing.observation_alerts import AlertJournal

    directory = tmp_path / "activation"
    directory.mkdir(mode=0o700)
    path = directory / "journal.jsonl"
    original_open = os.open

    def fail(file, flags, mode=0o777, **kwargs):
        if str(file) == str(path):
            assert path.with_name("journal.jsonl.hold").exists()
            raise OSError("synthetic create failure")
        return original_open(file, flags, mode, **kwargs)

    monkeypatch.setattr(os, "open", fail)
    with pytest.raises(OSError):
        AlertJournal.activate(path, source_profile=str(uuid4()), source_generation=str(uuid4()),
                              binding_version=str(uuid4()), role="primary", now=NOW)
    assert not path.exists() and path.with_name("journal.jsonl.hold").exists()


def test_recovery_keeps_old_generation_history_out_of_the_send_queue(tmp_path):
    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
                                 binding_version=binding, client=postal(posts, "unknown"),
                                 recipient="synthetic@example.invalid"))
        next_generation = str(uuid4())
        journal.append("recovery", {"expected_head": journal.head, "source_generation": next_generation,
                                    "at": (NOW + timedelta(seconds=300)).isoformat(),
                                    "evidence_ref": "synthetic:recovery"})
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, next_generation, NOW + timedelta(seconds=300)),
                                 peer=None, now=NOW + timedelta(seconds=300), binding_version=binding,
                                 client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(journal.incidents) == 1
        assert len(posts) == 1


def test_return_to_existing_binding_notifies_the_current_identity(tmp_path):
    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        for seconds, current_binding, outcome in (
            (0, binding, "unknown"), (1, str(uuid4()), "unknown"), (300, binding, "success")
        ):
            now = NOW + timedelta(seconds=seconds)
            asyncio.run(journal.tick(source=sample(profile, generation, now, failed=1), peer=None,
                                     now=now, binding_version=current_binding, client=postal(posts, outcome),
                                     recipient="synthetic@example.invalid"))
        incident = next(iter(journal.incidents.values()))
        assert len(posts) == 2
        assert incident["notified_key"] == posts[-1]["headers"]["X-2brain-Delivery-Key"]


def test_mail_outcome_uses_the_observed_completion_time(tmp_path):
    cls, path, profile, generation, binding = setup_journal(tmp_path)
    observed = NOW + timedelta(seconds=7)
    posts = []
    with cls(path, clock=lambda: observed) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
                                 binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
    records = [json.loads(raw) for raw in path.read_bytes().splitlines()]
    outcome = next(record["data"] for record in records if record["kind"] == "outcome")
    assert outcome["at"] == observed.isoformat()


def test_clock_rollback_during_mail_preserves_unknown_and_a_durable_hold(tmp_path):
    from twobrain_rec_server.billing.observation_alerts import ObservationError

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    clock = iter((NOW, NOW - timedelta(seconds=1)))
    with cls(path, clock=lambda: next(clock)) as journal, pytest.raises(ObservationError):
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
                                 binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
    assert len(posts) == 1
    with cls(path, read_only=True) as journal:
        assert next(iter(journal.messages.values()))["outcome"] == "unknown" and journal.hold
        with pytest.raises(ObservationError):
            journal.status()


@pytest.mark.parametrize("phase", ["before_post", "after_outcome"])
def test_clock_rollback_at_send_boundaries_blocks_further_mail(tmp_path, phase):
    from twobrain_rec_server.billing.observation_alerts import ObservationError

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    times = (NOW - timedelta(seconds=1),) if phase == "before_post" else (
        NOW, NOW + timedelta(seconds=7), NOW + timedelta(seconds=6))
    clock = iter(times)
    posts = []
    with cls(path, clock=lambda: next(clock)) as journal, pytest.raises(ObservationError):
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
                                 binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
    assert len(posts) == (0 if phase == "before_post" else 1)
    with cls(path, read_only=True) as journal:
        assert journal.hold and journal.tick_record is None
        with pytest.raises(ObservationError):
            journal.status()


def test_owner_transfer_advances_the_replayed_clock_boundary(tmp_path):
    from twobrain_rec_server.billing.observation_alerts import ObservationError, digest, stamp

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
                                 binding_version=binding, client=postal([]), recipient="synthetic@example.invalid"))
        incident = journal.current("reconciliation_failure")
        journal.transfer({"source_profile": profile, "source_generation": generation,
            "incident_id": incident["incident_id"], "incident_generation": 1,
            "expected_basis_revision": 1, "basis_hash": incident["basis_hash"], "action": "investigating",
            "evidence_class": "operational_review", "evidence_ref": "synthetic:review",
            "message_ref": "synthetic:clock:1", "message_at": stamp(NOW),
            "decision_digest": digest("synthetic decision")}, now=NOW + timedelta(seconds=10))
    with cls(path) as journal:
        with pytest.raises(ObservationError):
            asyncio.run(journal.tick(source=None, peer=None, now=NOW + timedelta(seconds=9),
                                     binding_version=binding, client=postal([]), recipient="synthetic@example.invalid"))
        assert journal.hold


@pytest.mark.parametrize("excess", [0, 1])
def test_single_record_size_boundary_is_enforced_before_write(tmp_path, excess):
    from twobrain_rec_server.billing.observation_alerts import (
        MAX_RECORD,
        ObservationError,
        canonical,
    )

    cls, path, *_ = setup_journal(tmp_path)
    with cls(path) as journal:
        data = {"at": "20261103T12.0Z", "source": None, "peer": None}
        value = {"sequence": journal.sequence + 1, "prev_sha256": journal.head,
                 "kind": "sample", "data": data, "record_sha256": "0" * 64}
        padding = MAX_RECORD + excess - len(canonical(value)) - 1
        data["at"] = "20261103T12." + "0" * (1 + padding) + "Z"
        before = path.read_bytes()
        if excess:
            with pytest.raises(ObservationError):
                journal.append("sample", data)
            assert path.read_bytes() == before
        else:
            journal.append("sample", data)
            assert path.stat().st_size == len(before) + MAX_RECORD
    with cls(path, read_only=True) as journal:
        assert journal.sequence == (1 if excess else 2)


@pytest.mark.parametrize("closed", [False, True])
def test_source_generation_preserves_the_incident_chain_and_retry_deadline(tmp_path, closed):
    from twobrain_rec_server.billing.observation_alerts import ObservationError, digest, stamp

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
                                 binding_version=binding, client=postal(posts, "unknown"), recipient="synthetic@example.invalid"))
        first = journal.current("reconciliation_failure").copy()
        manifest = {"source_profile": profile, "source_generation": generation, "incident_id": first["incident_id"],
            "incident_generation": 1, "expected_basis_revision": 1, "basis_hash": first["basis_hash"],
            "action": "investigating", "evidence_class": "operational_review", "evidence_ref": "synthetic:review",
            "message_ref": "synthetic:generation:1", "message_at": stamp(NOW), "decision_digest": digest("synthetic decision")}
        if closed:
            journal.transfer(manifest, now=NOW)
            journal.transfer({**manifest, "action": "resolved", "message_ref": "synthetic:generation:2"}, now=NOW)
        next_generation = str(uuid4())
        journal.append("recovery", {"expected_head": journal.head, "source_generation": next_generation,
            "at": stamp(NOW + timedelta(seconds=1)), "evidence_ref": "synthetic:verified"})
    with cls(path) as journal:
        now = NOW + timedelta(seconds=2)
        asyncio.run(journal.tick(source=sample(profile, next_generation, now, failed=1), peer=None, now=now,
                                 binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        current = journal.current("reconciliation_failure")
        assert current["incident_generation"] == (2 if closed else 1)
        assert current["basis_revision"] == (1 if closed else 2)
        assert (current["incident_id"] == first["incident_id"]) == (not closed)
        if not closed:
            assert all(current[k] == first[k] for k in ("detected_at", "initial_deadline", "next_allowed_at"))
            assert len(posts) == 1
        with pytest.raises(ObservationError):
            journal.transfer(manifest, now=now)
    with cls(path) as journal:
        assert journal.current("reconciliation_failure")["incident_id"] == current["incident_id"]
        now = NOW + timedelta(seconds=300)
        asyncio.run(journal.tick(source=sample(profile, next_generation, now, failed=1), peer=None, now=now,
                                 binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(posts) == 2
        assert journal.messages[first["current_message_key"]]["attempt"] == 1


@pytest.mark.parametrize("invalid", ["source_check", "peer_tick_at", "sequence", "wrong_role",
                                     "bool_sequence", "future_tick", "bad_time"])
def test_invalid_peer_schema_never_refreshes_its_tick(tmp_path, invalid):
    cls, path, profile, generation, binding = setup_journal(tmp_path)
    peer = {"schema_version": 1, "role": "witness", "completed_at": NOW.isoformat(),
            "source_check": "unavailable", "peer_tick_at": None, "sequence": 2, "head": "1" * 64}
    field, value = {"source_check": ("source_check", "invalid"), "peer_tick_at": ("peer_tick_at", "infinity"),
        "sequence": ("sequence", 0), "wrong_role": ("role", "primary"), "bool_sequence": ("sequence", True),
        "future_tick": ("completed_at", (NOW + timedelta(seconds=1)).isoformat()),
        "bad_time": ("completed_at", "infinity")}[invalid]
    peer[field] = value
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation), peer=peer, now=NOW,
                                 binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        assert journal.peer is None and not posts
    with cls(path, read_only=True) as journal:
        assert journal.peer is None


@pytest.mark.parametrize("invalid", ["extra_key", "bool_counter", "negative_counter", "counter_overflow",
    "string_counter", "failed_above_events", "conflicts_above_events", "missing_last_event", "bad_time",
    "future_source", "future_event", "wrong_profile", "wrong_generation", "counters_drop", "source_time_rollback"])
def test_invalid_source_sample_never_replaces_the_last_confirmed_observation(tmp_path, invalid):
    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation), peer=None, now=NOW,
                                 binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
    later = NOW + timedelta(seconds=300)
    changes = {
        "extra_key": {"unexpected": "synthetic-private"}, "bool_counter": {"event_count": True},
        "negative_counter": {"failed_event_count": -1}, "counter_overflow": {"event_count": 9223372036854775808},
        "string_counter": {"event_count": "2"}, "failed_above_events": {"failed_event_count": 3},
        "conflicts_above_events": {"conflicting_attempt_count": 2}, "missing_last_event": {"last_event_at": None},
        "bad_time": {"as_of": "infinity"}, "future_source": {"as_of": (later + timedelta(seconds=1)).isoformat()},
        "future_event": {"last_event_at": (later + timedelta(seconds=1)).isoformat()},
        "wrong_profile": {"source_profile": str(uuid4())}, "wrong_generation": {"source_generation": str(uuid4())},
        "counters_drop": {"event_count": 1}, "source_time_rollback": {
            "as_of": (NOW - timedelta(seconds=1)).isoformat(), "last_event_at": (NOW - timedelta(seconds=1)).isoformat()},
    }
    with cls(path) as journal:
        status = asyncio.run(journal.tick(source=sample(profile, generation, later) | changes[invalid],
            peer=None, now=later, binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        assert status["source_check"] == "discontinuity"
    with cls(path, read_only=True) as journal:
        assert journal.source == sample(profile, generation)
        assert {i["kind"] for i in journal.incidents.values()} == {"source_discontinuity"}
        assert journal.current("source_discontinuity")["closure"] is None
    assert len(posts) == 1 and "synthetic-private" not in path.read_text()


@pytest.mark.parametrize("outcome", ["unknown", "error"])
@pytest.mark.parametrize("change", ["basis", "binding"])
@pytest.mark.parametrize("late", ["before", "after"])
def test_superseded_attempt_cannot_notify_or_reenter_the_queue(tmp_path, outcome, change, late):
    from twobrain_rec_server.billing.observation_alerts import digest, stamp

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    next_binding = str(uuid4()) if change == "binding" else binding
    failed = 2 if change == "basis" else 1
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
            binding_version=binding, client=postal(posts, outcome), recipient="synthetic@example.invalid"))
        first = journal.current("reconciliation_failure").copy()
        old_key = first["current_message_key"]
    with cls(path) as journal:
        now = NOW + timedelta(seconds=299)
        asyncio.run(journal.tick(source=sample(profile, generation, now, events=3, failed=failed), peer=None, now=now,
            binding_version=next_binding, client=postal(posts), recipient="synthetic@example.invalid"))
        current = journal.current("reconciliation_failure")
        new_key = current["current_message_key"]
        assert new_key != old_key and len(posts) == 1
        assert all(current[k] == first[k] for k in ("incident_id", "detected_at", "initial_deadline", "next_allowed_at"))
        old_queue = journal.messages[old_key]["queue_seq"]
        if late == "before":
            journal.append("outcome", {"message_key": old_key, "attempt": 1, "outcome": "accepted",
                "acceptance_digest": digest("synthetic receipt"), "at": stamp(now)})
            assert current["notified_key"] is None
    with cls(path) as journal:
        now = NOW + timedelta(seconds=300)
        asyncio.run(journal.tick(source=sample(profile, generation, now, events=3, failed=failed), peer=None, now=now,
            binding_version=next_binding, client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(posts) == 2 and posts[-1]["headers"]["X-2brain-Delivery-Key"] == new_key
        if late == "after":
            journal.append("outcome", {"message_key": old_key, "attempt": 1, "outcome": "accepted",
                "acceptance_digest": digest("synthetic receipt"), "at": stamp(now)})
        assert journal.current("reconciliation_failure")["notified_key"] == new_key
    with cls(path) as journal:
        now = NOW + timedelta(seconds=600)
        asyncio.run(journal.tick(source=sample(profile, generation, now, events=4, failed=failed), peer=None, now=now,
            binding_version=next_binding, client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(posts) == 2 and len(journal.messages) == 2
        assert journal.messages[old_key]["queue_seq"] == old_queue
        assert all(m["attempt"] == 1 and m["outcome"] == "accepted" for m in journal.messages.values())


@pytest.mark.parametrize("invalid", ["source_profile", "source_generation", "incident_id", "incident_generation",
    "expected_basis_revision", "basis_hash", "actor", "message_time", "decision_digest", "evidence_ref",
    "action", "premature_close", "bool_revision"])
def test_owner_relay_rejects_wrong_identity_or_transition_without_any_write(tmp_path, invalid):
    from twobrain_rec_server.billing.observation_alerts import ObservationError, digest, stamp

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
            binding_version=binding, client=postal([]), recipient="synthetic@example.invalid"))
        incident = journal.current("reconciliation_failure")
        manifest = {"source_profile": profile, "source_generation": generation, "incident_id": incident["incident_id"],
            "incident_generation": 1, "expected_basis_revision": 1, "basis_hash": incident["basis_hash"],
            "action": "investigating", "evidence_class": "operational_review", "evidence_ref": "synthetic:review",
            "message_ref": "synthetic:chat:1", "message_at": stamp(NOW), "decision_digest": digest("synthetic decision")}
        changes = {"source_profile": {"source_profile": str(uuid4())}, "source_generation": {"source_generation": str(uuid4())},
            "incident_id": {"incident_id": str(uuid4())}, "incident_generation": {"incident_generation": 2},
            "expected_basis_revision": {"expected_basis_revision": 2}, "basis_hash": {"basis_hash": "0" * 64},
            "actor": {"actor": "owner"}, "message_time": {"message_at": stamp(NOW + timedelta(seconds=1))},
            "decision_digest": {"decision_digest": "invalid"}, "evidence_ref": {"evidence_ref": "synthetic-private@example.invalid"},
            "action": {"action": "notified"}, "premature_close": {"action": "accepted_risk"},
            "bool_revision": {"expected_basis_revision": True}}
        before = path.read_bytes(), journal.sequence, journal.head, digest(journal.incidents), set(journal.consumed)
        with pytest.raises((ObservationError, KeyError)):
            journal.transfer(manifest | changes[invalid], now=NOW)
        assert (path.read_bytes(), journal.sequence, journal.head, digest(journal.incidents), journal.consumed) == before
        journal.transfer(manifest, now=NOW)
        assert journal.sequence == before[1] + 1 and incident["investigating_at"] == stamp(NOW)
        assert manifest["message_ref"] in journal.consumed and digest(manifest) in journal.consumed


def test_equal_queue_sequence_uses_incident_identity_for_the_tie(tmp_path):
    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1, conflicts=1), peer=None, now=NOW,
            binding_version=binding, client=postal(posts, "unknown"), recipient="synthetic@example.invalid"))
    with cls(path) as journal:
        # Normal creation sequences are unique; exercise the specified tie selector directly.
        for message in journal.messages.values():
            message["queue_seq"] = journal.sequence
        expected = min(journal.messages.values(), key=lambda m: m["incident_id"])["message_key"]
        now = NOW + timedelta(seconds=300)
        asyncio.run(journal.tick(source=sample(profile, generation, now, failed=1, conflicts=1), peer=None, now=now,
            binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        assert len(posts) == 2 and posts[-1]["headers"]["X-2brain-Delivery-Key"] == expected


@pytest.mark.parametrize("invalid", ["rollback", "zero_head", "invalid_head", "extra_key", "schema_bool", "future_peer_tick"])
def test_invalid_peer_after_a_confirmed_tick_preserves_the_gap_anchor(tmp_path, invalid):
    cls, path, profile, generation, binding = setup_journal(tmp_path)
    peer = {"schema_version": 1, "role": "witness", "completed_at": NOW.isoformat(), "source_check": "available",
            "peer_tick_at": None, "sequence": 3, "head": "1" * 64}
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation), peer=peer, now=NOW,
            binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        previous = journal.peer.copy()
    later = NOW + timedelta(seconds=300)
    changes = {"rollback": {"completed_at": (NOW - timedelta(seconds=1)).isoformat()},
        "zero_head": {"head": "0" * 64}, "invalid_head": {"head": "invalid"}, "extra_key": {"private": "synthetic-private"},
        "schema_bool": {"schema_version": True}, "future_peer_tick": {"peer_tick_at": later.isoformat()}}
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, later), peer=peer | changes[invalid], now=later,
            binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        assert journal.peer == previous and not journal.incidents
    with cls(path) as journal:
        later = NOW + timedelta(seconds=900)
        asyncio.run(journal.tick(source=sample(profile, generation, later), peer=None, now=later,
            binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        assert set(i["kind"] for i in journal.incidents.values()) == {"witness_gap"}
        assert journal.current("witness_gap")["basis"]["anchor"] == NOW.isoformat()
    assert len(posts) == 1 and "synthetic-private" not in path.read_text()


@pytest.mark.parametrize("first", ["reconciliation_failure", "reconciliation_conflict"])
def test_late_subject_counters_change_only_their_own_basis_and_owner_manifest(tmp_path, first):
    from twobrain_rec_server.billing.observation_alerts import ObservationError, digest, stamp

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    kinds = ("reconciliation_failure", "reconciliation_conflict")
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, events=4, failed=1, conflicts=1),
            peer=None, now=NOW, binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        originals = {kind: journal.current(kind).copy() for kind in kinds}
    failed = conflicts = 1
    for seconds, changed in enumerate((None, first, next(kind for kind in kinds if kind != first)), 1):
        if changed == "reconciliation_failure":
            failed += 1
        elif changed == "reconciliation_conflict":
            conflicts += 1
        now = NOW + timedelta(seconds=seconds)
        with cls(path) as journal:
            before = {kind: journal.current(kind).copy() for kind in kinds}
            source = sample(profile, generation, now, events=6 + seconds, failed=failed, conflicts=conflicts)
            # A late commit advances counters without advancing the last producer timestamp.
            source["last_event_at"] = stamp(NOW + timedelta(seconds=1))
            asyncio.run(journal.tick(source=source, peer=None, now=now, binding_version=binding,
                client=postal(posts), recipient="synthetic@example.invalid"))
            for kind in kinds:
                current = journal.current(kind)
                assert all(current[key] == originals[kind][key] for key in (
                    "incident_id", "incident_generation", "detected_at", "initial_deadline"))
                assert current["basis_revision"] == before[kind]["basis_revision"] + (kind == changed)
                for key in ("basis_hash", "current_message_key"):
                    assert (current[key] != before[kind][key]) == (kind == changed)
                manifest = {"source_profile": profile, "source_generation": generation,
                    "incident_id": before[kind]["incident_id"], "incident_generation": 1,
                    "expected_basis_revision": before[kind]["basis_revision"], "basis_hash": before[kind]["basis_hash"],
                    "action": "investigating", "evidence_class": "operational_review", "evidence_ref": "synthetic:review",
                    "message_ref": f"synthetic:late:{kind}:{seconds}", "message_at": stamp(NOW),
                    "decision_digest": digest("synthetic decision")}
                if kind == changed:
                    unchanged = path.read_bytes(), journal.head, set(journal.consumed)
                    with pytest.raises(ObservationError):
                        journal.transfer(manifest, now=now)
                    assert (path.read_bytes(), journal.head, journal.consumed) == unchanged
                else:
                    journal.transfer(manifest, now=now)
                    assert manifest["message_ref"] in journal.consumed
            replay = digest(journal.incidents), digest(journal.messages), set(journal.consumed)
        with cls(path, read_only=True) as journal:
            assert (digest(journal.incidents), digest(journal.messages), journal.consumed) == replay


@pytest.mark.parametrize("kind", ["source_gap", "producer_gap", "witness_gap", "observer_gap"])
def test_continuing_gap_and_new_gap_keep_the_original_incident_deadlines(tmp_path, kind):
    from twobrain_rec_server.billing.observation_alerts import ObservationError, digest, stamp

    role = "witness" if kind == "observer_gap" else "primary"
    cls, path, profile, generation, binding = setup_journal(tmp_path, role=role)
    posts = []

    def tick(journal, seconds, *, healthy=False):
        now = NOW + timedelta(seconds=seconds)
        source = sample(profile, generation, now) if role == "primary" else None
        peer = {"schema_version": 1, "role": "primary" if role == "witness" else "witness",
                "completed_at": stamp(now), "source_check": "available", "peer_tick_at": None,
                "sequence": seconds + 2, "head": digest(seconds)}
        if not healthy:
            if kind == "source_gap":
                source = None
            elif kind == "producer_gap":
                source["last_event_at"] = journal.producer_at
            else:
                peer = None
        asyncio.run(journal.tick(source=source, peer=peer, now=now, binding_version=binding,
            client=postal(posts, "unknown"), recipient="synthetic@example.invalid"))

    with cls(path) as journal:
        tick(journal, 0, healthy=True)
        tick(journal, 900)
        first = journal.current(kind).copy()
        tick(journal, 901)
        assert all(journal.current(kind)[key] == first[key] for key in (
            "basis_hash", "basis_revision", "current_message_key", "detected_at", "initial_deadline"))
        tick(journal, 902, healthy=True)
        assert journal.current(kind)["closure"] is None
        assert journal.current(kind)["basis_hash"] == first["basis_hash"]
    with cls(path) as journal:
        tick(journal, 1801)
        previous = journal.current(kind).copy()
        old_key = previous["current_message_key"]
        assert previous["basis_revision"] == 1
        assert journal.messages[old_key]["reserved_at"] == stamp(NOW + timedelta(seconds=1801))
        assert previous["next_allowed_at"] == stamp(NOW + timedelta(seconds=2101))
        sent = len(posts)
        tick(journal, 1802)
        current = journal.current(kind)
        assert current["basis"]["anchor"] == stamp(NOW + timedelta(seconds=902))
        assert current["basis_hash"] != first["basis_hash"] and current["basis_revision"] == 2
        assert current["current_message_key"] != old_key
        assert all(current[key] == previous[key] for key in (
            "incident_id", "incident_generation", "detected_at", "initial_deadline", "next_allowed_at"))
        assert current["closure"] is None and journal.messages[current["current_message_key"]]["attempt"] == 0
        assert all(post["headers"]["X-2brain-Delivery-Key"] not in {old_key, current["current_message_key"]}
                   for post in posts[sent:])
        manifest = {"source_profile": profile, "source_generation": generation, "incident_id": first["incident_id"],
            "incident_generation": 1, "expected_basis_revision": 1, "basis_hash": first["basis_hash"],
            "action": "investigating", "evidence_class": "operational_review", "evidence_ref": "synthetic:review",
            "message_ref": "synthetic:gap:1", "message_at": stamp(NOW), "decision_digest": digest("synthetic decision")}
        unchanged = path.read_bytes(), journal.head, set(journal.consumed)
        with pytest.raises(ObservationError):
            journal.transfer(manifest, now=NOW + timedelta(seconds=1802))
        assert (path.read_bytes(), journal.head, journal.consumed) == unchanged
        replay = digest(journal.incidents), digest(journal.messages)
    with cls(path, read_only=True) as journal:
        assert (digest(journal.incidents), digest(journal.messages)) == replay


@pytest.mark.parametrize("boundary", ["allowed400", "allowed440", "writable_file", "writable_ancestor",
    "symlink", "hardlink", "directory", "wrong_owner", "changed_identity"])
def test_cli_transfer_checks_the_protected_decision_file_before_any_write(tmp_path, monkeypatch, boundary):
    import os
    from pathlib import Path

    from twobrain_rec_server.billing.observation_alerts import (
        ObservationError,
        canonical,
        digest,
        stamp,
    )
    from twobrain_rec_server.cli import billing_observation_alerts as cli

    cls, path, profile, generation, binding = setup_journal(tmp_path)
    posts = []
    with cls(path) as journal:
        asyncio.run(journal.tick(source=sample(profile, generation, failed=1), peer=None, now=NOW,
            binding_version=binding, client=postal(posts), recipient="synthetic@example.invalid"))
        incident = journal.current("reconciliation_failure").copy()
        before = path.read_bytes(), journal.sequence, journal.head, set(journal.consumed)
    directory = tmp_path / "relay"
    directory.mkdir(mode=0o700)
    decision = directory / "decision.json"
    manifest = {"source_profile": profile, "source_generation": generation, "incident_id": incident["incident_id"],
        "incident_generation": 1, "expected_basis_revision": 1, "basis_hash": incident["basis_hash"],
        "action": "investigating", "evidence_class": "operational_review", "evidence_ref": "synthetic:review",
        "message_ref": "synthetic:file:1", "message_at": stamp(NOW), "decision_digest": digest("synthetic decision")}
    decision.write_bytes(canonical(manifest))
    decision.chmod(0o440 if boundary == "allowed440" else 0o400)
    inode = decision.stat().st_ino
    if boundary == "writable_file":
        decision.chmod(0o600)
    elif boundary == "writable_ancestor":
        directory.chmod(0o770)
    elif boundary == "symlink":
        decision.rename(directory / "original.json")
        decision.symlink_to(directory / "original.json")
    elif boundary == "hardlink":
        os.link(decision, directory / "alias.json")
    elif boundary == "directory":
        decision.unlink()
        decision.mkdir(mode=0o700)
    original_fstat = os.fstat

    def root_file_metadata(fd):
        info = original_fstat(fd)
        if info.st_ino == inode:
            # Only root ownership is synthetic on the unprivileged Mac; mode/link/identity checks are real.
            values = list(info)
            values[4] = 12345 if boundary == "wrong_owner" else 0
            if boundary == "changed_identity":
                values[1] += 1
            return os.stat_result(values)
        return info

    monkeypatch.setattr(os, "fstat", root_file_metadata)
    monkeypatch.setattr(cli, "JOURNAL", path)
    monkeypatch.setattr(cli, "Path", lambda value: decision if str(value) == "/relay/decision.json" else Path(value))
    monkeypatch.setattr(cli, "configuration", lambda: {"source_profile": profile, "role": "primary"})
    if boundary.startswith("allowed"):
        assert asyncio.run(cli.run("transfer")) == {"schema_version": 1, "result_code": "reaction_recorded"}
    else:
        with pytest.raises((ObservationError, OSError)):
            asyncio.run(cli.run("transfer"))
    with cls(path, read_only=True) as journal:
        if boundary.startswith("allowed"):
            assert journal.sequence == before[1] + 1
            assert journal.consumed == {manifest["message_ref"], digest(manifest)}
            assert journal.current("reconciliation_failure")["investigating_at"] is not None
        else:
            assert (path.read_bytes(), journal.sequence, journal.head, journal.consumed) == before
    assert len(posts) == 1
