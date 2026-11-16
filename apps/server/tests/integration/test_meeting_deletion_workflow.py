from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

import twobrain_rec_server.deletion.service as deletion_service
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.admin import (
    DEFAULT_ADMIN_DEVICE_ID,
    DEFAULT_ADMIN_USER_ID,
    auth_headers_for,
    seed_default_workspace_admin_roles,
)
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from tests.fixtures.cabinet_access import set_artifact_policy
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    DispatchIntent,
    Meeting,
    MeetingDeletionArtifactState,
    MeetingDeletionReport,
    MeetingDeletionRequest,
    MeetingEgressAuditEvent,
    MeetingLifecycleAuditEvent,
    PurgeJournal,
    RecordingCalendarContextLink,
    TemporaryUploadObject,
    TrackArtifact,
    UploadPart,
    UploadSession,
    Workspace,
)
from twobrain_rec_server.ingest.store import _clear_orphan_cleanup_intents_for_authoritative_keys
from twobrain_rec_server.storage.recovery import mark_storage_recovery_unknown

BOUNDED_COPY = "Delete this meeting everywhere GRAF controls."


@pytest.fixture
def storage_recovery(client, tmp_path, monkeypatch):
    path = tmp_path / "storage-recovery"
    path.with_name(path.name + ".lock").touch()
    expected = uuid4()
    settings = Settings(
        strict_storage_scope="test-scope", strict_storage_recovery_file=path,
        strict_storage_recovery_id=expected, strict_storage_read_fence_directory=tmp_path,
    )
    monkeypatch.setitem(client.app_state["sessionmaker"].kw, "info", {"runtime_settings": settings})

    def set_state(state: str, recovery_id: UUID | None = None, *, advance=False, duplicate_state=None):
        if advance:
            assert recovery_id is not None
            settings.strict_storage_recovery_id = recovery_id
        payload = json.dumps({
            "schema": 1,
            "scope": "test-scope",
            "recovery_id": str(recovery_id or expected),
            "state": state,
        })
        if duplicate_state is not None:
            payload = json.dumps({"state": duplicate_state})[:-1] + "," + payload[1:]
        path.write_text(payload, encoding="utf-8")

    return set_state


@pytest.mark.parametrize("race", ["none", "journal", "recovery", "commit_ack"])
def test_lost_strict_upload_id_can_only_queue_current_obligation(
    client, storage_recovery, monkeypatch, race
) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    storage_recovery("reconciled")
    sessions = client.app_state["sessionmaker"]
    journal_id = uuid4()
    target = object()

    async def run():
        async with sessions.begin() as db:
            meeting = await db.get(Meeting, meeting_id)
            workspace = await db.get(Workspace, meeting.workspace_id)
            workspace_id = workspace.id
            key = (
                f"organizations/{workspace.organization_id}/workspaces/{workspace_id}/"
                f"meetings/{meeting_id}/artifacts/media-revisions/{uuid4()}/attempts/1/2/tracks/media"
            )
            db.add(PurgeJournal(
                id=journal_id, workspace_id=workspace_id, meeting_id=meeting_id,
                artifact_class=deletion_service.STRICT_UPLOAD_ATTEMPT, object_key=key,
                storage_scope="test-scope", storage_epoch=1, write_state="create_possible",
                state="terminal_unknown",
            ))

        async def find(received_target, *, key, deadline):
            assert received_target is target and key == expected_key
            async with sessions.begin() as db:
                assert await db.scalar(
                    select(Meeting.id).where(Meeting.id == meeting_id).with_for_update(nowait=True)
                ) == meeting_id
                if race == "journal":
                    row = await db.get(PurgeJournal, journal_id)
                    row.multipart_upload_id = "other-operator"
            if race == "recovery":
                storage_recovery("recovery_unknown")
            return "exact-id"

        @contextmanager
        def admit(scope, epoch, key, attempt_id):
            assert (scope, epoch, key, attempt_id) == ("test-scope", 1, expected_key, journal_id)
            yield target

        expected_key = key
        monkeypatch.setattr(deletion_service, "find_strict_multipart_for_cleanup", find)
        async with sessions() as db:
            assert not await deletion_service.queue_lost_strict_upload_cleanup(
                db, authorized_workspace_id=uuid4(), journal_id=journal_id, discovery_admission=admit
            )
        async with sessions() as db:
            async def queue():
                return await deletion_service.queue_lost_strict_upload_cleanup(
                    db, authorized_workspace_id=workspace_id, journal_id=journal_id,
                    discovery_admission=admit,
                )

            if race == "commit_ack":
                commit = db.commit

                async def commit_without_ack():
                    await commit()
                    raise SQLAlchemyError("synthetic lost acknowledgment")

                monkeypatch.setattr(db, "commit", commit_without_ack)
                with pytest.raises(deletion_service.ProblemDetail) as exc:
                    await queue()
                assert exc.value.code == "strict_upload_cleanup_commit_unknown"
            else:
                assert await queue() is (race == "none")
        async with sessions() as db:
            row = await db.get(PurgeJournal, journal_id)
            assert row.write_state == "create_possible"
            assert row.completed_at is None
            assert row.state == (
                "retryable_failed" if race in {"none", "commit_ack"} else "terminal_unknown"
            )
            assert row.multipart_upload_id == {
                "none": "exact-id", "journal": "other-operator", "recovery": None,
                "commit_ack": "exact-id",
            }[race]
            assert await deletion_service._strict_upload_open(db, workspace_id, meeting_id)

        if race == "none":
            class Cleaner:
                async def purge_strict_upload_attempt(self, **request):
                    assert request["upload_id"] == "exact-id"
                    assert request["attempt_id"] == journal_id and request["key"] == expected_key
                    return True

            async with sessions() as db:
                meeting = await db.get(Meeting, meeting_id)
                assert await deletion_service._reconcile_strict_upload_attempts(
                    db, meeting=meeting, storage=Cleaner(), limit=1
                )
            async with sessions() as db:
                row = await db.get(PurgeJournal, journal_id)
                assert row.state == "purged" and row.write_state == "create_possible"

    asyncio.run(run())


