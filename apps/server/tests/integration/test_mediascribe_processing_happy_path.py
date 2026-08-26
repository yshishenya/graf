import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_mediascribe import FakeMediaScribeClient
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.artifacts import deterministic_wav_bytes
from tests.fixtures.processing import create_finalized_meeting, create_finalized_mixed_recording
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaScribeJob,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    ProcessingAuditEvent,
    ProcessingDependencyState,
    ProcessingResult,
    ProcessingWorkflow,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
)
from twobrain_rec_server.mediascribe.schemas import (
    MediaScribeDiarizationSegment,
    MediaScribeResult,
    MediaScribeSegment,
    MediaScribeWordItem,
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
            transcript_status=ProcessingAvailabilityStatus.AVAILABLE,
            transcript=[
                MediaScribeSegment(
                    sequence=0, start_seconds=0, end_seconds=1, text="hello", source_role="mic"
                )
            ],
            diarization=[
                MediaScribeDiarizationSegment(
                    sequence=0,
                    start_seconds=0,
                    end_seconds=1,
                    text="hello",
                    source_role="incoming",
                    speaker_label="REMOTE_00",
                    words=[MediaScribeWordItem(word="hello", start=0, end=1)],
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
            persisted = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert (
                persisted is not None
                and persisted.source_result_hash is not None
                and fake_client.result is not None
            )
            persisted.status = ProcessingResultStatus.PARTIAL.value
            await store.persist_processing_result(
                db,
                job=submitted.job,
                result=fake_client.result,
                source_result_hash=persisted.source_result_hash,
            )
            transcripts = (
                await db.scalars(
                    select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
                )
            ).all()
            diarization = (
                await db.scalars(
                    select(DiarizationSegment).where(DiarizationSegment.meeting_id == meeting_id)
                )
            ).all()
            assert diarization[0].words_json == [{"word": "hello", "start": 0.0, "end": 1.0}]
            return imported.status.value, len(transcripts), len(diarization)

    status, transcript_count, diarization_count = asyncio.run(run_pipeline())
    assert status == "processed"
    assert transcript_count == 1
    assert diarization_count == 1


def test_pending_provider_status_reaches_ready_without_resubmission(client) -> None:
    finalized = create_finalized_meeting(client, "processing-pending-to-ready")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(
        external_job_id="job_pending_to_ready",
        status_sequence=[MediaScribeJobStatus.TRANSCRIBING, MediaScribeJobStatus.READY],
        result=MediaScribeResult(
            external_job_id="job_pending_to_ready",
            transcript_status=ProcessingAvailabilityStatus.AVAILABLE,
            transcript=[
                MediaScribeSegment(
                    sequence=0, start_seconds=0, end_seconds=1, text="hello", source_role="mic"
                )
            ],
            diarization=[
                MediaScribeDiarizationSegment(
                    sequence=0,
                    start_seconds=0,
                    end_seconds=1,
                    text="hello",
                    source_role="mic",
                    speaker_label="SPEAKER_00",
                )
            ],
        ),
    )

    async def run_pipeline() -> tuple[str, str, int, int]:
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
            pending = await poll_and_import_mediascribe_result(
                db=db,
                workflow=workflow,
                job=submitted.job,
                mediascribe_client=fake_client,
            )
            ready = await poll_and_import_mediascribe_result(
                db=db,
                workflow=workflow,
                job=submitted.job,
                mediascribe_client=fake_client,
            )
            return (
                pending.status.value,
                ready.status.value,
                len(fake_client.submissions),
                fake_client.poll_count,
            )

    assert asyncio.run(run_pipeline()) == ("polling", "processed", 1, 2)


def test_import_diagnostics_match_persisted_millisecond_rounding(client) -> None:
    finalized = create_finalized_meeting(client, "processing-rounding-boundary")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(
        external_job_id="job_rounding_boundary",
        status_sequence=[MediaScribeJobStatus.READY],
        result=MediaScribeResult(
            external_job_id="job_rounding_boundary",
            transcript_status=ProcessingAvailabilityStatus.AVAILABLE,
            transcript=[
                MediaScribeSegment(
                    sequence=0,
                    start_seconds=0,
                    end_seconds=0.0504,
                    text="synthetic",
                    source_role="mixed",
                )
            ],
            diarization=[
                MediaScribeDiarizationSegment(
                    sequence=0,
                    start_seconds=0,
                    end_seconds=0.0504,
                    text="synthetic",
                    source_role="mixed",
                    speaker_label="UNKNOWN",
                )
            ],
        ),
    )

    async def run_pipeline() -> tuple[str, str, float, dict[str, object]]:
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
            await poll_and_import_mediascribe_result(
                db=db,
                workflow=workflow,
                job=submitted.job,
                mediascribe_client=fake_client,
            )
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            unknown = await db.scalar(
                select(DiarizationSegment).where(
                    DiarizationSegment.meeting_id == meeting_id,
                    DiarizationSegment.speaker_label == "UNKNOWN",
                )
            )
            audit = await db.scalar(
                select(ProcessingAuditEvent).where(
                    ProcessingAuditEvent.meeting_id == meeting_id,
                    ProcessingAuditEvent.event_type == "result_imported",
                )
            )
            assert result is not None and unknown is not None and audit is not None
            return (
                result.failure_reason or "",
                result.failure_source or "",
                float(unknown.end_seconds),
                audit.metadata_json,
            )

    failure_reason, failure_source, end_seconds, metadata = asyncio.run(run_pipeline())

    assert failure_reason == "degraded_provider_result"
    assert failure_source == "mediascribe"
    assert end_seconds == 0.05
    assert metadata["unknown_tiny_count"] == 1
    assert metadata["attribution_result_state"] == "degraded_provider_result"
    review = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())
    assert review.status_code == 200
    assert review.json()["transcript"]["result_state"] == "degraded_provider_result"
    assert review.json()["speakers"]["result_state"] == "degraded_provider_result"


def test_v5_mixed_recording_submits_one_canonical_wav_and_imports_one_result(client) -> None:
    finalized = create_finalized_mixed_recording(client, "processing-v5-single-wav")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    media_digest = next(
        track["sha256"] for track in finalized["tracks"] if track["track_role"] == "media"
    )
    media_size = next(
        track["byte_length"] for track in finalized["tracks"] if track["track_role"] == "media"
    )
    fake_client = FakeMediaScribeClient(
        external_job_id="job_v5_single_wav",
        status_sequence=[MediaScribeJobStatus.READY],
        result=MediaScribeResult(
            external_job_id="job_v5_single_wav",
            transcript_status=ProcessingAvailabilityStatus.AVAILABLE,
            transcript=[
                MediaScribeSegment(
                    sequence=0,
                    start_seconds=0,
                    end_seconds=1,
                    text="synthetic_segment_0",
                    source_role="mixed",
                )
            ],
            diarization=[
                MediaScribeDiarizationSegment(
                    sequence=0,
                    start_seconds=0,
                    end_seconds=1,
                    text="synthetic_segment_0",
                    source_role="mixed",
                    speaker_label="SPEAKER_00",
                )
            ],
        ),
    )

    async def run_pipeline() -> tuple[str, str, bool, bool, int, int]:
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
            job = await db.scalar(
                select(MediaScribeJob).where(MediaScribeJob.id == submitted.job.id)
            )
            jobs = (
                await db.scalars(
                    select(MediaScribeJob).where(MediaScribeJob.meeting_id == meeting_id)
                )
            ).all()
            transcript_rows = (
                await db.scalars(
                    select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
                )
            ).all()
            assert job is not None
            return (
                imported.status.value,
                job.request_mode,
                job.source_track_artifact_id is not None,
                job.mic_track_artifact_id is None and job.incoming_track_artifact_id is None,
                len(transcript_rows),
                len(jobs),
            )

    assert asyncio.run(run_pipeline()) == ("processed", "single_track", True, True, 1, 1)
    assert len(fake_client.submissions) == 1
    submission = fake_client.submissions[0]
    expected_submission = {
        "request_mode": "single_track",
        "media_size": media_size,
        "media_sha256": media_digest,
        "media_content_type": "audio/wav",
        "media_filename": "meeting-transcription.wav",
        "diarize": True,
        "summarize": False,
    }
    assert {key: submission[key] for key in expected_submission} == expected_submission
    assert not {"mic_size", "incoming_size", "playback_size", "playback_filename"}.intersection(
        submission
    )

    review = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())
    assert review.status_code == 200
    review_payload = review.json()
    assert review_payload["meeting"]["status"] == "ready"
    assert review_payload["provenance"]["media_revision_id"] == str(media_revision_id)
    assert review_payload["provenance"]["source_roles"] == ["canonical_mixed"]
    assert review_payload["transcript"]["available"] is True
    assert len(review_payload["transcript"]["segments"]) == 1
    assert review_payload["speakers"]["available"] is True


def test_normal_recording_and_manual_upload_share_canonical_speaker_projection(client) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    normal = create_finalized_mixed_recording(client, "canonical-parity-normal")
    manual_response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Canonical parity manual",
            "duration_seconds": "2",
            "local_recording_id": "canonical-parity-manual",
        },
        files={"file": ("synthetic.wav", deterministic_wav_bytes(128), "audio/wav")},
    )
    assert manual_response.status_code == 202
    manual = manual_response.json()

    sources = (
        (
            UUID(normal["meeting"]["workspace_id"]),
            UUID(normal["meeting"]["meeting_id"]),
            UUID(normal["meeting"]["media_revision"]["media_revision_id"]),
            "job_parity_normal",
        ),
        (
            UUID(manual["meeting"]["workspace_id"]),
            UUID(manual["meeting"]["meeting_id"]),
            UUID(manual["meeting"]["media_revision"]["media_revision_id"]),
            "job_parity_manual",
        ),
    )

    async def import_same_result(
        workspace_id: UUID,
        meeting_id: UUID,
        media_revision_id: UUID,
        job_id: str,
    ) -> None:
        fake_client = FakeMediaScribeClient(
            external_job_id=job_id,
            status_sequence=[MediaScribeJobStatus.READY],
            result=MediaScribeResult(
                external_job_id=job_id,
                transcript_status=ProcessingAvailabilityStatus.AVAILABLE,
                transcript=[
                    MediaScribeSegment(
                        sequence=0,
                        start_seconds=0,
                        end_seconds=1,
                        text="alpha beta",
                        source_role="mixed",
                    )
                ],
                diarization=[
                    MediaScribeDiarizationSegment(
                        sequence=0,
                        start_seconds=0,
                        end_seconds=0.5,
                        text="alpha",
                        source_role="mixed",
                        speaker_label="voice-a",
                    ),
                    MediaScribeDiarizationSegment(
                        sequence=1,
                        start_seconds=0.5,
                        end_seconds=1,
                        text="beta",
                        source_role="mixed",
                        speaker_label="voice-b",
                    ),
                ],
            ),
        )
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.get_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            if workflow is None:
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
            await poll_and_import_mediascribe_result(
                db=db,
                workflow=workflow,
                job=submitted.job,
                mediascribe_client=fake_client,
            )

    for source in sources:
        asyncio.run(import_same_result(*source))

    reviews = [
        client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers()).json()
        for _workspace_id, meeting_id, _revision_id, _job_id in sources
    ]

    def projection(
        review: dict[str, object],
    ) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
        turns = review["transcript"]["speaker_turns"]
        speakers = review["speakers"]["speakers"]
        return (
            [
                (
                    turn["start_seconds"],
                    turn["end_seconds"],
                    turn["text"],
                    turn["provider_speaker_key"],
                    turn["speaker_label"],
                    turn["attribution_state"],
                    turn["result_state"],
                    turn["source_role"],
                )
                for turn in turns
            ],
            [
                (
                    speaker["provider_speaker_key"],
                    speaker["label"],
                    speaker["confirmed"],
                    speaker["segments"],
                )
                for speaker in speakers
            ],
        )

    assert projection(reviews[0]) == projection(reviews[1])


