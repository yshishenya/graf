from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.capabilities import PROVIDER_PRESETS, provider_preset_payloads
from twobrain_rec_server.calendar.credentials import seal_credential, sealed_credential_metadata
from twobrain_rec_server.calendar.lifecycle import disconnect_source
from twobrain_rec_server.calendar.sync import future_sync_horizon, record_source_sync_failure
from twobrain_rec_server.db.models import (
    CalendarCredentialEnvelope,
    CalendarEventSnapshot,
    CalendarSource,
    ExternalCalendar,
    Meeting,
    RecordingCalendarContextLink,
)

SUPPORTED_PROVIDER_FAMILIES = {preset.provider_family for preset in PROVIDER_PRESETS}
PROVIDER_LABELS = {preset.provider_family: preset.label for preset in PROVIDER_PRESETS}
PROVIDER_CAPABILITIES = {preset.provider_family: preset.capability_state for preset in PROVIDER_PRESETS}


def list_provider_presets() -> list[dict[str, object]]:
    return provider_preset_payloads()


def require_supported_provider(provider_family: str) -> None:
    if provider_family not in SUPPORTED_PROVIDER_FAMILIES:
        raise ProblemDetail(
            status=400,
            code="unsupported_calendar_provider",
            title="Unsupported calendar provider",
        )


async def list_sources(db: AsyncSession, tenant_scope: TenantScope) -> list[CalendarSource]:
    rows = await db.scalars(select(CalendarSource).where(CalendarSource.workspace_id == tenant_scope.workspace_id))
    return list(rows)


async def get_source(db: AsyncSession, tenant_scope: TenantScope, source_id: UUID) -> CalendarSource:
    source = await db.get(CalendarSource, source_id)
    if source is None or source.workspace_id != tenant_scope.workspace_id:
        raise ProblemDetail(status=404, code="calendar_source_not_found", title="Calendar source not found")
    return source


async def calendars_for_source(db: AsyncSession, source_id: UUID) -> list[ExternalCalendar]:
    rows = await db.scalars(select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source_id))
    return list(rows)


async def connect_source(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    provider_family: str,
    auth_mode: str,
    display_label: str | None,
    credential_input: str | None,
    selected_provider_calendar_ids: list[str],
    credential_key: bytes,
) -> CalendarSource:
    require_supported_provider(provider_family)
    selected_calendar_ids = list(dict.fromkeys(selected_provider_calendar_ids))
    source = CalendarSource(
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=tenant_scope.user_id,
        provider_family=provider_family,
        provider_label=display_label or PROVIDER_LABELS.get(provider_family, provider_family),
        auth_mode=auth_mode,
        credential_state="sealed" if credential_input else "pending",
        connection_state="active",
        sync_state="never_synced",
        selected_calendar_count=len(selected_calendar_ids),
        capabilities_json=PROVIDER_CAPABILITIES.get(provider_family, {}),
    )
    db.add(source)
    await db.flush()
    if credential_input:
        metadata = sealed_credential_metadata(secret=credential_input, secret_kind=auth_mode)
        db.add(
            CalendarCredentialEnvelope(
                calendar_source_id=source.id,
                workspace_id=tenant_scope.workspace_id,
                secret_kind=auth_mode,
                sealed_payload=seal_credential(credential_input, credential_key),
                key_version="local-v1",
                secret_fingerprint_sha256=metadata["secret_fingerprint_sha256"],
            )
        )
    await replace_selected_calendars(db, tenant_scope, source, selected_calendar_ids)
    return source


async def replace_selected_calendars(
    db: AsyncSession,
    tenant_scope: TenantScope,
    source: CalendarSource,
    selected_provider_calendar_ids: list[str],
) -> None:
    selected_ids = list(dict.fromkeys(selected_provider_calendar_ids))
    existing = {calendar.provider_calendar_id: calendar for calendar in await calendars_for_source(db, source.id)}
    for calendar in existing.values():
        calendar.visibility = "available"
    for provider_calendar_id in selected_ids:
        calendar = existing.get(provider_calendar_id)
        if calendar is None:
            db.add(
                ExternalCalendar(
                    calendar_source_id=source.id,
                    workspace_id=tenant_scope.workspace_id,
                    provider_calendar_id=provider_calendar_id,
                    display_label=provider_calendar_id,
                    visibility="selected",
                )
            )
        else:
            calendar.visibility = "selected"
    source.selected_calendar_count = len(selected_ids)


async def request_source_sync(
    db: AsyncSession,
    tenant_scope: TenantScope,
    source_id: UUID,
    *,
    failure_reason: str | None = None,
) -> CalendarSource:
    source = await get_source(db, tenant_scope, source_id)
    now = datetime.now(UTC)
    if failure_reason:
        record_source_sync_failure(source, reason=failure_reason, now=now)
        return source
    horizon_start, horizon_end = future_sync_horizon(now)
    source.sync_horizon_start = horizon_start
    source.sync_horizon_end = horizon_end
    source.last_sync_started_at = now
    source.last_sync_finished_at = now
    source.last_successful_sync_at = now
    source.sync_state = "synced"
    source.last_safe_error_code = None
    return source