def test_recovery_unknown_blocks_full_cleanup_and_empty_orphan_queue(
    client, storage_recovery, monkeypatch
) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    settings = client.app_state["sessionmaker"].kw["info"]["runtime_settings"]
    mark_storage_recovery_unknown(
        settings.strict_storage_recovery_file, scope=settings.strict_storage_scope,
        recovery_id=settings.strict_storage_recovery_id, previous_id=None,
    )
    storage = client.app_state["storage"]
    requests = f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests"

    async def must_not_purge(*args, **kwargs):
        pytest.fail("Destructive work must wait for recovery reconciliation")

    with monkeypatch.context() as scoped:
        scoped.setattr(deletion_service, "_purge_server_controlled_content", must_not_purge)
        response = client.post(
            requests, headers=auth_headers(), json={"confirmation_boundary": BOUNDED_COPY}
        )
        assert response.status_code == 503, response.text
        assert response.json()["code"] == "storage_recovery_unknown"

    async def verify():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting.deleted_at is not None
            assert await db.scalar(select(PurgeJournal.id).where(
                PurgeJournal.meeting_id == meeting_id
            ).limit(1)) is None
            assert await deletion_service.retry_orphan_purge_journals(
                db, meeting=meeting, storage=storage
            ) == {"reset_count": 0, "converged": False}
            assert await deletion_service.reconcile_deletion_purges(db, storage=storage) == 0

    asyncio.run(verify())
    persisted = asyncio.run(_load_deletion_rows(client, meeting_id))
    assert persisted["report"].overall_state == "retryable_failed"
    assert persisted["request"].failure_reason == "storage_recovery_unknown"


@pytest.mark.parametrize("restored_obligation", ["journal", "reference"])
def test_recovery_unknown_masks_saved_success_until_obligations_are_reconciled(
    client, storage_recovery, restored_obligation
) -> None:
    async def seed_roles():
        async with client.app_state["sessionmaker"]() as db:
            await seed_default_workspace_admin_roles(db)

    asyncio.run(seed_roles())
    admin = auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID)
    meeting_id = seed_cabinet_meetings(client).ready_id
    storage_recovery("reconciled")
    meeting_api = f"/api/v1/cabinet/meetings/{meeting_id}"

    def request():
        return client.post(
            f"{meeting_api}/deletion-requests",
            headers=auth_headers(),
            json={"confirmation_boundary": BOUNDED_COPY},
        )

    assert request().json()["lifecycle"]["state"] == "active_purge_complete"
    storage_recovery("recovery_unknown")

    def check_unverified():
        receipt = request().json()["lifecycle"]
        lifecycle = client.get(f"{meeting_api}/lifecycle", headers=auth_headers()).json()
        sync = client.post(
            "/api/v1/desktop/recordings/lifecycle", headers=auth_headers(),
            json={"meeting_ids": [str(meeting_id)]},
        ).json()[0]
        assert sync["state"] == "deletion_accepted"
        for state in (receipt, lifecycle, sync["receipt"]["lifecycle"]):
            assert state["state"] == "retryable_failed"
            assert state["reason"] == "storage_purge_unverified"
            assert not state["can_retry"]
        retry = client.post(f"{meeting_api}/deletion-retry", headers=auth_headers())
        assert retry.status_code == 409, retry.text
        files = client.get("/api/v1/admin/files?deletion_state=retryable_failed", headers=admin)
        assert files.status_code == 200, files.text
        assert any(row["meeting_id"] == str(meeting_id) for row in files.json()["files"])
        report = client.get(f"{meeting_api}/deletion-report", headers=auth_headers()).json()
        assert report["overall_state"] == "retryable_failed"
        assert not any(
            row["state"] == "purged" and row["control_scope"] == "controlled"
            for row in report["artifact_states"]
        )

    check_unverified()
    storage_recovery("reconciled", duplicate_state="recovery_unknown")
    check_unverified()
    storage_recovery("recovery_unknown")

    async def record_missing_obligation():
        async with client.app_state["sessionmaker"].begin() as db:
            meeting = await db.get(Meeting, meeting_id)
            if restored_obligation == "reference":
                artifact = await db.scalar(
                    select(TrackArtifact).where(TrackArtifact.meeting_id == meeting_id).limit(1)
                )
                assert artifact is not None
                artifact.status = "stored"
                artifact.storage_object_key = (
                    f"organizations/{uuid4()}/workspaces/{meeting.workspace_id}/"
                    f"meetings/{meeting_id}/artifacts/media-revisions/{uuid4()}/"
                    "attempts/1/2/tracks/media"
                )
                return
            db.add(PurgeJournal(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting_id,
                artifact_class=deletion_service.STRICT_UPLOAD_ATTEMPT,
                object_key="tests/missing-from-backup",
                storage_scope="test-scope",
                storage_epoch=1,
                write_state="create_possible",
            ))

    asyncio.run(record_missing_obligation())
    storage_recovery("reconciled")
    check_unverified()


def test_recovery_generation_changes_after_io_before_completion(
    client, storage_recovery, monkeypatch
) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    storage_recovery("reconciled")
    original = deletion_service._purge_server_controlled_content

    async def change_generation(*args, **kwargs):
        result = await original(*args, **kwargs)
        storage_recovery("reconciled", uuid4())
        return result

    monkeypatch.setattr(deletion_service, "_purge_server_controlled_content", change_generation)
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert response.status_code == 503, response.text
    assert response.json()["code"] == "storage_recovery_unknown"
    persisted = asyncio.run(_load_deletion_rows(client, meeting_id))
    assert persisted["meeting"].deleted_at is not None
    assert persisted["report"].overall_state == "deleting"


