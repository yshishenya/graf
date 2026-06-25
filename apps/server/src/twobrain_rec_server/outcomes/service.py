from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twobrain_rec_server.db.models import (
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    ProcessingResult,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
    OutcomeCategoryState,
    OutcomeGenerationAttemptStatus,
    OutcomeSetStatus,
    ProcessingAvailabilityStatus,
)
from twobrain_rec_server.outcomes.generator import generate_outcomes
from twobrain_rec_server.outcomes.models import OutcomeTranscriptSegment
from twobrain_rec_server.outcomes.store import (
    OUTCOME_GENERATOR_VERSION,
    create_outcome_set,
    record_generation_attempt,
    replace_outcome_items,
    set_outcome_category_states,
    should_reuse_outcome_set,
)


async def ensure_outcomes_for_meeting(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    meeting_id: UUID,
) -> MeetingOutcomeSet | None:
    async with sessionmaker() as db:
        result = await db.scalar(
            select(ProcessingResult)
            .where(ProcessingResult.meeting_id == meeting_id)
            .order_by(ProcessingResult.imported_at.desc(), ProcessingResult.created_at.desc())
        )
        if result is None:
            return None
        outcome_set = await ensure_outcomes_for_processing_result(db, result=result)
        await db.commit()
        return outcome_set


async def ensure_outcomes_for_processing_result(
    db: AsyncSession,
    *,
    result: ProcessingResult,
) -> MeetingOutcomeSet:
    existing = await _load_current_outcome_set(db, result=result)
    transcript_is_available = result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value and result.segment_count > 0
    if existing is not None and should_reuse_outcome_set(existing, transcript_is_available=transcript_is_available):
        return existing
    started_at = datetime.now(UTC)
    outcome_set = existing or await create_outcome_set(
            db,
            workspace_id=result.workspace_id,
            meeting_id=result.meeting_id,
            media_revision_id=result.media_revision_id,
            processing_result_id=result.id,
            source_result_hash=result.source_result_hash,
            started_at=started_at,
        )
    outcome_set.status = OutcomeSetStatus.GENERATING.value
    outcome_set.failure_reason = None
    outcome_set.started_at = outcome_set.started_at or started_at
    outcome_set.source_result_hash = result.source_result_hash
    set_outcome_category_states(outcome_set, OutcomeCategoryState.PROCESSING.value)
    if not transcript_is_available:
        outcome_set.status = OutcomeSetStatus.BLOCKED.value
        outcome_set.failure_reason = "outcomes_transcript_unavailable"
        set_outcome_category_states(outcome_set, OutcomeCategoryState.BLOCKED.value)
        await record_generation_attempt(
            db,
            workspace_id=result.workspace_id,
            meeting_id=result.meeting_id,
            media_revision_id=result.media_revision_id,
            processing_result_id=result.id,
            outcome_set_id=outcome_set.id,
            status=OutcomeGenerationAttemptStatus.BLOCKED.value,
            failure_reason="outcomes_transcript_unavailable",
            metadata_json={"segment_count": result.segment_count},
        )
        await db.flush()
        return outcome_set

    segments = await _load_transcript_segments(db, result=result)
    try:
        payload = generate_outcomes(segments)
    except Exception:
        ended_at = datetime.now(UTC)
        outcome_set.status = OutcomeSetStatus.BLOCKED.value
        outcome_set.failure_reason = "outcomes_generation_failed"
        outcome_set.generated_at = None
        outcome_set.latency_ms = max(0, int((ended_at - started_at).total_seconds() * 1000))
        set_outcome_category_states(outcome_set, OutcomeCategoryState.BLOCKED.value)
        await record_generation_attempt(
            db,
            workspace_id=result.workspace_id,
            meeting_id=result.meeting_id,
            media_revision_id=result.media_revision_id,
            processing_result_id=result.id,
            outcome_set_id=outcome_set.id,
            status=OutcomeGenerationAttemptStatus.FAILED_RETRYABLE.value,
            started_at=started_at,
            ended_at=ended_at,
            latency_ms=outcome_set.latency_ms,
            failure_reason="outcomes_generation_failed",
            metadata_json={"segment_count": len(segments)},
        )
        await db.flush()
        return outcome_set
    outcome_set.status = OutcomeSetStatus.AVAILABLE.value
    outcome_set.generated_at = datetime.now(UTC)
    outcome_set.latency_ms = max(0, int((outcome_set.generated_at - started_at).total_seconds() * 1000))
    for category, state in payload.category_states.items():
        setattr(outcome_set, f"{category}_state", state)
    outcome_set.content_hash = _payload_hash(payload.items)
    stored_items = [item.as_store_item() for item in payload.items]
    await replace_outcome_items(db, outcome_set=outcome_set, items=stored_items)
    await record_generation_attempt(
        db,
        workspace_id=result.workspace_id,
        meeting_id=result.meeting_id,
        media_revision_id=result.media_revision_id,
        processing_result_id=result.id,
        outcome_set_id=outcome_set.id,
        status=OutcomeGenerationAttemptStatus.STORED.value,
        started_at=started_at,
        ended_at=outcome_set.generated_at,
        latency_ms=outcome_set.latency_ms,
        metadata_json={
            "segment_count": len(segments),
            "category_count": len(payload.category_states),
            "item_count": len(stored_items),
        },
    )
    await db.flush()
    return outcome_set


