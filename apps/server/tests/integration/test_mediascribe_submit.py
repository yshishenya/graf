import asyncio
from uuid import UUID

import pytest

from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.reasons import BLOCKED_AUDIO_TOO_LARGE
from twobrain_rec_server.processing.submit import submit_to_mediascribe


def test_submit_persists_external_job_id_before_retry_continues(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "mediascribe-submit")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_submit")

    async def submit_twice() -> tuple[str | None, int, bool]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
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


def test_submit_blocks_large_track_pair_before_loading_audio_bytes(client) -> None:
    finalized = create_finalized_meeting(client, "mediascribe-large-track-pair")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    fake_client = FakeMediaScribeClient(external_job_id="job_should_not_submit")
    original_limit = client.app.state.settings.processing_max_in_memory_audio_bytes
    client.app.state.settings.processing_max_in_memory_audio_bytes = 1

    class NonReadingStorage:
        def get_bytes(self, _object_key: str) -> bytes:
            raise AssertionError("processing must block before loading audio bytes")

    async def submit_large_pair() -> tuple[str, str | None, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=UUID(finalized["meeting"]["workspace_id"]),
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            with pytest.raises(RuntimeError, match=BLOCKED_AUDIO_TOO_LARGE):
                await submit_to_mediascribe(
                    db=db,
                    settings=client.app.state.settings,
                    storage=NonReadingStorage(),
                    mediascribe_client=fake_client,
                    workflow=workflow,
                )
            return workflow.status, workflow.last_reason_code, len(fake_client.submissions)

    try:
        status, reason_code, submission_count = asyncio.run(submit_large_pair())
    finally:
        client.app.state.settings.processing_max_in_memory_audio_bytes = original_limit

    assert status == ProcessingStatus.BLOCKED.value
    assert reason_code == BLOCKED_AUDIO_TOO_LARGE
    assert submission_count == 0