def test_deletion_reconciler_reloads_meetings_after_rollback(client, monkeypatch) -> None:
    """A failed item must not leave the next Meeting ORM row expired."""
    seeds = seed_cabinet_meetings(client)

    async def seed_journals() -> None:
        async with client.app_state["sessionmaker"]() as db:
            for meeting_id in (seeds.ready_id, seeds.processing_id):
                meeting = await db.get(Meeting, meeting_id)
                assert meeting is not None
                db.add(
                    PurgeJournal(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        artifact_class="object_store",
                        object_key=f"tests/reconcile/{meeting.id}",
                        state="pending",
                    )
                )
            await db.commit()

    asyncio.run(seed_journals())
    calls: list[UUID] = []

    async def fail_first_item(db, *, meeting: Meeting, storage, limit: int = 20) -> bool:
        calls.append(meeting.id)
        if len(calls) == 1:
            await db.rollback()
            return False
        return True

    monkeypatch.setattr(deletion_service, "_reconcile_orphan_purge_journals", fail_first_item)

    async def reconcile() -> int:
        async with client.app_state["sessionmaker"]() as db:
            return await deletion_service.reconcile_deletion_purges(
                db,
                storage=None,
                limit=20,
            )

    assert asyncio.run(reconcile()) == 1
    assert len(calls) == 2
    assert set(calls) == {seeds.ready_id, seeds.processing_id}


def test_manual_deletion_persists_request_audit_report_and_meeting_lifecycle(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )

    assert response.status_code == 202
    persisted = asyncio.run(_load_deletion_rows(client, seeds.ready_id))
    assert persisted["meeting"].deletion_state == "active_purge_complete"
    assert persisted["request"].state == "active_purge_complete"
    assert persisted["request"].confirmation_boundary == BOUNDED_COPY
    assert persisted["audit"].event_type == "deletion_requested"
    assert persisted["report"].bounded_copy == BOUNDED_COPY
    assert {row.artifact_class for row in persisted["artifact_states"]} >= {
        "meeting_row",
        "audio_object",
        "playback_candidate",
        "playback_canonical",
        "normalization_attempt_temp",
        "normalization_job",
        "normalization_backfill",
        "transcript",
        "diarization",
        "mediascribe",
        "langfuse",
        "backup",
        "post_egress_copy",
    }


@pytest.mark.parametrize("full_deletion", [False, True])
@pytest.mark.parametrize("outcome", ["missing_id", "cleaned", "timeout"])
def test_strict_upload_cleanup_claims_before_io_and_never_falls_back(
    client,
    monkeypatch,
    full_deletion,
    outcome,
) -> None:
    known_upload = outcome != "missing_id"
    cleaned = outcome == "cleaned"
    meeting_id = seed_cabinet_meetings(client).ready_id
    sessionmaker = client.app_state["sessionmaker"]
    storage = client.app_state["storage"]
    key = "tests/strict-upload-attempt"
    journal_id = uuid4()
    legacy_id = uuid4()
    storage.objects[key] = b"test"
    calls = []
    generic_reads = []
    original_exists = storage.object_exists_async

    async def object_exists(candidate):
        generic_reads.append(candidate)
        return await original_exists(candidate)

    async def seed() -> None:
        async with sessionmaker.begin() as db:
            meeting = await db.get(Meeting, meeting_id)
            db.add(
                PurgeJournal(
                    id=journal_id,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    artifact_class=deletion_service.STRICT_UPLOAD_ATTEMPT,
                    object_key=key,
                    storage_scope="test-scope",
                    storage_epoch=1,
                    deletion_epoch=0,
                    write_state="upload_id_known" if known_upload else "create_possible",
                    multipart_upload_id="test-upload-id" if known_upload else None,
                )
            )
            db.add(
                PurgeJournal(
                    id=legacy_id,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    artifact_class="object_store",
                    object_key=key,
                )
            )

    async def purge(**claim):
        from time import monotonic

        assert monotonic() < claim.pop("deadline") <= monotonic() + 30
        calls.append(claim)
        async with sessionmaker.begin() as db:
            row = await db.get(PurgeJournal, journal_id)
            assert (row.state, row.attempt_count) == ("deleting", 1)
            assert (
                await db.scalar(
                    select(Meeting.id).where(Meeting.id == meeting_id).with_for_update(nowait=True)
                )
                == meeting_id
            )
        if outcome == "timeout":
            raise TimeoutError
        storage.objects.pop(key)
        return True

    async def reconcile_orphans() -> int:
        async with sessionmaker() as db:
            return await deletion_service.reconcile_deletion_purges(db, storage=storage)

    async def inspect() -> tuple[str, int, bool]:
        async with sessionmaker() as db:
            row = await db.get(PurgeJournal, journal_id)
            meeting = await db.get(Meeting, meeting_id)
            duplicates = (
                await db.scalars(select(PurgeJournal.id).where(PurgeJournal.object_key == key))
            ).all()
            assert set(duplicates) == {journal_id, legacy_id}
            return row.state, row.attempt_count, meeting.deletion_state == "active_purge_complete"

    asyncio.run(seed())
    monkeypatch.setattr(storage, "object_exists_async", object_exists)
    monkeypatch.setattr(storage, "purge_strict_upload_attempt", purge, raising=False)
    if full_deletion:
        response = client.post(
            f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
            headers=auth_headers(),
            json={"confirmation_boundary": BOUNDED_COPY},
        )
        assert response.status_code == (202 if cleaned else 503), response.text
    else:
        assert asyncio.run(reconcile_orphans()) == int(cleaned)
    if known_upload:
        assert calls == [
            dict(
                scope="test-scope",
                epoch=1,
                key=key,
                upload_id="test-upload-id",
                attempt_id=journal_id,
            )
        ]
    if cleaned:
        assert key not in storage.objects
        assert asyncio.run(inspect()) == ("purged", 1, full_deletion)
    elif outcome == "timeout":
        assert storage.objects[key] == b"test"
        assert asyncio.run(inspect()) == ("retryable_failed", 1, False)
    else:
        assert calls == []
        assert storage.objects[key] == b"test"
        assert asyncio.run(inspect()) == ("retryable_failed", 1, False)

        async def operator_retry() -> None:
            async with sessionmaker() as db:
                meeting = await db.get(Meeting, meeting_id)
                assert await deletion_service.retry_orphan_purge_journals(
                    db,
                    meeting=meeting,
                    storage=storage,
                ) == {"reset_count": 0, "converged": False}
            async with sessionmaker.begin() as db:
                row = await db.get(PurgeJournal, journal_id)
                row.state = "deleting"
                row.attempt_count = deletion_service.MAX_PURGE_JOURNAL_ATTEMPTS
                row.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)
            async with sessionmaker() as db:
                meeting = await db.get(Meeting, meeting_id)
                assert await deletion_service.retry_orphan_purge_journals(
                    db,
                    meeting=meeting,
                    storage=storage,
                ) == {"reset_count": 1, "converged": False}

        asyncio.run(operator_retry())
        assert calls == []
        assert storage.objects[key] == b"test"
        assert asyncio.run(inspect()) == ("retryable_failed", 1, False)
    assert key not in generic_reads
    assert key not in storage.deleted_keys


