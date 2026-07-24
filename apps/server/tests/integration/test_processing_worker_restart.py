import asyncio
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fixtures.processing import create_finalized_meeting, create_finalized_mixed_recording
from twobrain_rec_server.db.models import MediaScribeJob, ProcessingWorkflow
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClientError
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import submit_to_mediascribe


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
            return len(first_client.submissions), len(second_client.submissions), resumed.submitted, persisted.status

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
            return first_client.submission_count, len(restarted_client.submissions), resumed.job.external_job_id

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
