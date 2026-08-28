import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select
from temporalio import activity

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import tenant_scope
from tests.fixtures.processing import create_finalized_meeting, create_finalized_mixed_recording
from twobrain_rec_server.cabinet.queries import _latest_workflow
from twobrain_rec_server.db.models import (
    MediaRevision,
    MediaScribeJob,
    Meeting,
    ProcessingAuditEvent,
    ProcessingResult,
    ProcessingWorkflow,
    UsageReservation,
)
from twobrain_rec_server.deletion.service import reconcile_transient_media_purges
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingStatus
from twobrain_rec_server.ingest.desktop_sync import _latest_processing_workflow
from twobrain_rec_server.mediascribe.client import MediaScribeClientError
from twobrain_rec_server.mediascribe.import_results import MediaScribeResultValidationError
from twobrain_rec_server.mediascribe.schemas import MediaScribePollResponse, MediaScribeResult
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.status import get_content_safe_processing_status
from twobrain_rec_server.processing.submit import (
    _ensure_processing_fence,
    poll_and_import_mediascribe_result,
    submit_to_mediascribe,
)
from twobrain_rec_server.workflows import worker


class FailingMediaScribeClient:
    def __init__(self, reason_code: str, retryable: bool) -> None:
        self.reason_code = reason_code
        self.retryable = retryable

    async def submit_dual_track(self, **_kwargs):
        raise MediaScribeClientError(self.reason_code, retryable=self.retryable)


class MalformedResultMediaScribeClient:
    async def poll_job(self, external_job_id: str):
        from twobrain_rec_server.domain.statuses import MediaScribeJobStatus
        from twobrain_rec_server.mediascribe.schemas import MediaScribePollResponse

        return MediaScribePollResponse(external_job_id=external_job_id, status=MediaScribeJobStatus.READY)

    async def fetch_result(self, _external_job_id: str):
        raise MediaScribeResultValidationError("invalid_transcript_timing")


class FailedPollMediaScribeClient:
    def __init__(self, *, error_code: str, error_origin: str | None) -> None:
        self.error_code = error_code
        self.error_origin = error_origin

    async def poll_job(self, external_job_id: str):
        return MediaScribePollResponse(
            external_job_id=external_job_id,
            status=MediaScribeJobStatus.FAILED,
            reason_code=self.error_code,
            error_code=self.error_code,
            error_origin=self.error_origin,
        )


class RetryableV5SubmitClient:
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        self.submission_count = 0
        self.idempotency_keys: list[str | None] = []

    async def submit_single_track(self, **kwargs):
        self.submission_count += 1
        self.idempotency_keys.append(kwargs.get("idempotency_key"))
        raise MediaScribeClientError(self.reason_code, retryable=True)


def test_processing_failure_matrix_marks_auth_terminal_and_timeout_retryable(client) -> None:
    terminal = _run_submit_failure(client, "failure-auth", "mediascribe_auth_failed", retryable=False)
    retryable = _run_submit_failure(client, "failure-timeout", "mediascribe_timeout", retryable=True)
    assert terminal == ("failed_terminal", "mediascribe_auth_failed")
    assert retryable == ("failed_retryable", "mediascribe_timeout")


def test_v5_timeout_retries_same_job_intent(client) -> None:
    finalized = create_finalized_mixed_recording(client, "failure-v5-ambiguous-submit")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    mediascribe_client = RetryableV5SubmitClient("mediascribe_timeout")

    async def run() -> tuple[int, str, str | None, str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            for _ in range(2):
                with pytest.raises(MediaScribeClientError) as exc:
                    await submit_to_mediascribe(
                        db=db,
                        settings=client.app.state.settings,
                        storage=client.app_state["storage"],
                        mediascribe_client=mediascribe_client,
                        workflow=workflow,
                    )
                assert exc.value.reason_code == "mediascribe_timeout"
                assert exc.value.retryable
            persisted_workflow = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.id == workflow.id))
            persisted_job = await db.scalar(select(MediaScribeJob).where(MediaScribeJob.meeting_id == meeting_id))
            assert persisted_workflow is not None
            assert persisted_job is not None
            return (
                mediascribe_client.submission_count,
                persisted_workflow.status,
                persisted_workflow.last_reason_code,
                persisted_job.status,
                persisted_job.last_error_code,
            )

    assert asyncio.run(run()) == (
        2,
        "failed_retryable",
        "mediascribe_timeout",
        "not_submitted",
        "mediascribe_timeout",
    )
    assert mediascribe_client.idempotency_keys[0] == mediascribe_client.idempotency_keys[1]