def test_orphan_retry_rechecks_strict_journal_after_legacy_io(client, monkeypatch) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    sessions = client.app_state["sessionmaker"]
    storage = client.app_state["storage"]
    legacy_key = "tests/legacy-in-progress"
    original_exists = storage.object_exists_async

    async def object_exists(key):
        if key == legacy_key:
            async with sessions.begin() as db:
                meeting = await db.scalar(
                    select(Meeting).where(Meeting.id == meeting_id).with_for_update(nowait=True)
                )
                db.add(
                    PurgeJournal(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting_id,
                        artifact_class=deletion_service.STRICT_UPLOAD_ATTEMPT,
                        object_key="tests/concurrent-strict",
                        write_state="create_possible",
                        storage_scope="test",
                        storage_epoch=1,
                    )
                )
        return await original_exists(key)

    async def verify() -> None:
        async with sessions.begin() as db:
            meeting = await db.get(Meeting, meeting_id)
            db.add(
                PurgeJournal(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting_id,
                    artifact_class="object_store",
                    object_key=legacy_key,
                    state="terminal_unknown",
                )
            )
        async with sessions() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert await deletion_service.retry_orphan_purge_journals(
                db,
                meeting=meeting,
                storage=storage,
            ) == {"reset_count": 1, "converged": False}

    monkeypatch.setattr(storage, "object_exists_async", object_exists)
    asyncio.run(verify())


def test_strict_cleanup_claims_one_row_at_a_time(client, monkeypatch) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    sessions = client.app_state["sessionmaker"]
    storage = client.app_state["storage"]
    first, second = uuid4(), uuid4()
    calls = []

    async def run() -> bool:
        async with sessions() as db:
            meeting = await db.get(Meeting, meeting_id)
            return await deletion_service._reconcile_orphan_purge_journals(
                db,
                meeting=meeting,
                storage=storage,
            )

    async def purge(**claim):
        calls.append(claim["attempt_id"])
        if claim["attempt_id"] == first:
            async with sessions() as db:
                assert (await db.get(PurgeJournal, second)).state == "pending"
            # The second worker can finish its own row while the first is in I/O.
            assert await run() is False
        return True

    async def verify() -> None:
        now = datetime.now(UTC)
        async with sessions.begin() as db:
            meeting = await db.get(Meeting, meeting_id)
            for order, row_id in enumerate((first, second)):
                db.add(
                    PurgeJournal(
                        id=row_id,
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting_id,
                        artifact_class=deletion_service.STRICT_UPLOAD_ATTEMPT,
                        object_key=f"tests/concurrent/{order}",
                        write_state="upload_id_known",
                        storage_scope="test",
                        storage_epoch=1,
                        multipart_upload_id=f"id-{order}",
                        created_at=now + timedelta(seconds=order),
                    )
                )
        assert await run() is True
        assert calls == [first, second]

    monkeypatch.setattr(storage, "purge_strict_upload_attempt", purge, raising=False)
    asyncio.run(verify())


