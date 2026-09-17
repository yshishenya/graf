"""Read-only summary progress shared by status, HTML and desktop sync."""

from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.cabinet.read_prefetch import (
    CabinetReadPrefetch,
    active_read_prefetch,
)
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
)
from twobrain_rec_server.domain.statuses import OutcomeSetStatus, ProcessingResultStatus
from twobrain_rec_server.outcomes.service import load_pinned_egress_outcome
from twobrain_rec_server.processing.fences import meeting_is_deleted_or_deleting


async def batch_pinned_egress_outcomes(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    requests: Iterable[tuple[UUID, str, UUID]],
    prefetch: CabinetReadPrefetch | None = None,
) -> dict[tuple[UUID, UUID], MeetingOutcomeSet | None]:
    """Batch variant of `load_pinned_egress_outcome` for (meeting, template, id) rows."""
    if prefetch is None:
        prefetch = active_read_prefetch(db)
    request_list = list(dict.fromkeys(requests))
    result: dict[tuple[UUID, UUID], MeetingOutcomeSet | None] = {
        (meeting_id, outcome_set_id): None for meeting_id, _, outcome_set_id in request_list
    }
    if not request_list:
        return result
    meeting_ids = {meeting_id for meeting_id, _, _ in request_list}
    outcome_ids = {outcome_set_id for _, _, outcome_set_id in request_list}
    rows = await db.scalars(
        select(MeetingOutcomeSet).where(
            MeetingOutcomeSet.id.in_(outcome_ids),
            MeetingOutcomeSet.workspace_id == workspace_id,
            MeetingOutcomeSet.meeting_id.in_(meeting_ids),
            MeetingOutcomeSet.lifecycle_state == "active",
            MeetingOutcomeSet.status.in_(
                (OutcomeSetStatus.AVAILABLE.value, OutcomeSetStatus.PARTIAL.value)
            ),
        )
    )
    outcomes = {
        row.id: row
        for row in rows
    }
    result_ids = {
        outcome.processing_result_id
        for outcome in outcomes.values()
        if outcome.processing_result_id is not None
    }
    results: dict[UUID, ProcessingResult] = {}
    if result_ids:
        result_rows = await db.scalars(
            select(ProcessingResult).where(
                ProcessingResult.id.in_(result_ids),
                ProcessingResult.workspace_id == workspace_id,
                ProcessingResult.meeting_id.in_(meeting_ids),
                ProcessingResult.status == ProcessingResultStatus.IMPORTED.value,
            )
        )
        results = {row.id: row for row in result_rows}
    for meeting_id, template_key, outcome_set_id in request_list:
        outcome = outcomes.get(outcome_set_id)
        if (
            outcome is None
            or outcome.meeting_id != meeting_id
            or outcome.template_key != template_key
            or outcome.revision_state not in (None, "accepted")
        ):
            continue
        result_row = (
            results.get(outcome.processing_result_id)
            if outcome.processing_result_id is not None
            else None
        )
        if result_row is None or outcome.media_revision_id != result_row.media_revision_id:
            continue
        result_source_hash = result_row.source_result_hash or sha256(
            f"legacy-processing-result:{result_row.id}".encode()
        ).hexdigest()
        outcome_source_hash = outcome.source_result_hash or result_source_hash
        if outcome_source_hash == result_source_hash:
            result[(meeting_id, outcome_set_id)] = outcome
    if prefetch is not None:
        prefetch.pinned_outcomes.update(result)
    return result


async def batch_latest_summary_attempts(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    requests: Iterable[tuple[UUID, str, UUID, UUID | None]],
    prefetch: CabinetReadPrefetch | None = None,
) -> dict[tuple[UUID, str, UUID, UUID | None], MeetingOutcomeGenerationAttempt | None]:
    """Batch variant of `latest_summary_attempt` for (meeting, template, result) rows."""
    if prefetch is None:
        prefetch = active_read_prefetch(db)
    request_list = list(dict.fromkeys(requests))
    result: dict[
        tuple[UUID, str, UUID, UUID | None], MeetingOutcomeGenerationAttempt | None
    ] = {request: None for request in request_list}
    if not request_list:
        return result
    meeting_ids = {meeting_id for meeting_id, _, _, _ in request_list}
    result_ids = {result_id for _, _, result_id, _ in request_list}
    rows = await db.scalars(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
            MeetingOutcomeGenerationAttempt.meeting_id.in_(meeting_ids),
            MeetingOutcomeGenerationAttempt.processing_result_id.in_(result_ids),
        )
        .distinct(
            MeetingOutcomeGenerationAttempt.meeting_id,
            MeetingOutcomeGenerationAttempt.template_key,
            MeetingOutcomeGenerationAttempt.processing_result_id,
            MeetingOutcomeGenerationAttempt.media_revision_id,
        )
        .order_by(
            MeetingOutcomeGenerationAttempt.meeting_id,
            MeetingOutcomeGenerationAttempt.template_key,
            MeetingOutcomeGenerationAttempt.processing_result_id,
            MeetingOutcomeGenerationAttempt.media_revision_id,
            MeetingOutcomeGenerationAttempt.created_at.desc(),
            MeetingOutcomeGenerationAttempt.id.desc(),
        )
    )
    for row in rows:
        key = (row.meeting_id, row.template_key, row.processing_result_id, row.media_revision_id)
        if key in result:
            result[key] = row
    if prefetch is not None:
        prefetch.summary_attempts.update(result)
    return result


