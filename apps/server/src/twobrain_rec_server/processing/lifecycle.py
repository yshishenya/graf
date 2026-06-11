from __future__ import annotations

from dataclasses import dataclass

from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing import reasons

TERMINAL_PROCESSING_STATUSES = {
    ProcessingStatus.PROCESSED,
    ProcessingStatus.BLOCKED,
    ProcessingStatus.FAILED_TERMINAL,
    ProcessingStatus.CANCELED,
}

ALLOWED_PROCESSING_TRANSITIONS = {
    ProcessingStatus.NOT_SUBMITTED: {ProcessingStatus.STARTING, ProcessingStatus.BLOCKED},
    ProcessingStatus.STARTING: {ProcessingStatus.WORKFLOW_STARTED, ProcessingStatus.BLOCKED},
    ProcessingStatus.WORKFLOW_STARTED: {ProcessingStatus.SUBMITTING, ProcessingStatus.FAILED_RETRYABLE},
    ProcessingStatus.SUBMITTING: {ProcessingStatus.SUBMITTED, ProcessingStatus.FAILED_RETRYABLE, ProcessingStatus.FAILED_TERMINAL},
    ProcessingStatus.SUBMITTED: {ProcessingStatus.POLLING, ProcessingStatus.FAILED_RETRYABLE, ProcessingStatus.FAILED_TERMINAL},
    ProcessingStatus.POLLING: {ProcessingStatus.IMPORTING, ProcessingStatus.FAILED_RETRYABLE, ProcessingStatus.FAILED_TERMINAL},
    ProcessingStatus.IMPORTING: {ProcessingStatus.PROCESSED, ProcessingStatus.FAILED_RETRYABLE, ProcessingStatus.FAILED_TERMINAL},
    ProcessingStatus.FAILED_RETRYABLE: {
        ProcessingStatus.SUBMITTING,
        ProcessingStatus.POLLING,
        ProcessingStatus.FAILED_TERMINAL,
    },
}


@dataclass(frozen=True, slots=True)
class FailureClassification:
    processing_status: ProcessingStatus
    reason_code: str
    retryable: bool


def can_transition(current: ProcessingStatus, target: ProcessingStatus) -> bool:
    if current == target:
        return True
    if current in TERMINAL_PROCESSING_STATUSES:
        return False
    return target in ALLOWED_PROCESSING_TRANSITIONS.get(current, set())


def classify_mediascribe_error(status_code: int | None, *, timeout: bool = False) -> FailureClassification:
    if timeout:
        return FailureClassification(ProcessingStatus.FAILED_RETRYABLE, reasons.MEDIASCRIBE_TIMEOUT, True)
    if status_code == 401:
        return FailureClassification(ProcessingStatus.FAILED_TERMINAL, reasons.MEDIASCRIBE_AUTH_FAILED, False)
    if status_code == 413:
        return FailureClassification(ProcessingStatus.FAILED_TERMINAL, reasons.MEDIASCRIBE_PAYLOAD_TOO_LARGE, False)
    if status_code == 409:
        return FailureClassification(ProcessingStatus.FAILED_RETRYABLE, reasons.MEDIASCRIBE_RESULT_NOT_READY, True)
    if status_code == 429 or (status_code is not None and status_code >= 500):
        return FailureClassification(ProcessingStatus.FAILED_RETRYABLE, reasons.MEDIASCRIBE_RATE_LIMITED if status_code == 429 else reasons.MEDIASCRIBE_SERVER_ERROR, True)
    if status_code is not None and 400 <= status_code < 500:
        return FailureClassification(ProcessingStatus.FAILED_TERMINAL, reasons.MEDIASCRIBE_VALIDATION_FAILED, False)
    return FailureClassification(ProcessingStatus.FAILED_RETRYABLE, reasons.UNKNOWN_DEPENDENCY_STATUS, True)
