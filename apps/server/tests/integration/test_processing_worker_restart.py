import asyncio
from uuid import UUID

import pytest

from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fixtures.processing import create_finalized_meeting, create_finalized_mixed_recording
from twobrain_rec_server.domain.statuses import ProcessingStatus
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

    async def run() -> tuple[int, int, bool]:
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
            return len(first_client.submissions), len(second_client.submissions), resumed.submitted

    assert asyncio.run(run()) == (1, 0, False)


def test_worker_restart_never_resubmits_v5_after_unknown_submit_outcome(client) -> None:
    finalized = create_finalized_mixed_recording(client, "worker-restart-v5-unknown-submit")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    first_client = TimeoutAfterPostClient()
    restarted_client = FakeMediaScribeClient(external_job_id="job_must_not_be_created")

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
            assert first_error.value.reason_code == "blocked_mediascribe_submission_outcome_unknown"
            with pytest.raises(MediaScribeClientError) as restart_error:
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=client.app_state["storage"],
                    mediascribe_client=restarted_client,
                    workflow=workflow,
                )
            return first_client.submission_count, len(restarted_client.submissions), restart_error.value.reason_code

    assert asyncio.run(run()) == (1, 0, "blocked_mediascribe_submission_outcome_unknown")


class TimeoutAfterPostClient:
    def __init__(self) -> None:
        self.submission_count = 0

    async def submit_single_track(self, **_kwargs):
        self.submission_count += 1
        raise MediaScribeClientError("mediascribe_timeout", retryable=True)
