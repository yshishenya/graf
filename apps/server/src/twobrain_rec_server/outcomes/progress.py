"""Read-only summary progress shared by status, HTML and desktop sync."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import (
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingSummarySlot,
    ProcessingResult,
)
from twobrain_rec_server.outcomes.service import load_pinned_egress_outcome
from twobrain_rec_server.processing.fences import meeting_is_deleted_or_deleting


async def latest_summary_attempt(
    db: AsyncSession, *, meeting: Meeting, result: ProcessingResult | None, template_key: str,
) -> MeetingOutcomeGenerationAttempt | None:
    if result is None or meeting_is_deleted_or_deleting(meeting):
        return None
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
    query = select(MeetingSummarySlot).where(
        MeetingSummarySlot.workspace_id == meeting.workspace_id,
        MeetingSummarySlot.meeting_id == meeting.id,
    )
    slot = await db.scalar(query.where(
        MeetingSummarySlot.template_key == template_key if template_key is not None
        else MeetingSummarySlot.is_meeting_default.is_(True)
    ))
    if slot is not None and slot.current_outcome_set_id is not None:
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
    state = "not_requested" if result is None else (
        result.summary_status if result.summary_status in {"failed", "unavailable"}
        else "not_requested"
    )
    return state
