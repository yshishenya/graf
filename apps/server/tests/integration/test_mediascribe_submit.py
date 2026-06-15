import asyncio
from uuid import UUID

from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import submit_to_mediascribe


def test_submit_persists_external_job_id_before_retry_continues(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "mediascribe-submit")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_submit")

    async def submit_twice() -> tuple[str | None, int, bool]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                workflow_id=f"processing/{meeting_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            first = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            second = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            return first.job.external_job_id, len(fake_client.submissions), second.submitted

    external_job_id, submission_count, second_submitted = asyncio.run(submit_twice())
    assert external_job_id == "job_submit"
    assert submission_count == 1
    assert second_submitted is False
