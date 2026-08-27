from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing import reasons

TERMINAL_PROCESSING_STATUSES = {
    ProcessingStatus.PROCESSED,
    ProcessingStatus.BLOCKED,
    ProcessingStatus.FAILED_TERMINAL,
    ProcessingStatus.CANCELED,
}

MEDIA_REVISION_DELETION_SAFE_REASON = "Media revision identity retained as lifecycle metadata"
PROCESSING_START_RECONCILE_AFTER = timedelta(minutes=1)
PROCESSING_ACTIVE_RECONCILE_AFTER = timedelta(minutes=15)

RECONCILABLE_PROCESSING_STATUSES = {
    ProcessingStatus.STARTING.value,
    ProcessingStatus.WORKFLOW_STARTED.value,
    ProcessingStatus.SUBMITTING.value,
    ProcessingStatus.SUBMITTED.value,
    ProcessingStatus.POLLING.value,
    ProcessingStatus.IMPORTING.value,
    ProcessingStatus.FAILED_RETRYABLE.value,
    ProcessingStatus.WAITING_RETRY.value,
    ProcessingStatus.BLOCKED_UNKNOWN.value,
}

ALLOWED_PROCESSING_TRANSITIONS = {
    ProcessingStatus.NOT_SUBMITTED: {
        ProcessingStatus.STARTING,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.CANCELED,
    },
    # A freshly admitted user retry can reach the Temporal activity before
    # the optional workflow-start projection is persisted. The activity's
    # durable first step is submission, so this transition must be valid.
    ProcessingStatus.STARTING: {
        ProcessingStatus.WORKFLOW_STARTED,
        ProcessingStatus.SUBMITTING,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.BLOCKED_UNKNOWN,
        ProcessingStatus.FAILED_RETRYABLE,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.CANCELED,
    },
    ProcessingStatus.WORKFLOW_STARTED: {
        ProcessingStatus.SUBMITTING,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.BLOCKED_UNKNOWN,
        ProcessingStatus.FAILED_RETRYABLE,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.CANCELED,
    },
    ProcessingStatus.SUBMITTING: {
        ProcessingStatus.SUBMITTED,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.FAILED_RETRYABLE,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.BLOCKED_UNKNOWN,
        ProcessingStatus.WAITING_RETRY,
        ProcessingStatus.CANCELED,
    },
    ProcessingStatus.SUBMITTED: {
        ProcessingStatus.POLLING,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.FAILED_RETRYABLE,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.WAITING_RETRY,
        ProcessingStatus.CANCELED,
    },
    ProcessingStatus.POLLING: {
        ProcessingStatus.IMPORTING,
        ProcessingStatus.PROCESSED,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.FAILED_RETRYABLE,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.WAITING_RETRY,
        ProcessingStatus.BLOCKED_UNKNOWN,
        ProcessingStatus.CANCELED,
    },
    ProcessingStatus.WAITING_RETRY: {
        ProcessingStatus.POLLING,
        ProcessingStatus.SUBMITTING,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.BLOCKED_UNKNOWN,
        ProcessingStatus.CANCELED,
    },
    ProcessingStatus.BLOCKED_UNKNOWN: {
        ProcessingStatus.POLLING,
        ProcessingStatus.SUBMITTING,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.CANCELED,
    },
    ProcessingStatus.IMPORTING: {
        ProcessingStatus.PROCESSED,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.FAILED_RETRYABLE,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.CANCELED,
    },
    ProcessingStatus.FAILED_RETRYABLE: {
        ProcessingStatus.SUBMITTING,
        ProcessingStatus.POLLING,
        ProcessingStatus.WAITING_RETRY,
        ProcessingStatus.BLOCKED_UNKNOWN,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.CANCELED,
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


def processing_start_reconciliation_due(
    *,
    status: str,
    updated_at: datetime | None,
    now: datetime,
    workflow_run_id: str | None = None,
) -> bool:
    if status not in RECONCILABLE_PROCESSING_STATUSES or updated_at is None:
        return False
    has_run_id = isinstance(workflow_run_id, str) and bool(workflow_run_id.strip())
    if not has_run_id and status not in {
        ProcessingStatus.STARTING.value,
        ProcessingStatus.WORKFLOW_STARTED.value,
    }:
        return False
    current_time = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    last_update = updated_at if updated_at.tzinfo is not None else updated_at.replace(tzinfo=UTC)
    threshold = (
        PROCESSING_ACTIVE_RECONCILE_AFTER if has_run_id else PROCESSING_START_RECONCILE_AFTER
    )
    return current_time - last_update >= threshold


def classify_mediascribe_error(
    status_code: int | None, *, timeout: bool = False
) -> FailureClassification:
    if timeout:
        return FailureClassification(
            ProcessingStatus.FAILED_RETRYABLE, reasons.MEDIASCRIBE_TIMEOUT, True
        )
    if status_code == 401:
        return FailureClassification(
            ProcessingStatus.FAILED_TERMINAL, reasons.MEDIASCRIBE_AUTH_FAILED, False
        )
    if status_code == 413:
        return FailureClassification(
            ProcessingStatus.FAILED_TERMINAL, reasons.MEDIASCRIBE_PAYLOAD_TOO_LARGE, False
        )
    if status_code == 408:
        return FailureClassification(
            ProcessingStatus.FAILED_RETRYABLE, reasons.MEDIASCRIBE_TIMEOUT, True
        )
    if status_code == 409:
        return FailureClassification(
            ProcessingStatus.FAILED_RETRYABLE, reasons.MEDIASCRIBE_RESULT_NOT_READY, True
        )
    if status_code == 429:
        return FailureClassification(
            ProcessingStatus.FAILED_RETRYABLE, reasons.MEDIASCRIBE_RATE_LIMITED, True
        )
    if status_code == 500:
        return FailureClassification(
            ProcessingStatus.FAILED_TERMINAL, reasons.MEDIASCRIBE_SERVER_ERROR, False
        )
    if status_code in {502, 503, 504}:
        return FailureClassification(
            ProcessingStatus.FAILED_RETRYABLE, reasons.MEDIASCRIBE_SERVER_ERROR, True
        )
    if status_code is not None and 400 <= status_code < 500:
        return FailureClassification(
            ProcessingStatus.FAILED_TERMINAL, reasons.MEDIASCRIBE_VALIDATION_FAILED, False
        )
    return FailureClassification(
        ProcessingStatus.FAILED_RETRYABLE, reasons.UNKNOWN_DEPENDENCY_STATUS, True
    )
