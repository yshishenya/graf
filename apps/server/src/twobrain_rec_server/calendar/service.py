from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    CalendarContextCandidateView,
    CalendarContextRosterView,
    CalendarRosterSnapshotItem,
    MeetingCalendarContextResponse,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.cabinet.access import ShareRecipientAccessProof, decide_meeting_access
from twobrain_rec_server.calendar.audit import (
    calendar_match_audit_metadata,
    write_calendar_audit_event,
)
from twobrain_rec_server.calendar.capabilities import PROVIDER_PRESETS, provider_preset_payloads
from twobrain_rec_server.calendar.credentials import seal_credential, sealed_credential_metadata
from twobrain_rec_server.calendar.lifecycle import disconnect_source
from twobrain_rec_server.calendar.matching import (
    MAX_CANDIDATE_ROWS,
    MAX_SELECTED_SOURCES,
    MAX_VISIBLE_CANDIDATES,
    PRESTART_GRACE,
    RECENTLY_ENDED_GUARD,
    calendar_event_recurring_series_fingerprint,
    calendar_event_source_version_fingerprint,
    is_safe_calendar_context_candidate,
    safe_calendar_event_title,
)
from twobrain_rec_server.calendar.sync import future_sync_horizon, record_source_sync_failure
from twobrain_rec_server.db.models import (
    CalendarCredentialEnvelope,
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSettingsPreference,
    CalendarSource,
    ExternalCalendar,
    Meeting,
    RecordingCalendarContextLink,
)
from twobrain_rec_server.domain.metadata_text import safe_metadata_text
from twobrain_rec_server.processing.fences import meeting_is_deleted_or_deleting

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
EXPLICIT_CONTEXT_REASONS = {
    "manual_selection",
    "ambiguity_resolution",
    "correction",
    "current_event_prompt",
    "event_start_prompt",
}
AUTHORITATIVE_NON_CALENDAR_TITLE_SOURCES = {
    "user_confirmed",
    "upload_provided",
    "file_name_derived",
    "legacy_unknown",
    "user",
    "user_or_generic",
    "unknown",
}
VALID_CONTEXT_STATES = {
    "matched_auto",
    "matched_user",
    "ambiguous",
    "no_context",
    "skipped_private",
    "skipped_all_day",
    "skipped_stale_calendar",
    "calendar_unavailable",
    "skipped_offline_or_unknown",
    "skipped_manual_upload",
    "declined_by_user",
    "cleared_by_user",
    "deleted",
    "legacy_linked",
}
VALID_CONTEXT_CONFIDENCE = {"high", "selected", "ambiguous", "none"}
VALID_CONTEXT_DECISION_SOURCES = {"automatic", "user", "system_skip", "legacy"}
VALID_CONTEXT_REASON_CODES = {
    "single_fresh_candidate",
    "multiple_time_candidates",
    "back_to_back_boundary",
    "no_matching_event",
    "weak_event_signal",
    "private_free_busy_skipped",
    "all_day_skipped",
    "selected_source_stale",
    "latest_sync_failed",
    "calendar_not_connected",
    "calendar_not_selected",
    "calendar_unavailable",
    "manual_upload_skipped",
    "offline_or_unknown_skipped",
    "prestart_not_reached",
    "user_selected",
    "user_declined",
    "user_cleared",
    "meeting_deleted",
}
VALID_MEETING_TITLE_SOURCES = {
    "user_confirmed",
    "calendar",
    "app_context",
    "generic",
    "upload_provided",
    "file_name_derived",
    "legacy_unknown",
    "user",
    "user_or_generic",
    "unknown",
}


def list_provider_presets() -> list[dict[str, object]]:
    return provider_preset_payloads()


