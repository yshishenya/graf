from __future__ import annotations

from collections.abc import Iterable
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
    CalendarSettingsPreference,
    CalendarSource,
    ExternalCalendar,
    Meeting,
    RecordingCalendarContextLink,
)

SELECTABLE_CALENDAR_VISIBILITIES = {
    "available",
    "private",
    "shared",
    "delegated",
    "duplicate_label",
}
SUPPORTED_PROVIDER_FAMILIES = {preset.provider_family for preset in PROVIDER_PRESETS}
PROVIDER_LABELS = {preset.provider_family: preset.label for preset in PROVIDER_PRESETS}
PROVIDER_CAPABILITIES = {
    preset.provider_family: preset.capability_state for preset in PROVIDER_PRESETS
}
PROVIDER_AUTH_MODES = {
    "caldav_yandex": {"app_password"},
    "caldav_mail_ru": {"app_password"},
    "custom_caldav_vk_workspace": {"manual_url"},
    "caldav_mailion_myoffice": {"manual_url"},
    "caldav_r7_office": {"manual_url"},
    "caldav_communigate_pro": {"manual_url"},
    "caldav_rupost": {"manual_url"},
    "caldav_nextcloud_sogo": {"manual_url"},
    "custom_caldav": {"manual_url"},
}


def list_provider_presets() -> list[dict[str, object]]:
    return provider_preset_payloads()


def calendar_duplicate_group_key(event: CalendarEventSnapshot) -> str:
    meeting_link_key = (getattr(event, "conference_summary_json", None) or {}).get("url_hash")
    if meeting_link_key:
        return f"link:{meeting_link_key}"
    provider_event_id = getattr(event, "provider_event_id", None)
    calendar_source_id = getattr(event, "calendar_source_id", None)
    if provider_event_id and calendar_source_id:
        return f"provider:{calendar_source_id}:{provider_event_id}"
    return f"event:{event.id}"


def dedupe_calendar_events(
    events: Iterable[CalendarEventSnapshot],
) -> list[CalendarEventSnapshot]:
    deduped: dict[str, CalendarEventSnapshot] = {}
    for event in events:
        deduped.setdefault(calendar_duplicate_group_key(event), event)
    return list(deduped.values())


def require_supported_provider(provider_family: str) -> None:
    if provider_family not in SUPPORTED_PROVIDER_FAMILIES:
        raise ProblemDetail(
            status=400,
            code="unsupported_calendar_provider",
            title="Unsupported calendar provider",
        )


def require_supported_auth_mode(provider_family: str, auth_mode: str) -> None:
    require_supported_provider(provider_family)
    if auth_mode not in PROVIDER_AUTH_MODES.get(provider_family, set()):
        raise ProblemDetail(
            status=400,
            code="unsupported_calendar_auth_mode",
            title="Unsupported calendar authentication mode",
        )


async def list_sources(db: AsyncSession, tenant_scope: TenantScope) -> list[CalendarSource]:
    rows = await db.scalars(
        select(CalendarSource).where(
            CalendarSource.workspace_id == tenant_scope.workspace_id,
            CalendarSource.owner_user_id == tenant_scope.user_id,
        )
    )
    return list(rows)


async def get_source(
    db: AsyncSession, tenant_scope: TenantScope, source_id: UUID
) -> CalendarSource:
    source = await db.get(CalendarSource, source_id)
    if (
        source is None
        or source.workspace_id != tenant_scope.workspace_id
        or source.owner_user_id != tenant_scope.user_id
    ):
        raise ProblemDetail(
            status=404, code="calendar_source_not_found", title="Calendar source not found"
        )
    return source


async def calendars_for_source(db: AsyncSession, source_id: UUID) -> list[ExternalCalendar]:
    rows = await db.scalars(
        select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source_id)
    )
    return list(rows)


async def load_calendar_settings_preferences(
    db: AsyncSession,
    tenant_scope: TenantScope,
) -> CalendarSettingsPreference:
    preference = await get_calendar_settings_preferences(db, tenant_scope)
    if preference is not None:
        return preference
    preference = CalendarSettingsPreference(
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=tenant_scope.user_id,
    )
    db.add(preference)
    await db.flush()
    return preference


async def get_calendar_settings_preferences(
    db: AsyncSession,
    tenant_scope: TenantScope,
) -> CalendarSettingsPreference | None:
    return await db.scalar(
        select(CalendarSettingsPreference).where(
            CalendarSettingsPreference.workspace_id == tenant_scope.workspace_id,
            CalendarSettingsPreference.owner_user_id == tenant_scope.user_id,
        )
    )


