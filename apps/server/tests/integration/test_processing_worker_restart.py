import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import select
from temporalio.client import WorkflowExecutionStatus
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

import twobrain_rec_server.api.processing as processing_api
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting, create_finalized_mixed_recording
from twobrain_rec_server.db.models import (
    MediaRevision,
    MediaScribeJob,
    Meeting,
    ProcessingResult,
    ProcessingWorkflow,
    UploadSession,
)
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context,
)
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.mediascribe.client import MediaScribeClientError
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import submit_to_mediascribe
from twobrain_rec_server.workflows.worker import reconcile_stale_processing_starts


def test_closed_temporal_unknown_submission_reuses_same_job_key(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-unknown-submission")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def recover() -> tuple[str, str, str, str, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.get(MediaRevision, media_revision_id)
            assert revision is not None
            source_fingerprint = source_fingerprint_for_revision(revision)
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.BLOCKED_UNKNOWN,
                source_fingerprint=source_fingerprint,
            )
            job = MediaScribeJob(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                processing_workflow_id=workflow.id,
                idempotency_key=f"mediascribe:{workflow.id}:{source_fingerprint}",
                source_fingerprint=source_fingerprint,
                status=MediaScribeJobStatus.BLOCKED.value,
                last_error_code="blocked_mediascribe_submission_outcome_unknown",
            )
            db.add(job)
            await db.commit()
            original_key = job.idempotency_key or ""
            replacement = await store.prepare_closed_workflow_same_job_recovery(
                db,
                workflow=workflow,
            )
            assert replacement is not None
            await db.refresh(job)
            await db.refresh(workflow)
            return (
                original_key,
                job.idempotency_key or "",
                job.processing_workflow_id.hex,
                replacement.id.hex,
                workflow.status,
                replacement.stage,
            )

    (
        original_key,
        recovered_key,
        job_workflow_id,
        replacement_id,
        closed_status,
        replacement_stage,
    ) = asyncio.run(recover())
    assert recovered_key == original_key
    assert job_workflow_id == replacement_id
    assert closed_status == ProcessingStatus.CANCELED.value
    assert replacement_stage == "submit"


def test_closed_temporal_unknown_submission_with_provider_job_only_polls(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-known-provider-job")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_already_accepted")

    async def recover() -> tuple[str, str, bool, int]:
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.get(MediaRevision, media_revision_id)
            assert revision is not None
            source_fingerprint = source_fingerprint_for_revision(revision)
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.FAILED_RETRYABLE,
                source_fingerprint=source_fingerprint,
            )
            job = MediaScribeJob(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                processing_workflow_id=workflow.id,
                external_job_id=fake_client.external_job_id,
                idempotency_key=f"mediascribe:{workflow.id}:{source_fingerprint}",
                source_fingerprint=source_fingerprint,
                status=MediaScribeJobStatus.BLOCKED.value,
                last_error_code="blocked_mediascribe_submission_outcome_unknown",
            )
            db.add(job)
            await db.commit()
            replacement = await store.prepare_closed_workflow_same_job_recovery(
                db,
                workflow=workflow,
            )
            assert replacement is not None
            replacement = await store.set_workflow_status(
                db,
                replacement,
                ProcessingStatus.WORKFLOW_STARTED,
                reason_code="temporal_execution_closed_same_job_recovery",
            )
            submitted = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=fake_client,
                workflow=replacement,
            )
            return (
                replacement.stage,
                submitted.job.external_job_id or "",
                submitted.submitted,
                len(fake_client.submissions),
            )

    assert asyncio.run(recover()) == ("poll", fake_client.external_job_id, False, 0)


