import asyncio
from contextlib import suppress
from uuid import UUID

from sqlalchemy import select
from temporalio import activity

from tests.fakes.auth_contexts import tenant_scope
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import (
    MediaScribeJob,
    ProcessingAuditEvent,
    ProcessingResult,
    ProcessingWorkflow,
)
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClientError
from twobrain_rec_server.mediascribe.import_results import MediaScribeResultValidationError
from twobrain_rec_server.mediascribe.schemas import MediaScribePollResponse
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import (
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


def test_processing_failure_matrix_marks_auth_terminal_and_timeout_retryable(client) -> None:
    terminal = _run_submit_failure(client, "failure-auth", "mediascribe_auth_failed", retryable=False)
    retryable = _run_submit_failure(client, "failure-timeout", "mediascribe_timeout", retryable=True)
    assert terminal == ("failed_terminal", "mediascribe_auth_failed")
    assert retryable == ("failed_retryable", "mediascribe_timeout")


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


def test_result_import_validation_error_is_persisted_as_retryable_safe_reason(client) -> None:
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
        ProcessingStatus.FAILED_RETRYABLE,
        "failed_retryable",
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
        "import_status": "processed",
        "workflow_status": "processed",
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


async def _submitted_job(db, workspace_id: UUID, meeting_id: UUID, media_revision_id: UUID):
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
        external_job_id=f"job_{meeting_id}",
        status=MediaScribeJobStatus.UPLOADED,
    )
    return workflow, job
