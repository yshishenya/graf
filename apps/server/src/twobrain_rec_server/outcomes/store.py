from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import (
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
)
from twobrain_rec_server.domain.statuses import (
    OutcomeGenerationAttemptStatus,
    OutcomeGeneratorKind,
    OutcomeSetStatus,
)

OUTCOME_GENERATOR_VERSION = "outcomes-extractive-v1"

REUSABLE_OUTCOME_SET_STATUSES = {
    OutcomeSetStatus.AVAILABLE.value,
    OutcomeSetStatus.PARTIAL.value,
    OutcomeSetStatus.UNSAFE.value,
    OutcomeSetStatus.QUEUED.value,
    OutcomeSetStatus.GENERATING.value,
}


async def get_current_outcome_set(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
    processing_result_id: UUID,
    generator_version: str = OUTCOME_GENERATOR_VERSION,
) -> MeetingOutcomeSet | None:
    result = await session.execute(
        select(MeetingOutcomeSet).where(
            MeetingOutcomeSet.workspace_id == workspace_id,
            MeetingOutcomeSet.meeting_id == meeting_id,
            MeetingOutcomeSet.media_revision_id == media_revision_id,
            MeetingOutcomeSet.processing_result_id == processing_result_id,
            MeetingOutcomeSet.generator_version == generator_version,
        )
    )
    return result.scalar_one_or_none()


async def create_outcome_set(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
    processing_result_id: UUID,
    source_result_hash: str | None = None,
    generator_version: str = OUTCOME_GENERATOR_VERSION,
    status: str = OutcomeSetStatus.QUEUED.value,
    started_at: datetime | None = None,
) -> MeetingOutcomeSet:
    current = await get_current_outcome_set(
        session,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        processing_result_id=processing_result_id,
        generator_version=generator_version,
    )
    if current is not None:
        return current
    outcome_set = MeetingOutcomeSet(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        processing_result_id=processing_result_id,
        source_result_hash=source_result_hash,
        generator_version=generator_version,
        status=status,
        started_at=started_at,
    )
    session.add(outcome_set)
    await session.flush()
    return outcome_set


async def replace_outcome_items(
    session: AsyncSession,
    *,
    outcome_set: MeetingOutcomeSet,
    items: Iterable[Mapping[str, object]],
) -> list[MeetingOutcomeItem]:
    await session.execute(delete(MeetingOutcomeItem).where(MeetingOutcomeItem.outcome_set_id == outcome_set.id))
    rows: list[MeetingOutcomeItem] = []
    for item in items:
        row = MeetingOutcomeItem(
            workspace_id=outcome_set.workspace_id,
            meeting_id=outcome_set.meeting_id,
            outcome_set_id=outcome_set.id,
            category=str(item["category"]),
            sequence=int(item.get("sequence", len(rows))),
            state=str(item.get("state", "available")),
            text=item.get("text") if item.get("text") is None else str(item.get("text")),
            owner_text=item.get("owner_text") if item.get("owner_text") is None else str(item.get("owner_text")),
            due_date_text=item.get("due_date_text") if item.get("due_date_text") is None else str(item.get("due_date_text")),
            truth_label=str(item.get("truth_label", "supported")),
            source_refs_json=list(item.get("source_refs_json", [])),
        )
        session.add(row)
        rows.append(row)
    await session.flush()
    return rows


async def record_generation_attempt(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None,
    processing_result_id: UUID,
    outcome_set_id: UUID | None = None,
    status: str = OutcomeGenerationAttemptStatus.QUEUED.value,
    provider_kind: str = OutcomeGeneratorKind.DETERMINISTIC_EXTRACTIVE.value,
    generator_version: str = OUTCOME_GENERATOR_VERSION,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    latency_ms: int | None = None,
    failure_reason: str | None = None,
    metadata_json: dict | None = None,
) -> MeetingOutcomeGenerationAttempt:
    attempt = MeetingOutcomeGenerationAttempt(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        processing_result_id=processing_result_id,
        outcome_set_id=outcome_set_id,
        status=status,
        provider_kind=provider_kind,
        generator_version=generator_version,
        started_at=started_at,
        ended_at=ended_at,
        latency_ms=latency_ms,
        failure_reason=failure_reason,
        metadata_json=metadata_json or {},
    )
    session.add(attempt)
    await session.flush()
    return attempt


def category_states(outcome_set: MeetingOutcomeSet) -> dict[str, str]:
    return {
        "summary": outcome_set.summary_state,
        "key_points": outcome_set.key_points_state,
        "decisions": outcome_set.decisions_state,
        "action_items": outcome_set.action_items_state,
        "followups": outcome_set.followups_state,
        "risks": outcome_set.risks_state,
        "questions": outcome_set.questions_state,
        "evidence": outcome_set.evidence_state,
    }


def should_reuse_outcome_set(outcome_set: MeetingOutcomeSet, *, transcript_is_available: bool) -> bool:
    if outcome_set.status in REUSABLE_OUTCOME_SET_STATUSES:
        return True
    return not transcript_is_available


def set_outcome_category_states(outcome_set: MeetingOutcomeSet, state: str) -> None:
    outcome_set.summary_state = state
    outcome_set.key_points_state = state
    outcome_set.decisions_state = state
    outcome_set.action_items_state = state
    outcome_set.followups_state = state
    outcome_set.risks_state = state
    outcome_set.questions_state = state
    outcome_set.evidence_state = state