async def save_calendar_settings_preferences(
    db: AsyncSession,
    tenant_scope: TenantScope,
    **updates: bool,
) -> CalendarSettingsPreference:
    preference = await load_calendar_settings_preferences(db, tenant_scope)
    allowed = {
        "join_prompt_enabled",
        "record_prompt_enabled",
        "show_upcoming_time",
        "show_upcoming_title",
        "include_events_without_participants",
        "include_events_without_link_or_location",
        "include_all_day_events",
        "include_private_free_busy_prompt_candidates",
    }
    for key, value in updates.items():
        if key in allowed:
            setattr(preference, key, bool(value))
    await db.flush()
    return preference


async def connect_source(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    provider_family: str,
    auth_mode: str,
    display_label: str | None,
    credential_input: str | None,
    selected_provider_calendar_ids: list[str],
    credential_encryption_key: bytes | None,
) -> CalendarSource:
    require_supported_auth_mode(provider_family, auth_mode)
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
        if credential_encryption_key is None:
            raise ProblemDetail(
                status=503,
                code="credential_encryption_key_unavailable",
                title="Credential encryption key unavailable",
            )
        metadata = sealed_credential_metadata(secret=credential_input, secret_kind=auth_mode)
        db.add(
            CalendarCredentialEnvelope(
                calendar_source_id=source.id,
                workspace_id=tenant_scope.workspace_id,
                secret_kind=auth_mode,
                sealed_payload=seal_credential(credential_input, credential_encryption_key),
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
    *,
    allow_missing: bool = True,
) -> None:
    selected_ids = list(dict.fromkeys(selected_provider_calendar_ids))
    existing = {
        calendar.provider_calendar_id: calendar
        for calendar in await calendars_for_source(db, source.id)
    }
    for calendar in existing.values():
        calendar.selected = False
        if calendar.visibility == "selected":
            calendar.visibility = "available"
    for provider_calendar_id in selected_ids:
        calendar = existing.get(provider_calendar_id)
        if calendar is None:
            if not allow_missing:
                continue
            db.add(
                ExternalCalendar(
                    calendar_source_id=source.id,
                    workspace_id=tenant_scope.workspace_id,
                    provider_calendar_id=provider_calendar_id,
                    display_label=provider_calendar_id,
                    visibility="available",
                    selected=True,
                )
            )
        elif calendar.visibility in SELECTABLE_CALENDAR_VISIBILITIES:
            calendar.selected = True
    source.selected_calendar_count = sum(1 for calendar in existing.values() if calendar.selected)
    if allow_missing:
        source.selected_calendar_count += sum(
            1 for provider_calendar_id in selected_ids if provider_calendar_id not in existing
        )


async def request_source_sync(
    db: AsyncSession,
    tenant_scope: TenantScope,
    source_id: UUID,
    *,
    failure_reason: str | None = None,
) -> CalendarSource:
    source = await get_source(db, tenant_scope, source_id)
    if source.disconnected_at is not None or source.connection_state == "disconnected":
        source.sync_state = "failed_closed"
        return source
    if source.connection_state in {"disabled", "disabled_by_policy", "needs_action"}:
        return source
    if source.sync_state in {"queued", "syncing"}:
        return source
    if source.sync_state in {
        "credential_failed",
        "provider_unavailable",
        "rate_limited",
        "failed_closed",
    }:
        return source
    now = datetime.now(UTC)
    if failure_reason:
        record_source_sync_failure(source, reason=failure_reason, now=now)
        return source
    horizon_start, horizon_end = future_sync_horizon(now)
    source.sync_horizon_start = horizon_start
    source.sync_horizon_end = horizon_end
    source.last_sync_started_at = now
    source.sync_state = "queued"
    source.last_safe_error_code = None
    return source


async def disconnect_calendar_source(
    db: AsyncSession, tenant_scope: TenantScope, source_id: UUID
) -> dict[str, object]:
    source = await get_source(db, tenant_scope, source_id)
    return await disconnect_source(db, source)


async def list_upcoming_events(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    starts_from: datetime | None = None,
    starts_to: datetime | None = None,
    limit: int = 50,
    preference: CalendarSettingsPreference | None = None,
) -> tuple[list[CalendarEventSnapshot], bool]:
    starts_from = starts_from or datetime.now(UTC)
    starts_to = starts_to or starts_from + timedelta(days=30)
    capped_limit = min(max(limit, 1), 100)
    query = (
        select(CalendarEventSnapshot)
        .join(ExternalCalendar, CalendarEventSnapshot.external_calendar_id == ExternalCalendar.id)
        .join(CalendarSource, CalendarEventSnapshot.calendar_source_id == CalendarSource.id)
        .where(
            CalendarEventSnapshot.workspace_id == tenant_scope.workspace_id,
            CalendarSource.workspace_id == tenant_scope.workspace_id,
            CalendarSource.owner_user_id == tenant_scope.user_id,
            ExternalCalendar.workspace_id == tenant_scope.workspace_id,
            ExternalCalendar.selected.is_(True),
            ExternalCalendar.visibility.in_(SELECTABLE_CALENDAR_VISIBILITIES),
            CalendarEventSnapshot.ends_at > starts_from,
            CalendarEventSnapshot.starts_at <= starts_to,
            CalendarEventSnapshot.source_deleted_at.is_(None),
        )
        .order_by(CalendarEventSnapshot.starts_at)
    )
    query = _apply_calendar_preference_query_filters(query, preference)
    fetch_limit = min(max(capped_limit * 5, capped_limit + 1), 500)
    query = query.limit(fetch_limit + 1)
    rows = await db.scalars(query)
    events = list(rows)
    reached_fetch_cap = len(events) > fetch_limit
    events = events[:fetch_limit]
    if preference is not None:
        events = [event for event in events if calendar_event_matches_preferences(event, preference)]
    return events[:capped_limit], reached_fetch_cap or len(events) > capped_limit


def _apply_calendar_preference_query_filters(query, preference: CalendarSettingsPreference | None):
    if preference is None:
        return query
    if not preference.include_all_day_events:
        query = query.where(CalendarEventSnapshot.all_day.is_(False))
    if not preference.include_private_free_busy_prompt_candidates:
        query = query.where(
            CalendarEventSnapshot.safe_to_show_in_list.is_(True),
            CalendarEventSnapshot.privacy_class.notin_(
                {"private", "free_busy", "free_busy_only"}
            ),
        )
    return query


def calendar_event_matches_preferences(
    event: CalendarEventSnapshot,
    preference: CalendarSettingsPreference | None,
) -> bool:
    include_all_day = bool(preference.include_all_day_events) if preference else False
    include_private = (
        bool(preference.include_private_free_busy_prompt_candidates) if preference else False
    )
    include_no_participants = (
        bool(preference.include_events_without_participants) if preference else False
    )
    include_no_link_or_location = (
        bool(preference.include_events_without_link_or_location) if preference else False
    )
    if event.all_day and not include_all_day:
        return False
    if (
        event.privacy_class in {"private", "free_busy", "free_busy_only"}
        or not event.safe_to_show_in_list
    ):
        return include_private
    participant_count = _event_participant_count(event)
    has_link_or_location = bool(
        (event.conference_summary_json or {}).get("meeting_link_present") or event.location
    )
    if participant_count > 0 or has_link_or_location:
        return True
    if not include_no_participants:
        return False
    return bool(include_no_link_or_location)


def _event_participant_count(event: CalendarEventSnapshot) -> int:
    conference = event.conference_summary_json or {}
    provider_extras = event.provider_extras_json or {}
    raw = conference.get("participant_count", provider_extras.get("participant_count", 0))
    try:
        return max(int(raw or 0), 0)
    except (TypeError, ValueError):
        return 0


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
    current = [
        event
        for event in dedupe_calendar_events(events)
        if _as_utc(event.starts_at) <= recording_started_at < _as_utc(event.ends_at)
    ]
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
    if (
        meeting is None
        or meeting.workspace_id != tenant_scope.workspace_id
        or meeting.created_by_user_id != tenant_scope.user_id
    ):
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    event = await db.get(CalendarEventSnapshot, event_id)
    if event is None or event.workspace_id != tenant_scope.workspace_id:
        raise ProblemDetail(
            status=404, code="calendar_event_not_found", title="Calendar event not found"
        )
    source = await db.get(CalendarSource, event.calendar_source_id)
    if (
        source is None
        or source.workspace_id != tenant_scope.workspace_id
        or source.owner_user_id != tenant_scope.user_id
    ):
        raise ProblemDetail(
            status=404, code="calendar_event_not_found", title="Calendar event not found"
        )
    calendar = await db.get(ExternalCalendar, event.external_calendar_id)
    if (
        calendar is None
        or calendar.workspace_id != tenant_scope.workspace_id
        or calendar.calendar_source_id != source.id
        or not calendar.selected
        or calendar.visibility not in SELECTABLE_CALENDAR_VISIBILITIES
    ):
        raise ProblemDetail(
            status=404, code="calendar_event_not_found", title="Calendar event not found"
        )
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
    link.context_confidence = (
        "high"
        if context_reason in {"manual_selection", "current_event_prompt", "event_start_prompt"}
        else "none"
    )
    link.context_reasons_json = [context_reason]
    link.title_source = (
        "calendar" if event.safe_to_use_as_title and not meeting.title else "user_or_generic"
    )
    link.roster_source = (
        "calendar" if (event.provider_extras_json or {}).get("participant_count", 0) else "none"
    )
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
    if (
        meeting is None
        or meeting.workspace_id != tenant_scope.workspace_id
        or meeting.created_by_user_id != tenant_scope.user_id
    ):
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