def test_terminal_watchdog_attempt_resumes_existing_provider_job(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-watchdog-provider-job")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def recover() -> tuple[str, str, bool]:
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.get(MediaRevision, media_revision_id)
            assert revision is not None
            source_fingerprint = source_fingerprint_for_revision(revision)
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.FAILED_TERMINAL,
                reason_code="processing_retry_deadline_exceeded",
                source_fingerprint=source_fingerprint,
            )
            workflow.retry_class = "terminal"
            job = MediaScribeJob(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                processing_workflow_id=workflow.id,
                external_job_id="job_watchdog_still_running",
                source_fingerprint=source_fingerprint,
                status=MediaScribeJobStatus.DIARIZING.value,
            )
            db.add(job)
            await db.commit()
            creation = await store.create_processing_attempt(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            assert creation.result == "created"
            assert creation.workflow is not None
            await db.refresh(job)
            return (
                creation.workflow.stage,
                job.external_job_id or "",
                job.processing_workflow_id == creation.workflow.id,
            )

    assert asyncio.run(recover()) == ("poll", "job_watchdog_still_running", True)


async def _seed_no_speech_retry(
    client,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID,
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        workflow = await store.upsert_processing_workflow(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            workflow_id=f"processing/{media_revision_id}",
            status=ProcessingStatus.PROCESSED,
        )
        job = MediaScribeJob(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            processing_workflow_id=workflow.id,
            external_job_id=f"job_retry_{meeting_id}",
            status=MediaScribeJobStatus.READY.value,
        )
        db.add(job)
        await db.flush()
        db.add(
            ProcessingResult(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                mediascribe_job_id=job.id,
                processing_workflow_id=workflow.id,
                result_version=1,
                status=ProcessingResultStatus.IMPORTED.value,
                transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
                diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
                summary_status=SummaryStatus.NOT_REQUESTED.value,
                segment_count=0,
                diarization_segment_count=0,
                failure_reason="no_recognizable_speech",
            )
        )
        await db.commit()


def test_processing_start_intent_is_committed_before_temporal_rpc(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-start-intent")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])

    class CommitObservingTemporalClient(FakeTemporalClient):
        status_seen: str | None = None
        options_seen: dict[str, object] | None = None

        async def start_workflow(self, workflow, payload, *, id, task_queue, **options):
            async with client.app_state["sessionmaker"]() as db:
                persisted = await db.scalar(
                    select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
                )
                assert persisted is not None
                self.status_seen = persisted.status
            self.options_seen = options
            return await super().start_workflow(
                workflow,
                payload,
                id=id,
                task_queue=task_queue,
                **options,
            )

    temporal = CommitObservingTemporalClient()
    client.app.state.temporal_client = temporal

    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": str(meeting_id)},
    )

    assert response.status_code == 202
    assert response.json()["started_count"] == 1
    assert temporal.status_seen == ProcessingStatus.WORKFLOW_STARTED.value
    assert temporal.options_seen is not None
    assert temporal.options_seen["id_reuse_policy"] is WorkflowIDReusePolicy.REJECT_DUPLICATE


def test_user_retry_commits_workflow_started_before_temporal_rpc(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-user-start-intent")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    asyncio.run(
        _seed_no_speech_retry(
            client,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )

    class CommitObservingTemporalClient(FakeTemporalClient):
        status_seen: str | None = None

        async def start_workflow(self, workflow, payload, *, id, task_queue, **options):
            async with client.app_state["sessionmaker"]() as db:
                persisted = await db.scalar(
                    select(ProcessingWorkflow).where(
                        ProcessingWorkflow.meeting_id == meeting_id,
                        ProcessingWorkflow.attempt_ordinal == 2,
                    )
                )
                assert persisted is not None
                self.status_seen = persisted.status
            return await super().start_workflow(
                workflow,
                payload,
                id=id,
                task_queue=task_queue,
                **options,
            )

    temporal = CommitObservingTemporalClient()
    client.app.state.temporal_client = temporal
    response = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/attempt",
        headers=auth_headers(),
    )

    assert response.status_code == 202
    assert response.json()["state"] == ProcessingStatus.WORKFLOW_STARTED.value
    assert temporal.status_seen == ProcessingStatus.WORKFLOW_STARTED.value


@pytest.mark.parametrize(
    ("failure_mode", "expected_status", "expected_http_status"),
    [
        ("ambiguous_start", ProcessingStatus.WORKFLOW_STARTED.value, 202),
        ("run_id_persistence", ProcessingStatus.WORKFLOW_STARTED.value, 202),
        ("definite_start", ProcessingStatus.FAILED_TERMINAL.value, 503),
    ],
)
def test_user_retry_preserves_only_ambiguous_temporal_starts(
    client,
    monkeypatch,
    failure_mode: str,
    expected_status: str,
    expected_http_status: int,
) -> None:
    finalized = create_finalized_meeting(client, f"worker-restart-user-{failure_mode}")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    asyncio.run(
        _seed_no_speech_retry(
            client,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )

    class StartFailureTemporalClient(FakeTemporalClient):
        async def start_workflow(self, *args, **kwargs):
            if failure_mode == "ambiguous_start":
                raise TimeoutError("start outcome unknown")
            if failure_mode == "definite_start":
                raise ValueError("request rejected before start")
            return await super().start_workflow(*args, **kwargs)

    if failure_mode == "run_id_persistence":

        async def fail_run_id_persistence(*_args, **_kwargs):
            raise RuntimeError("database write failed")

        monkeypatch.setattr(
            processing_api.store,
            "record_processing_attempt_run",
            fail_run_id_persistence,
        )
    client.app.state.temporal_client = StartFailureTemporalClient()

    response = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/attempt",
        headers=auth_headers(),
    )

    assert response.status_code == expected_http_status
    if expected_http_status == 202:
        body = response.json()
        assert body["attempt_result"] == "created"
        assert body["dispatch"] == ("started" if failure_mode == "run_id_persistence" else None)

    async def persisted_attempt() -> tuple[str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(
                    ProcessingWorkflow.meeting_id == meeting_id,
                    ProcessingWorkflow.attempt_ordinal == 2,
                )
            )
            assert workflow is not None
            return workflow.status, workflow.workflow_run_id

    assert asyncio.run(persisted_attempt()) == (expected_status, None)


def test_stale_starting_intent_is_reconciled_on_pickup(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-stale-starting")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed_stale_intent() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.STARTING,
            )
            workflow.updated_at = datetime.now(UTC) - timedelta(minutes=2)
            await db.commit()

    asyncio.run(seed_stale_intent())
    temporal = FakeTemporalClient()
    client.app.state.temporal_client = temporal

    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": str(meeting_id)},
    )

    assert response.status_code == 202
    assert response.json()["started_count"] == 1
    assert f"processing/{media_revision_id}" in temporal.starts


def test_stale_start_intent_is_reconciled_without_another_request(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-maintenance-start")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    stale_at = datetime.now(UTC) - timedelta(minutes=2)
    temporal = FakeTemporalClient()

    async def reconcile() -> int:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            workflow.updated_at = stale_at
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="processing_recovery_reconciliation",
                    actor_id="processing-recovery-test",
                    reason_category="durable_start_recovery",
                    feature_area="content_regeneration",
                ),
            )
            return await reconcile_stale_processing_starts(
                db,
                settings=client.app.state.settings,
                temporal_client=temporal,
                now=datetime.now(UTC),
                limit=1,
            )

    assert asyncio.run(reconcile()) == 1
    assert f"processing/{media_revision_id}" in temporal.starts