def test_waiting_retry_reuses_existing_job_and_reaches_poll_boundary(client) -> None:
    finalized = create_finalized_meeting(client, "failure-waiting-retry-existing-job")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> tuple[str, str, bool]:
        async with client.app_state["sessionmaker"]() as db:
            workflow, job = await _submitted_job(db, workspace_id, meeting_id, media_revision_id)
            workflow.status = ProcessingStatus.WAITING_RETRY.value
            workflow.retry_class = "retryable"
            await db.commit()

            recovered = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=object(),
                workflow=workflow,
            )
            return workflow.status, recovered.job.status, recovered.submitted

    assert asyncio.run(run()) == (
        ProcessingStatus.SUBMITTED.value,
        MediaScribeJobStatus.UPLOADED.value,
        False,
    )


def test_unknown_outcome_manual_claim_release_keeps_same_job_recovery_available(client) -> None:
    finalized = create_finalized_meeting(client, "failure-unknown-manual-dispatch")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> tuple[str, str, str, int, str]:
        async with client.app_state["sessionmaker"]() as db:
            workflow, job = await _submitted_job(db, workspace_id, meeting_id, media_revision_id)
            workflow.status = ProcessingStatus.BLOCKED_UNKNOWN.value
            workflow.retry_class = "unknown_outcome"
            workflow.last_reason_code = "blocked_mediascribe_submission_outcome_unknown"
            job.status = MediaScribeJobStatus.BLOCKED.value
            job.last_error_code = "blocked_mediascribe_submission_outcome_unknown"
            await db.commit()

            claim = await store.claim_processing_manual_check(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            assert claim.request_result == "accepted"
            assert claim.workflow is not None
            command_version = int(claim.workflow.manual_command_version or 0)
            await db.commit()
            assert await store.release_processing_manual_check_claim(
                db,
                workflow_id=claim.workflow.id,
                manual_command_version=command_version,
            )

            status = await get_content_safe_processing_status(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            assert status is not None
            return status.state.value, status.manual_action, status.retry_class

    assert asyncio.run(run()) == ("blocked_unknown", "check_now", "unknown_outcome")


def test_temporal_dispatch_failure_allows_a_fresh_attempt_after_recovery(client) -> None:
    finalized = create_finalized_meeting(client, "failure-temporal-dispatch")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> tuple[str, str, int | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.STARTING,
            )
            assert await store.fail_processing_attempt_dispatch(db, workflow_id=workflow.id)
            failed = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.id == workflow.id))
            assert failed is not None
            creation = await store.create_processing_attempt(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            return failed.status, creation.result, creation.attempt_ordinal

    assert asyncio.run(run()) == ("failed_terminal", "created", 2)


def test_starting_attempt_persists_terminal_provider_failure(client) -> None:
    finalized = create_finalized_meeting(client, "failure-starting-terminal")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> tuple[str, str]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.STARTING,
            )
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.FAILED_TERMINAL,
                reason_code="mediascribe_auth_failed",
                terminal=True,
            )
            failed = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.id == workflow.id))
            assert failed is not None
            return failed.status, failed.last_reason_code or ""

    assert asyncio.run(run()) == ("failed_terminal", "mediascribe_auth_failed")


