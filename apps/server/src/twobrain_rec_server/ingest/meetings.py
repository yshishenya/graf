import re
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.policy import validate_recording_duration
from twobrain_rec_server.ingest.store import (
    MeetingRecord,
    load_meeting_record,
    persist_audit_event,
    persist_meeting,
)

UNSAFE_MEETING_TITLE_RE = re.compile(
    r"https?://|www\.|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|token=|password|bearer\s|(?:^|[^A-Z0-9])sk-[A-Z0-9_-]{8,}|\b(?:meet\.google\.com/[A-Z0-9_-]+|zoom\.us/(?:j|my)/[A-Z0-9._-]+|teams\.microsoft\.com/l/meetup-join|whereby\.com/[A-Z0-9_-]+|webex\.com/meet/[A-Z0-9._-]+)",
    re.IGNORECASE,
)


async def create_or_get_meeting(
    *,
    settings: Settings,
    tenant_scope: TenantScope,
    db: AsyncSession | None = None,
    local_recording_id: str,
    local_media_revision_id: str | None = None,
    duration_seconds: int,
    title: str | None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> MeetingRecord:
    validate_recording_duration(settings, duration_seconds)
    validate_meeting_title_policy(title)
    persisted = await load_meeting_record(
        db,
        workspace_id=tenant_scope.workspace_id,
        local_recording_id=local_recording_id,
    )
    if persisted is not None:
        if persisted.duration_seconds != duration_seconds or persisted.title != title:
            raise ProblemDetail(status=409, code="idempotency_conflict", title="Meeting create conflicts with existing recording")
        if local_media_revision_id is not None and persisted.local_media_revision_id != local_media_revision_id:
            raise ProblemDetail(status=409, code="media_revision_conflict", title="Media revision conflicts with existing recording")
        return persisted
    meeting = store_module.store.create_or_get_meeting(
        settings=settings,
        organization_id=tenant_scope.organization_id,
        workspace_id=tenant_scope.workspace_id,
        user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        local_recording_id=local_recording_id,
        local_media_revision_id=local_media_revision_id,
        duration_seconds=duration_seconds,
        title=title,
    )
    meeting.started_at = started_at
    meeting.ended_at = ended_at
    event = record_audit_event(
        event_type="meeting_created",
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        metadata={"local_recording_id": local_recording_id},
    )
    await persist_meeting(db, meeting, commit=False)
    await persist_audit_event(db, event, commit=False)
    return meeting


def validate_meeting_title_policy(title: str | None) -> None:
    if title is None:
        return
    if UNSAFE_MEETING_TITLE_RE.search(title) or any(ord(char) < 32 or ord(char) == 127 for char in title):
        raise ProblemDetail(
            status=400,
            code="unsafe_meeting_title",
            title="Meeting title rejected by metadata policy",
        )
