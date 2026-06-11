import asyncio
from contextlib import suppress
from uuid import UUID

from sqlalchemy import select
from temporalio import activity

from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import ProcessingWorkflow
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClientError
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import submit_to_mediascribe
from twobrain_rec_server.workflows import worker


class FailingMediaScribeClient:
    def __init__(self, reason_code: str, retryable: bool) -> None:
        self.reason_code = reason_code
        self.retryable = retryable

    async def submit_dual_track(self, **_kwargs):
        raise MediaScribeClientError(self.reason_code, retryable=self.retryable)


def test_processing_failure_matrix_marks_auth_terminal_and_timeout_retryable(client) -> None:
    terminal = _run_submit_failure(client, "failure-auth", "mediascribe_auth_failed", retryable=False)
    retryable = _run_submit_failure(client, "failure-timeout", "mediascribe_timeout", retryable=True)
    assert terminal == ("failed_terminal", "mediascribe_auth_failed")
    assert retryable == ("failed_retryable", "mediascribe_timeout")


def test_worker_activity_persists_blocked_config_when_mediascribe_is_unconfigured(client, monkeypatch) -> None:
    finalized = create_finalized_meeting(client, "failure-worker-config")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    monkeypatch.setattr(worker, "get_settings", lambda: client.app.state.settings)
    monkeypatch.setattr(activity, "heartbeat", lambda *_args, **_kwargs: None)

    async def run() -> tuple[dict[str, str], str, str | None, bool]:
        async with client.app_state["sessionmaker"]() as db:
            await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                workflow_id=f"processing/{meeting_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
        result = await worker.run_processing_pipeline_activity(
            {"meeting_id": str(meeting_id), "workspace_id": str(workspace_id)}
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


def _run_submit_failure(client, local_recording_id: str, reason_code: str, *, retryable: bool) -> tuple[str, str | None]:
    finalized = create_finalized_meeting(client, local_recording_id)
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def run() -> tuple[str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                workflow_id=f"processing/{meeting_id}",
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