def test_full_deletion_resumes_after_background_clears_strict_key_with_legacy_alias(
    client,
    monkeypatch,
) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    sessions = client.app_state["sessionmaker"]
    storage = client.app_state["storage"]
    key = (
        f"organizations/{uuid4()}/workspaces/{uuid4()}/meetings/{meeting_id}/"
        f"artifacts/media-revisions/{uuid4()}/attempts/1/2/tracks/media"
    )
    storage.objects[key] = b"test"
    original_exists = storage.object_exists_async
    read_keys = []

    async def object_exists(candidate):
        read_keys.append(candidate)
        return await original_exists(candidate)

    async def purge(**claim):
        response = await asyncio.to_thread(
            client.post,
            f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
            headers=auth_headers(),
            json={"confirmation_boundary": BOUNDED_COPY},
        )
        assert response.status_code == 503, response.text
        assert (await _load_deletion_rows(client, meeting_id))["report"].overall_state == (
            "retryable_failed"
        )
        assert claim["key"] == key
        storage.objects.pop(key)
        return True

    async def verify() -> None:
        async with sessions.begin() as db:
            meeting = await db.get(Meeting, meeting_id)
            for kind in (deletion_service.STRICT_UPLOAD_ATTEMPT, "object_store"):
                row = PurgeJournal(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting_id,
                    artifact_class=kind,
                    object_key=key,
                )
                if kind == deletion_service.STRICT_UPLOAD_ATTEMPT:
                    row.write_state = "upload_id_known"
                    row.storage_scope = "test"
                    row.storage_epoch = 1
                    row.multipart_upload_id = "test-upload"
                db.add(row)
        async with sessions() as db:
            await deletion_service.reconcile_deletion_purges(db, storage=storage)
        assert key not in storage.objects
        async with sessions() as db:
            assert await deletion_service.reconcile_deletion_purges(db, storage=storage) == 1
        assert (await _load_deletion_rows(client, meeting_id))["report"].overall_state == (
            "active_purge_complete"
        )

    monkeypatch.setattr(storage, "object_exists_async", object_exists)
    monkeypatch.setattr(storage, "purge_strict_upload_attempt", purge, raising=False)
    asyncio.run(verify())
    assert key not in read_keys
    assert key not in storage.deleted_keys


@pytest.mark.parametrize(
    "outcome", [
        "deleted", "wrong_owner", "unknown_recovery", "false_receipt", "stale_receipt",
        "terminal", "retry_after_receipt", "foreign_marker", "stale_foreign_marker",
    ],
)
def test_accepted_strict_object_is_only_cleaned_for_tombstoned_meeting(
    client, storage_recovery, monkeypatch, outcome
) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    storage_recovery("reconciled")
    sessions = client.app_state["sessionmaker"]
    storage = client.app_state["storage"]
    journal_id = uuid4()
    calls = []
    fail_after_receipt = outcome == "retry_after_receipt"
    restore_after_first_receipt = outcome in {"stale_receipt", "stale_foreign_marker"}
    original_exists = storage.object_exists_async
    original_commit = deletion_service._commit_completed_purge

    async def seed():
        async with sessions.begin() as db:
            meeting = await db.get(Meeting, meeting_id)
            workspace = await db.get(Workspace, meeting.workspace_id)
            artifact = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.meeting_id == meeting_id, TrackArtifact.track_role == "media"
                )
            )
            assert artifact is not None
            owner = uuid4() if outcome == "wrong_owner" else workspace.organization_id
            key = (
                f"organizations/{owner}/workspaces/{workspace.id}/meetings/{meeting_id}/"
                f"artifacts/media-revisions/{artifact.media_revision_id or uuid4()}/"
                f"attempts/1/2/tracks/{artifact.track_role}"
            )
            if outcome == "deleted":
                part = await db.scalar(
                    select(UploadPart).join(UploadSession).where(
                        UploadSession.meeting_id == meeting_id, UploadPart.track_role == "media",
                    )
                )
                assert part is not None
                key = (
                    f"organizations/{owner}/workspaces/{workspace.id}/meetings/{meeting_id}/"
                    f"sessions/{part.upload_session_id}/tracks/media/parts/"
                    f"{part.part_number:08d}/calendar-attempts/1/2"
                )
                part.storage_object_key = key
                db.add(TemporaryUploadObject(
                    workspace_id=workspace.id, upload_session_id=part.upload_session_id,
                    media_revision_id=artifact.media_revision_id, storage_object_key=key,
                    byte_length=part.byte_length,
                ))
            artifact.storage_object_key = key
            db.add(PurgeJournal(
                id=journal_id, workspace_id=workspace.id, meeting_id=meeting_id,
                artifact_class=deletion_service.STRICT_UPLOAD_ATTEMPT,
                object_key=key, storage_scope="test-scope", storage_epoch=1,
                deletion_epoch=meeting.deletion_epoch, write_state="accepted",
                multipart_upload_id="exact-id",
                state={"false_receipt": "purged", "terminal": "terminal_unknown"}.get(outcome, "retained"),
            ))
            return key

    key = asyncio.run(seed())
    storage.objects[key] = b"synthetic"

    async def object_exists(candidate):
        nonlocal fail_after_receipt
        assert candidate != key, "Protected object must not use the generic storage client"
        if fail_after_receipt:
            assert calls == [key]
            fail_after_receipt = False
            raise RuntimeError("synthetic failure after protected object cleanup")
        return await original_exists(candidate)

    async def purge(**request):
        calls.append(request["key"])
        assert request["key"] == key and request["attempt_id"] == journal_id
        assert request["upload_id"] == "exact-id" and request["epoch"] == 1
        async with sessions.begin() as db:
            meeting = await db.scalar(
                select(Meeting).where(Meeting.id == meeting_id).with_for_update(nowait=True)
            )
            journal = await db.get(PurgeJournal, journal_id)
            assert meeting.deleted_at is not None and meeting.deletion_epoch > journal.deletion_epoch
            assert journal.state == "deleting" and journal.write_state == "accepted"
        if outcome == "foreign_marker" or (outcome == "stale_foreign_marker" and len(calls) == 2):
            return False
        storage.objects.pop(key)
        if outcome == "unknown_recovery":
            storage_recovery("recovery_unknown")
        return True

    async def verify_live_meeting():
        async with sessions() as db:
            meeting = await db.get(Meeting, meeting_id)
            with pytest.raises(RuntimeError, match="strict_upload_requires_explicit_ownership"):
                await _clear_orphan_cleanup_intents_for_authoritative_keys(
                    db, workspace_id=meeting.workspace_id, meeting_id=meeting_id, object_keys=[key],
                )
            assert await deletion_service.retry_orphan_purge_journals(
                db, meeting=meeting, storage=storage
            ) == {"reset_count": 0, "converged": outcome not in {"terminal", "false_receipt"}}
        async with sessions() as db:
            assert await deletion_service.reconcile_deletion_purges(db, storage=storage) == 0

    monkeypatch.setattr(storage, "object_exists_async", object_exists)
    monkeypatch.setattr(storage, "purge_strict_upload_attempt", purge, raising=False)
    if restore_after_first_receipt:
        async def restore_after_receipt(db, generation):
            nonlocal restore_after_first_receipt
            await original_commit(db, generation)
            if restore_after_first_receipt:
                restore_after_first_receipt = False
                storage.objects[key] = b"restored-synthetic"
                storage_recovery("reconciled", uuid4(), advance=True)

        monkeypatch.setattr(deletion_service, "_commit_completed_purge", restore_after_receipt)
    asyncio.run(verify_live_meeting())
    assert calls == [] and key in storage.objects
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(), json={"confirmation_boundary": BOUNDED_COPY},
    )
    if outcome == "deleted":
        assert response.status_code == 202, response.text
        assert response.json()["lifecycle"]["state"] == "active_purge_complete"
    else:
        assert response.status_code == 503, response.text
    calls_expected = outcome in {
        "deleted", "unknown_recovery", "stale_receipt", "retry_after_receipt", "foreign_marker",
        "stale_foreign_marker",
    }
    assert calls == ([key] if calls_expected else [])
    assert key not in storage.deleted_keys

    if outcome == "retry_after_receipt":
        async def reconcile():
            async with sessions() as db:
                assert await deletion_service.reconcile_deletion_purges(db, storage=storage) == 1

        asyncio.run(reconcile())
        report = asyncio.run(_load_deletion_rows(client, meeting_id))["report"]
        assert report.overall_state == "active_purge_complete"
        assert calls == [key]
    if outcome == "foreign_marker":
        assert storage.objects[key] == b"synthetic"

    async def verify_persisted():
        async with sessions() as db:
            journal = await db.get(PurgeJournal, journal_id)
            has_receipt = outcome in {
                "deleted", "stale_receipt", "retry_after_receipt", "stale_foreign_marker",
            }
            assert (journal.safe_reason == "object_deleted_verified") is has_receipt
            assert (journal.completed_at is not None) is has_receipt
            if outcome == "unknown_recovery":
                assert journal.state == "deleting"
            if outcome == "deleted":
                for model, status in (
                    (TrackArtifact, TrackArtifact.status),
                    (UploadPart, UploadPart.status),
                    (TemporaryUploadObject, TemporaryUploadObject.cleanup_status),
                ):
                    assert list(await db.scalars(
                        select(status).where(model.storage_object_key == key)
                    )) == ["purged"]

    asyncio.run(verify_persisted())
    if outcome in {"stale_receipt", "stale_foreign_marker"}:
        assert storage.objects[key] == b"restored-synthetic"
        retry = client.post(
            f"/api/v1/cabinet/meetings/{meeting_id}/deletion-retry", headers=auth_headers()
        )
        assert calls == [key, key]
        if outcome == "stale_receipt":
            assert retry.status_code == 202, retry.text
            assert retry.json()["lifecycle"]["state"] == "active_purge_complete"
            assert key not in storage.objects
        else:
            assert retry.status_code == 503, retry.text
            assert storage.objects[key] == b"restored-synthetic"