def test_deleted_missing_intent_does_not_starve_next_recovery(client) -> None:
    deleted = create_finalized_meeting(client, "worker-restart-deleted-missing-intent")
    recoverable = create_finalized_meeting(client, "worker-restart-next-missing-intent")
    deleted_meeting_id = UUID(deleted["meeting"]["meeting_id"])
    recoverable_meeting_id = UUID(recoverable["meeting"]["meeting_id"])
    recoverable_revision_id = UUID(recoverable["meeting"]["media_revision"]["media_revision_id"])
    client.app.state.settings.processing_enabled = True
    temporal = FakeTemporalClient()

    async def reconcile() -> int:
        async with client.app_state["sessionmaker"]() as db:
            sessions = list(
                await db.scalars(
                    select(UploadSession).where(
                        UploadSession.meeting_id.in_({deleted_meeting_id, recoverable_meeting_id})
                    )
                )
            )
            assert len(sessions) == 2
            for session in sessions:
                session.processing_status = ProcessingStatus.STARTING.value
                session.finalized_at = datetime.now(UTC) - timedelta(minutes=2)
            deleted_meeting = await db.scalar(
                select(Meeting).where(Meeting.id == deleted_meeting_id)
            )
            assert deleted_meeting is not None
            deleted_meeting.deleted_at = datetime.now(UTC)
            deleted_meeting.deletion_state = "deleting"
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="processing_recovery_reconciliation",
                    actor_id="processing-recovery-test",
                    reason_category="durable_start_recovery",
                    feature_area="content_regeneration",
                ),
            )
            return await reconcile_stale_processing_starts(
                db,
                settings=client.app.state.settings,
                temporal_client=temporal,
                now=datetime.now(UTC),
                limit=1,
            )

    assert asyncio.run(reconcile()) == 1
    assert set(temporal.starts) == {f"processing/{recoverable_revision_id}"}


