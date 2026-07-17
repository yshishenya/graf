import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.matching import consume_recording_calendar_match_attempt
from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.metadata_text import contains_forbidden_metadata_text
from twobrain_rec_server.domain.statuses import MediaRevisionSourceKind
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.media_revisions import normalize_initial_local_media_revision_id
from twobrain_rec_server.ingest.policy import validate_recording_duration
from twobrain_rec_server.ingest.store import (
    MeetingRecord,
    load_meeting_record,
    persist_audit_event,
    persist_meeting,
)

MEETING_TITLE_SOURCES = frozenset(
    {
        "user_confirmed",
        "calendar",
        "app_context",
        "generic",
        "upload_provided",
        "file_name_derived",
        "legacy_unknown",
    }
)

FIRST_PARTY_RECORDING_SOURCE_MODES = {
    MediaRevisionSourceKind.INITIAL_RECORDING.value: "dual",
    MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value: "single_wav_v1",
}


def validate_first_party_recording_source_mode(
    *,
    source_kind: MediaRevisionSourceKind | str,
    media_scribe_source_mode: str | None,
) -> None:
    source_kind_value = str(getattr(source_kind, "value", source_kind))
    expected_mode = FIRST_PARTY_RECORDING_SOURCE_MODES.get(source_kind_value)
    if expected_mode is None:
        raise ProblemDetail(
            status=400,
            code="unsupported_recording_source_kind",
            title="Unsupported first-party recording source kind",
        )
    if media_scribe_source_mode != expected_mode:
        raise ProblemDetail(
            status=400,
            code="invalid_recording_source_mode",
            title="Recording source mode does not match the recording source kind",
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
    title_source: str | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    recording_display_timezone_offset_minutes: int | None = None,
    media_revision_source_kind: MediaRevisionSourceKind = MediaRevisionSourceKind.INITIAL_RECORDING,
    media_scribe_source_mode: str | None = None,
    calendar_match_attempt_id: UUID | None = None,
    consume_calendar_context: bool = False,
) -> MeetingRecord:
    validate_recording_duration(settings, duration_seconds)
    if (
        media_revision_source_kind == MediaRevisionSourceKind.INITIAL_MIXED_RECORDING
        or media_scribe_source_mode is not None
    ):
        validate_first_party_recording_source_mode(
            source_kind=media_revision_source_kind,
            media_scribe_source_mode=media_scribe_source_mode,
        )
    normalized_title_source = normalize_meeting_title_source(
        title=title,
        title_source=title_source,
    )
    create_request_fingerprint = meeting_create_request_fingerprint(
        local_recording_id=local_recording_id,
        local_media_revision_id=local_media_revision_id,
        duration_seconds=duration_seconds,
        title=title,
        title_source=normalized_title_source,
        started_at=started_at,
        ended_at=ended_at,
        recording_display_timezone_offset_minutes=recording_display_timezone_offset_minutes,
        media_revision_source_kind=media_revision_source_kind,
        media_scribe_source_mode=(
            media_scribe_source_mode
            if media_revision_source_kind == MediaRevisionSourceKind.INITIAL_MIXED_RECORDING
            else None
        ),
        calendar_match_attempt_id=calendar_match_attempt_id,
    )
    persisted = await load_meeting_record(
        db,
        workspace_id=tenant_scope.workspace_id,
        created_by_user_id=tenant_scope.user_id,
        local_recording_id=local_recording_id,
    )
    if persisted is not None:
        if (
            local_media_revision_id is not None
            and persisted.local_media_revision_id != local_media_revision_id
        ) or persisted.media_revision_source_kind != media_revision_source_kind:
            raise ProblemDetail(
                status=409,
                code="media_revision_conflict",
                title="Media revision conflicts with existing recording",
            )
        if persisted.create_request_fingerprint_sha256 is not None:
            request_conflicts = (
                persisted.create_request_fingerprint_sha256 != create_request_fingerprint
            )
        else:
            request_conflicts = (
                persisted.duration_seconds != duration_seconds
                or persisted.title != title
                or persisted.title_source != normalized_title_source
                or not same_optional_instant(persisted.started_at, started_at)
                or not same_optional_instant(persisted.ended_at, ended_at)
                or persisted.recording_display_timezone_offset_minutes
                != recording_display_timezone_offset_minutes
                or persisted.media_revision_source_kind != media_revision_source_kind
            )
        if request_conflicts:
            raise ProblemDetail(
                status=409,
                code="idempotency_conflict",
                title="Meeting create conflicts with existing recording",
            )
        if consume_calendar_context and db is not None:
            await consume_recording_calendar_match_attempt(
                db,
                tenant_scope,
                meeting=persisted,
                attempt_id=calendar_match_attempt_id,
            )
        return persisted
    validate_meeting_title_policy(title)
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
        title_source=normalized_title_source,
        media_revision_source_kind=media_revision_source_kind,
    )
    meeting.started_at = started_at
    meeting.ended_at = ended_at
    meeting.recording_display_timezone_offset_minutes = recording_display_timezone_offset_minutes
    if (
        meeting.create_request_fingerprint_sha256 is not None
        and meeting.create_request_fingerprint_sha256 != create_request_fingerprint
    ):
        raise ProblemDetail(
            status=409,
            code="idempotency_conflict",
            title="Meeting create conflicts with existing recording",
        )
    meeting.create_request_fingerprint_sha256 = create_request_fingerprint
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
    if consume_calendar_context and db is not None:
        await consume_recording_calendar_match_attempt(
            db,
            tenant_scope,
            meeting=meeting,
            attempt_id=calendar_match_attempt_id,
        )
    return meeting


