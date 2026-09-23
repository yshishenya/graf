import asyncio
import importlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy import func, select
from temporalio import activity

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import tenant_scope
from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fakes.mediascribe_v1 import MediaScribeV1Fixture
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.billing.usage import reserve_free_usage
from twobrain_rec_server.db.models import (
    FreeUsageWindow,
    MediaRevision,
    MediaScribeJob,
    Meeting,
    MeetingDeletionArtifactState,
    ProcessingResult,
    ProcessingWorkflow,
    TrackArtifact,
    UsageReservation,
)
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingStatus
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.mediascribe.client import MediaScribeClient
from twobrain_rec_server.mediascribe.schemas import (
    MediaScribeDeletionState,
    MediaScribeDiarizationSegment,
    MediaScribeResult,
    MediaScribeTranscriptSegment,
)
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.pickup import pick_up_processing
from twobrain_rec_server.processing.submit import submit_to_mediascribe
from twobrain_rec_server.workflows import worker


@pytest.fixture(autouse=True)
def activity_heartbeat(monkeypatch):
    monkeypatch.setattr(activity, "heartbeat", lambda *_args, **_kwargs: None)


async def historical_revision(db, finalized):
    # Model an already stored pre-v5 revision without using retired API writes.
    revision = await db.get(
        MediaRevision, UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    )
    revision.source_kind = "initial_recording"
    revision.track_sha256_by_role = {"microphone": "a" * 64, "system": "b" * 64}
    await db.commit()
    return revision


@pytest.mark.parametrize(
    "state", ["not_submitted", "workflow_started", "waiting_retry", "blocked_unknown"]
)
@pytest.mark.parametrize("entry", ["submit", "worker", "pickup", "closed_recovery", "manual_retry"])
def test_historical_pending_stops_without_quota_claim_or_egress(client, monkeypatch, state, entry):
    finalized = create_finalized_meeting(client, f"retired-{state}-{entry}")
    provider = FakeMediaScribeClient()
    monkeypatch.setattr(worker, "get_settings", lambda: client.app.state.settings)
    reservation = AsyncMock(side_effect=AssertionError("retired source reserved processing quota"))
    claim = AsyncMock(side_effect=AssertionError("retired source claimed submission"))
    monkeypatch.setattr(store, "ensure_processing_usage_reservation", reservation)
    monkeypatch.setattr(store, "_reserve_processing_attempt_quota", reservation)
    monkeypatch.setattr(store, "claim_mediascribe_submission", claim)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            revision = await historical_revision(db, finalized)
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=revision.workspace_id,
                meeting_id=revision.meeting_id,
                media_revision_id=revision.id,
                workflow_id=f"processing/{revision.id}",
                status=ProcessingStatus(state),
            )
            workflow.next_attempt_at = datetime.now(UTC) + timedelta(seconds=10)
            workflow.retry_class = "unknown_outcome" if state == "blocked_unknown" else "retryable"
            job = MediaScribeJob(
                workspace_id=revision.workspace_id,
                meeting_id=revision.meeting_id,
                media_revision_id=revision.id,
                processing_workflow_id=workflow.id,
                request_mode="dual_track",
                status="blocked",
                last_error_code="blocked_mediascribe_submission_outcome_unknown",
                idempotency_key="retained-legacy-key",
                source_fingerprint=source_fingerprint_for_revision(revision),
                request_fingerprint="c" * 64,
            )
            db.add(job)
            await db.commit()
            workflow_id = workflow.id
            job_id = job.id
            if entry == "submit":
                with pytest.raises(RuntimeError, match="unsupported_recording_source"):
                    await submit_to_mediascribe(
                        db=db,
                        settings=client.app.state.settings,
                        storage=client.app_state["storage"],
                        mediascribe_client=provider,
                        workflow=workflow,
                    )
            elif entry == "pickup":
                await pick_up_processing(
                    db=db,
                    settings=client.app.state.settings,
                    workspace_id=revision.workspace_id,
                    meeting_id=revision.meeting_id,
                    temporal_client=FakeTemporalClient(),
                )
            elif entry == "closed_recovery":
                assert (
                    await store.prepare_closed_workflow_same_job_recovery(db, workflow=workflow)
                    is None
                )
            elif entry == "manual_retry":
                result = await store.create_processing_attempt(
                    db,
                    workspace_id=revision.workspace_id,
                    meeting_id=revision.meeting_id,
                )
                assert result.result == "source_unavailable"
        if entry == "worker":
            scope = tenant_scope()
            outcome = await worker.run_processing_pipeline_activity(
                {
                    "meeting_id": str(revision.meeting_id),
                    "media_revision_id": str(revision.id),
                    "processing_workflow_id": str(workflow_id),
                    "workspace_id": str(scope.workspace_id),
                    "organization_id": str(scope.organization_id),
                    "user_id": str(scope.user_id),
                    "device_id": str(scope.device_id),
                    "single_step": "true",
                },
                sessionmaker=client.app_state["sessionmaker"],
                storage=client.app_state["storage"],
                mediascribe_client=provider,
            )
            assert outcome["processing_status"] == "failed_terminal"
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.get(ProcessingWorkflow, workflow_id)
            job = await db.get(MediaScribeJob, job_id)
            assert workflow.status == "failed_terminal"
            assert workflow.last_reason_code == "unsupported_recording_source"
            assert workflow.ended_at is not None
            assert workflow.next_attempt_at is None
            assert workflow.retry_class == "terminal"
            assert job.idempotency_key == "retained-legacy-key"
            assert job.request_fingerprint == "c" * 64
            assert await db.scalar(select(func.count()).select_from(MediaScribeJob)) == 1
            assert (
                await store.load_processing_source(
                    db,
                    workspace_id=revision.workspace_id,
                    meeting_id=revision.meeting_id,
                    media_revision_id=revision.id,
                )
                is None
            )
        reservation.assert_not_awaited()
        claim.assert_not_awaited()
        assert provider.submissions == []

    asyncio.run(run())