@pytest.mark.parametrize(
    ("failure_reason", "failure_source"),
    [
        ("no_recognizable_speech", None),
        ("invalid_audio_payload", "input_audio"),
    ],
)
@pytest.mark.parametrize("workflow_status", [ProcessingStatus.PROCESSED, ProcessingStatus.POLLING])
def test_imported_terminal_input_result_allows_a_fresh_attempt(
    client,
    failure_reason: str,
    failure_source: str | None,
    workflow_status: ProcessingStatus,
) -> None:
    finalized = create_finalized_meeting(client, f"failure-{failure_reason}-new-attempt")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> tuple[str, int, str, bool, str, bool, bool]:
        async with client.app_state["sessionmaker"]() as db:
            workflow, job = await _submitted_job(db, workspace_id, meeting_id, media_revision_id)
            workflow.status = workflow_status.value
            workflow.last_reason_code = failure_reason
            job.status = MediaScribeJobStatus.READY.value
            result = ProcessingResult(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                mediascribe_job_id=job.id,
                processing_workflow_id=workflow.id,
                result_version=1,
                status="imported",
                transcript_status="unavailable",
                diarization_status="unavailable",
                summary_status="not_requested",
                segment_count=0,
                diarization_segment_count=0,
                failure_reason=failure_reason,
                failure_source=failure_source,
            )
            db.add(result)
            await db.commit()

            creation = await store.create_processing_attempt(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            assert creation.workflow is not None
            timestamp = datetime.now(UTC)
            workflow.updated_at = timestamp + timedelta(minutes=1)
            creation.workflow.updated_at = timestamp
            await db.flush()
            cabinet_workflow = await _latest_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            desktop_workflow = await _latest_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            old_result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.id == result.id)
            )
            return (
                creation.result,
                creation.attempt_ordinal or 0,
                old_result.failure_reason if old_result is not None else "missing",
                old_result.processing_workflow_id == workflow.id if old_result is not None else "missing",
                workflow.status,
                cabinet_workflow.id == creation.workflow.id if cabinet_workflow is not None else False,
                desktop_workflow.id == creation.workflow.id if desktop_workflow is not None else False,
            )

    previous_status = (
        ProcessingStatus.FAILED_TERMINAL.value
        if workflow_status == ProcessingStatus.POLLING
        else ProcessingStatus.PROCESSED.value
    )
    assert asyncio.run(run()) == (
        "created",
        2,
        failure_reason,
        True,
        previous_status,
        True,
        True,
    )


