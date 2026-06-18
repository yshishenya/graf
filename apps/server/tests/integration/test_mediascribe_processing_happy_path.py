import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaScribeJob,
    ProcessingDependencyState,
    ProcessingResult,
    ProcessingWorkflow,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingStatus,
    SummaryStatus,
)
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
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
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


def test_processing_e2e_submits_uploaded_track_hashes_and_persists_result_rows(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "processing-e2e-proof")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    expected_hashes = {str(track["track_role"]): str(track["sha256"]) for track in finalized["tracks"]}
    fake_client = FakeMediaScribeClient(
        external_job_id="job_e2e",
        status_sequence=[MediaScribeJobStatus.READY],
        result=MediaScribeResult(
            external_job_id="job_e2e",
            language="en",
            summary_status=SummaryStatus.AVAILABLE,
            transcript=[
                MediaScribeSegment(
                    sequence=0,
                    start_seconds=0.0,
                    end_seconds=1.25,
                    text="local speaker",
                    source_role="microphone",
                    source_role_original="microphone",
                ),
                MediaScribeSegment(
                    sequence=1,
                    start_seconds=1.25,
                    end_seconds=2.5,
                    text="remote speaker",
                    source_role="system",
                    source_role_original="system",
                ),
            ],
            diarization=[
                MediaScribeDiarizationSegment(
                    sequence=0,
                    start_seconds=0.0,
                    end_seconds=1.25,
                    text="local speaker",
                    source_role="mic",
                    speaker_label="LOCAL_MIC",
                ),
                MediaScribeDiarizationSegment(
                    sequence=1,
                    start_seconds=1.25,
                    end_seconds=2.5,
                    text="remote speaker",
                    source_role="incoming",
                    speaker_label="REMOTE_00",
                ),
            ],
        ),
    )
    pickup = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": str(meeting_id)},
    )
    assert pickup.status_code == 202
    assert pickup.json()["started_count"] == 1

    async def run_pipeline() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.get_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            assert workflow is not None
            assert workflow.status == ProcessingStatus.WORKFLOW_STARTED.value
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
            persisted_workflow = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id))
            persisted_job = await db.scalar(select(MediaScribeJob).where(MediaScribeJob.meeting_id == meeting_id))
            persisted_result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            transcripts = (
                await db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.sequence))
            ).all()
            diarization = (
                await db.scalars(
                    select(DiarizationSegment).where(DiarizationSegment.meeting_id == meeting_id).order_by(DiarizationSegment.sequence)
                )
            ).all()
            dependency = await db.scalar(select(ProcessingDependencyState).where(ProcessingDependencyState.meeting_id == meeting_id))
            return {
                "import_status": imported.status.value,
                "workflow_status": persisted_workflow.status,
                "job_status": persisted_job.status,
                "job_external_id": persisted_job.external_job_id,
                "job_ready_at": persisted_job.ready_at is not None,
                "result_status": persisted_result.status,
                "result_language": persisted_result.language,
                "result_summary_status": persisted_result.summary_status,
                "result_segment_count": persisted_result.segment_count,
                "result_diarization_segment_count": persisted_result.diarization_segment_count,
                "result_hash_recorded": bool(persisted_result.source_result_hash),
                "transcript_rows": [
                    (row.sequence, float(row.start_seconds), float(row.end_seconds), row.text, row.source_role, row.source_role_original)
                    for row in transcripts
                ],
                "diarization_rows": [
                    (row.sequence, float(row.start_seconds), float(row.end_seconds), row.text, row.source_role, row.speaker_label)
                    for row in diarization
                ],
                "dependency": (dependency.dependency, dependency.state, dependency.external_reference),
            }

    persisted = asyncio.run(run_pipeline())

    assert fake_client.submissions == [
        {
            "mic_size": 16,
            "incoming_size": 24,
            "mic_sha256": expected_hashes["microphone"],
            "incoming_sha256": expected_hashes["system"],
            "diarize": True,
            "summarize": False,
        }
    ]
    assert persisted == {
        "import_status": "processed",
        "workflow_status": "processed",
        "job_status": "ready",
        "job_external_id": "job_e2e",
        "job_ready_at": True,
        "result_status": "imported",
        "result_language": "en",
        "result_summary_status": "available",
        "result_segment_count": 2,
        "result_diarization_segment_count": 2,
        "result_hash_recorded": True,
        "transcript_rows": [
            (0, 0.0, 1.25, "local speaker", "mic", "microphone"),
            (1, 1.25, 2.5, "remote speaker", "incoming", "system"),
        ],
        "diarization_rows": [
            (0, 0.0, 1.25, "local speaker", "mic", "LOCAL_MIC"),
            (1, 1.25, 2.5, "remote speaker", "incoming", "REMOTE_00"),
        ],
        "dependency": ("mediascribe", "imported", "job_e2e"),
    }
