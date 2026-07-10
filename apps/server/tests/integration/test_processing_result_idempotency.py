import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import ProcessingResult, TranscriptSegment
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    ProcessingStatus,
)
from twobrain_rec_server.mediascribe.schemas import MediaScribeResult, MediaScribeSegment
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import (
    poll_and_import_mediascribe_result,
    submit_to_mediascribe,
)


def test_result_import_is_idempotent_for_same_normalized_result(client) -> None:
    finalized = create_finalized_meeting(client, "processing-idempotency")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    result = MediaScribeResult(
        external_job_id="job_idempotent",
        transcript=[MediaScribeSegment(sequence=0, start_seconds=0, end_seconds=1, text="hello", source_role="mic")],
    )
    fake_client = FakeMediaScribeClient(
        external_job_id="job_idempotent",
        status_sequence=[MediaScribeJobStatus.READY],
        result=result,
    )

    async def import_twice() -> int:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            submitted = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            await poll_and_import_mediascribe_result(db=db, workflow=workflow, job=submitted.job, mediascribe_client=fake_client)
            await poll_and_import_mediascribe_result(db=db, workflow=workflow, job=submitted.job, mediascribe_client=fake_client)
            return len((await db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id))).all())

    assert asyncio.run(import_twice()) == 1


def test_processing_result_persists_contract_transcript_status_without_rows(client) -> None:
    finalized = create_finalized_meeting(client, "processing-authoritative-status")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(
        external_job_id="job_authoritative_status",
        status_sequence=[MediaScribeJobStatus.READY],
        result=MediaScribeResult(
            external_job_id="job_authoritative_status",
            transcript_status=ProcessingAvailabilityStatus.AVAILABLE,
            transcript=[],
        ),
    )

    async def import_result() -> tuple[str, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            submitted = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            await poll_and_import_mediascribe_result(db=db, workflow=workflow, job=submitted.job, mediascribe_client=fake_client)
            persisted = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            return persisted.transcript_status, persisted.segment_count

    assert asyncio.run(import_result()) == ("available", 0)