def test_stale_terminal_completion_cannot_regress_a_replacement_attempt(client) -> None:
    finalized = create_finalized_meeting(client, "failure-stale-terminal-completion")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> tuple[str, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            old_workflow, job = await _submitted_job(
                db,
                workspace_id,
                meeting_id,
                media_revision_id,
            )
            old_workflow.status = ProcessingStatus.POLLING.value
            job.status = MediaScribeJobStatus.READY.value
            db.add(
                ProcessingResult(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    mediascribe_job_id=job.id,
                    processing_workflow_id=old_workflow.id,
                    result_version=1,
                    status="imported",
                    transcript_status="unavailable",
                    diarization_status="unavailable",
                    summary_status="not_requested",
                    segment_count=0,
                    diarization_segment_count=0,
                    failure_reason="invalid_audio_payload",
                    failure_source="input_audio",
                    source_result_hash="terminal-input-result",
                )
            )
            await db.commit()

            creation = await store.create_processing_attempt(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            assert creation.workflow is not None
            replacement_id = creation.workflow.id
            await db.commit()

            class SupersededPollClient:
                poll_calls = 0

                async def poll_job(self, _external_job_id: str):
                    self.poll_calls += 1
                    raise AssertionError("superseded workflow must not poll MediaScribe")

            poll_client = SupersededPollClient()
            stale_poll = await poll_and_import_mediascribe_result(
                db=db,
                workflow=old_workflow,
                job=job,
                mediascribe_client=poll_client,
            )
            assert stale_poll.status == ProcessingStatus.CANCELED
            with pytest.raises(store.ProcessingLifecycleBlocked, match="processing_workflow_superseded"):
                await store.persist_processing_result(
                    db,
                    job=job,
                    result=MediaScribeResult(external_job_id=job.external_job_id or "missing"),
                    source_result_hash="superseded-result",
                )

            await store.set_workflow_status(
                db,
                old_workflow,
                ProcessingStatus.FAILED_TERMINAL,
                reason_code="invalid_audio_payload",
                terminal=True,
            )
            replacement = await db.get(ProcessingWorkflow, replacement_id)
            meeting = await db.get(Meeting, meeting_id)
            reservation = await db.scalar(
                select(UsageReservation).where(
                    UsageReservation.workspace_id == workspace_id,
                    UsageReservation.idempotency_key == f"processing:{media_revision_id}",
                )
            )
            assert replacement is not None
            assert meeting is not None
            assert reservation is not None
            result_count = len(
                (
                    await db.scalars(
                        select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
                    )
                ).all()
            )
            return (
                replacement.status,
                meeting.processing_status,
                reservation.state,
                poll_client.poll_calls,
                f"{result_count}:{stale_poll.status.value}",
            )

    assert asyncio.run(run()) == ("starting", "starting", "active", 0, "1:canceled")


def test_desktop_sync_projects_persisted_processed_terminal_input_as_failed(client) -> None:
    local_recording_id = "failure-desktop-sync-terminal-input"
    finalized = create_finalized_meeting(client, local_recording_id)
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow, job = await _submitted_job(db, workspace_id, meeting_id, media_revision_id)
            workflow.status = ProcessingStatus.PROCESSED.value
            job.status = MediaScribeJobStatus.READY.value
            db.add(
                ProcessingResult(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    mediascribe_job_id=job.id,
                    processing_workflow_id=workflow.id,
                    result_version=1,
                    status="imported",
                    transcript_status="unavailable",
                    diarization_status="unavailable",
                    summary_status="not_requested",
                    segment_count=0,
                    diarization_segment_count=0,
                    failure_reason="invalid_audio_payload",
                    failure_source="input_audio",
                    source_result_hash="desktop-terminal-input-result",
                )
            )
            await db.commit()

    asyncio.run(seed())
    response = client.get(
        f"/api/v1/desktop/recordings/{local_recording_id}/sync-state",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["processing"] == {
        "status": "failed_terminal",
        "workflow_id": f"processing/{media_revision_id}",
        "reason_code": "invalid_audio_payload",
    }
    assert body["meeting"]["processing_status"] == "failed_terminal"
    assert body["review"]["status"] == "failed"
    assert body["conflict"]["state"] == "processing_failed"
    idempotent_create = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": local_recording_id, "duration_seconds": 60},
    )
    assert idempotent_create.status_code == 200
    assert idempotent_create.json()["processing_status"] == "failed_terminal"


def test_desktop_sync_hides_a_previous_attempt_result_while_replacement_is_active(client) -> None:
    local_recording_id = "failure-desktop-sync-stale-ready-result"
    finalized = create_finalized_meeting(client, local_recording_id)
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            old_workflow, job = await _submitted_job(
                db,
                workspace_id,
                meeting_id,
                media_revision_id,
            )
            old_workflow.status = ProcessingStatus.PROCESSED.value
            job.status = MediaScribeJobStatus.READY.value
            db.add(
                ProcessingResult(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    mediascribe_job_id=job.id,
                    processing_workflow_id=old_workflow.id,
                    result_version=1,
                    status="imported",
                    transcript_status="available",
                    diarization_status="available",
                    summary_status="not_requested",
                    segment_count=1,
                    diarization_segment_count=1,
                )
            )
            replacement = ProcessingWorkflow(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}/attempt-2",
                purpose="transcription",
                status=ProcessingStatus.STARTING.value,
                attempt_ordinal=2,
            )
            db.add(replacement)
            await db.commit()

    asyncio.run(seed())
    response = client.get(
        f"/api/v1/desktop/recordings/{local_recording_id}/sync-state",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["processing"]["status"] == "starting"
    assert body["meeting"]["processing_status"] == "starting"
    assert body["review"]["status"] == "processing"
    assert body["review"]["transcript_available"] is False
    assert body["review"]["diarization_available"] is False
    assert body["review"]["content_available"] is False


def test_replacement_no_archive_attempt_owns_transient_media_purge(client, monkeypatch) -> None:
    finalized = create_finalized_meeting(
        client,
        "failure-no-archive-replacement-purge",
        archive_audio=False,
    )
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    source_keys = set(client.app_state["storage"].objects)

    async def run() -> tuple[bool, int, bool, int, bool]:
        async with client.app_state["sessionmaker"]() as db:
            workflow, job = await _submitted_job(
                db,
                workspace_id,
                meeting_id,
                media_revision_id,
                archive_audio=False,
            )
            workflow.status = ProcessingStatus.POLLING.value
            job.status = MediaScribeJobStatus.READY.value
            db.add(
                ProcessingResult(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    mediascribe_job_id=job.id,
                    processing_workflow_id=workflow.id,
                    result_version=1,
                    status="imported",
                    transcript_status="unavailable",
                    diarization_status="unavailable",
                    summary_status="not_requested",
                    segment_count=0,
                    diarization_segment_count=0,
                    failure_reason="invalid_audio_payload",
                    failure_source="input_audio",
                )
            )
            await db.commit()

            workflow.transient_hard_deadline = datetime.now(UTC)
            await db.commit()
            expired_creation = await store.create_processing_attempt(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            assert expired_creation.result == "source_expired"
            workflow.transient_hard_deadline = datetime.now(UTC) + timedelta(hours=1)
            await db.commit()

            reserve_quota = store._reserve_processing_attempt_quota

            async def expire_while_reserving(*args, **kwargs) -> bool:
                admitted = await reserve_quota(*args, **kwargs)
                workflow.transient_hard_deadline = datetime.now(UTC)
                return admitted

            monkeypatch.setattr(store, "_reserve_processing_attempt_quota", expire_while_reserving)
            raced_creation = await store.create_processing_attempt(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            assert raced_creation.result == "source_expired"
            raced_reservation = await db.scalar(
                select(UsageReservation).where(
                    UsageReservation.workspace_id == workspace_id,
                    UsageReservation.idempotency_key == f"processing:{media_revision_id}",
                )
            )
            assert raced_reservation is not None
            assert raced_reservation.state == "released"
            monkeypatch.setattr(store, "_reserve_processing_attempt_quota", reserve_quota)
            workflow.transient_hard_deadline = datetime.now(UTC) + timedelta(hours=1)
            await db.commit()

            creation = await store.create_processing_attempt(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            assert creation.workflow is not None
            assert workflow.transient_purge_due_at is not None
            hard_deadline_preserved = (
                creation.workflow.transient_hard_deadline == workflow.transient_hard_deadline
            )
            stale_deadline = workflow.transient_purge_due_at
            await db.commit()

            purged_while_replacement_active = await reconcile_transient_media_purges(
                db,
                storage=client.app_state["storage"],
                now=stale_deadline,
            )
            source_survived = source_keys <= set(client.app_state["storage"].objects)

            assert await store.fail_processing_attempt_dispatch(
                db,
                workflow_id=creation.workflow.id,
            )
            assert creation.workflow.transient_purge_due_at is not None
            purged_after_latest_terminal = await reconcile_transient_media_purges(
                db,
                storage=client.app_state["storage"],
                now=creation.workflow.transient_purge_due_at,
            )
            source_purged = source_keys.isdisjoint(client.app_state["storage"].objects)
            return (
                hard_deadline_preserved,
                purged_while_replacement_active,
                source_survived,
                purged_after_latest_terminal,
                source_purged,
            )

    assert asyncio.run(run()) == (True, 0, True, 1, True)


def test_no_archive_hard_deadline_terminalizes_active_attempt_before_purge(client) -> None:
    finalized = create_finalized_meeting(
        client,
        "failure-no-archive-active-hard-deadline",
        archive_audio=False,
    )
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    source_keys = set(client.app_state["storage"].objects)

    async def run() -> tuple[int, str, str, bool]:
        async with client.app_state["sessionmaker"]() as db:
            workflow, _job = await _submitted_job(
                db,
                workspace_id,
                meeting_id,
                media_revision_id,
                archive_audio=False,
            )
            deadline = datetime.now(UTC)
            workflow.transient_hard_deadline = deadline
            await db.commit()
            purged = await reconcile_transient_media_purges(
                db,
                storage=client.app_state["storage"],
                now=deadline,
            )
            await db.refresh(workflow)
            with pytest.raises(
                store.ProcessingLifecycleBlocked,
                match="processing_workflow_terminal",
            ):
                await _ensure_processing_fence(db, workflow)
            return (
                purged,
                workflow.status,
                workflow.last_reason_code or "",
                source_keys.isdisjoint(client.app_state["storage"].objects),
            )

    assert asyncio.run(run()) == (1, "failed_terminal", "audio_purged", True)


def test_worker_activity_persists_blocked_config_when_mediascribe_is_unconfigured(client, monkeypatch) -> None:
    finalized = create_finalized_meeting(client, "failure-worker-config")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    monkeypatch.setattr(worker, "get_settings", lambda: client.app.state.settings)
    monkeypatch.setattr(activity, "heartbeat", lambda *_args, **_kwargs: None)

    async def run() -> tuple[dict[str, str], str, str | None, bool]:
        async with client.app_state["sessionmaker"]() as db:
            await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            await db.commit()
        scope = tenant_scope()
        result = await worker.run_processing_pipeline_activity(
            {
                "meeting_id": str(meeting_id),
                "workspace_id": str(workspace_id),
                "organization_id": str(scope.organization_id),
                "user_id": str(scope.user_id),
                "device_id": str(scope.device_id),
                "media_revision_id": str(media_revision_id),
            }
        )
        async with client.app_state["sessionmaker"]() as db:
            persisted = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id))
            return result, persisted.status, persisted.last_reason_code, persisted.ended_at is not None

    assert asyncio.run(run()) == (
        {"meeting_id": str(meeting_id), "processing_status": "blocked"},
        "blocked",
        "blocked_config",
        True,
    )


def test_legacy_worker_callback_cannot_select_newer_revision_workflow(client, monkeypatch) -> None:
    finalized = create_finalized_meeting(client, "failure-stale-legacy-callback")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    monkeypatch.setattr(worker, "get_settings", lambda: client.app.state.settings)
    monkeypatch.setattr(worker.MediaScribeClient, "from_settings", lambda _settings: object())
    monkeypatch.setattr(activity, "heartbeat", lambda *_args, **_kwargs: None)

    async def run() -> tuple[dict[str, str], str]:
        async with client.app_state["sessionmaker"]() as db:
            await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            db.add(
                MediaRevision(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    local_media_revision_id="failure-stale-legacy-callback--new",
                    revision_number=2,
                    source_kind="reprocess",
                    status="accepted",
                    manifest_sha256="a" * 64,
                    track_sha256_by_role={},
                    duration_seconds=60,
                    immutable=True,
                )
            )
            await db.commit()
        scope = tenant_scope()
        result = await worker.run_processing_pipeline_activity(
            {
                "meeting_id": str(meeting_id),
                "workspace_id": str(workspace_id),
                "organization_id": str(scope.organization_id),
                "user_id": str(scope.user_id),
                "device_id": str(scope.device_id),
            }
        )
        async with client.app_state["sessionmaker"]() as db:
            persisted = await db.scalar(
                select(ProcessingWorkflow).where(
                    ProcessingWorkflow.media_revision_id == media_revision_id
                )
            )
            assert persisted is not None
            return result, persisted.status

    assert asyncio.run(run()) == (
        {
            "meeting_id": str(meeting_id),
            "processing_status": ProcessingStatus.CANCELED.value,
            "reason_code": "processing_source_revision_stale",
        },
        ProcessingStatus.CANCELED.value,
    )


def test_unmarked_null_lineage_is_terminalized_when_new_revision_is_accepted(client, monkeypatch) -> None:
    finalized = create_finalized_meeting(client, "failure-stale-unmarked-null-lineage")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    monkeypatch.setattr(worker, "get_settings", lambda: client.app.state.settings)
    monkeypatch.setattr(worker.MediaScribeClient, "from_settings", lambda _settings: object())
    monkeypatch.setattr(activity, "heartbeat", lambda *_args, **_kwargs: None)

    async def run() -> tuple[dict[str, str], str]:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                ProcessingWorkflow(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=None,
                    source_fingerprint=f"meeting:{meeting_id}",
                    workflow_id=f"processing/legacy-unmarked/{meeting_id}",
                    status=ProcessingStatus.WORKFLOW_STARTED.value,
                )
            )
            db.add(
                MediaRevision(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    local_media_revision_id="failure-stale-unmarked-null-lineage--new",
                    revision_number=2,
                    source_kind="reprocess",
                    status="accepted",
                    manifest_sha256="d" * 64,
                    track_sha256_by_role={"media": "e" * 64},
                    duration_seconds=60,
                    immutable=True,
                )
            )
            await db.commit()
        scope = tenant_scope()
        result = await worker.run_processing_pipeline_activity(
            {
                "meeting_id": str(meeting_id),
                "workspace_id": str(workspace_id),
                "organization_id": str(scope.organization_id),
                "user_id": str(scope.user_id),
                "device_id": str(scope.device_id),
            }
        )
        async with client.app_state["sessionmaker"]() as db:
            persisted = await db.scalar(
                select(ProcessingWorkflow).where(
                    ProcessingWorkflow.workflow_id == f"processing/legacy-unmarked/{meeting_id}"
                )
            )
            assert persisted is not None
            return result, persisted.status

    assert asyncio.run(run()) == (
        {
            "meeting_id": str(meeting_id),
            "processing_status": ProcessingStatus.CANCELED.value,
            "reason_code": "processing_source_revision_stale",
        },
        ProcessingStatus.CANCELED.value,
    )


def test_result_import_validation_error_is_persisted_as_terminal_safe_reason(client) -> None:
    finalized = create_finalized_meeting(client, "failure-malformed-result")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> tuple[ProcessingStatus, str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.SUBMITTED,
            )
            job = await store.upsert_mediascribe_job(
                db,
                workflow=workflow,
                mic_artifact=await _track_artifact(db, workspace_id, meeting_id, "microphone"),
                incoming_artifact=await _track_artifact(db, workspace_id, meeting_id, "system"),
            )
            await store.persist_mediascribe_submission(
                db,
                job=job,
                external_job_id="job_malformed_result",
                status=MediaScribeJobStatus.UPLOADED,
            )
            result = await poll_and_import_mediascribe_result(
                db=db,
                workflow=workflow,
                job=job,
                mediascribe_client=MalformedResultMediaScribeClient(),
            )
            persisted = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.id == workflow.id))
            return result.status, persisted.status, persisted.last_reason_code

    assert asyncio.run(run()) == (
        ProcessingStatus.FAILED_TERMINAL,
        "failed_terminal",
        "mediascribe_malformed_response",
    )


