from __future__ import annotations

import unicodedata
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.db.models import MeetingSpeakerName, ProcessingAuditEvent


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
) -> str | None:
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
    if name:
        if row is None:
            db.add(
                MeetingSpeakerName(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    speaker_key=speaker_key,
                    display_name=name,
                    updated_by_user_id=actor_user_id,
                )
            )
        else:
            row.display_name = name
            row.updated_by_user_id = actor_user_id
        event_type = "speaker_display_name_set"
    else:
        if row is not None:
            await db.delete(row)
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