def test_deletion_closes_committed_processing_start_intent(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-delete-start-intent")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])

    async def mark_starting() -> None:
        async with client.app_state["sessionmaker"]() as db:
            session = await db.scalar(
                select(UploadSession).where(UploadSession.meeting_id == meeting_id)
            )
            assert session is not None
            session.processing_status = ProcessingStatus.STARTING.value
            session.finalized_at = datetime.now(UTC) - timedelta(minutes=2)
            await db.commit()

    asyncio.run(mark_starting())
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": "Delete this meeting everywhere GRAF controls."},
    )
    assert response.status_code == 202

    async def processing_status() -> str:
        async with client.app_state["sessionmaker"]() as db:
            session = await db.scalar(
                select(UploadSession).where(UploadSession.meeting_id == meeting_id)
            )
            assert session is not None
            return session.processing_status

    assert asyncio.run(processing_status()) == ProcessingStatus.CANCELED.value


def test_accepted_meeting_without_workflow_is_reconciled_after_crash(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-missing-intent")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    client.app.state.settings.processing_enabled = True
    temporal = FakeTemporalClient()

    async def reconcile() -> int:
        async with client.app_state["sessionmaker"]() as db:
            session = await db.scalar(
                select(UploadSession).where(UploadSession.meeting_id == meeting_id)
            )
            assert session is not None
            session.processing_status = ProcessingStatus.STARTING.value
            session.finalized_at = datetime.now(UTC) - timedelta(minutes=2)
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="processing_recovery_reconciliation",
                    actor_id="processing-recovery-test",
                    reason_category="durable_start_recovery",
                    feature_area="content_regeneration",
                ),
            )
            return await reconcile_stale_processing_starts(
                db,
                settings=client.app.state.settings,
                temporal_client=temporal,
                now=datetime.now(UTC),
                limit=1,
            )

    assert asyncio.run(reconcile()) == 1
    assert f"processing/{media_revision_id}" in temporal.starts


def test_processing_disabled_upload_is_not_later_treated_as_crash_gap(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-processing-disabled")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    client.app.state.settings.processing_enabled = True
    temporal = FakeTemporalClient()

    async def reconcile() -> int:
        async with client.app_state["sessionmaker"]() as db:
            session = await db.scalar(
                select(UploadSession).where(UploadSession.meeting_id == meeting_id)
            )
            assert session is not None
            session.finalized_at = datetime.now(UTC) - timedelta(minutes=2)
            assert session.processing_status == ProcessingStatus.NOT_SUBMITTED.value
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="processing_recovery_reconciliation",
                    actor_id="processing-recovery-test",
                    reason_category="durable_start_recovery",
                    feature_area="content_regeneration",
                ),
            )
            return await reconcile_stale_processing_starts(
                db,
                settings=client.app.state.settings,
                temporal_client=temporal,
                now=datetime.now(UTC),
                limit=4,
            )

    assert asyncio.run(reconcile()) == 0
    assert temporal.starts == {}