@pytest.mark.parametrize("state", ["workflow_started", "blocked_unknown", "failed_terminal"])
def test_historical_known_id_continues_poll_and_import_without_post(client, monkeypatch, state):
    finalized = create_finalized_meeting(client, "retired-known-provider-id")
    provider = FakeMediaScribeClient(status_sequence=[MediaScribeJobStatus.READY])
    provider.result = MediaScribeResult(
        external_job_id=provider.external_job_id,
        transcript_status="available",
        transcript=[
            MediaScribeTranscriptSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=1,
                text="Synthetic test segment.",
                source_role="mic",
            )
        ],
        diarization=[
            MediaScribeDiarizationSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=1,
                text="Synthetic test segment.",
                source_role="mic",
                speaker_label="LOCAL_00",
            )
        ],
    )
    monkeypatch.setattr(worker, "get_settings", lambda: client.app.state.settings)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            revision = await historical_revision(db, finalized)
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=revision.workspace_id,
                meeting_id=revision.meeting_id,
                media_revision_id=revision.id,
                workflow_id=f"processing/{revision.id}",
                status=ProcessingStatus(state),
                reason_code="processing_retry_deadline_exceeded"
                if state == "failed_terminal"
                else None,
            )
            db.add(
                MediaScribeJob(
                    workspace_id=revision.workspace_id,
                    meeting_id=revision.meeting_id,
                    media_revision_id=revision.id,
                    processing_workflow_id=workflow.id,
                    request_mode="dual_track",
                    external_job_id=provider.external_job_id,
                    status="submitted",
                    source_fingerprint=source_fingerprint_for_revision(revision),
                )
            )
            await db.commit()
            if state == "failed_terminal":
                attempt = await store.create_processing_attempt(
                    db,
                    workspace_id=revision.workspace_id,
                    meeting_id=revision.meeting_id,
                )
                assert attempt.result == "created"
                workflow = attempt.workflow
                assert workflow.stage == "poll"
                await db.commit()
            workflow_id = workflow.id
        scope = tenant_scope()
        outcome = await worker.run_processing_pipeline_activity(
            {
                "meeting_id": str(revision.meeting_id),
                "media_revision_id": str(revision.id),
                "processing_workflow_id": str(workflow_id),
                "workspace_id": str(scope.workspace_id),
                "organization_id": str(scope.organization_id),
                "user_id": str(scope.user_id),
                "device_id": str(scope.device_id),
                "single_step": "true",
            },
            sessionmaker=client.app_state["sessionmaker"],
            storage=client.app_state["storage"],
            mediascribe_client=provider,
        )
        async with client.app_state["sessionmaker"]() as db:
            saved_workflow = await db.get(ProcessingWorkflow, workflow_id)
            assert outcome["processing_status"] == "processed", (
                outcome,
                saved_workflow.last_reason_code,
                provider.poll_count,
            )
            imported = await db.scalar(
                select(ProcessingResult).where(
                    ProcessingResult.processing_workflow_id == workflow_id,
                )
            )
            assert imported is not None and imported.status == "imported"
            assert imported.segment_count == 1
        assert provider.poll_count == 1
        assert provider.submissions == []

    asyncio.run(run())


