from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.db.models import (
    MeetingOutcomeGenerationAttempt,
    MeetingSpeakerName,
    ProcessingAuditEvent,
    ProcessingResult,
)
from twobrain_rec_server.domain.speaker_turns import legacy_speaker_name_key
from twobrain_rec_server.processing.fences import (
    lock_meeting_fence,
    meeting_is_deleted_or_deleting,
)

SPEAKER_ATTRIBUTION_EVENT_TYPES = {
    "speaker_display_name_set",
    "speaker_display_name_cleared",
}
def speaker_names_for_result(
    rows: Iterable[MeetingSpeakerName],
    *,
    result_imported_at: datetime | None,
) -> dict[str, str]:
    return {
        row.speaker_key: row.display_name
        for row in rows
        if legacy_speaker_name_key(row.speaker_key) is None
        or (
            result_imported_at is not None
            and row.updated_at is not None
            and row.updated_at >= result_imported_at
        )
    }


def normalize_speaker_name(value: str) -> str:
    name = value.strip()
    if len(name) > 80 or any(unicodedata.category(char) in {"Cc", "Cf"} for char in name):
        raise ProblemDetail(
            status=422, code="speaker_name_invalid", title="Некорректное имя спикера"
        )
    if "<" in name or ">" in name:
        raise ProblemDetail(
            status=422, code="speaker_name_invalid", title="Некорректное имя спикера"
        )
    return name


async def save_speaker_name(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    speaker_key: str,
    display_name: str,
    actor_user_id: UUID,
    known_speaker_keys: set[str],
    processing_result_id: UUID | None = None,
    legacy_speaker_key: str | None = None,
) -> str | None:
    meeting = await lock_meeting_fence(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        raise ProblemDetail(
            status=409,
            code="meeting_deleting",
            title="Встреча удаляется",
        )
    if speaker_key not in known_speaker_keys:
        raise ProblemDetail(status=404, code="speaker_not_found", title="Спикер не найден")
    name = normalize_speaker_name(display_name)
    row = await db.scalar(
        select(MeetingSpeakerName).where(
            MeetingSpeakerName.workspace_id == workspace_id,
            MeetingSpeakerName.meeting_id == meeting_id,
            MeetingSpeakerName.speaker_key == speaker_key,
        )
    )
    legacy_row = None
    if legacy_speaker_key is not None and legacy_speaker_key != speaker_key:
        legacy_row = await db.scalar(
            select(MeetingSpeakerName).where(
                MeetingSpeakerName.workspace_id == workspace_id,
                MeetingSpeakerName.meeting_id == meeting_id,
                MeetingSpeakerName.speaker_key == legacy_speaker_key,
            )
        )
        result_imported_at = (
            await db.scalar(
                select(ProcessingResult.imported_at).where(
                    ProcessingResult.workspace_id == workspace_id,
                    ProcessingResult.meeting_id == meeting_id,
                    ProcessingResult.id == processing_result_id,
                )
            )
            if processing_result_id is not None
            else None
        )
        if (
            result_imported_at is None
            or legacy_row is None
            or legacy_row.updated_at is None
            or legacy_row.updated_at < result_imported_at
        ):
            legacy_row = None
    if name:
        if row is None:
            if legacy_row is not None:
                row = legacy_row
                row.speaker_key = speaker_key
            else:
                row = MeetingSpeakerName(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    speaker_key=speaker_key,
                    display_name=name,
                    updated_by_user_id=actor_user_id,
                )
                db.add(row)
        elif row.display_name == name and legacy_row is None:
            return name
        row.display_name = name
        row.updated_by_user_id = actor_user_id
        if legacy_row is not None and legacy_row is not row:
            await db.delete(legacy_row)
        event_type = "speaker_display_name_set"
    else:
        if row is None and legacy_row is None:
            return None
        if row is not None:
            await db.delete(row)
        if legacy_row is not None and legacy_row is not row:
            await db.delete(legacy_row)
        event_type = "speaker_display_name_cleared"
    db.add(
        ProcessingAuditEvent(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            metadata_json={"speaker_key": speaker_key},
        )
    )
    return name or None


async def speaker_attribution_revision(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> str:
    event_id = await db.scalar(
        select(ProcessingAuditEvent.id)
        .where(
            ProcessingAuditEvent.workspace_id == workspace_id,
            ProcessingAuditEvent.meeting_id == meeting_id,
            ProcessingAuditEvent.event_type.in_(SPEAKER_ATTRIBUTION_EVENT_TYPES),
        )
        .order_by(ProcessingAuditEvent.created_at.desc(), ProcessingAuditEvent.id.desc())
        .limit(1)
    )
    return str(event_id or "")


async def candidate_speaker_attribution_is_current(
    db: AsyncSession,
    attempt: MeetingOutcomeGenerationAttempt,
) -> bool:
    if attempt.status == "accepted":
        return True
    stored_revision = (attempt.metadata_json or {}).get("speaker_attribution_revision")
    return isinstance(
        stored_revision, str
    ) and stored_revision == await speaker_attribution_revision(
        db,
        workspace_id=attempt.workspace_id,
        meeting_id=attempt.meeting_id,
    )