def test_superseded_crash_intent_does_not_start_a_newer_disabled_revision(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-superseded-intent")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    client.app.state.settings.processing_enabled = True
    temporal = FakeTemporalClient()

    async def reconcile() -> tuple[int, str]:
        async with client.app_state["sessionmaker"]() as db:
            session = await db.scalar(
                select(UploadSession).where(UploadSession.meeting_id == meeting_id)
            )
            assert session is not None
            session.processing_status = ProcessingStatus.STARTING.value
            session.finalized_at = datetime.now(UTC) - timedelta(minutes=2)
            db.add(
                MediaRevision(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    local_media_revision_id="worker-restart-superseded-intent--new",
                    revision_number=2,
                    source_kind="reprocess",
                    status="accepted",
                    manifest_sha256="a" * 64,
                    track_sha256_by_role={"media": "b" * 64},
                    duration_seconds=60,
                    immutable=True,
                )
            )
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="processing_recovery_reconciliation",
                    actor_id="processing-recovery-test",
                    reason_category="durable_start_recovery",
                    feature_area="content_regeneration",
                ),
            )
            reconciled = await reconcile_stale_processing_starts(
                db,
                settings=client.app.state.settings,
                temporal_client=temporal,
                now=datetime.now(UTC),
                limit=1,
            )
            session = await db.scalar(
                select(UploadSession).where(UploadSession.meeting_id == meeting_id)
            )
            assert session is not None
            return reconciled, session.processing_status

    assert asyncio.run(reconcile()) == (1, ProcessingStatus.CANCELED.value)
    assert temporal.starts == {}


def test_closed_known_temporal_run_recovers_same_provider_job(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-closed-known-run")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    original_workflow_id = f"processing/{media_revision_id}"
    deadline = datetime.now(UTC) + timedelta(hours=2)

    class ClosedHandle:
        async def describe(self):
            return SimpleNamespace(status=WorkflowExecutionStatus.COMPLETED)

    class ClosedOriginalTemporal(FakeTemporalClient):
        async def start_workflow(self, *args, id, **kwargs):
            if id == original_workflow_id:
                raise WorkflowAlreadyStartedError(
                    id,
                    "MediaScribeProcessingWorkflow",
                    run_id="run-closed",
                )
            return await super().start_workflow(*args, id=id, **kwargs)

        def get_workflow_handle(self, workflow_id, *, run_id=None):
            assert workflow_id == original_workflow_id
            assert run_id == "run-closed"
            return ClosedHandle()

    async def reconcile() -> tuple[int, int, str | None, datetime | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=original_workflow_id,
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            workflow.workflow_run_id = "run-closed"
            workflow.status = ProcessingStatus.POLLING.value
            workflow.deadline_at = deadline
            workflow.updated_at = datetime.now(UTC) - timedelta(minutes=16)
            db.add(
                MediaScribeJob(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    processing_workflow_id=workflow.id,
                    idempotency_key=f"mediascribe:{workflow.id}:same-source",
                    source_fingerprint=workflow.source_fingerprint,
                    external_job_id="job_closed_known_run",
                    status=MediaScribeJobStatus.TRANSCRIBING.value,
                )
            )
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="processing_recovery_reconciliation",
                    actor_id="processing-recovery-test",
                    reason_category="durable_start_recovery",
                    feature_area="content_regeneration",
                ),
            )
            reconciled = await reconcile_stale_processing_starts(
                db,
                settings=client.app.state.settings,
                temporal_client=ClosedOriginalTemporal(),
                now=datetime.now(UTC),
                limit=2,
            )
            workflows = list(
                await db.scalars(
                    select(ProcessingWorkflow)
                    .where(ProcessingWorkflow.meeting_id == meeting_id)
                    .order_by(ProcessingWorkflow.attempt_ordinal)
                )
            )
            job = await db.scalar(
                select(MediaScribeJob).where(MediaScribeJob.meeting_id == meeting_id)
            )
            assert job is not None
            return reconciled, len(workflows), job.external_job_id, workflows[-1].deadline_at

    assert asyncio.run(reconcile()) == (1, 2, "job_closed_known_run", deadline)