@pytest.mark.parametrize("restored_evidence", ["pending_alias", "purged_alias", "live_reference"])
def test_reserved_attempt_without_strict_journal_stays_unverified(
    client, monkeypatch, restored_evidence
) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    sessions = client.app_state["sessionmaker"]
    storage = client.app_state["storage"]
    prefix = f"organizations/{uuid4()}/workspaces/{uuid4()}/meetings/{meeting_id}/"
    key = prefix + (
        f"sessions/{uuid4()}/tracks/system/parts/00000001/calendar-attempts/1/2"
        if restored_evidence == "pending_alias"
        else f"artifacts/media-revisions/{uuid4()}/attempts/1/2/tracks/media"
    )
    storage.objects[key] = b"synthetic"
    original_exists = storage.object_exists_async
    reads = []

    async def object_exists(candidate):
        reads.append(candidate)
        return await original_exists(candidate)

    async def verify_orphans():
        async with sessions.begin() as db:
            meeting = await db.get(Meeting, meeting_id)
            if restored_evidence == "live_reference":
                artifact = await db.scalar(
                    select(TrackArtifact).where(TrackArtifact.meeting_id == meeting_id).limit(1)
                )
                assert artifact is not None
                artifact.storage_object_key = key
            else:
                db.add(PurgeJournal(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting_id,
                    artifact_class="object_store",
                    object_key=key,
                    state="pending" if restored_evidence == "pending_alias" else "purged",
                ))
    async def check_reconciliation(*, converged):
        async with sessions() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert await deletion_service.retry_orphan_purge_journals(
                db, meeting=meeting, storage=storage
            ) == {"reset_count": 0, "converged": converged}
        async with sessions() as db:
            assert await deletion_service.reconcile_deletion_purges(db, storage=storage) == 0

    monkeypatch.setattr(storage, "object_exists_async", object_exists)
    asyncio.run(verify_orphans())
    asyncio.run(check_reconciliation(converged=restored_evidence == "live_reference"))
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert response.status_code == 503, response.text
    assert response.json()["code"] == "deletion_purge_terminal_unknown"
    assert (asyncio.run(_load_deletion_rows(client, meeting_id)))["report"].overall_state == (
        "retryable_failed"
    )
    asyncio.run(check_reconciliation(converged=False))
    assert key not in reads
    assert key not in storage.deleted_keys
    assert storage.objects[key] == b"synthetic"