async def _load_current_available_set(
    db: AsyncSession,
    *,
    result: ProcessingResult,
) -> MeetingOutcomeSet | None:
    return await _load_current_outcome_set(db, result=result)


async def _load_current_outcome_set(
    db: AsyncSession,
    *,
    result: ProcessingResult,
) -> MeetingOutcomeSet | None:
    return await db.scalar(
        select(MeetingOutcomeSet).where(
            MeetingOutcomeSet.workspace_id == result.workspace_id,
            MeetingOutcomeSet.meeting_id == result.meeting_id,
            MeetingOutcomeSet.media_revision_id == result.media_revision_id,
            MeetingOutcomeSet.processing_result_id == result.id,
            MeetingOutcomeSet.generator_version == OUTCOME_GENERATOR_VERSION,
        )
    )


async def _load_transcript_segments(
    db: AsyncSession,
    *,
    result: ProcessingResult,
) -> list[OutcomeTranscriptSegment]:
    rows = (
        await db.scalars(
            select(TranscriptSegment)
            .where(
                TranscriptSegment.workspace_id == result.workspace_id,
                TranscriptSegment.meeting_id == result.meeting_id,
                TranscriptSegment.processing_result_id == result.id,
            )
            .order_by(TranscriptSegment.sequence.asc(), TranscriptSegment.start_seconds.asc())
        )
    ).all()
    return [
        OutcomeTranscriptSegment(
            segment_id=row.id,
            sequence=row.sequence,
            start_seconds=row.start_seconds,
            end_seconds=row.end_seconds,
            speaker_label=f"Speaker {row.sequence + 1}",
            source_role=row.source_role,
            text=row.text,
        )
        for row in rows
    ]


def _payload_hash(items: list[object]) -> str:
    payload = "|".join(repr(item) for item in items)
    return sha256(payload.encode("utf-8")).hexdigest()


async def load_outcome_items(
    db: AsyncSession,
    *,
    outcome_set: MeetingOutcomeSet | None,
) -> list[MeetingOutcomeItem]:
    if outcome_set is None:
        return []
    return (
        await db.scalars(
            select(MeetingOutcomeItem)
            .where(MeetingOutcomeItem.outcome_set_id == outcome_set.id)
            .order_by(MeetingOutcomeItem.category.asc(), MeetingOutcomeItem.sequence.asc())
        )
    ).all()