@pytest.mark.parametrize(
    ("workflow_status", "job_status", "reason", "has_result"),
    [
        ("processed", "ready", None, True),
        ("failed_terminal", "failed", "processing_retry_deadline_exceeded", False),
        ("failed_terminal", "ready", "processing_retry_deadline_exceeded", True),
    ],
    ids=["completed", "provider-failed", "already-imported"],
)
def test_c1_nonresumable_known_id_without_source_rejects_attempt_before_quota(
    client,
    monkeypatch,
    workflow_status,
    job_status,
    reason,
    has_result,
):
    finalized = create_finalized_meeting(client, "retired-nonresumable-known-id")
    reservation = AsyncMock(side_effect=AssertionError("nonresumable job reserved new quota"))
    claim = AsyncMock(side_effect=AssertionError("nonresumable job claimed submission"))
    monkeypatch.setattr(store, "_reserve_processing_attempt_quota", reservation)
    monkeypatch.setattr(store, "ensure_processing_usage_reservation", reservation)
    monkeypatch.setattr(store, "claim_mediascribe_submission", claim)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            revision = await historical_revision(db, finalized)
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=revision.workspace_id,
                meeting_id=revision.meeting_id,
                media_revision_id=revision.id,
                workflow_id=f"processing/{revision.id}",
                status=ProcessingStatus(workflow_status),
                reason_code=reason,
            )
            job = MediaScribeJob(
                workspace_id=revision.workspace_id,
                meeting_id=revision.meeting_id,
                media_revision_id=revision.id,
                processing_workflow_id=workflow.id,
                request_mode="dual_track",
                external_job_id="retained-nonresumable-job",
                status=job_status,
                source_fingerprint=source_fingerprint_for_revision(revision),
                idempotency_key="retained-nonresumable-key",
                request_fingerprint="d" * 64,
            )
            db.add(job)
            await db.flush()
            if has_result:
                db.add(
                    ProcessingResult(
                        workspace_id=revision.workspace_id,
                        meeting_id=revision.meeting_id,
                        media_revision_id=revision.id,
                        processing_workflow_id=workflow.id,
                        mediascribe_job_id=job.id,
                        status="imported",
                        source_result_hash="f" * 64,
                    )
                )
            for artifact in await db.scalars(
                select(TrackArtifact).where(
                    TrackArtifact.media_revision_id == revision.id,
                )
            ):
                artifact.status = "purged"
            await db.commit()
            assert (
                await store.load_processing_source(
                    db,
                    workspace_id=revision.workspace_id,
                    meeting_id=revision.meeting_id,
                    media_revision_id=revision.id,
                )
                is None
            )
            workflow_id, job_id = workflow.id, job.id
            for _ in range(2):
                attempt = await store.create_processing_attempt(
                    db,
                    workspace_id=revision.workspace_id,
                    meeting_id=revision.meeting_id,
                    allow_processed=workflow_status == "processed",
                )
                assert attempt.result == "source_unavailable"
                await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            saved_workflow = await db.get(ProcessingWorkflow, workflow_id)
            saved_job = await db.get(MediaScribeJob, job_id)
            assert saved_workflow.status == workflow_status
            assert saved_workflow.attempt_ordinal == 1
            assert saved_job.processing_workflow_id == workflow_id
            assert saved_job.status == job_status
            assert saved_job.external_job_id == "retained-nonresumable-job"
            assert saved_job.idempotency_key == "retained-nonresumable-key"
            assert saved_job.request_fingerprint == "d" * 64
            assert await db.scalar(select(func.count()).select_from(ProcessingWorkflow)) == 1
            assert await db.scalar(select(func.count()).select_from(MediaScribeJob)) == 1
            assert await db.scalar(select(func.count()).select_from(UsageReservation)) == 0
        reservation.assert_not_awaited()
        claim.assert_not_awaited()

    asyncio.run(run())