def test_worker_restart_resumes_from_persisted_mediascribe_job_without_resubmit(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    first_client = FakeMediaScribeClient(external_job_id="job_restart")
    second_client = FakeMediaScribeClient(external_job_id="job_should_not_submit")

    async def run() -> tuple[int, int, bool, str]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=first_client,
                workflow=workflow,
            )
            resumed = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=second_client,
                workflow=workflow,
            )
            persisted = await store.get_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            assert persisted is not None
            return (
                len(first_client.submissions),
                len(second_client.submissions),
                resumed.submitted,
                persisted.status,
            )

    assert asyncio.run(run()) == (1, 0, False, ProcessingStatus.SUBMITTED.value)


def test_worker_restart_projects_external_job_before_polling(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-crash-after-post")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    restarted_client = FakeMediaScribeClient(external_job_id="job_after_crash")

    async def run() -> str:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            source = await store.load_processing_source(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            assert source is not None
            job = await store.upsert_mediascribe_job(
                db,
                workflow=workflow,
                mic_artifact=source.mic_artifact,
                incoming_artifact=source.incoming_artifact,
                source_artifact=source.source_artifact,
                request_mode=source.request_mode,
                source_fingerprint=workflow.source_fingerprint,
            )
            job.external_job_id = "job_after_crash"
            job.status = "submitted"
            await db.commit()
            resumed = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=restarted_client,
                workflow=workflow,
            )
            assert resumed.submitted is False
            persisted = await store.get_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            assert persisted is not None
            return persisted.status

    assert asyncio.run(run()) == ProcessingStatus.SUBMITTED.value


def test_worker_restart_retries_v5_timeout_with_same_idempotency_key(client) -> None:
    finalized = create_finalized_mixed_recording(client, "worker-restart-v5-unknown-submit")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    first_client = TimeoutAfterPostClient()
    restarted_client = FakeMediaScribeClient(external_job_id="job_after_retry")

    async def run() -> tuple[int, int, str]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            with pytest.raises(MediaScribeClientError) as first_error:
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=client.app_state["storage"],
                    mediascribe_client=first_client,
                    workflow=workflow,
                )
            assert first_error.value.reason_code == "mediascribe_timeout"
            resumed = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=restarted_client,
                workflow=workflow,
            )
            return (
                first_client.submission_count,
                len(restarted_client.submissions),
                resumed.job.external_job_id,
            )

    first_count, restart_count, external_job_id = asyncio.run(run())
    assert (first_count, restart_count, external_job_id) == (1, 1, "job_after_retry")
    assert first_client.idempotency_keys == [restarted_client.submissions[0]["idempotency_key"]]