def test_failed_job_invalid_audio_payload_is_input_audio_business_outcome(client) -> None:
    finalized = create_finalized_meeting(client, "failure-invalid-audio-payload")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            workflow, job = await _submitted_job(db, workspace_id, meeting_id, media_revision_id)
            result = await poll_and_import_mediascribe_result(
                db=db,
                workflow=workflow,
                job=job,
                mediascribe_client=FailedPollMediaScribeClient(
                    error_code="invalid_audio_payload",
                    error_origin="input_audio",
                ),
            )
            persisted_workflow = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.id == workflow.id))
            persisted_job = await db.scalar(select(MediaScribeJob).where(MediaScribeJob.id == job.id))
            persisted_result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            audit = await db.scalar(select(ProcessingAuditEvent).where(ProcessingAuditEvent.meeting_id == meeting_id))
            return {
                "import_status": result.status.value,
                "workflow_status": persisted_workflow.status,
                "workflow_reason": persisted_workflow.last_reason_code,
                "job_status": persisted_job.status,
                "job_error_code": persisted_job.last_error_code,
                "result_transcript_status": persisted_result.transcript_status,
                "result_failure_reason": persisted_result.failure_reason,
                "result_failure_source": persisted_result.failure_source,
                "audit_event_type": audit.event_type,
                "audit_metadata": audit.metadata_json,
            }

    persisted = asyncio.run(run())

    assert persisted == {
        "import_status": "failed_terminal",
        "workflow_status": "failed_terminal",
        "workflow_reason": "invalid_audio_payload",
        "job_status": "failed",
        "job_error_code": "invalid_audio_payload",
        "result_transcript_status": "unavailable",
        "result_failure_reason": "invalid_audio_payload",
        "result_failure_source": "input_audio",
        "audit_event_type": "input_audio_problem",
        "audit_metadata": {
            "mediascribe_job_id": persisted["audit_metadata"]["mediascribe_job_id"],
            "error_code": "invalid_audio_payload",
            "error_origin": "input_audio",
            "failure_reason": "invalid_audio_payload",
            "failure_source": "input_audio",
            "diagnostic_class": "input_audio_problem",
            "transcript_status": "unavailable",
        },
    }