def test_c2_retiring_not_submitted_releases_existing_reservation(client, monkeypatch):
    finalized = create_finalized_meeting(client, "retired-existing-reservation")
    provider = FakeMediaScribeClient()
    new_reservation = AsyncMock(side_effect=AssertionError("retirement reserved new quota"))
    claim = AsyncMock(side_effect=AssertionError("retirement claimed submission"))
    monkeypatch.setattr(store, "ensure_processing_usage_reservation", new_reservation)
    monkeypatch.setattr(store, "_reserve_processing_attempt_quota", new_reservation)
    monkeypatch.setattr(store, "claim_mediascribe_submission", claim)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            revision = await historical_revision(db, finalized)
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=revision.workspace_id,
                meeting_id=revision.meeting_id,
                media_revision_id=revision.id,
                workflow_id=f"processing/{revision.id}",
                status=ProcessingStatus.NOT_SUBMITTED,
            )
            workflow.next_attempt_at = datetime.now(UTC) + timedelta(minutes=1)
            workflow.retry_class = "retryable"
            db.add(
                MediaScribeJob(
                    workspace_id=revision.workspace_id,
                    meeting_id=revision.meeting_id,
                    media_revision_id=revision.id,
                    processing_workflow_id=workflow.id,
                    request_mode="dual_track",
                    status="not_submitted",
                    source_fingerprint=source_fingerprint_for_revision(revision),
                )
            )
            now = datetime.now(UTC)
            reservation = await reserve_free_usage(
                db,
                workspace_id=revision.workspace_id,
                reservation_key=f"processing:{revision.id}",
                declared_seconds=60,
                now=now,
                expires_at=now + timedelta(hours=1),
            )
            await db.commit()
            window = await db.get(FreeUsageWindow, reservation.window_id)
            assert reservation.state == "active"
            assert window.reserved_seconds == 60
            assert window.committed_seconds == 0
            workflow_id, reservation_id, window_id = workflow.id, reservation.id, window.id
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.get(ProcessingWorkflow, workflow_id)
            with pytest.raises(RuntimeError, match="unsupported_recording_source"):
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=client.app_state["storage"],
                    mediascribe_client=provider,
                    workflow=workflow,
                )
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.get(ProcessingWorkflow, workflow_id)
            reservation = await db.get(UsageReservation, reservation_id)
            window = await db.get(FreeUsageWindow, window_id)
            assert workflow.status == "failed_terminal"
            assert workflow.last_reason_code == "unsupported_recording_source"
            assert workflow.ended_at is not None
            assert workflow.next_attempt_at is None
            assert workflow.retry_class == "terminal"
            assert reservation.state == "released"
            assert reservation.committed_seconds == 0
            assert window.reserved_seconds == 0
            assert window.committed_seconds == 0
            assert await db.scalar(select(func.count()).select_from(UsageReservation)) == 1
        new_reservation.assert_not_awaited()
        claim.assert_not_awaited()
        assert provider.submissions == []

    asyncio.run(run())


def test_historical_pickup_without_workflow_is_terminal_and_never_dispatched(client, monkeypatch):
    finalized = create_finalized_meeting(client, "retired-no-workflow")
    temporal = FakeTemporalClient()
    reservation = AsyncMock(side_effect=AssertionError("retired source reserved processing quota"))
    monkeypatch.setattr(
        "twobrain_rec_server.processing.pickup._reserve_processing_usage", reservation
    )

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            revision = await historical_revision(db, finalized)
            for _ in range(2):
                result = await pick_up_processing(
                    db=db,
                    settings=client.app.state.settings,
                    workspace_id=revision.workspace_id,
                    meeting_id=revision.meeting_id,
                    temporal_client=temporal,
                )
                assert result.started_count == 0
            workflows = list(await db.scalars(select(ProcessingWorkflow)))
            assert len(workflows) == 1
            assert workflows[0].status == "failed_terminal"
            assert workflows[0].last_reason_code == "unsupported_recording_source"
            assert workflows[0].ended_at is not None
            assert await db.scalar(select(func.count()).select_from(MediaScribeJob)) == 0
            reservation.assert_not_awaited()

    asyncio.run(run())