def meeting_create_request_fingerprint(
    *,
    local_recording_id: str,
    local_media_revision_id: str | None,
    duration_seconds: int,
    title: str | None,
    title_source: str,
    started_at: datetime | None,
    ended_at: datetime | None,
    recording_display_timezone_offset_minutes: int | None,
    media_revision_source_kind: MediaRevisionSourceKind,
    media_scribe_source_mode: str | None = None,
    calendar_match_attempt_id: UUID | None = None,
) -> str:
    payload = {
        "calendar_match_attempt_id": (
            str(calendar_match_attempt_id) if calendar_match_attempt_id else None
        ),
        "duration_seconds": duration_seconds,
        "ended_at": _canonical_optional_instant(ended_at),
        "local_media_revision_id": normalize_initial_local_media_revision_id(
            local_recording_id,
            local_media_revision_id,
        ),
        "local_recording_id": local_recording_id,
        "media_revision_source_kind": media_revision_source_kind.value,
        "recording_display_timezone_offset_minutes": recording_display_timezone_offset_minutes,
        "started_at": _canonical_optional_instant(started_at),
        "title": title,
        "title_source": title_source,
        "version": 1,
    }
    if media_scribe_source_mode is not None:
        payload["media_scribe_source_mode"] = media_scribe_source_mode
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _canonical_optional_instant(value: datetime | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def normalize_meeting_title_source(*, title: str | None, title_source: str | None) -> str:
    if title is None:
        return "generic"
    if title_source in MEETING_TITLE_SOURCES:
        return str(title_source)
    return "legacy_unknown"


def validate_meeting_title_policy(title: str | None) -> None:
    if title is None:
        return
    if contains_forbidden_metadata_text(title):
        raise ProblemDetail(
            status=400,
            code="unsafe_meeting_title",
            title="Meeting title rejected by metadata policy",
        )


def same_optional_instant(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    left_utc = left.replace(tzinfo=UTC) if left.tzinfo is None else left.astimezone(UTC)
    right_utc = right.replace(tzinfo=UTC) if right.tzinfo is None else right.astimezone(UTC)
    return left_utc == right_utc