def test_failed_job_missing_origin_remains_mediascribe_service_failure(client) -> None:
    finalized = create_finalized_meeting(client, "failure-mediascribe-origin")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            workflow, job = await _submitted_job(db, workspace_id, meeting_id, media_revision_id)
            result = await poll_and_import_mediascribe_result(
                db=db,
                workflow=workflow,
                job=job,
                mediascribe_client=FailedPollMediaScribeClient(
                    error_code="worker_failed",
                    error_origin=None,
                ),
            )
            persisted = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.id == workflow.id))
            processing_result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            audit = await db.scalar(select(ProcessingAuditEvent).where(ProcessingAuditEvent.meeting_id == meeting_id))
            return {
                "import_status": result.status.value,
                "workflow_status": persisted.status,
                "workflow_reason": persisted.last_reason_code,
                "processing_result_present": processing_result is not None,
                "audit_event_type": audit.event_type,
                "audit_metadata": audit.metadata_json,
            }

    persisted = asyncio.run(run())

    assert persisted == {
        "import_status": "failed_terminal",
        "workflow_status": "failed_terminal",
        "workflow_reason": "worker_failed",
        "processing_result_present": False,
        "audit_event_type": "mediascribe_service_problem",
        "audit_metadata": {
            "mediascribe_job_id": persisted["audit_metadata"]["mediascribe_job_id"],
            "error_code": "worker_failed",
            "failure_reason": "worker_failed",
            "failure_source": "mediascribe",
            "diagnostic_class": "mediascribe_service_problem",
        },
    }


