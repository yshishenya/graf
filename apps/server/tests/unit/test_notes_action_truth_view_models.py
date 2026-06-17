from __future__ import annotations

from uuid import uuid4

from twobrain_rec_server.cabinet import view_models
from twobrain_rec_server.db.models import ProcessingResult
from twobrain_rec_server.domain.statuses import (
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    SummaryStatus,
)


def _result(*, summary_status: SummaryStatus = SummaryStatus.NOT_REQUESTED) -> ProcessingResult:
    return ProcessingResult(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
        summary_status=summary_status.value,
        segment_count=2,
        diarization_segment_count=2,
    )


def test_ready_transcript_without_stored_outcomes_is_deferred_not_available() -> None:
    truth = view_models.notes_action_truth_state(status="ready", result=_result())

    assert truth.source_basis == "policy_deferral"
    assert truth.summary.state == "deferred"
    assert truth.decisions.state == "deferred"
    assert truth.action_items.state == "deferred"
    assert truth.followups.state == "deferred"
    assert truth.summary.readiness_impact == "keeps_gap_open"


def test_processing_outcomes_stay_processing_until_result_is_ready() -> None:
    truth = view_models.notes_action_truth_state(status="processing", result=None)

    assert truth.source_basis == "processing_status"
    assert {truth.summary.state, truth.decisions.state, truth.action_items.state, truth.followups.state} == {
        "processing"
    }


def test_available_summary_status_without_stored_sections_is_blocked() -> None:
    truth = view_models.notes_action_truth_state(status="ready", result=_result(summary_status=SummaryStatus.AVAILABLE))

    assert truth.source_basis == "processing_status"
    assert truth.summary.state == "blocked"
    assert truth.summary.copy_key == "notes.summary.blocked_missing_stored_output"
    assert truth.summary.readiness_impact == "keeps_gap_open"