async def disconnect_calendar_source(db: AsyncSession, tenant_scope: TenantScope, source_id: UUID) -> dict[str, object]:
    source = await get_source(db, tenant_scope, source_id)
    return await disconnect_source(db, source)


async def list_upcoming_events(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    starts_from: datetime | None = None,
    starts_to: datetime | None = None,
    limit: int = 50,
) -> tuple[list[CalendarEventSnapshot], bool]:
    starts_from = starts_from or datetime.now(UTC)
    starts_to = starts_to or starts_from + timedelta(days=30)
    capped_limit = min(max(limit, 1), 100)
    rows = await db.scalars(
        select(CalendarEventSnapshot)
        .where(
            CalendarEventSnapshot.workspace_id == tenant_scope.workspace_id,
            CalendarEventSnapshot.starts_at >= starts_from,
            CalendarEventSnapshot.starts_at <= starts_to,
            CalendarEventSnapshot.source_deleted_at.is_(None),
        )
        .order_by(CalendarEventSnapshot.starts_at)
        .limit(capped_limit + 1)
    )
    events = list(rows)
    return events[:capped_limit], len(events) > capped_limit


def choose_recording_context(
    events: list[CalendarEventSnapshot],
    *,
    recording_started_at: datetime,
    selected_event_id: UUID | None = None,
) -> tuple[CalendarEventSnapshot | None, str]:
    recording_started_at = _as_utc(recording_started_at)
    if selected_event_id is not None:
        selected = next((event for event in events if event.id == selected_event_id), None)
        if selected is None or _as_utc(selected.ends_at) <= recording_started_at:
            return None, "no_context"
        if _as_utc(selected.starts_at) <= recording_started_at:
            return selected, "selected_current_event"
        return selected, "selected_future_event"
    current = [event for event in events if _as_utc(event.starts_at) <= recording_started_at < _as_utc(event.ends_at)]
    if len(current) == 1:
        return current[0], "current_event"
    if len(current) > 1:
        return None, "ambiguous_current_events"
    return None, "no_context"


async def link_meeting_calendar_context(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    meeting_id: UUID,
    event_id: UUID,
    context_reason: str,
) -> RecordingCalendarContextLink:
    meeting = await db.get(Meeting, meeting_id)
    if meeting is None or meeting.workspace_id != tenant_scope.workspace_id:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    event = await db.get(CalendarEventSnapshot, event_id)
    if event is None or event.workspace_id != tenant_scope.workspace_id:
        raise ProblemDetail(status=404, code="calendar_event_not_found", title="Calendar event not found")
    recording_started_at = _as_utc(meeting.started_at or datetime.now(UTC))
    if _as_utc(event.ends_at) <= recording_started_at:
        raise ProblemDetail(
            status=409,
            code="calendar_event_not_linkable",
            title="Calendar event cannot be linked to this recording",
        )

    existing = await db.scalar(
        select(RecordingCalendarContextLink).where(
            RecordingCalendarContextLink.workspace_id == tenant_scope.workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting_id,
            RecordingCalendarContextLink.unlinked_at.is_(None),
        )
    )
    link = existing or RecordingCalendarContextLink(
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        calendar_event_snapshot_id=event_id,
    )
    if existing is None:
        db.add(link)
    link.calendar_event_snapshot_id = event_id
    link.context_confidence = "high" if context_reason in {"manual_selection", "current_event_prompt", "event_start_prompt"} else "none"
    link.context_reasons_json = [context_reason]
    link.title_source = "calendar" if event.safe_to_use_as_title and not meeting.title else "user_or_generic"
    link.roster_source = "calendar" if (event.provider_extras_json or {}).get("participant_count", 0) else "none"
    link.manual_override_state = context_reason
    link.linked_at = datetime.now(UTC)
    link.unlinked_at = None
    if not meeting.title and event.safe_to_use_as_title and event.title:
        meeting.title = event.title
    return link


async def unlink_meeting_calendar_context(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    meeting_id: UUID,
) -> RecordingCalendarContextLink | None:
    meeting = await db.get(Meeting, meeting_id)
    if meeting is None or meeting.workspace_id != tenant_scope.workspace_id:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    link = await db.scalar(
        select(RecordingCalendarContextLink).where(
            RecordingCalendarContextLink.workspace_id == tenant_scope.workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting_id,
            RecordingCalendarContextLink.unlinked_at.is_(None),
        )
    )
    if link is not None:
        link.unlinked_at = datetime.now(UTC)
        link.manual_override_state = "unlinked"
    return link


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