def calendar_duplicate_group_key(event: CalendarEventSnapshot) -> str:
    conference_summary = getattr(event, "conference_summary_json", None) or {}
    bounded_hashes = conference_summary.get("url_hashes") or ()
    normalized_hashes = sorted(str(value) for value in bounded_hashes if value)
    meeting_link_key = (
        normalized_hashes[0] if normalized_hashes else conference_summary.get("url_hash")
    )
    if meeting_link_key:
        return f"link:{meeting_link_key}"
    provider_event_id = getattr(event, "provider_event_id", None)
    calendar_source_id = getattr(event, "calendar_source_id", None)
    external_calendar_id = getattr(event, "external_calendar_id", None)
    if provider_event_id and calendar_source_id and external_calendar_id:
        return f"provider:{calendar_source_id}:{external_calendar_id}:{provider_event_id}"
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
        events = [
            event for event in events if calendar_event_matches_preferences(event, preference)
        ]
    return events[:capped_limit], reached_fetch_cap or len(events) > capped_limit


def _apply_calendar_preference_query_filters(query, preference: CalendarSettingsPreference | None):
    if preference is None:
        return query
    if not preference.include_all_day_events:
        query = query.where(CalendarEventSnapshot.all_day.is_(False))
    if not preference.include_private_free_busy_prompt_candidates:
        query = query.where(
            CalendarEventSnapshot.safe_to_show_in_list.is_(True),
            CalendarEventSnapshot.privacy_class.notin_({"private", "free_busy", "free_busy_only"}),
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
    if context_reason not in EXPLICIT_CONTEXT_REASONS:
        raise ProblemDetail(
            status=400,
            code="invalid_calendar_context_reason",
            title="Invalid calendar context reason",
        )
    # The meeting row is the serialization boundary even when the context row
    # does not exist yet.  This prevents concurrent owner choices from creating
    # competing authoritative rows.
    meeting = await db.scalar(
        select(Meeting)
        .where(
            Meeting.id == meeting_id,
            Meeting.workspace_id == tenant_scope.workspace_id,
            Meeting.created_by_user_id == tenant_scope.user_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if meeting_is_deleted_or_deleting(meeting):
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is active")
    choice = await _owner_event_choice_data(
        db,
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=tenant_scope.user_id,
        event_id=event_id,
        required=True,
    )
    assert choice is not None
    event, source, _calendar, participants, participant_count = choice
    if meeting.started_at is not None and _as_utc(event.ends_at) + RECENTLY_ENDED_GUARD < _as_utc(
        meeting.started_at
    ):
        raise ProblemDetail(
            status=409,
            code="calendar_event_not_linkable",
            title="Calendar event cannot be linked to this recording",
        )
    existing = await db.scalar(
        select(RecordingCalendarContextLink)
        .where(
            RecordingCalendarContextLink.workspace_id == tenant_scope.workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    link = existing or RecordingCalendarContextLink(
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        calendar_event_snapshot_id=event_id,
    )
    if existing is None:
        db.add(link)
    now = datetime.now(UTC)
    link.calendar_event_snapshot_id = event_id
    link.context_state = "matched_user"
    link.context_confidence = "selected"
    link.context_reasons_json = [context_reason]
    safe_title = safe_calendar_event_title(event)
    original_title_source = meeting.title_source
    title_replaceable = original_title_source in {"app_context", "generic", "calendar"}
    title_applied = bool(safe_title and title_replaceable)
    if title_applied:
        meeting.title = safe_title
        meeting.title_source = "calendar"
        meeting.title_updated_at = now
    link.title_source = meeting.title_source
    link.manual_override_state = context_reason
    link.safe_reason_code = "user_selected"
    link.decision_source = "user"
    link.matcher_version = None
    link.evaluated_at = now
    link.candidate_event_ids_json = []
    link.candidate_count = 0
    link.matched_event_starts_at = event.starts_at
    link.matched_event_ends_at = event.ends_at
    link.matched_title = safe_title
    link.matched_title_state = (
        "available"
        if safe_title
        else "policy_hidden"
        if not event.safe_to_use_as_title
        else "unavailable"
    )
    link.matched_roster_json = [_participant_snapshot(participant) for participant in participants]
    link.matched_roster_count = max(
        participant_count,
        _event_participant_count(event),
    )
    link.matched_roster_state = "available" if link.matched_roster_count else "not_available"
    link.roster_source = "calendar" if link.matched_roster_state == "available" else "none"
    link.recurring_series_key_sha256 = calendar_event_recurring_series_fingerprint(event)
    link.source_version_fingerprint_sha256 = calendar_event_source_version_fingerprint(event)
    link.linked_at = now
    link.unlinked_at = None
    await db.flush()
    await _write_explicit_context_audit(
        db,
        tenant_scope,
        meeting_id=meeting_id,
        event_id=event.id,
        source_id=source.id,
        outcome="matched_user",
        safe_reason_code="user_selected",
        roster_count=link.matched_roster_count,
        title_applied=title_applied,
        user_override_preserved=(
            True
            if not title_applied
            and original_title_source in AUTHORITATIVE_NON_CALENDAR_TITLE_SOURCES
            else None
        ),
    )
    return link


async def unlink_meeting_calendar_context(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    meeting_id: UUID,
) -> RecordingCalendarContextLink:
    meeting = await db.scalar(
        select(Meeting)
        .where(
            Meeting.id == meeting_id,
            Meeting.workspace_id == tenant_scope.workspace_id,
            Meeting.created_by_user_id == tenant_scope.user_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if meeting_is_deleted_or_deleting(meeting):
        raise ProblemDetail(status=409, code="meeting_deletion_active", title="Meeting deletion is active")
    link = await db.scalar(
        select(RecordingCalendarContextLink)
        .where(
            RecordingCalendarContextLink.workspace_id == tenant_scope.workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if link is None:
        link = RecordingCalendarContextLink(
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
        )
        db.add(link)
    now = datetime.now(UTC)
    link.unlinked_at = now
    link.manual_override_state = "cleared_by_user"
    link.calendar_event_snapshot_id = None
    link.context_state = "cleared_by_user"
    link.context_confidence = "none"
    link.context_reasons_json = ["user_cleared"]
    link.title_source = meeting.title_source
    link.roster_source = "none"
    link.safe_reason_code = "user_cleared"
    link.decision_source = "user"
    link.matcher_version = None
    link.evaluated_at = now
    link.candidate_event_ids_json = []
    link.candidate_count = 0
    link.matched_event_starts_at = None
    link.matched_event_ends_at = None
    link.matched_title = None
    link.matched_title_state = "unavailable"
    link.matched_roster_json = []
    link.matched_roster_state = "not_available"
    link.matched_roster_count = 0
    link.recurring_series_key_sha256 = None
    link.source_version_fingerprint_sha256 = None
    await db.flush()
    await _write_explicit_context_audit(
        db,
        tenant_scope,
        meeting_id=meeting_id,
        event_id=None,
        source_id=None,
        outcome="cleared_by_user",
        safe_reason_code="user_cleared",
        roster_count=0,
        title_applied=False,
    )
    return link


async def get_meeting_calendar_context_response(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    viewer_user_id: UUID,
    meeting_id: UUID,
    recipient_proof: ShareRecipientAccessProof | None = None,
) -> MeetingCalendarContextResponse:
    """Project one authorization-aware, metadata-bounded context response."""

    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == meeting_id,
        )
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    access = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=viewer_user_id,
        recipient_proof=recipient_proof,
    )
    if not access.can_view:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    owner = meeting.created_by_user_id == viewer_user_id
    link = await db.scalar(
        select(RecordingCalendarContextLink).where(
            RecordingCalendarContextLink.workspace_id == workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting_id,
        )
    )
    if link is None:
        return MeetingCalendarContextResponse(
            meeting_id=meeting.id,
            context_state="no_context",
            title_source=_safe_title_source(meeting.title_source),
            can_change=False,
            can_clear=False,
        )

    raw_state = link.context_state if link.context_state in VALID_CONTEXT_STATES else "no_context"
    matched_state = raw_state in {"matched_auto", "matched_user", "legacy_linked"}
    public_state = raw_state if owner or matched_state else "no_context"
    matched_title = (
        safe_metadata_text(link.matched_title, max_length=500)
        if matched_state and link.matched_title_state == "available"
        else None
    )
    matched_starts_at, matched_ends_at = _safe_matched_event_interval(link, matched_state)
    candidates = (
        await _owner_context_candidates(
            db,
            workspace_id=workspace_id,
            owner_user_id=viewer_user_id,
            candidate_ids=link.candidate_event_ids_json or [],
        )
        if owner
        else []
    )
    roster = _context_roster_view(link) if matched_state else None
    can_change = owner and raw_state != "deleted"
    can_clear = owner and raw_state not in {"cleared_by_user", "deleted"}
    context_confidence = (
        link.context_confidence
        if (owner or matched_state) and link.context_confidence in VALID_CONTEXT_CONFIDENCE
        else "none"
    )
    return MeetingCalendarContextResponse(
        meeting_id=meeting.id,
        event_id=link.calendar_event_snapshot_id if owner and matched_state else None,
        context_state=public_state,
        context_confidence=context_confidence,
        reason_code=(
            link.safe_reason_code
            if owner and link.safe_reason_code in VALID_CONTEXT_REASON_CODES
            else None
        ),
        decision_source=(
            link.decision_source
            if matched_state and link.decision_source in VALID_CONTEXT_DECISION_SOURCES
            else link.decision_source
            if owner and link.decision_source in VALID_CONTEXT_DECISION_SOURCES
            else None
        ),
        title_source=_safe_title_source(link.title_source or meeting.title_source),
        matched_title=matched_title,
        matched_event_starts_at=matched_starts_at,
        matched_event_ends_at=matched_ends_at,
        candidate_count=max(int(link.candidate_count or 0), 0) if owner else 0,
        candidates=candidates,
        roster=roster,
        previous_recurring_meeting=None,
        can_change=can_change,
        can_clear=can_clear,
    )


def _safe_matched_event_interval(
    link: RecordingCalendarContextLink,
    matched_state: bool,
) -> tuple[datetime | None, datetime | None]:
    if not matched_state:
        return None, None
    starts_at = link.matched_event_starts_at
    ends_at = link.matched_event_ends_at
    if starts_at is None or ends_at is None:
        return None, None
    normalized_start = _as_utc(starts_at)
    normalized_end = _as_utc(ends_at)
    if normalized_end <= normalized_start:
        return None, None
    return normalized_start, normalized_end


async def list_owner_context_correction_candidates(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    owner_user_id: UUID,
    meeting_id: UUID,
) -> list[CalendarContextCandidateView]:
    """Load bounded, owner-safe events near the immutable recording start."""

    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.id == meeting_id,
            Meeting.workspace_id == workspace_id,
            Meeting.created_by_user_id == owner_user_id,
        )
    )
    if meeting is None or meeting.started_at is None:
        return []

    source_ids = list(
        await db.scalars(
            select(CalendarSource.id)
            .where(
                CalendarSource.workspace_id == workspace_id,
                CalendarSource.owner_user_id == owner_user_id,
                CalendarSource.connection_state == "active",
                CalendarSource.disconnected_at.is_(None),
                CalendarSource.selected_calendar_count > 0,
            )
            .order_by(CalendarSource.id)
            .limit(MAX_SELECTED_SOURCES + 1)
        )
    )
    if not source_ids or len(source_ids) > MAX_SELECTED_SOURCES:
        return []

    calendar_ids = list(
        await db.scalars(
            select(ExternalCalendar.id).where(
                ExternalCalendar.workspace_id == workspace_id,
                ExternalCalendar.calendar_source_id.in_(source_ids),
                ExternalCalendar.selected.is_(True),
                ExternalCalendar.visibility.in_(SELECTABLE_CALENDAR_VISIBILITIES),
            )
        )
    )
    if not calendar_ids:
        return []

    recording_start = _as_utc(meeting.started_at)
    events = list(
        await db.scalars(
            select(CalendarEventSnapshot)
            .where(
                CalendarEventSnapshot.workspace_id == workspace_id,
                CalendarEventSnapshot.calendar_source_id.in_(source_ids),
                CalendarEventSnapshot.external_calendar_id.in_(calendar_ids),
                CalendarEventSnapshot.source_deleted_at.is_(None),
                CalendarEventSnapshot.starts_at <= recording_start + PRESTART_GRACE,
                CalendarEventSnapshot.ends_at >= recording_start - RECENTLY_ENDED_GUARD,
            )
            .order_by(CalendarEventSnapshot.starts_at, CalendarEventSnapshot.id)
            .limit(MAX_CANDIDATE_ROWS + 1)
        )
    )
    if len(events) > MAX_CANDIDATE_ROWS:
        return []

    deduped = dedupe_calendar_events(events)
    return await _owner_context_candidates(
        db,
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        candidate_ids=[event.id for event in deduped[:MAX_VISIBLE_CANDIDATES]],
    )


async def _owner_context_candidates(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    owner_user_id: UUID,
    candidate_ids: Iterable[object],
) -> list[CalendarContextCandidateView]:
    ordered_ids: list[UUID] = []
    for raw_id in candidate_ids:
        try:
            candidate_id = UUID(str(raw_id))
        except (TypeError, ValueError):
            continue
        if candidate_id not in ordered_ids:
            ordered_ids.append(candidate_id)
        if len(ordered_ids) == 10:
            break
    projected: list[CalendarContextCandidateView] = []
    for event_id in ordered_ids:
        choice = await _owner_event_choice_data(
            db,
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            event_id=event_id,
            required=False,
        )
        if choice is None:
            continue
        event, source, calendar, _participants, participant_count = choice
        projected.append(
            CalendarContextCandidateView(
                event_id=event.id,
                safe_title=safe_calendar_event_title(event),
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                safe_source_label=(
                    safe_metadata_text(calendar.display_label, max_length=160)
                    or safe_metadata_text(source.provider_label, max_length=160)
                    or "Календарь"
                ),
                roster_state="available" if participant_count else "not_available",
                participant_count=participant_count,
            )
        )
    return projected


async def _owner_event_choice_data(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    owner_user_id: UUID,
    event_id: UUID,
    required: bool,
) -> (
    tuple[
        CalendarEventSnapshot,
        CalendarSource,
        ExternalCalendar,
        list[CalendarParticipant],
        int,
    ]
    | None
):
    event = await db.get(CalendarEventSnapshot, event_id)
    if event is None or event.workspace_id != workspace_id:
        return _missing_event_choice(required)
    source = await db.get(CalendarSource, event.calendar_source_id)
    if (
        source is None
        or source.workspace_id != workspace_id
        or source.owner_user_id != owner_user_id
    ):
        return _missing_event_choice(required)
    calendar = await db.get(ExternalCalendar, event.external_calendar_id)
    if (
        calendar is None
        or calendar.workspace_id != workspace_id
        or calendar.calendar_source_id != source.id
        or not calendar.selected
        or calendar.visibility not in SELECTABLE_CALENDAR_VISIBILITIES
    ):
        return _missing_event_choice(required)
    participant_count = int(
        await db.scalar(
            select(func.count(CalendarParticipant.id)).where(
                CalendarParticipant.workspace_id == workspace_id,
                CalendarParticipant.calendar_event_snapshot_id == event.id,
            )
        )
        or 0
    )
    if (
        source.connection_state != "active"
        or source.disconnected_at is not None
        or not is_safe_calendar_context_candidate(
            event,
            participant_count=participant_count,
        )
    ):
        if required:
            raise ProblemDetail(
                status=409,
                code="calendar_event_not_linkable",
                title="Calendar event cannot be linked to this recording",
            )
        return None
    participants = list(
        await db.scalars(
            select(CalendarParticipant)
            .where(
                CalendarParticipant.workspace_id == workspace_id,
                CalendarParticipant.calendar_event_snapshot_id == event.id,
            )
            .order_by(
                CalendarParticipant.participant_kind.asc(),
                CalendarParticipant.display_name.asc(),
                CalendarParticipant.id.asc(),
            )
            .limit(100)
        )
    )
    return event, source, calendar, participants, participant_count


def _missing_event_choice(required: bool) -> None:
    if required:
        raise ProblemDetail(
            status=404,
            code="calendar_event_not_found",
            title="Calendar event not found",
        )
    return None


def _context_roster_view(
    link: RecordingCalendarContextLink,
) -> CalendarContextRosterView | None:
    if link.matched_roster_state != "available" or link.matched_roster_count <= 0:
        return None
    participants: list[CalendarRosterSnapshotItem] = []
    for raw in (link.matched_roster_json or [])[:100]:
        if not isinstance(raw, Mapping):
            continue
        participants.append(
            CalendarRosterSnapshotItem(
                participant_kind=_safe_text(raw.get("participant_kind"), 80) or "unknown",
                response_status=_safe_text(raw.get("response_status"), 80) or "unknown",
                display_name=safe_metadata_text(raw.get("display_name"), max_length=240),
                email_present=bool(raw.get("email_present")),
                workspace_relation=_safe_text(raw.get("workspace_relation"), 80) or "unknown",
                recipient_candidate_class=(
                    _safe_text(raw.get("recipient_candidate_class"), 80) or "unknown"
                ),
            )
        )
    return CalendarContextRosterView(
        roster_state="available",
        participant_count=max(int(link.matched_roster_count or 0), len(participants)),
        participants=participants,
    )


def _participant_snapshot(participant: CalendarParticipant) -> dict[str, object]:
    return {
        "participant_kind": _safe_text(participant.participant_kind, 80) or "unknown",
        "response_status": _safe_text(participant.response_status, 80) or "unknown",
        "display_name": safe_metadata_text(participant.display_name, max_length=240),
        "email_present": bool(participant.email_hash or participant.email),
        "workspace_relation": _safe_text(participant.workspace_relation, 80) or "unknown",
        "recipient_candidate_class": (
            _safe_text(participant.recipient_candidate_class, 80) or "unknown"
        ),
    }


async def _write_explicit_context_audit(
    db: AsyncSession,
    tenant_scope: TenantScope,
    *,
    meeting_id: UUID,
    event_id: UUID | None,
    source_id: UUID | None,
    outcome: str,
    safe_reason_code: str,
    roster_count: int,
    title_applied: bool,
    user_override_preserved: bool | None = None,
) -> None:
    metadata = calendar_match_audit_metadata(
        {
            "context_state": outcome,
            "safe_reason_code": safe_reason_code,
            "candidate_count": 0,
            "roster_count": roster_count,
            "decision_source": "user",
            "title_applied": title_applied,
            "user_override_preserved": user_override_preserved,
        }
    )
    await write_calendar_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        calendar_source_id=source_id,
        calendar_event_snapshot_id=event_id,
        meeting_id=meeting_id,
        actor_user_id=tenant_scope.user_id,
        device_id=tenant_scope.device_id,
        event_type="calendar_context_owner_mutation",
        outcome=outcome,
        safe_reason_code=safe_reason_code,
        metadata=metadata,
    )


def _safe_title_source(value: object) -> str | None:
    text = str(value) if value is not None else None
    return text if text in VALID_MEETING_TITLE_SOURCES else None


def _safe_text(value: object, max_length: int) -> str | None:
    if value is None:
        return None
    text = "".join(
        character for character in str(value) if ord(character) >= 32 and ord(character) != 127
    ).strip()
    return text[:max_length] if text else None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