def test_active_submission_claim_is_not_replayed_after_restart(client, monkeypatch) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-active-claim")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    restarted_client = FakeMediaScribeClient(external_job_id="job_must_not_be_created")
    monkeypatch.setattr(store, "MEDIASCRIBE_SUBMISSION_WAIT_SECONDS", 0.0)

    async def run() -> tuple[int, str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            source = await store.load_processing_source(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            assert source is not None
            job = await store.upsert_mediascribe_job(
                db,
                workflow=workflow,
                mic_artifact=source.mic_artifact,
                incoming_artifact=source.incoming_artifact,
                source_artifact=source.source_artifact,
                request_mode=source.request_mode,
                source_fingerprint=workflow.source_fingerprint,
            )
            assert await store.claim_mediascribe_submission(db, job=job)
            with pytest.raises(MediaScribeClientError) as raised:
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=client.app_state["storage"],
                    mediascribe_client=restarted_client,
                    workflow=workflow,
                )
            persisted = await store.get_mediascribe_job(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            assert persisted is not None
            return len(restarted_client.submissions), persisted.status, raised.value.reason_code

    assert asyncio.run(run()) == (
        0,
        "submitting",
        "mediascribe_submission_in_progress",
    )


def test_null_submission_claim_timestamp_is_treated_as_stale(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-null-claim")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> bool:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            source = await store.load_processing_source(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            assert source is not None
            job = await store.upsert_mediascribe_job(
                db,
                workflow=workflow,
                mic_artifact=source.mic_artifact,
                incoming_artifact=source.incoming_artifact,
                source_artifact=source.source_artifact,
                request_mode=source.request_mode,
                source_fingerprint=workflow.source_fingerprint,
            )
            job.status = MediaScribeJobStatus.SUBMITTING.value
            job.submission_claimed_at = None
            await db.commit()
            return await store.claim_mediascribe_submission(db, job=job) is not None

    assert asyncio.run(run())


def test_stale_mediascribe_poll_cannot_regress_ready_job(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart-stale-poll")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> str:
        async with client.app_state["sessionmaker"]() as first_db:
            workflow = await store.upsert_processing_workflow(
                first_db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            source = await store.load_processing_source(
                first_db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            assert source is not None
            job = await store.upsert_mediascribe_job(
                db=first_db,
                workflow=workflow,
                mic_artifact=source.mic_artifact,
                incoming_artifact=source.incoming_artifact,
                source_artifact=source.source_artifact,
                request_mode=source.request_mode,
                source_fingerprint=workflow.source_fingerprint,
            )
            job.external_job_id = "job-stale-poll"
            job.status = MediaScribeJobStatus.SUBMITTED.value
            await first_db.commit()
            stale_job = await first_db.scalar(
                select(MediaScribeJob).where(MediaScribeJob.id == job.id)
            )
            assert stale_job is not None
            async with client.app_state["sessionmaker"]() as second_db:
                current = await second_db.scalar(
                    select(MediaScribeJob).where(MediaScribeJob.id == job.id)
                )
                assert current is not None
                current.status = MediaScribeJobStatus.READY.value
                await second_db.commit()
            returned = await store.update_mediascribe_job_status(
                first_db,
                job=stale_job,
                status=MediaScribeJobStatus.TRANSCRIBING,
            )
            return returned.status

    assert asyncio.run(run()) == MediaScribeJobStatus.READY.value


def test_concurrent_job_upsert_reuses_one_deterministic_lineage_row(client) -> None:
    finalized = create_finalized_meeting(client, "worker-concurrent-job-upsert")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> tuple[UUID, UUID, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            workflow_id = workflow.id

        async def upsert_once():
            async with client.app_state["sessionmaker"]() as db:
                workflow = await db.get(ProcessingWorkflow, workflow_id)
                assert workflow is not None
                source = await store.load_processing_source(
                    db,
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                )
                assert source is not None
                return await store.upsert_mediascribe_job(
                    db,
                    workflow=workflow,
                    mic_artifact=source.mic_artifact,
                    incoming_artifact=source.incoming_artifact,
                    source_artifact=source.source_artifact,
                    request_mode=source.request_mode,
                    source_fingerprint=workflow.source_fingerprint,
                )

        first, second = await asyncio.gather(upsert_once(), upsert_once())
        return first.id, second.id, first.idempotency_key, second.idempotency_key

    first_id, second_id, first_key, second_key = asyncio.run(run())
    assert first_id == second_id
    assert first_key == second_key


def test_stale_worker_cannot_reopen_terminal_workflow(client) -> None:
    finalized = create_finalized_meeting(client, "worker-stale-terminal-status")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> str:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.BLOCKED,
                reason_code="test_terminal",
                terminal=True,
            )
            await store.set_workflow_status(db, workflow, ProcessingStatus.SUBMITTING)
            persisted = await store.get_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                source_fingerprint=workflow.source_fingerprint,
            )
            assert persisted is not None
            return persisted.status

    assert asyncio.run(run()) == "blocked"


class TimeoutAfterPostClient:
    def __init__(self) -> None:
        self.submission_count = 0
        self.idempotency_keys: list[str | None] = []

    async def submit_single_track(self, **kwargs):
        self.submission_count += 1
        self.idempotency_keys.append(kwargs.get("idempotency_key"))
        raise MediaScribeClientError("mediascribe_timeout", retryable=True)