async def latest_summary_attempt(
    db: AsyncSession, *, meeting: Meeting, result: ProcessingResult | None, template_key: str,
) -> MeetingOutcomeGenerationAttempt | None:
    if result is None or meeting_is_deleted_or_deleting(meeting):
        return None
    prefetch = active_read_prefetch(db)
    cache_key = (meeting.id, template_key, result.id, result.media_revision_id)
    if prefetch is not None and cache_key in prefetch.summary_attempts:
        attempt = prefetch.summary_attempts[cache_key]
    else:
        attempt = await db.scalar(
            select(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.workspace_id == meeting.workspace_id,
                MeetingOutcomeGenerationAttempt.meeting_id == meeting.id,
                MeetingOutcomeGenerationAttempt.template_key == template_key,
                MeetingOutcomeGenerationAttempt.processing_result_id == result.id,
                MeetingOutcomeGenerationAttempt.media_revision_id == result.media_revision_id,
            ).order_by(MeetingOutcomeGenerationAttempt.created_at.desc(), MeetingOutcomeGenerationAttempt.id.desc())
        )
    if attempt is None:
        return None
    if (attempt.deletion_epoch_at_start is not None
            and attempt.deletion_epoch_at_start != meeting.deletion_epoch):
        return None
    if attempt.source_result_hash and attempt.source_result_hash != result.source_result_hash:
        return None
    return attempt


async def summary_progress(
    db: AsyncSession, *, meeting: Meeting, result: ProcessingResult | None,
    template_key: str | None = None,
) -> str:
    if meeting_is_deleted_or_deleting(meeting):
        return "unavailable"
    prefetch = active_read_prefetch(db)
    slot = None
    if prefetch is not None and (meeting.id, template_key) in prefetch.summary_slots:
        slot = prefetch.summary_slots[(meeting.id, template_key)]
    else:
        query = select(MeetingSummarySlot).where(
            MeetingSummarySlot.workspace_id == meeting.workspace_id,
            MeetingSummarySlot.meeting_id == meeting.id,
        )
        slot = await db.scalar(query.where(
            MeetingSummarySlot.template_key == template_key if template_key is not None
            else MeetingSummarySlot.is_meeting_default.is_(True)
        ))
    if slot is not None and slot.current_outcome_set_id is not None:
        pinned_key = (meeting.id, slot.current_outcome_set_id)
        if prefetch is not None and pinned_key in prefetch.pinned_outcomes:
            outcome = prefetch.pinned_outcomes[pinned_key]
        else:
            outcome = await load_pinned_egress_outcome(
                db, meeting=meeting, template_key=slot.template_key,
                outcome_set_id=slot.current_outcome_set_id,
            )
        if outcome is not None and result is not None and outcome.media_revision_id == result.media_revision_id:
            return outcome.status
    key = template_key or (slot.template_key if slot is not None else None)
    if key is not None:
        attempt = await latest_summary_attempt(db, meeting=meeting, result=result, template_key=key)
        if attempt is not None:
            if attempt.status in {"queued", "generating", "blocked_dependency"}:
                return attempt.status
            if attempt.status in {"failed", "cancelled", "expired", "stale"}:
                return "failed"
            if attempt.status == "candidate":
                return "candidate"
    # A stored-result flag alone never proves published summary content.
    if template_key is None and result is not None and result.summary_status == "available":
        return "unavailable"
    state = "not_requested" if result is None else (
        result.summary_status if result.summary_status in {"failed", "unavailable"}
        else "not_requested"
    )
    return state
