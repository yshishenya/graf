import asyncio
from uuid import UUID

from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import submit_to_mediascribe


def test_worker_restart_resumes_from_persisted_mediascribe_job_without_resubmit(client) -> None:
    finalized = create_finalized_meeting(client, "worker-restart")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    first_client = FakeMediaScribeClient(external_job_id="job_restart")
    second_client = FakeMediaScribeClient(external_job_id="job_should_not_submit")

    async def run() -> tuple[int, int, bool]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                workflow_id=f"processing/{meeting_id}",
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
