"""Source lineage on disposable PostgreSQL, without admitting analytics."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    MediaRevision,
    MediaScribeJob,
    Meeting,
    ProcessingResult,
    ProcessingWorkflow,
    ProductActivationMilestone,
    UploadSession,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision

NOW = datetime(2026, 11, 16, 10, tzinfo=UTC)
START = NOW - timedelta(days=1)


async def _seed_source(db, *, source_kind="manual_upload", revision_audit=False):
    created = START + timedelta(hours=1)
    meeting = Meeting(
        id=uuid4(), workspace_id=WORKSPACE_ID, created_by_user_id=USER_ID,
        device_id=DEVICE_ID, local_recording_id="synthetic-source",
        duration_seconds=60, created_at=created, deletion_state="none", deletion_epoch=0,
        create_request_fingerprint_sha256="a" * 64,
        # An old conversation is a legitimate new upload.
        started_at=START - timedelta(days=100),
    )
    db.add(meeting)
    await db.flush()
    revision = MediaRevision(
        id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
        local_media_revision_id="synthetic-source--initial", revision_number=1,
        source_kind=source_kind, status="accepted", immutable=True,
        manifest_sha256="b" * 64, track_sha256_by_role={"media": "c" * 64},
        duration_seconds=60, created_at=created,
        accepted_at=created + timedelta(minutes=2),
    )
    db.add(revision)
    await db.flush()
    upload = UploadSession(
        id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
        media_revision_id=revision.id, created_by_user_id=USER_ID, device_id=DEVICE_ID,
        status="finalized", created_at=created + timedelta(minutes=1),
        finalized_at=created + timedelta(minutes=2, seconds=1),
        expires_at=created + timedelta(days=1),
        max_package_bytes_snapshot=4096, max_track_bytes_snapshot=4096,
    )
    workflow = ProcessingWorkflow(
        id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
        media_revision_id=revision.id, workflow_id=f"synthetic-{uuid4()}", status="processed",
        source_fingerprint=source_fingerprint_for_revision(revision), deletion_epoch_at_start=0,
    )
    db.add_all([upload, workflow])
    await db.flush()
    job = MediaScribeJob(
        id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
        media_revision_id=revision.id, processing_workflow_id=workflow.id,
    )
    db.add(job)
    await db.flush()
    result = ProcessingResult(
        id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
        media_revision_id=revision.id, processing_workflow_id=workflow.id,
        mediascribe_job_id=job.id, result_version=2, status="imported",
        transcript_status="available", segment_count=1,
        diarization_status="available", diarization_segment_count=1,
        deletion_epoch_at_start=0, imported_at=created + timedelta(minutes=3),
    )
    events = [
        IngestAuditEvent(
            id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
            actor_user_id=USER_ID, device_id=DEVICE_ID,
            event_type="meeting_created", created_at=created,
        ),
        IngestAuditEvent(
            id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
            actor_user_id=USER_ID, device_id=DEVICE_ID, upload_session_id=upload.id,
            media_revision_id=revision.id if revision_audit else None,
            event_type="media_revision_upload_session_created" if revision_audit else "session_created",
            created_at=upload.created_at,
        ),
        IngestAuditEvent(
            id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
            actor_user_id=USER_ID, device_id=DEVICE_ID, upload_session_id=upload.id,
            event_type="finalized",
            # The real ingest records this event before assigning finalized_at.
            created_at=revision.accepted_at,
        ),
    ]
    db.add_all([result, *events])
    await db.commit()
    return meeting, revision, upload, workflow, result, events


def _run(url, scenario):
    async def execute():
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            await scenario(async_sessionmaker(engine, expire_on_commit=False))
        finally:
            await engine.dispose()

    asyncio.run(execute())


async def _load(db, rows, **overrides):
    from twobrain_rec_server.cabinet.result_visibility import load_result_view_source

    meeting, revision, _, _, result, _ = rows
    params = dict(
        owner_id=USER_ID, workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
        media_revision_id=revision.id, processing_result_id=result.id,
        started_at=START, now=NOW,
    )
    return await load_result_view_source(db, **(params | overrides))


@pytest.mark.parametrize("source_kind,capture,revision_audit", [
    ("manual_upload", False, False),
    ("initial_mixed_recording", None, False),
    ("manual_upload", False, True),
])
def test_full_new_ingest_accepts_imported_result_and_preserves_capture_unknown(
    postgres_seeded_database_url, source_kind, capture, revision_audit,
):
    async def scenario(sessions):
        async with sessions() as db:
            rows = await _seed_source(db, source_kind=source_kind, revision_audit=revision_audit)
            source = await _load(db, rows)
            assert source is not None
            assert source.meeting_id == rows[0].id
            assert source.result_id == rows[4].id and source.result_version == 2
            assert source.source_fingerprint == source_fingerprint_for_revision(rows[1])
            assert source.first_recording_completed is capture
            assert (await db.scalars(select(ProductActivationMilestone))).all() == []

    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("broken", [
    "old_meeting", "missing_request_fingerprint", "invalid_request_fingerprint",
    "missing_meeting_audit", "missing_session_audit", "missing_finalize_audit",
    "wrong_audit_actor", "wrong_audit_device", "wrong_audit_session",
    "wrong_audit_revision", "old_audit", "future_audit", "old_upload", "old_acceptance",
    "unfinished_upload", "mutable_revision", "invalid_digest", "workflow_source",
    "workflow_deletion_epoch", "result_deletion_epoch", "deleted", "unready_result",
    "unknown_started_at", "future_started_at", "wrong_owner", "wrong_workspace",
    "wrong_selected_revision", "future_upload", "future_result", "historical_dual_source",
    "unavailable_transcript", "unavailable_diarization", "empty_transcript", "empty_diarization",
])
def test_incomplete_or_mismatched_lineage_never_becomes_a_fact(postgres_seeded_database_url, broken):
    async def scenario(sessions):
        async with sessions() as db:
            rows = await _seed_source(db)
            meeting, revision, upload, workflow, result, events = rows
            overrides = {}
            if broken == "old_meeting":
                meeting.created_at = START - timedelta(seconds=1)
            elif broken in {"missing_request_fingerprint", "invalid_request_fingerprint"}:
                meeting.create_request_fingerprint_sha256 = None if broken.startswith("missing") else "x" * 64
            elif broken.startswith("missing_"):
                await db.delete(events[{"missing_meeting_audit": 0, "missing_session_audit": 1,
                                        "missing_finalize_audit": 2}[broken]])
            elif broken == "wrong_audit_actor":
                events[2].actor_user_id = None
            elif broken == "wrong_audit_device":
                events[2].device_id = None
            elif broken == "wrong_audit_session":
                events[2].upload_session_id = None
            elif broken == "wrong_audit_revision":
                # Use another real revision so FK validity cannot hide the mismatch.
                other = MediaRevision(
                    id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
                    revision_number=2, local_media_revision_id="synthetic-other",
                )
                db.add(other)
                await db.flush()
                events[2].media_revision_id = other.id
            elif broken == "old_audit":
                events[0].created_at = START - timedelta(seconds=1)
            elif broken == "future_audit":
                events[2].created_at = NOW + timedelta(seconds=1)
            elif broken == "old_upload":
                upload.created_at = START - timedelta(seconds=1)
            elif broken == "old_acceptance":
                revision.accepted_at = START - timedelta(seconds=1)
            elif broken == "unfinished_upload":
                upload.status = "pending"
            elif broken == "mutable_revision":
                revision.immutable = False
            elif broken == "invalid_digest":
                revision.track_sha256_by_role = {"media": "broken"}
            elif broken == "workflow_source":
                workflow.source_fingerprint = "d" * 64
            elif broken == "workflow_deletion_epoch":
                workflow.deletion_epoch_at_start = 1
            elif broken == "result_deletion_epoch":
                result.deletion_epoch_at_start = 1
            elif broken == "deleted":
                meeting.deletion_state = "deleting"
            elif broken == "unready_result":
                result.status = "importing"
            elif broken == "unknown_started_at":
                overrides["started_at"] = None
            elif broken == "future_started_at":
                overrides["started_at"] = NOW + timedelta(seconds=1)
            elif broken == "wrong_owner":
                overrides["owner_id"] = uuid4()
            elif broken == "wrong_workspace":
                overrides["workspace_id"] = uuid4()
            elif broken == "wrong_selected_revision":
                overrides["media_revision_id"] = uuid4()
            elif broken == "future_upload":
                upload.finalized_at = NOW + timedelta(seconds=1)
            elif broken == "future_result":
                result.imported_at = NOW + timedelta(seconds=1)
            elif broken == "unavailable_transcript":
                result.transcript_status = "unavailable"
            elif broken == "unavailable_diarization":
                result.diarization_status = "unavailable"
            elif broken == "empty_transcript":
                result.segment_count = 0
            elif broken == "empty_diarization":
                result.diarization_segment_count = 0
            elif broken == "historical_dual_source":
                revision.source_kind = "initial_recording"
                revision.track_sha256_by_role = {"microphone": "c" * 64, "system": "d" * 64}
                workflow.source_fingerprint = source_fingerprint_for_revision(revision)
            else:
                raise AssertionError(broken)
            await db.commit()
            assert await _load(db, rows, **overrides) is None
            assert (await db.scalars(select(ProductActivationMilestone))).all() == []

    _run(postgres_seeded_database_url, scenario)


def test_source_reloads_after_committed_change_in_another_session(postgres_seeded_database_url):
    async def scenario(sessions):
        async with sessions() as db:
            rows = await _seed_source(db)
            assert await _load(db, rows) is not None
            async with sessions() as writer:
                meeting = await writer.get(Meeting, rows[0].id)
                meeting.deletion_epoch = 1
                await writer.commit()
            # db still has an old identity-map instance; it must not authorize it.
            assert await _load(db, rows) is None

    _run(postgres_seeded_database_url, scenario)
