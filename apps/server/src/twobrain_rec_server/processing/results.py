"""Shared selection and lineage rules for user-visible processing results."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, false, nullslast, or_, select

from twobrain_rec_server.db.models import ProcessingResult
from twobrain_rec_server.domain.statuses import (
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
)


def complete_processing_result_clause(model: Any = ProcessingResult) -> Any:
    """Return the SQL predicate for the first user-usable result milestone."""

    return and_(
        model.status == ProcessingResultStatus.IMPORTED.value,
        model.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value,
        model.segment_count > 0,
        model.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value,
        model.diarization_segment_count > 0,
    )


def effective_processing_result_query(
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
):
    """Build the one result query used by content-safe projections.

    A missing revision is intentionally an empty result set. Results without a
    workflow lineage are accepted only when they contain the complete,
    same-revision user milestone; incomplete legacy rows remain hidden.
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
        or_(
            ProcessingResult.processing_workflow_id.is_not(None),
            complete_processing_result_clause(),
        ),
    ).order_by(
        case((complete_processing_result_clause(), 1), else_=0).desc(),
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
        and (
            getattr(result, "processing_workflow_id", None) is not None
            or result_is_complete(result)
        )
    )


def result_is_complete(result: object | None) -> bool:
    """Mirror ``complete_processing_result_clause`` for in-memory projections."""

    if result is None:
        return False
    status = getattr(result, "status", None)
    transcript_status = getattr(result, "transcript_status", None)
    diarization_status = getattr(result, "diarization_status", None)
    return bool(
        getattr(status, "value", status) == ProcessingResultStatus.IMPORTED.value
        and getattr(transcript_status, "value", transcript_status)
        == ProcessingAvailabilityStatus.AVAILABLE.value
        and int(getattr(result, "segment_count", 0) or 0) > 0
        and getattr(diarization_status, "value", diarization_status)
        == ProcessingAvailabilityStatus.AVAILABLE.value
        and int(getattr(result, "diarization_segment_count", 0) or 0) > 0
    )