def test_processing_e2e_submits_uploaded_track_hashes_and_persists_result_rows(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "processing-e2e-proof")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    expected_hashes = {
        str(track["track_role"]): str(track["sha256"]) for track in finalized["tracks"]
    }
    fake_client = FakeMediaScribeClient(
        external_job_id="job_e2e",
        status_sequence=[MediaScribeJobStatus.READY],
        result=MediaScribeResult(
            external_job_id="job_e2e",
            language="en",
            transcript_status=ProcessingAvailabilityStatus.AVAILABLE,
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
                media_revision_id=media_revision_id,
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
            persisted_workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            persisted_job = await db.scalar(
                select(MediaScribeJob).where(MediaScribeJob.meeting_id == meeting_id)
            )
            persisted_result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            transcripts = (
                await db.scalars(
                    select(TranscriptSegment)
                    .where(TranscriptSegment.meeting_id == meeting_id)
                    .order_by(TranscriptSegment.sequence)
                )
            ).all()
            diarization = (
                await db.scalars(
                    select(DiarizationSegment)
                    .where(DiarizationSegment.meeting_id == meeting_id)
                    .order_by(DiarizationSegment.sequence)
                )
            ).all()
            dependency = await db.scalar(
                select(ProcessingDependencyState).where(
                    ProcessingDependencyState.meeting_id == meeting_id
                )
            )
            return {
                "import_status": imported.status.value,
                "workflow_status": persisted_workflow.status,
                "job_status": persisted_job.status,
                "job_external_id": persisted_job.external_job_id,
                "job_ready_at": persisted_job.ready_at is not None,
                "result_status": persisted_result.status,
                "result_language": persisted_result.language,
                "result_transcript_status": persisted_result.transcript_status,
                "result_summary_status": persisted_result.summary_status,
                "result_segment_count": persisted_result.segment_count,
                "result_diarization_segment_count": persisted_result.diarization_segment_count,
                "result_hash_recorded": bool(persisted_result.source_result_hash),
                "transcript_rows": [
                    (
                        row.sequence,
                        float(row.start_seconds),
                        float(row.end_seconds),
                        row.text,
                        row.source_role,
                        row.source_role_original,
                    )
                    for row in transcripts
                ],
                "diarization_rows": [
                    (
                        row.sequence,
                        float(row.start_seconds),
                        float(row.end_seconds),
                        row.text,
                        row.source_role,
                        row.speaker_label,
                    )
                    for row in diarization
                ],
                "dependency": (
                    dependency.dependency,
                    dependency.state,
                    dependency.external_reference,
                ),
            }

    persisted = asyncio.run(run_pipeline())

    expected_submission = {
        "mic_size": 16,
        "incoming_size": 24,
        "mic_sha256": expected_hashes["microphone"],
        "incoming_sha256": expected_hashes["system"],
        "diarize": True,
        "summarize": False,
    }
    assert len(fake_client.submissions) == 1
    assert {
        key: fake_client.submissions[0][key] for key in expected_submission
    } == expected_submission
    assert persisted == {
        "import_status": "processed",
        "workflow_status": "processed",
        "job_status": "ready",
        "job_external_id": "job_e2e",
        "job_ready_at": True,
        "result_status": "imported",
        "result_language": "en",
        "result_transcript_status": "available",
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

    review = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())
    assert review.status_code == 200
    review_payload = review.json()
    assert review_payload["meeting"]["status"] == "ready"
    assert review_payload["provenance"]["media_revision_id"] == str(media_revision_id)
    assert review_payload["processing"]["state"] == "ready"
    assert review_payload["processing"]["transcript_available"] is True
    assert review_payload["processing"]["diarization_available"] is True
    assert review_payload["transcript"]["available"] is True
    assert review_payload["speakers"]["available"] is True


def test_ready_unavailable_no_speech_imports_processed_no_transcript_business_outcome(
    client,
) -> None:
    finalized = create_finalized_meeting(client, "processing-no-recognizable-speech")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    fake_client = FakeMediaScribeClient(
        external_job_id="job_no_speech",
        status_sequence=[MediaScribeJobStatus.READY],
        result=MediaScribeResult(
            external_job_id="job_no_speech",
            transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE,
            transcript_reason="no_recognizable_speech",
            transcript=[],
        ),
    )

    async def run_pipeline() -> dict[str, object]:
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
            persisted_workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
            )
            persisted_result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            outcome_set = await db.scalar(
                select(MeetingOutcomeSet).where(MeetingOutcomeSet.meeting_id == meeting_id)
            )
            attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.meeting_id == meeting_id
                )
            )
            audit = await db.scalar(
                select(ProcessingAuditEvent).where(ProcessingAuditEvent.meeting_id == meeting_id)
            )
            transcripts = (
                await db.scalars(
                    select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
                )
            ).all()
            return {
                "import_status": imported.status.value,
                "workflow_status": persisted_workflow.status,
                "workflow_reason": persisted_workflow.last_reason_code,
                "result_transcript_status": persisted_result.transcript_status,
                "result_segment_count": persisted_result.segment_count,
                "result_failure_reason": persisted_result.failure_reason,
                "result_failure_source": persisted_result.failure_source,
                "outcome_status": outcome_set.status,
                "outcome_failure_reason": outcome_set.failure_reason,
                "outcome_failure_source": outcome_set.failure_source,
                "attempt_status": attempt.status,
                "attempt_failure_reason": attempt.failure_reason,
                "attempt_failure_source": attempt.failure_source,
                "audit_event_type": audit.event_type,
                "audit_metadata": audit.metadata_json,
                "transcript_rows": len(transcripts),
            }

    persisted = asyncio.run(run_pipeline())

    assert persisted == {
        "import_status": "processed",
        "workflow_status": "processed",
        "workflow_reason": "no_recognizable_speech",
        "result_transcript_status": "unavailable",
        "result_segment_count": 0,
        "result_failure_reason": "no_recognizable_speech",
        "result_failure_source": "input_audio",
        "outcome_status": "blocked",
        "outcome_failure_reason": "no_recognizable_speech",
        "outcome_failure_source": "input_audio",
        "attempt_status": "blocked",
        "attempt_failure_reason": "no_recognizable_speech",
        "attempt_failure_source": "input_audio",
        "audit_event_type": "processed_no_transcript",
        "audit_metadata": {
            "mediascribe_job_id": persisted["audit_metadata"]["mediascribe_job_id"],
            "transcript_status": "unavailable",
            "transcript_reason": "no_recognizable_speech",
            "failure_reason": "no_recognizable_speech",
            "failure_source": "input_audio",
            "diagnostic_class": "processed_no_transcript",
            "segment_count": 0,
        },
        "transcript_rows": 0,
    }