def _run_submit_failure(client, local_recording_id: str, reason_code: str, *, retryable: bool) -> tuple[str, str | None]:
    finalized = create_finalized_meeting(client, local_recording_id)
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> tuple[str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            with suppress(MediaScribeClientError):
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=client.app_state["storage"],
                    mediascribe_client=FailingMediaScribeClient(reason_code, retryable),
                    workflow=workflow,
                )
            persisted = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.id == workflow.id))
            return persisted.status, persisted.last_reason_code

    return asyncio.run(run())


async def _track_artifact(db, workspace_id: UUID, meeting_id: UUID, track_role: str):
    from twobrain_rec_server.db.models import TrackArtifact

    artifact = await db.scalar(
        select(TrackArtifact).where(
            TrackArtifact.workspace_id == workspace_id,
            TrackArtifact.meeting_id == meeting_id,
            TrackArtifact.track_role == track_role,
        )
    )
    assert artifact is not None
    return artifact


async def _submitted_job(
    db,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID,
    *,
    archive_audio: bool = True,
):
    workflow = await store.upsert_processing_workflow(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        workflow_id=f"processing/{media_revision_id}",
        status=ProcessingStatus.SUBMITTED,
        archive_audio=archive_audio,
    )
    job = await store.upsert_mediascribe_job(
        db,
        workflow=workflow,
        mic_artifact=await _track_artifact(db, workspace_id, meeting_id, "microphone"),
        incoming_artifact=await _track_artifact(db, workspace_id, meeting_id, "system"),
    )
    await store.persist_mediascribe_submission(
        db,
        job=job,
        external_job_id=f"job_{meeting_id}",
        status=MediaScribeJobStatus.UPLOADED,
    )
    return workflow, job
