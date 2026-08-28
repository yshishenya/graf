from __future__ import annotations

from uuid import uuid4

from twobrain_rec_server.cabinet.view_models import (
    primary_action_for_status,
    processing_state,
)
from twobrain_rec_server.db.models import Meeting, ProcessingResult, ProcessingWorkflow
from twobrain_rec_server.domain.statuses import (
    MeetingStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
)


def _meeting(*, status: str, processing_status: str) -> Meeting:
    return Meeting(
        id=uuid4(),
        workspace_id=uuid4(),
        created_by_user_id=uuid4(),
        device_id=uuid4(),
        local_recording_id=f"synthetic-{status}-{processing_status}",
        status=status,
        processing_status=processing_status,
        duration_seconds=60,
    )


def _result(*, transcript: bool, diarization: bool) -> tuple[ProcessingResult, ProcessingWorkflow]:
    workflow_id = uuid4()
    result = ProcessingResult(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        mediascribe_job_id=uuid4(),
        processing_workflow_id=workflow_id,
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=(
            ProcessingAvailabilityStatus.AVAILABLE.value
            if transcript
            else ProcessingAvailabilityStatus.UNAVAILABLE.value
        ),
        diarization_status=(
            ProcessingAvailabilityStatus.AVAILABLE.value
            if diarization
            else ProcessingAvailabilityStatus.UNAVAILABLE.value
        ),
        summary_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        segment_count=1 if transcript else 0,
        diarization_segment_count=1 if diarization else 0,
    )
    workflow = ProcessingWorkflow(
        id=workflow_id,
        workspace_id=result.workspace_id,
        meeting_id=result.meeting_id,
        workflow_id=f"processing/{workflow_id}",
        status=ProcessingStatus.PROCESSED.value,
    )
    return result, workflow


def test_one_artifact_specific_lifecycle_projects_without_a_second_queue() -> None:
    cases = (
        (MeetingStatus.DRAFT.value, ProcessingStatus.NOT_SUBMITTED.value, None, "local_only", "open_desktop_queue"),
        (MeetingStatus.UPLOADING.value, ProcessingStatus.NOT_SUBMITTED.value, None, "uploading", "wait"),
        (MeetingStatus.INGESTED_PENDING_PROCESSING.value, ProcessingStatus.NOT_SUBMITTED.value, None, "submitted", "wait"),
        (MeetingStatus.INGESTED_PENDING_PROCESSING.value, ProcessingStatus.POLLING.value, None, "processing", "wait"),
        (MeetingStatus.INGESTED_PENDING_PROCESSING.value, ProcessingStatus.PROCESSED.value, _result(transcript=True, diarization=False), "partial", "none"),
        (MeetingStatus.INGESTED_PENDING_PROCESSING.value, ProcessingStatus.PROCESSED.value, _result(transcript=True, diarization=True), "ready", "none"),
        (MeetingStatus.FAILED.value, ProcessingStatus.FAILED_RETRYABLE.value, None, "failed", "contact_operator"),
    )

    for meeting_status, server_status, processing, expected_state, expected_action in cases:
        result, workflow = processing if processing is not None else (None, None)
        state = processing_state(
            _meeting(status=meeting_status, processing_status=server_status),
            result=result,
            workflow=workflow,
        )

        assert state.state == expected_state
        assert state.next_action == expected_action
        assert primary_action_for_status(state.state) in {
            "open",
            "wait",
            "open_status",
            "retry_future",
            "unavailable",
        }


def test_ready_partial_and_failed_are_artifact_independent_human_states() -> None:
    ready_meeting = _meeting(
        status=MeetingStatus.INGESTED_PENDING_PROCESSING.value,
        processing_status=ProcessingStatus.PROCESSED.value,
    )
    ready_result, ready_workflow = _result(transcript=True, diarization=True)
    ready = processing_state(
        ready_meeting,
        result=ready_result,
        workflow=ready_workflow,
    )
    partial_result, partial_workflow = _result(transcript=True, diarization=False)
    partial = processing_state(
        _meeting(
            status=MeetingStatus.INGESTED_PENDING_PROCESSING.value,
            processing_status=ProcessingStatus.PROCESSED.value,
        ),
        result=partial_result,
        workflow=partial_workflow,
    )
    failed = processing_state(
        _meeting(
            status=MeetingStatus.FAILED.value,
            processing_status=ProcessingStatus.FAILED_TERMINAL.value,
        ),
        result=None,
        workflow=None,
    )

    assert (ready.state, ready.content_available, ready.transcript_available) == (
        "ready",
        True,
        True,
    )
    assert ready_meeting.status == MeetingStatus.INGESTED_PENDING_PROCESSING.value
    assert (partial.state, partial.content_available, partial.transcript_available) == (
        "partial",
        False,
        False,
    )
    assert (failed.state, failed.content_available, failed.transcript_available) == (
        "failed",
        False,
        False,
    )
