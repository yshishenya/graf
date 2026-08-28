"""Shared selection and lineage rules for user-visible processing results."""

from __future__ import annotations

from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import and_, false, nullslast, select

from twobrain_rec_server.db.models import ProcessingResult
from twobrain_rec_server.domain.statuses import ProcessingAvailabilityStatus, ProcessingResultStatus
from twobrain_rec_server.processing.reasons import (
    FAILURE_SOURCE_INPUT_AUDIO,
    INVALID_AUDIO_PAYLOAD,
    NO_RECOGNIZABLE_SPEECH,
)


def complete_processing_result_clause(model: Any = ProcessingResult) -> Any:
    """Return the predicate for the first user-usable result milestone."""

    return and_(
        model.status == ProcessingResultStatus.IMPORTED.value,
        model.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value,
        model.segment_count > 0,
        model.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value,
        model.diarization_segment_count > 0,
    )


def result_is_complete(result: object | None) -> bool:
    """Mirror the complete-result predicate for in-memory projections."""

    if result is None:
        return False
    return bool(
        getattr(result, "status", None) == ProcessingResultStatus.IMPORTED.value
        and getattr(result, "transcript_status", None)
        == ProcessingAvailabilityStatus.AVAILABLE.value
        and int(getattr(result, "segment_count", 0) or 0) > 0
        and getattr(result, "diarization_status", None)
        == ProcessingAvailabilityStatus.AVAILABLE.value
        and int(getattr(result, "diarization_segment_count", 0) or 0) > 0
    )


def effective_processing_result_query(
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
):
    """Build the one result query used by content-safe projections.

    A missing revision is intentionally an empty result set. Results without
    an explicit workflow lineage are never user-visible.
    """

    query = select(ProcessingResult).where(
        ProcessingResult.workspace_id == workspace_id,
        ProcessingResult.meeting_id == meeting_id,
        ProcessingResult.status == ProcessingResultStatus.IMPORTED.value,
    )
    if media_revision_id is None:
        return query.where(false())
    return query.where(
        ProcessingResult.media_revision_id == media_revision_id,
        ProcessingResult.processing_workflow_id.is_not(None),
    ).order_by(
        ProcessingResult.result_version.desc(),
        nullslast(ProcessingResult.imported_at.desc()),
        ProcessingResult.created_at.desc(),
        ProcessingResult.id.desc(),
    )


def result_lineage_is_current(
    result: object | None,
    *,
    media_revision_id: UUID | None,
) -> bool:
    """Check the result's non-null source lineage without binding to attempt."""

    return bool(
        result is not None
        and media_revision_id is not None
        and getattr(result, "media_revision_id", None) == media_revision_id
        and getattr(result, "processing_workflow_id", None) is not None
    )


def result_source_hash_is_attested(result: object | None) -> bool:
    """Reject hashes synthesized by the historical outcome-lineage migration."""

    if result is None:
        return False
    result_id = getattr(result, "id", None)
    source_hash = getattr(result, "source_result_hash", None)
    if result_id is None or not source_hash:
        return False
    legacy_hash = sha256(f"legacy-processing-result:{result_id}".encode()).hexdigest()
    return source_hash != legacy_hash


def result_is_terminal_input(result: object | None) -> bool:
    """Return whether an imported result proves a terminal input outcome."""

    if result is None:
        return False
    status = getattr(result, "status", None)
    reason = getattr(result, "failure_reason", None)
    source = getattr(result, "failure_source", None)
    return bool(
        getattr(status, "value", status) == ProcessingResultStatus.IMPORTED.value
        and (
            reason == NO_RECOGNIZABLE_SPEECH
            or (reason == INVALID_AUDIO_PAYLOAD and source == FAILURE_SOURCE_INPUT_AUDIO)
        )
    )