def test_manual_deletion_cancels_started_outcome_dispatch_and_keeps_workflow_reference(
    client,
) -> None:
    seeds = seed_cabinet_meetings(client)

    async def seed_started_intent() -> str:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == seeds.ready_id))
            assert meeting is not None
            workflow_id = f"outcome-generation/{uuid4()}"
            db.add(
                DispatchIntent(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    candidate_id=uuid4(),
                    intent_kind="summary_generation",
                    idempotency_key=f"delete-dispatch-{uuid4()}",
                    state="started",
                    reconciliation_state="started",
                    payload_json={},
                    deletion_epoch=int(meeting.deletion_epoch or 0),
                    lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
                    external_workflow_id=workflow_id,
                    started_at=datetime.now(UTC),
                )
            )
            await db.commit()
            return workflow_id

    workflow_id = asyncio.run(seed_started_intent())
    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert response.status_code == 202

    async def load_intent() -> DispatchIntent:
        async with client.app_state["sessionmaker"]() as db:
            intent = await db.scalar(
                select(DispatchIntent).where(DispatchIntent.meeting_id == seeds.ready_id)
            )
            assert intent is not None
            return intent

    intent = asyncio.run(load_intent())
    assert intent.state == "cancelled"
    assert intent.reconciliation_state == "cancelled"
    assert intent.lease_expires_at is None
    assert intent.external_workflow_id == workflow_id


def test_098_deletion_report_accounts_for_calendar_context_artifact(client) -> None:
    # FR-041: a synthetic calendar context is named explicitly in lifecycle accounting.
    seeds = seed_cabinet_meetings(client)
    _seed_synthetic_calendar_context(client, seeds.ready_id)

    deletion = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )

    assert deletion.status_code == 202
    assert report.status_code == 200
    calendar_rows = [
        row
        for row in report.json()["artifact_states"]
        if row["artifact_class"] == "calendar_context"
    ]
    assert len(calendar_rows) == 1
    assert calendar_rows[0]["control_scope"] == "controlled"
    assert calendar_rows[0]["state"] in {"purged", "metadata_retained"}


def test_098_failed_deletion_rolls_back_calendar_context_and_accounting(client) -> None:
    # FR-041, SC-010: fail-closed storage errors preserve pre-request synthetic lifecycle truth.
    seeds = seed_cabinet_meetings(client)
    _seed_synthetic_calendar_context(client, seeds.ready_id)
    original_storage = client.app.state.storage
    client.app.state.storage = object()
    try:
        response = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
            headers=auth_headers(),
            json={"confirmation_boundary": BOUNDED_COPY},
        )
    finally:
        client.app.state.storage = original_storage
    truth = asyncio.run(_load_calendar_rollback_truth(client, seeds.ready_id))

    assert response.status_code == 503
    assert response.json()["code"] == "deletion_storage_unavailable"
    assert truth["meeting"].deletion_state == "none"
    assert truth["request"] is None
    assert truth["report"] is None
    assert truth["artifact_states"] == []
    assert truth["context"].context_state == "no_context"
    assert truth["context"].manual_override_state == "none"
    assert truth["context"].unlinked_at is None


def test_manual_deletion_purges_server_audio_objects_and_upload_temps(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def purge_targets() -> tuple[list[str], list[str]]:
        async with client.app_state["sessionmaker"]() as db:
            artifacts = (
                await db.scalars(
                    select(TrackArtifact)
                    .where(TrackArtifact.meeting_id == seeds.ready_id)
                    .order_by(TrackArtifact.track_role)
                )
            ).all()
            temps = (
                await db.scalars(
                    select(TemporaryUploadObject)
                    .where(
                        TemporaryUploadObject.media_revision_id == artifacts[0].media_revision_id
                    )
                    .order_by(TemporaryUploadObject.storage_object_key)
                )
            ).all()
            return [artifact.storage_object_key for artifact in artifacts], [
                temp.storage_object_key for temp in temps
            ]

    artifact_keys, temp_keys = asyncio.run(purge_targets())
    storage = client.app_state["storage"]
    assert all(key in storage.objects for key in artifact_keys + temp_keys)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )

    assert response.status_code == 202
    assert all(key not in storage.objects for key in artifact_keys + temp_keys)

    async def purge_states() -> tuple[set[str], set[str]]:
        async with client.app_state["sessionmaker"]() as db:
            artifacts = (
                await db.scalars(
                    select(TrackArtifact).where(TrackArtifact.meeting_id == seeds.ready_id)
                )
            ).all()
            temps = (
                await db.scalars(
                    select(TemporaryUploadObject).where(
                        TemporaryUploadObject.storage_object_key.in_(temp_keys)
                    )
                )
            ).all()
            return {artifact.status for artifact in artifacts}, {
                temp.cleanup_status for temp in temps
            }

    assert asyncio.run(purge_states()) == ({"purged"}, {"purged"})


def test_manual_deletion_purges_part_only_upload_object(client) -> None:
    seeds = seed_cabinet_meetings(client)
    object_key = f"workspace/{seeds.ready_id}/part-only-object"

    async def seed_part_only() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            session = UploadSession(
                meeting_id=meeting.id,
                media_revision_id=None,
                workspace_id=meeting.workspace_id,
                device_id=meeting.device_id,
                created_by_user_id=meeting.created_by_user_id,
                upload_strategy="server_mediated",
                status="pending",
                processing_status="not_submitted",
                expected_track_roles=["media"],
                expected_track_sizes={},
                max_package_bytes_snapshot=10_000,
                max_track_bytes_snapshot=10_000,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
            db.add(session)
            await db.flush()
            db.add(
                UploadPart(
                    upload_session_id=session.id,
                    track_role="media",
                    part_number=0,
                    byte_offset=0,
                    byte_length=4,
                    sha256="a" * 64,
                    storage_object_key=object_key,
                    status="accepted",
                )
            )
            await db.commit()

    asyncio.run(seed_part_only())
    storage = client.app.state["storage"]
    storage.objects[object_key] = b"part"

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )

    assert response.status_code == 202
    assert object_key not in storage.objects


