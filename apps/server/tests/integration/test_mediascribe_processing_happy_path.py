import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import DiarizationSegment, TranscriptSegment
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingStatus
from twobrain_rec_server.mediascribe.schemas import (
    MediaScribeDiarizationSegment,
    MediaScribeResult,
    MediaScribeSegment,
)
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import (
    poll_and_import_mediascribe_result,
    submit_to_mediascribe,
)


def test_processing_happy_path_imports_transcript_and_diarization(client) -> None:
    finalized = create_finalized_meeting(client, "processing-happy-path")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(
        external_job_id="job_happy",
        status_sequence=[MediaScribeJobStatus.READY],
        result=MediaScribeResult(
            external_job_id="job_happy",
            transcript=[MediaScribeSegment(sequence=0, start_seconds=0, end_seconds=1, text="hello", source_role="mic")],
            diarization=[
                MediaScribeDiarizationSegment(
                    sequence=0,
                    start_seconds=0,
                    end_seconds=1,
                    text="hello",
                    source_role="incoming",
                    speaker_label="REMOTE_00",
                )
            ],
        ),
    )

    async def run_pipeline() -> tuple[str, int, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                workflow_id=f"processing/{meeting_id}",
                status=ProcessingStatus.WORKFLOW_STARTED,
            )
            submitted = await submit_to_mediascribe(
                db=db,
                settings=client.app.state.settings,
                storage=client.app_state["storage"],
                mediascribe_client=fake_client,
                workflow=workflow,
            )
            imported = await poll_and_import_mediascribe_result(
                db=db,
                workflow=workflow,
                job=submitted.job,
                mediascribe_client=fake_client,
            )
            transcripts = (await db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id))).all()
            diarization = (await db.scalars(select(DiarizationSegment).where(DiarizationSegment.meeting_id == meeting_id))).all()
            return imported.status.value, len(transcripts), len(diarization)

    status, transcript_count, diarization_count = asyncio.run(run_pipeline())
    assert status == "processed"
    assert transcript_count == 1
    assert diarization_count == 1
