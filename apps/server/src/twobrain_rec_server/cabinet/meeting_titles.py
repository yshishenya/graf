"""Owner-only title edits, serialized with calendar and deletion writers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.db.models import Meeting
from twobrain_rec_server.domain.metadata_text import contains_forbidden_metadata_text
from twobrain_rec_server.processing.fences import (
    lock_meeting_fence,
    meeting_is_deleted_or_deleting,
    normalize_db_timestamp,
)

TITLE_ERRORS = {
    "meeting_title_empty": "Введите название встречи",
    "meeting_title_too_long": "Название должно содержать не больше 500 символов",
    "unsafe_meeting_title": "Укажите название без ссылок, адресов почты, секретных данных и пути к файлу",
    "meeting_title_conflict": "Название уже изменено в другом окне. Нажмите Enter, чтобы сохранить своё, или Esc, чтобы оставить текущее",
}


def meeting_title_version(meeting: Meeting) -> str:
    stamp = normalize_db_timestamp(meeting.title_updated_at)
    state = [
        str(meeting.id),
        meeting.title,
        meeting.title_source,
        stamp.isoformat() if stamp else None,
    ]
    return hashlib.sha256(json.dumps(state, ensure_ascii=True).encode()).hexdigest()


async def save_meeting_title(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    user_id: UUID,
    title: str,
    expected_version: str,
) -> Meeting:
    meeting = await lock_meeting_fence(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if meeting is None or meeting.created_by_user_id != user_id or meeting.deleted_at is not None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Встреча больше недоступна")
    if meeting_is_deleted_or_deleting(meeting):
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Встреча удаляется")
    clean = title.strip()
    code = (
        "meeting_title_empty"
        if not clean
        else "meeting_title_too_long"
        if len(clean) > 500
        else "unsafe_meeting_title"
        if (
            contains_forbidden_metadata_text(title)
            or re.search(r"[\x80-\x9f\u2028\u2029]", title)
            or clean.startswith(("/", "\\"))
            or re.match(r"^[A-Za-z]:[/\\]", clean)
        )
        else None
    )
    if code:
        raise ProblemDetail(status=422, code=code, title=TITLE_ERRORS[code])
    # A lost response can safely be retried without changing the version again.
    if meeting.title == clean and meeting.title_source == "user_confirmed":
        return meeting
    if expected_version != meeting_title_version(meeting):
        raise ProblemDetail(
            status=409, code="meeting_title_conflict", title=TITLE_ERRORS["meeting_title_conflict"]
        )
    previous = normalize_db_timestamp(meeting.title_updated_at)
    now = datetime.now(UTC)
    meeting.title = clean
    meeting.title_source = "user_confirmed"
    meeting.title_updated_at = max(now, previous + timedelta(microseconds=1)) if previous else now
    await db.flush()
    return meeting
