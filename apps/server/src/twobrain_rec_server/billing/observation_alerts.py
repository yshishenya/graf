"""Independent billing observation journal; never a payment authority."""
from __future__ import annotations

import asyncio
import copy
import fcntl
import hashlib
import json
import os
import re
import stat
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from email.utils import formataddr
from pathlib import Path
from uuid import UUID, uuid4

from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError, PostalEmailLoginClient

MAX_RECORD = 16 * 1024
MAX_JOURNAL = 64 * 1024 * 1024
MAX_RECORDS = 262144
MAX_INCIDENTS = 500
ZERO_HASH = "0" * 64
HOLD_MARKER = b"GRAF_OBSERVATION_HOLD_V1\n"
RECEIPT_COUNTERS = {f"receipt_{kind}": f"receipt_{kind}_count" for kind in
                    ("canceled", "overdue_confirmed", "overdue_unknown")}
RECEIPT_SUMMARIES = {
    "receipt_canceled": "Регистрация чека отменена.",
    "receipt_overdue_confirmed": "Подтверждено ожидание регистрации чека.",
    "receipt_overdue_unknown": "Последнее подтверждённое состояние — ожидание, актуальность неизвестна.",
}
KINDS = frozenset({"reconciliation_failure", "reconciliation_conflict", "source_gap", "producer_gap",
                   "observer_gap", "witness_gap", "source_discontinuity", *RECEIPT_COUNTERS})
REASONS = ("schema_invalid", "source_generation_changed", "counters_decreased",
           "source_time_invalid", "local_clock_rollback", "source_version_decreased")
COUNTERS = ("event_count", "failed_event_count", "conflicting_attempt_count")


class ObservationError(RuntimeError):
    def __init__(self):
        super().__init__("observation_unavailable")


def require(condition):
    if not condition:
        raise ObservationError()


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def closed(value, keys):
    require(type(value) is dict and set(value) == set(keys))


def integer(value, maximum=9223372036854775807):
    require(type(value) is int and 0 <= value <= maximum)


def uuid(value):
    require(type(value) is str and str(UUID(value)) == value)


def sha(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None)


def reference(value):
    # References are opaque technical codes, never free text or email addresses.
    require(type(value) is str and len(value.encode()) <= 255
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_:/.-]{0,254}", value) is not None)


def timestamp(value):
    require(type(value) is str)
    result = datetime.fromisoformat(value)
    require(result.tzinfo is not None and result.utcoffset() == timedelta(0))
    return result


def stamp(value):
    require(isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() == timedelta(0))
    return value.astimezone(UTC).isoformat()


def update_breach(incident, now):
    observed = now if incident["closure"] is None else timestamp(incident["closure"]["at"])
    incident["breached"] = incident["breached"] or observed > timestamp(incident["initial_deadline"])


def decode(raw):
    require(len(raw) <= MAX_RECORD)

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result

    def invalid(_value):
        raise ObservationError()

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, TypeError, RecursionError) as error:
        raise ObservationError() from error


def validate_sample(value):
    require(type(value) is dict and type(value.get("schema_version")) is int and value["schema_version"] in (1, 2))
    receipt_fields = tuple(RECEIPT_COUNTERS.values()) if value["schema_version"] == 2 else ()
    closed(value, {"schema_version", "source_profile", "source_generation", "as_of", "coverage",
                   *COUNTERS, *receipt_fields, "last_event_at"})
    require(value["coverage"] == "partial")
    uuid(value["source_profile"])
    uuid(value["source_generation"])
    timestamp(value["as_of"])
    for key in (*COUNTERS, *receipt_fields):
        integer(value[key])
    require(value["failed_event_count"] <= value["event_count"]
            and value["conflicting_attempt_count"] <= value["event_count"] // 2)
    if value["last_event_at"] is not None:
        timestamp(value["last_event_at"])
    require((value["event_count"] == 0) == (value["last_event_at"] is None))


def secure_open(path, *, create=False, owner=None, mode=0o600, read_only=False):
    """Reject links and writable ancestors before using the retained descriptor."""
    path = Path(path).absolute()
    owner = os.getuid() if owner is None else owner
    for parent in reversed(path.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and not info.st_mode & 0o022
                and info.st_uid in {0, owner})
    require(stat.S_IMODE(path.parent.lstat().st_mode) == 0o700)
    before = None if create else path.lstat()
    fd = os.open(path, (os.O_RDONLY if read_only else os.O_RDWR) | os.O_NOFOLLOW |
                 (os.O_CREAT | os.O_EXCL if create else 0), mode)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == owner
                and stat.S_IMODE(info.st_mode) == mode)
        current = path.lstat()
        require((current.st_dev, current.st_ino) == (info.st_dev, info.st_ino))
        if before is not None:
            require((before.st_dev, before.st_ino) == (info.st_dev, info.st_ino))
        return fd
    except BaseException:
        os.close(fd)
        raise