def test_deletion_report_includes_safe_post_egress_limits_from_download_and_export_audit(
    client,
) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(
        client, seeds.ready_id, transcript_download="allowed", package_export="allowed"
    )
    download = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=auth_headers(),
    )
    export = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/exports",
        headers=auth_headers(),
        json={"artifact_classes": ["transcript"]},
    )
    assert download.status_code == 200
    assert export.status_code == 202

    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )

    assert report.status_code == 200
    serialized = report.text.lower()
    assert "download_completed" in serialized
    assert "export_completed" in serialized
    assert SAFE_TRANSCRIPT_TEXT.lower() not in serialized
    assert "storage_object_key" not in serialized
    assert "share_token_hash" not in serialized


def test_deletion_report_treats_legacy_playback_completed_as_post_egress(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def seed_playback_egress() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            db.add(
                MeetingEgressAuditEvent(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    actor_user_id=None,
                    device_id=None,
                    event_type="playback_completed",
                    artifact_class="audio",
                    policy_reason="server_mediated_review_playback",
                    outcome="completed",
                    metadata_json={"artifact_class": "audio", "source_mode": "stored_review_m4a"},
                )
            )
            await db.commit()

    asyncio.run(seed_playback_egress())

    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )

    assert report.status_code == 200
    assert "post_egress_events:playback_completed" in report.text
    assert "stored_review_m4a" not in report.text


def test_deletion_report_treats_stream_prepared_events_as_post_egress(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def seed_stream_egress() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            for event_type in ("download_stream_prepared", "playback_stream_prepared"):
                db.add(
                    MeetingEgressAuditEvent(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        actor_user_id=None,
                        device_id=None,
                        event_type=event_type,
                        artifact_class="audio",
                        policy_reason="server_mediated_review_playback",
                        outcome="prepared",
                        metadata_json={"artifact_class": "audio", "stream_state": "prepared"},
                    )
                )
            await db.commit()

    asyncio.run(seed_stream_egress())

    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )

    assert report.status_code == 200
    assert "post_egress_events:" in report.text
    assert "download_stream_prepared" in report.text
    assert "playback_stream_prepared" in report.text
    assert "stream_state" not in report.text


def test_deletion_report_activity_remains_metadata_only_after_local_purge_ack(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202
    task = client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"][
        0
    ]

    ack = client.post(
        task["ack_url"],
        headers=auth_headers(),
        json={"state": "acknowledged", "reason_code": "local_buffers_purged"},
    )
    assert ack.status_code == 200

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )

    assert report.status_code == 200
    activity = report.json()["activity"]
    assert [item["event_type"] for item in activity] == [
        "deletion_requested",
        "local_purge_acknowledged",
    ]
    assert activity[0]["actor_label"] == "Owner/Admin"
    assert activity[1]["actor_label"] == "Desktop device"
    serialized = report.text.lower()
    assert SAFE_TRANSCRIPT_TEXT.lower() not in serialized
    assert "/users/" not in serialized
    assert "storage_object_key" not in serialized


async def _load_deletion_rows(client, meeting_id):
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        request = await db.scalar(
            select(MeetingDeletionRequest).where(MeetingDeletionRequest.meeting_id == meeting_id)
        )
        audit = await db.scalar(
            select(MeetingLifecycleAuditEvent).where(
                MeetingLifecycleAuditEvent.meeting_id == meeting_id
            )
        )
        report = await db.scalar(
            select(MeetingDeletionReport).where(MeetingDeletionReport.meeting_id == meeting_id)
        )
        artifact_states = (
            await db.scalars(
                select(MeetingDeletionArtifactState).where(
                    MeetingDeletionArtifactState.meeting_id == meeting_id
                )
            )
        ).all()
        return {
            "meeting": meeting,
            "request": request,
            "audit": audit,
            "report": report,
            "artifact_states": artifact_states,
        }


def _seed_synthetic_calendar_context(client, meeting_id) -> None:
    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting_id
                )
            )
            if context is None:
                context = RecordingCalendarContextLink(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting_id,
                )
                db.add(context)
            context.context_state = "no_context"
            context.context_confidence = "none"
            context.context_reasons_json = ["no_matching_event"]
            context.title_source = "generic"
            context.roster_source = "none"
            context.manual_override_state = "none"
            context.safe_reason_code = "no_matching_event"
            context.decision_source = "system_skip"
            context.candidate_event_ids_json = []
            context.candidate_count = 0
            context.matched_title_state = "unavailable"
            context.matched_roster_json = []
            context.matched_roster_state = "not_available"
            context.matched_roster_count = 0
            context.unlinked_at = None
            await db.commit()

    asyncio.run(seed())


async def _load_calendar_rollback_truth(client, meeting_id):
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        request = await db.scalar(
            select(MeetingDeletionRequest).where(MeetingDeletionRequest.meeting_id == meeting_id)
        )
        report = await db.scalar(
            select(MeetingDeletionReport).where(MeetingDeletionReport.meeting_id == meeting_id)
        )
        artifact_states = (
            await db.scalars(
                select(MeetingDeletionArtifactState).where(
                    MeetingDeletionArtifactState.meeting_id == meeting_id
                )
            )
        ).all()
        context = await db.scalar(
            select(RecordingCalendarContextLink).where(
                RecordingCalendarContextLink.meeting_id == meeting_id
            )
        )
        return {
            "meeting": meeting,
            "request": request,
            "report": report,
            "artifact_states": artifact_states,
            "context": context,
        }
