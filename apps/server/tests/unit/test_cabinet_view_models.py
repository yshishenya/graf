from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from twobrain_rec_server.cabinet import view_models
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    Meeting,
    ProcessingResult,
    ProcessingWorkflow,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
)


def _meeting(processing_status: ProcessingStatus = ProcessingStatus.PROCESSED) -> Meeting:
    return Meeting(
        id=uuid4(),
        workspace_id=uuid4(),
        created_by_user_id=uuid4(),
        device_id=uuid4(),
        local_recording_id="local-id",
        title=None,
        started_at=datetime(2026, 6, 16, 8, 0, tzinfo=UTC),
        duration_seconds=60,
        status="ingested_pending_processing",
        processing_status=processing_status.value,
    )


def test_status_mapping_handles_ready_partial_processing_and_failed() -> None:
    ready = ProcessingResult(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        segment_count=1,
        diarization_segment_count=1,
    )
    partial = ProcessingResult(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        segment_count=1,
        diarization_segment_count=0,
    )

    assert view_models.review_status(_meeting(), result=ready, workflow=None) == "ready"
    assert view_models.review_status(_meeting(), result=partial, workflow=None) == "partial"
    assert view_models.review_status(_meeting(ProcessingStatus.POLLING), result=None, workflow=None) == "processing"
    assert view_models.review_status(_meeting(ProcessingStatus.FAILED_TERMINAL), result=None, workflow=None) == "failed"


def test_transcript_mapping_uses_timestamp_speaker_and_source_role_truth() -> None:
    meeting = _meeting()
    result_id = uuid4()
    transcript = [
        TranscriptSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("65.500"),
            end_seconds=Decimal("70.000"),
            text="hello",
            source_role="incoming",
        )
    ]
    diarization = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            sequence=0,
            start_seconds=Decimal("65.500"),
            end_seconds=Decimal("70.000"),
            text="hello",
            speaker_label="Speaker 2",
            source_role="incoming",
        )
    ]

    state = view_models.transcript_state(
        language="ru",
        transcript_segments=transcript,
        diarization_segments=diarization,
        status="ready",
    )

    assert state.available is True
    assert state.segments[0].timestamp_label == "01:05"
    assert state.segments[0].speaker_label == "Speaker 2"
    assert state.segments[0].source_role == "incoming_system"


def test_speaker_mapping_calculates_talk_time_percentages() -> None:
    result_id = uuid4()
    meeting_id = uuid4()
    workspace_id = uuid4()
    segments = [
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            sequence=0,
            start_seconds=Decimal("0"),
            end_seconds=Decimal("30"),
            text="one",
            speaker_label="Speaker 1",
            source_role="mic",
        ),
        DiarizationSegment(
            id=uuid4(),
            processing_result_id=result_id,
            meeting_id=meeting_id,
            workspace_id=workspace_id,
            sequence=1,
            start_seconds=Decimal("30"),
            end_seconds=Decimal("60"),
            text="two",
            speaker_label="Speaker 2",
            source_role="incoming",
        ),
    ]

    state = view_models.speaker_state(segments)

    assert state.available is True
    assert [(speaker.label, speaker.talk_time_percent) for speaker in state.speakers] == [
        ("Speaker 1", 50),
        ("Speaker 2", 50),
    ]


def test_governance_states_are_non_mutating_and_truthful() -> None:
    governance = view_models.governance_summary()

    assert governance.share.state == "planned"
    assert governance.export.state == "planned"
    assert governance.download.state == "planned"
    assert governance.retention.state == "planned"
    assert governance.delete.destructive is True
    assert "2brain Rec" in governance.delete.label


def test_processing_state_uses_safe_reason_and_next_action() -> None:
    meeting = _meeting(ProcessingStatus.FAILED_TERMINAL)
    workflow = ProcessingWorkflow(
        id=uuid4(),
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        workflow_id="private-workflow",
        status=ProcessingStatus.FAILED_TERMINAL.value,
        last_reason_code="mediascribe_validation_failed",
    )

    state = view_models.processing_state(meeting, result=None, workflow=workflow)

    assert state.state == "failed"
    assert state.reason_code == "mediascribe_validation_failed"
    assert state.next_action == "contact_operator"
    assert "private-workflow" not in state.model_dump_json()