class AlertJournal:
    def __init__(self, path, *, deadline=None, read_only=False, clock=None, recovery=False):
        self.path = Path(path)
        self.hold_path = self.path.with_name(self.path.name + ".hold")
        self.hold_fd = None
        self.recovery = recovery
        require(not (read_only and recovery))
        self.deadline = time.monotonic() + 60 if deadline is None else deadline
        self.fd = None
        self.sequence = 0
        self.head = ZERO_HASH
        self.activation = None
        self.incidents = {}
        self.messages = {}
        self.consumed = set()
        self.source = None
        self.receipt_totals = None
        self.receipt_ready = False
        self.source_checked_at = None
        self.producer_at = None
        self.peer = None
        self.tick_record = None
        self.last_now = None
        self.hold = False
        self.discontinuity = None
        self.read_only = read_only
        self.clock = clock
        self.replaying = False

    @classmethod
    def activate(cls, path, *, source_profile, source_generation, binding_version, role, now):
        journal = cls(path)
        data = {"installation_id": str(uuid4()), "source_profile": source_profile,
                "source_generation": source_generation, "binding_version": binding_version,
                "role": role, "activated_at": stamp(now)}
        copy.copy(journal).apply("activation", data, 1)
        require(not os.path.lexists(path))
        try:
            journal.begin_record()
            journal.fd = secure_open(path, create=True)
            journal.lock()
            journal.append("activation", data)
        finally:
            journal.__exit__(None, None, None)

    def lock(self):
        lock_deadline = min(self.deadline, time.monotonic() + 2)
        while True:
            try:
                fcntl.flock(self.fd, (fcntl.LOCK_SH if self.read_only else fcntl.LOCK_EX) | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                require(time.monotonic() < lock_deadline)
                time.sleep(0.01)

    def sync_directory(self):
        directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def check_interlock(self):
        fd = secure_open(self.hold_path, read_only=True)
        try:
            info, held = os.fstat(fd), os.fstat(self.hold_fd)
            require((info.st_dev, info.st_ino) == (held.st_dev, held.st_ino)
                    and os.read(fd, len(HOLD_MARKER) + 1) == HOLD_MARKER)
        finally:
            os.close(fd)

    def begin_record(self):
        require(self.hold_fd is None)
        self.hold_fd = secure_open(self.hold_path, create=True)
        require(os.write(self.hold_fd, HOLD_MARKER) == len(HOLD_MARKER))
        os.fsync(self.hold_fd)
        self.sync_directory()
        self.check_deadline()

    def finish_record(self):
        self.check_deadline()
        self.check_interlock()
        os.unlink(self.hold_path)
        os.close(self.hold_fd)
        self.hold_fd = None
        try:
            self.sync_directory()
            self.check_deadline()
        except BaseException:
            # The journal is synced; restoring a visible veto is best effort on a failed FS.
            with suppress(OSError, ObservationError):
                self.begin_record()
            raise

    def __enter__(self):
        try:
            self.fd = secure_open(self.path, read_only=self.read_only)
            self.lock()
            if os.path.lexists(self.hold_path):
                require(self.recovery)
                self.hold_fd = secure_open(self.hold_path)
                self.check_interlock()
            require(os.fstat(self.fd).st_size <= MAX_JOURNAL)
            self.replaying = True
            last_sample = None
            with os.fdopen(os.dup(self.fd), "rb") as stream:
                for raw in stream:
                    self.check_deadline()
                    require(len(raw) <= MAX_RECORD and raw.endswith(b"\n"))
                    record = decode(raw)
                    closed(record, {"sequence", "prev_sha256", "kind", "data", "record_sha256"})
                    integer(record["sequence"], MAX_RECORDS)
                    require(record["sequence"] == self.sequence + 1 and record["prev_sha256"] == self.head)
                    expected = record.pop("record_sha256")
                    sha(expected)
                    require(digest(record) == expected)
                    self.apply(record["kind"], record["data"], record["sequence"])
                    if record["kind"] == "sample":
                        last_sample = timestamp(record["data"]["at"])
                    self.sequence, self.head = record["sequence"], expected
            self.replaying = False
            # Samples are monotonic, so only the latest can add a missed deadline.
            if last_sample is not None:
                for incident in self.incidents.values():
                    update_breach(incident, last_sample)
            self.check_deadline()
            require(self.activation is not None)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_args):
        if self.hold_fd is not None:
            os.close(self.hold_fd)
            self.hold_fd = None
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def check_deadline(self):
        require(time.monotonic() < self.deadline)

    def append(self, kind, data):
        self.check_deadline()
        require(self.fd is not None and not self.read_only and self.sequence < MAX_RECORDS
                and (not self.hold or kind == "recovery")
                and (self.hold_fd is None or kind == "activation" or (kind == "recovery" and self.recovery)))
        if kind == "recovery" and data.get("source_generation") == self.activation["source_generation"]:
            require(self.recovery and self.hold_fd is not None)
        next_sequence = self.sequence + 1
        # Validate against a copy before touching the authoritative file.
        candidate = copy.copy(self)
        candidate.incidents = copy.deepcopy(self.incidents)
        candidate.messages = copy.deepcopy(self.messages)
        candidate.consumed = self.consumed.copy()
        candidate.apply(kind, data, next_sequence)
        record = {"sequence": next_sequence, "prev_sha256": self.head, "kind": kind, "data": data}
        head = digest(record)
        raw = canonical({**record, "record_sha256": head}) + b"\n"
        require(len(raw) <= MAX_RECORD and os.fstat(self.fd).st_size + len(raw) <= MAX_JOURNAL)
        try:
            if self.hold_fd is None:
                self.begin_record()
            elif kind == "recovery":
                self.check_interlock()
                os.fsync(self.hold_fd)
                self.sync_directory()
                os.fsync(self.fd)
            self.check_deadline()
            os.lseek(self.fd, 0, os.SEEK_END)
            require(os.write(self.fd, raw) == len(raw))
            os.fsync(self.fd)
            self.finish_record()
        except BaseException:
            self.hold = True
            raise
        self.apply(kind, data, next_sequence)
        self.sequence, self.head = next_sequence, head

    def apply(self, kind, data, seq):
        require(type(kind) is str and type(data) is dict)
        if kind == "activation":
            closed(data, {"installation_id", "source_profile", "source_generation", "binding_version",
                          "role", "activated_at"})
            require(seq == 1 and self.activation is None and data["role"] in {"primary", "witness"})
            for key in ("installation_id", "source_profile", "source_generation", "binding_version"):
                uuid(data[key])
            timestamp(data["activated_at"])
            self.activation = data
            self.last_now = data["activated_at"]
            return
        require(self.activation is not None)
        if kind == "sample":
            closed(data, {"at", "source", "peer"})
            now = timestamp(data["at"])
            require(now >= timestamp(self.last_now))
            if data["source"] is not None:
                validate_sample(data["source"])
                require(data["source"]["source_profile"] == self.activation["source_profile"]
                        and data["source"]["source_generation"] == self.activation["source_generation"])
                require(self.receipt_source_issue(data["source"]) is None)
                if data["source"]["schema_version"] == 2:
                    require(self.discontinuity is None and self.source_time_valid(data["source"], now))
                    self.receipt_totals = {key: data["source"][key] for key in RECEIPT_COUNTERS.values()}
                    self.receipt_ready = True
                self.source = data["source"]
                self.source_checked_at = data["at"]
                self.producer_at = data["source"]["last_event_at"]
            if data["peer"] is not None:
                closed(data["peer"], {"completed_at", "head"})
                timestamp(data["peer"]["completed_at"])
                sha(data["peer"]["head"])
                self.peer = data["peer"]
            self.last_now = data["at"]
            if not self.replaying:
                for incident in self.incidents.values():
                    update_breach(incident, now)
        elif kind == "incident":
            closed(data, {"incident_id", "kind", "incident_generation", "basis_revision", "basis",
                          "basis_hash", "detected_at", "initial_deadline"})
            uuid(data["incident_id"])
            integer(data["basis_revision"])
            integer(data["incident_generation"])
            require(data["kind"] in KINDS and data["basis_hash"] == digest(data["basis"]))
            self.validate_basis(data["kind"], data["basis"])
            detected = timestamp(data["detected_at"])
            require(timestamp(data["initial_deadline"]) == detected + timedelta(seconds=300))
            previous = self.current(data["kind"])
            if data["kind"] in RECEIPT_COUNTERS:
                require(self.receipt_ready and self.discontinuity is None
                        and data["basis"]["count"] == self.receipt_totals[RECEIPT_COUNTERS[data["kind"]]]
                        and (previous is None or data["basis"]["count"] > previous["basis"]["count"]))
            if data["incident_id"] in self.incidents:
                require(previous is self.incidents[data["incident_id"]] and previous["closure"] is None
                        and data["basis_revision"] == previous["basis_revision"] + 1
                        and data["incident_generation"] == previous["incident_generation"]
                        and data["detected_at"] == previous["detected_at"]
                        and data["initial_deadline"] == previous["initial_deadline"]
                        and data["basis_hash"] != previous["basis_hash"])
                previous.update(data, notified_key=None, investigating_at=None, evidence_ref=data["basis_hash"])
            else:
                require(len(self.incidents) < MAX_INCIDENTS and data["basis_revision"] == 1
                        and (previous is None or previous["closure"] is not None)
                        and data["incident_generation"] == (1 if previous is None else previous["incident_generation"] + 1))
                self.incidents[data["incident_id"]] = {**data, "severity": "high", "owner": "GRAF_owner",
                    "contained_at": data["detected_at"], "containment": "observation_incomplete",
                    "owner_assigned_at": data["detected_at"], "notified_key": None,
                    "investigating_at": None, "closure": None, "next_allowed_at": data["detected_at"],
                    "breached": False, "current_message_key": None,
                    "evidence_class": "operational_observation", "evidence_ref": data["basis_hash"]}
        elif kind == "message":
            closed(data, {"incident_id", "basis_revision", "binding_version", "message_key"})
            incident = self.incidents[data["incident_id"]]
            integer(data["basis_revision"])
            uuid(data["binding_version"])
            require(data["basis_revision"] == incident["basis_revision"] and incident["closure"] is None
                    and self.sendable(incident)
                    and data["message_key"] == self.message_key(incident, data["binding_version"]))
            if data["message_key"] in self.messages:
                require(incident["current_message_key"] != data["message_key"]
                        and all(self.messages[data["message_key"]][k] == v for k, v in data.items()))
            else:
                self.messages[data["message_key"]] = {**data, "attempt": 0, "outcome": None,
                    "queue_seq": seq, "reserved_at": None, "acceptance_digest": None}
            incident["current_message_key"] = data["message_key"]
            incident["notified_key"] = (data["message_key"] if self.messages[data["message_key"]]["outcome"] == "accepted"
                                        else None)
        elif kind == "reservation":
            closed(data, {"message_key", "attempt", "at", "next_allowed_at"})
            message = self.messages[data["message_key"]]
            integer(data["attempt"])
            incident = self.incidents[message["incident_id"]]
            now = timestamp(data["at"])
            require(data["attempt"] == message["attempt"] + 1 and message["outcome"] != "accepted"
                    and message["basis_revision"] == incident["basis_revision"] and incident["closure"] is None
                    and data["message_key"] == incident["current_message_key"]
                    and self.sendable(incident)
                    and now >= timestamp(self.last_now)
                    and now >= timestamp(incident["next_allowed_at"])
                    and timestamp(data["next_allowed_at"]) == now + timedelta(seconds=300))
            message.update(attempt=data["attempt"], reserved_at=data["at"], outcome="unknown", queue_seq=seq)
            incident["next_allowed_at"] = data["next_allowed_at"]
            self.last_now = data["at"]
        elif kind == "outcome":
            closed(data, {"message_key", "attempt", "outcome", "acceptance_digest", "at"})
            message = self.messages[data["message_key"]]
            integer(data["attempt"])
            require(data["attempt"] == message["attempt"] and message["attempt"] > 0
                    and data["outcome"] in {"accepted", "failed", "unknown"}
                    and message["outcome"] != "accepted")
            require(timestamp(data["at"]) >= timestamp(self.last_now)
                    and timestamp(data["at"]) >= timestamp(message["reserved_at"]))
            if data["acceptance_digest"] is not None:
                sha(data["acceptance_digest"])
            require(data["outcome"] == "accepted" or data["acceptance_digest"] is None)
            message.update(outcome=data["outcome"], acceptance_digest=data["acceptance_digest"])
            self.last_now = data["at"]
            incident = self.incidents[message["incident_id"]]
            if (data["outcome"] == "accepted" and message["basis_revision"] == incident["basis_revision"]
                    and message["message_key"] == incident["current_message_key"]):
                incident["notified_key"] = message["message_key"]
        elif kind == "tick":
            closed(data, {"completed_at", "source_check", "binding_version"})
            require(timestamp(data["completed_at"]) >= timestamp(self.last_now)
                    and data["source_check"] in {"available", "unavailable", "discontinuity"})
            uuid(data["binding_version"])
            self.tick_record = {**data, "sequence": seq,
                                "head": digest({"sequence": seq, "prev_sha256": self.head, "kind": kind, "data": data})}
            self.last_now = data["completed_at"]
        elif kind == "discontinuity":
            closed(data, {"reason", "at", "hold"})
            require(data["reason"] in REASONS and type(data["hold"]) is bool)
            timestamp(data["at"])
            if self.discontinuity is None:
                self.discontinuity = {"sequence": seq, "reason": data["reason"]}
            self.hold = self.hold or data["hold"]
        elif kind == "transfer":
            self.apply_transfer(data)
        elif kind == "recovery":
            closed(data, {"expected_head", "source_generation", "at", "evidence_ref"})
            require(data["expected_head"] == self.head and timestamp(data["at"]) >= timestamp(self.last_now))
            uuid(data["source_generation"])
            reference(data["evidence_ref"])
            if data["source_generation"] == self.activation["source_generation"]:
                require(self.discontinuity is None and not self.hold)
            else:
                self.activation = {**self.activation, "source_generation": data["source_generation"]}
                self.source = self.source_checked_at = self.producer_at = self.peer = None
            self.receipt_ready = False
            self.discontinuity = None
            self.hold = False
            self.last_now = data["at"]
        else:
            raise ObservationError()

    def current(self, kind):
        return next((x for x in reversed(list(self.incidents.values())) if x["kind"] == kind), None)

    def receipt_source_issue(self, source):
        if self.receipt_totals is not None:
            if source["schema_version"] < 2:
                return "source_version_decreased"
            if any(source[key] < count for key, count in self.receipt_totals.items()):
                return "counters_decreased"
        return None

    def source_time_valid(self, source, now):
        as_of = timestamp(source["as_of"])
        last_event = timestamp(source["last_event_at"]) if source["last_event_at"] is not None else None
        return (as_of <= now
                and (self.source is None or as_of >= timestamp(self.source["as_of"]))
                and (last_event is None or last_event <= as_of)
                and (self.producer_at is None or last_event is None or last_event >= timestamp(self.producer_at)))

    def sendable(self, incident):
        if incident["kind"] in RECEIPT_COUNTERS:
            return self.receipt_ready and self.discontinuity is None
        return incident["basis"]["source_generation"] == self.activation["source_generation"]

    def validate_basis(self, kind, basis):
        common = {"source_profile", "source_generation", "kind"}
        fields = {"reconciliation_failure": {"count"}, "reconciliation_conflict": {"count"},
                  "source_discontinuity": {"sequence", "reason"},
                  **dict.fromkeys(RECEIPT_COUNTERS, {"count"})}
        closed(basis, common | fields.get(kind, {"anchor", "head"}))
        require(basis["kind"] == kind and basis["source_profile"] == self.activation["source_profile"]
                and basis["source_generation"] == self.activation["source_generation"])
        if "count" in basis:
            integer(basis["count"])
            require(basis["count"] > 0)
        elif "sequence" in basis:
            integer(basis["sequence"], MAX_RECORDS)
            require(basis["reason"] in REASONS)
        else:
            timestamp(basis["anchor"])
            sha(basis["head"])

    def message_key(self, incident, binding):
        return digest({key: incident["basis"][key] for key in ("source_profile", "source_generation")} |
                      {key: incident[key] for key in ("incident_id", "incident_generation", "basis_revision", "kind")} |
                      {"binding_version": binding})

    def detect(self, kind, fields, now):
        basis = {key: self.activation[key] for key in ("source_profile", "source_generation")} | {"kind": kind} | fields
        previous = self.current(kind)
        if previous is not None and previous["basis_hash"] == digest(basis):
            return
        updating = previous is not None and previous["closure"] is None
        self.append("incident", {"incident_id": previous["incident_id"] if updating else str(uuid4()),
            "kind": kind, "incident_generation": previous["incident_generation"] if updating else
            (1 if previous is None else previous["incident_generation"] + 1),
            "basis_revision": previous["basis_revision"] + 1 if updating else 1,
            "basis": basis, "basis_hash": digest(basis),
            "detected_at": previous["detected_at"] if updating else stamp(now),
            "initial_deadline": previous["initial_deadline"] if updating else stamp(now + timedelta(seconds=300))})

    def status(self):
        require(not self.hold and self.hold_fd is None and not os.path.lexists(self.hold_path))
        return {"schema_version": 1, "role": self.activation["role"],
                "completed_at": None if self.tick_record is None else self.tick_record["completed_at"],
                "source_check": "unavailable" if self.tick_record is None else self.tick_record["source_check"],
                "peer_tick_at": None if self.peer is None else self.peer["completed_at"],
                "sequence": 0 if self.tick_record is None else self.tick_record["sequence"],
                "head": ZERO_HASH if self.tick_record is None else self.tick_record["head"]}

    def observed_time(self, fallback):
        observed = fallback if self.clock is None else self.clock()
        stamp(observed)
        if observed < timestamp(self.last_now):
            self.append("discontinuity", {"reason": "local_clock_rollback", "at": self.last_now, "hold": True})
        require(not self.hold)
        return observed

    async def tick(self, *, source, peer, now, binding_version, client: PostalEmailLoginClient, recipient):
        uuid(binding_version)
        stamp(now)
        if now < timestamp(self.last_now):
            self.append("discontinuity", {"reason": "local_clock_rollback", "at": self.last_now, "hold": True})
        require(not self.hold)
        reason = None
        if source is not None:
            try:
                validate_sample(source)
                require(source["source_profile"] == self.activation["source_profile"])
            except (ObservationError, ValueError, TypeError, KeyError, OverflowError):
                reason = "schema_invalid"
            if reason is None and source["source_generation"] != self.activation["source_generation"]:
                reason = "source_generation_changed"
            if reason is None:
                reason = self.receipt_source_issue(source)
            if reason is None and self.source is not None and any(source[k] < self.source[k] for k in COUNTERS):
                reason = "counters_decreased"
            if reason is None and not self.source_time_valid(source, now):
                reason = "source_time_invalid"
            if reason is not None:
                self.append("discontinuity", {"reason": reason, "at": stamp(now), "hold": False})
        if peer is not None:
            try:
                closed(peer, {"schema_version", "role", "completed_at", "source_check", "peer_tick_at", "sequence", "head"})
                require(type(peer["schema_version"]) is int and peer["schema_version"] == 1
                        and peer["role"] == ("witness" if self.activation["role"] == "primary" else "primary"))
                integer(peer["sequence"], MAX_RECORDS)
                sha(peer["head"])
                require(peer["sequence"] > 0 and peer["head"] != ZERO_HASH
                        and peer["source_check"] in {"available", "unavailable", "discontinuity"}
                        and peer["completed_at"] is not None and timestamp(peer["completed_at"]) <= now)
                if peer["peer_tick_at"] is not None:
                    require(timestamp(peer["peer_tick_at"]) <= timestamp(peer["completed_at"]))
                if self.peer is not None:
                    require(timestamp(peer["completed_at"]) >= timestamp(self.peer["completed_at"]))
                peer = {"completed_at": peer["completed_at"], "head": peer["head"]}
            except (ObservationError, ValueError, TypeError, KeyError):
                peer = None
        accepted_source = source if source is not None and self.discontinuity is None else None
        self.append("sample", {"at": stamp(now), "source": accepted_source, "peer": peer})
        if self.activation["role"] == "primary":
            if accepted_source is not None:
                for kind, key in (("reconciliation_failure", "failed_event_count"),
                                  ("reconciliation_conflict", "conflicting_attempt_count")):
                    if accepted_source[key] > 0:
                        self.detect(kind, {"count": accepted_source[key]}, now)
                if accepted_source["schema_version"] == 2:
                    for kind, key in RECEIPT_COUNTERS.items():
                        previous = self.current(kind)
                        if accepted_source[key] > (previous["basis"]["count"] if previous else 0):
                            self.detect(kind, {"count": accepted_source[key]}, now)
            for kind, anchor in (("source_gap", self.source_checked_at), ("producer_gap", self.producer_at)):
                anchor = anchor or self.activation["activated_at"]
                if now - timestamp(anchor) >= timedelta(seconds=900):
                    self.detect(kind, {"anchor": anchor, "head": ZERO_HASH}, now)
            if self.discontinuity is not None:
                self.detect("source_discontinuity", self.discontinuity, now)
        anchor = self.peer["completed_at"] if self.peer else self.activation["activated_at"]
        if now - timestamp(anchor) >= timedelta(seconds=900):
            self.detect("witness_gap" if self.activation["role"] == "primary" else "observer_gap",
                        {"anchor": anchor, "head": self.peer["head"] if self.peer else ZERO_HASH}, now)
        for incident in self.incidents.values():
            if incident["closure"] is not None or not self.sendable(incident):
                continue
            key = self.message_key(incident, binding_version)
            if key not in self.messages or incident["current_message_key"] != key:
                self.append("message", {"incident_id": incident["incident_id"], "basis_revision": incident["basis_revision"],
                                        "binding_version": binding_version, "message_key": key})
        eligible = []
        for message in self.messages.values():
            incident = self.incidents[message["incident_id"]]
            if (incident["closure"] is None and message["basis_revision"] == incident["basis_revision"]
                    and self.sendable(incident)
                    and message["message_key"] == incident["current_message_key"]
                    and message["binding_version"] == binding_version and message["outcome"] != "accepted"
                    and now >= timestamp(incident["next_allowed_at"])):
                eligible.append(message)
        if eligible:
            message = min(eligible, key=lambda m: (m["queue_seq"], m["incident_id"]))
            incident = self.incidents[message["incident_id"]]
            reserved = self.observed_time(now)
            self.append("reservation", {"message_key": message["message_key"], "attempt": message["attempt"] + 1,
                "at": stamp(reserved), "next_allowed_at": stamp(reserved + timedelta(seconds=300))})
            label = RECEIPT_SUMMARIES.get(incident["kind"], incident["kind"])
            text = (f"GRAF: {label}\nВажность: high\nИнцидент: {incident['incident_id']}\n"
                    f"Обнаружен: {incident['detected_at']}\nПроверить до: {incident['initial_deadline']}\n"
                    "Подтверждения: operational_observation. Ответственный: владелец GRAF.\n"
                    "Наблюдение неполное; неизвестный исход не является финансовым отказом.\n"
                    "Принятие риска требует отдельного явного решения владельца в чате.")
            receipt = None
            try:
                async with asyncio.timeout(min(10, max(0, self.deadline - time.monotonic()))):
                    receipt = await client._post_message({"to": [recipient],
                        "from": formataddr(("GRAF", client.from_address)), "subject": "GRAF: требуется проверка наблюдения",
                        "plain_body": text, "tag": "billing-observation",
                        "headers": {"X-2brain-Email-Purpose": "billing-observation",
                                    "X-2brain-Delivery-Key": message["message_key"]}})
                outcome = "accepted"
            except EmailLoginDeliveryError as error:
                outcome = "unknown" if error.outcome_unknown else "failed"
            except TimeoutError:
                outcome = "unknown"
            self.append("outcome", {"message_key": message["message_key"], "attempt": message["attempt"],
                "outcome": outcome, "acceptance_digest": digest(receipt) if receipt is not None else None,
                "at": stamp(self.observed_time(now))})
        completed = self.observed_time(now)
        self.append("tick", {"completed_at": stamp(completed), "source_check": "discontinuity" if self.discontinuity
                             else ("available" if accepted_source is not None else "unavailable"),
                             "binding_version": binding_version})
        return self.status()

    def apply_transfer(self, data):
        closed(data, {"source_profile", "source_generation", "incident_id", "incident_generation",
                      "expected_basis_revision", "basis_hash", "action", "evidence_class", "evidence_ref",
                      "message_ref", "message_at", "decision_digest", "transferred_at", "manifest_digest"})
        incident = self.incidents[data["incident_id"]]
        for field in ("source_profile", "source_generation"):
            require(data[field] == incident["basis"][field])
        integer(data["incident_generation"])
        integer(data["expected_basis_revision"])
        require(data["incident_generation"] == incident["incident_generation"]
                and data["expected_basis_revision"] == incident["basis_revision"]
                and data["basis_hash"] == incident["basis_hash"] and incident["closure"] is None
                and data["manifest_digest"] not in self.consumed)
        for field in ("evidence_class", "evidence_ref", "message_ref"):
            reference(data[field])
        sha(data["decision_digest"])
        sha(data["manifest_digest"])
        require(data["message_ref"] not in self.consumed and data["action"] in {"investigating", "resolved", "accepted_risk"}
                and timestamp(data["transferred_at"]) >= timestamp(self.last_now)
                and timestamp(data["message_at"]) <= timestamp(data["transferred_at"]))
        if data["action"] == "investigating":
            incident["investigating_at"] = data["transferred_at"]
        else:
            require(incident["investigating_at"] is not None)
            if incident["kind"] in RECEIPT_COUNTERS and data["action"] == "resolved":
                require(data["evidence_class"] == "receipt_reconciliation_verified")
            incident["closure"] = {"action": data["action"], "at": data["transferred_at"],
                                   "evidence_class": data["evidence_class"], "evidence_ref": data["evidence_ref"]}
            update_breach(incident, timestamp(data["transferred_at"]))
        self.consumed.update({data["manifest_digest"], data["message_ref"]})
        self.last_now = data["transferred_at"]

    def transfer(self, manifest, *, now):
        require(not self.hold)
        closed(manifest, {"source_profile", "source_generation", "incident_id", "incident_generation",
                          "expected_basis_revision", "basis_hash", "action", "evidence_class", "evidence_ref",
                          "message_ref", "message_at", "decision_digest"})
        self.append("transfer", {**manifest, "transferred_at": stamp(now), "manifest_digest": digest(manifest)})

    def backup(self, target):
        require(not self.hold and self.hold_fd is None and not os.path.lexists(self.hold_path))
        fd = secure_open(target, create=True)
        try:
            os.lseek(self.fd, 0, os.SEEK_SET)
            while raw := os.read(self.fd, 65536):
                self.check_deadline()
                require(os.write(fd, raw) == len(raw))
            os.fsync(fd)
            directory = os.open(Path(target).parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            os.close(fd)
        return {"sequence": self.sequence, "head": self.head}
