from uuid import UUID

import pytest

from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing.lifecycle import can_transition, classify_mediascribe_error
from twobrain_rec_server.processing.reasons import (
    MEDIASCRIBE_AUTH_FAILED,
    MEDIASCRIBE_PAYLOAD_TOO_LARGE,
    MEDIASCRIBE_RATE_LIMITED,
    MEDIASCRIBE_TIMEOUT,
)
from twobrain_rec_server.workflows.temporal_client import (
    processing_workflow_id,
    validate_processing_workflow_id,
)


def test_processing_state_machine_allows_happy_path_and_blocks_terminal_reopen() -> None:
    assert can_transition(ProcessingStatus.NOT_SUBMITTED, ProcessingStatus.STARTING)
    assert can_transition(ProcessingStatus.STARTING, ProcessingStatus.WORKFLOW_STARTED)
    assert can_transition(ProcessingStatus.STARTING, ProcessingStatus.SUBMITTING)
    assert can_transition(ProcessingStatus.WORKFLOW_STARTED, ProcessingStatus.SUBMITTING)
    assert can_transition(ProcessingStatus.SUBMITTING, ProcessingStatus.SUBMITTED)
    assert can_transition(ProcessingStatus.SUBMITTED, ProcessingStatus.POLLING)
    assert can_transition(ProcessingStatus.POLLING, ProcessingStatus.IMPORTING)
    assert can_transition(ProcessingStatus.IMPORTING, ProcessingStatus.PROCESSED)
    assert not can_transition(ProcessingStatus.PROCESSED, ProcessingStatus.SUBMITTING)


def test_mediascribe_failure_classification_covers_retryable_and_terminal_cases() -> None:
    assert classify_mediascribe_error(401).reason_code == MEDIASCRIBE_AUTH_FAILED
    assert not classify_mediascribe_error(401).retryable
    assert classify_mediascribe_error(413).reason_code == MEDIASCRIBE_PAYLOAD_TOO_LARGE
    assert classify_mediascribe_error(429).reason_code == MEDIASCRIBE_RATE_LIMITED
    assert classify_mediascribe_error(429).retryable
    assert classify_mediascribe_error(None, timeout=True).reason_code == MEDIASCRIBE_TIMEOUT


def test_processing_workflow_id_contains_only_fixed_prefix_and_meeting_uuid() -> None:
    meeting_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    workflow_id = processing_workflow_id(meeting_id)
    assert workflow_id == "processing/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    validate_processing_workflow_id(workflow_id)
    with pytest.raises(ValueError):
        validate_processing_workflow_id("processing/meeting-title-secret")