def test_historical_known_id_preserves_local_and_provider_deletion_without_post(client):
    finalized = create_finalized_meeting(client, "retired-known-id-deletion")
    transport = MediaScribeV1Fixture(job_id="retained-historical-job")
    provider = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="synthetic-test-key",
        transport=transport.transport(),
    )

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            revision = await historical_revision(db, finalized)
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=revision.workspace_id,
                meeting_id=revision.meeting_id,
                media_revision_id=revision.id,
                workflow_id=f"processing/{revision.id}",
                status=ProcessingStatus.POLLING,
            )
            job = MediaScribeJob(
                workspace_id=revision.workspace_id,
                meeting_id=revision.meeting_id,
                media_revision_id=revision.id,
                processing_workflow_id=workflow.id,
                request_mode="dual_track",
                external_job_id=transport.job_id,
                status="submitted",
                source_fingerprint=source_fingerprint_for_revision(revision),
                idempotency_key="retained-historical-delete-key",
                request_fingerprint="e" * 64,
            )
            db.add(job)
            await db.commit()
            return revision.meeting_id, job.id, workflow.id

    meeting_id, job_id, workflow_id = asyncio.run(seed())
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": "Delete this meeting everywhere GRAF controls."},
    )
    assert response.status_code == 202

    async def verify_and_delete_provider_job():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            workflow = await db.get(ProcessingWorkflow, workflow_id)
            job = await db.get(MediaScribeJob, job_id)
            assert meeting.deletion_state == "active_purge_complete"
            assert workflow.status == "canceled"
            assert job.request_mode == "dual_track"
            assert job.external_job_id == transport.job_id
            assert job.idempotency_key == "retained-historical-delete-key"
            assert job.request_fingerprint == "e" * 64
            assert job.status == "blocked" and job.last_error_code == "meeting_deleting"
            artifacts = list(
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == meeting_id,
                    )
                )
            )
            assert artifacts and all(artifact.status == "purged" for artifact in artifacts)
            assert all(
                artifact.storage_object_key not in client.app_state["storage"].objects
                for artifact in artifacts
            )
            dependency = await db.scalar(
                select(MeetingDeletionArtifactState).where(
                    MeetingDeletionArtifactState.meeting_id == meeting_id,
                    MeetingDeletionArtifactState.artifact_class == "mediascribe",
                )
            )
            # Local deletion does not claim provider deletion is automated.
            assert dependency.state == "unknown"
            assert transport.calls == []
            deletion = await provider.delete_job(job.external_job_id)
            confirmed = await provider.get_deletion(job.external_job_id)
            assert deletion.state == confirmed.state == MediaScribeDeletionState.COMPLETED

    asyncio.run(verify_and_delete_provider_job())
    assert transport.calls == [
        ("DELETE", f"/v1/audio/transcriptions/{transport.job_id}"),
        ("GET", f"/v1/audio/transcriptions/{transport.job_id}/deletion"),
    ]
    assert transport.submissions == []


def test_single_source_default_migration_preserves_historical_job(client):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    migration = importlib.import_module(
        "twobrain_rec_server.db.migrations.versions.0098_single_source_job_default"
    )
    finalized = create_finalized_meeting(client, "retired-default-migration")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            revision = await historical_revision(db, finalized)
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=revision.workspace_id,
                meeting_id=revision.meeting_id,
                media_revision_id=revision.id,
                workflow_id=f"processing/{revision.id}",
                status=ProcessingStatus.PROCESSED,
            )
            job = MediaScribeJob(
                workspace_id=revision.workspace_id,
                meeting_id=revision.meeting_id,
                media_revision_id=revision.id,
                processing_workflow_id=workflow.id,
                request_mode="dual_track",
                status="ready",
                external_job_id="retained-job",
                request_fingerprint="f" * 64,
                idempotency_key="retained-migration-key",
            )
            db.add(job)
            await db.commit()
            job_id = job.id
        async with client.app_state["engine"].begin() as connection:

            def upgrade(sync_connection):
                with Operations.context(MigrationContext.configure(sync_connection)):
                    migration.downgrade()
                    migration.upgrade()
                columns = inspect(sync_connection).get_columns("mediascribe_jobs")
                default = next(
                    column["default"] for column in columns if column["name"] == "request_mode"
                )
                assert "single_track" in default

            await connection.run_sync(upgrade)
        async with client.app_state["sessionmaker"]() as db:
            job = await db.get(MediaScribeJob, job_id)
            assert job.request_mode == "dual_track"
            assert job.external_job_id == "retained-job"
            assert job.request_fingerprint == "f" * 64
            assert job.idempotency_key == "retained-migration-key"

    asyncio.run(run())
