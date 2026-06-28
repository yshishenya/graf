from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    CalendarDisconnectResponse,
    CalendarEventSummary,
    CalendarProviderListResponse,
    CalendarSourceListResponse,
    CalendarSourceResponse,
    CalendarSourceSummary,
    CalendarSyncResponse,
    ConnectCalendarSourceRequest,
    DesktopCalendarPromptEvent,
    DesktopCalendarPromptResponse,
    ExternalCalendarSummary,
    MeetingCalendarContextResponse,
    PutMeetingCalendarContextRequest,
    SelectCalendarsRequest,
    UpcomingCalendarEventsResponse,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.dependencies import get_principal, get_tenant_scope
from twobrain_rec_server.calendar.credentials import (
    calendar_connection_secret,
    generate_credential_key,
)
from twobrain_rec_server.calendar.service import (
    calendars_for_source,
    connect_source,
    dedupe_calendar_events,
    disconnect_calendar_source,
    get_calendar_settings_preferences,
    get_source,
    link_meeting_calendar_context,
    list_provider_presets,
    list_sources,
    list_upcoming_events,
    replace_selected_calendars,
    request_source_sync,
    require_supported_auth_mode,
    unlink_meeting_calendar_context,
)
from twobrain_rec_server.db.models import (
    CalendarEventSnapshot,
    CalendarSettingsPreference,
    CalendarSource,
    ExternalCalendar,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope

router = APIRouter(prefix="/api/v1", tags=["calendar"])
PrincipalDependency = Depends(get_principal)
TenantDependency = Depends(get_tenant_scope)


async def get_request_db_session(
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        await apply_tenant_scope(session, tenant_scope)
        yield session


DbDependency = Depends(get_request_db_session)


async def commit_if_available(db: AsyncSession | None) -> None:
    if db is not None:
        await db.commit()


def require_db(db: AsyncSession | None) -> AsyncSession:
    if db is None:
        raise ProblemDetail(
            status=503, code="calendar_store_unavailable", title="Calendar store unavailable"
        )
    return db


def _credential_key(request: Request) -> bytes:
    key = getattr(request.app.state, "calendar_credential_key", None)
    if key is None:
        settings = request.app.state.settings
        key_file = getattr(settings, "calendar_credential_key_file", None)
        if key_file is not None:
            try:
                key = key_file.read_text(encoding="utf-8").strip().encode("utf-8")
                Fernet(key)
            except (OSError, ValueError) as exc:
                raise ProblemDetail(
                    status=503,
                    code="calendar_credential_key_unavailable",
                    title="Calendar credential key unavailable",
                ) from exc
        elif settings.env.lower() == "production":
            raise ProblemDetail(
                status=503,
                code="calendar_credential_key_unavailable",
                title="Calendar credential key unavailable",
            )
        else:
            key = generate_credential_key()
        request.app.state.calendar_credential_key = key
    return key


def _connect_credential_input(payload: ConnectCalendarSourceRequest) -> str | None:
    require_supported_auth_mode(payload.provider_family, payload.auth_mode)
    if payload.auth_mode == "manual_url":
        secret = calendar_connection_secret(
            method_category="manual_url",
            caldav_url=payload.caldav_url,
            username=payload.username,
            credential_input=payload.credential_input,
        )
        if secret is None:
            raise ProblemDetail(
                status=400,
                code="invalid_calendar_connection_fields",
                title="Invalid calendar connection fields",
            )
        return secret
    if payload.auth_mode == "app_password":
        secret = calendar_connection_secret(
            method_category="app_password",
            caldav_url=None,
            username=payload.username,
            credential_input=payload.credential_input,
        )
        if secret is None:
            raise ProblemDetail(
                status=400,
                code="invalid_calendar_connection_fields",
                title="Invalid calendar connection fields",
            )
        return secret
    raise ProblemDetail(
        status=400,
        code="unsupported_calendar_auth_mode",
        title="Unsupported calendar authentication mode",
    )


def _source_summary(source: CalendarSource) -> CalendarSourceSummary:
    return CalendarSourceSummary(
        source_id=source.id,
        provider_family=source.provider_family,
        provider_label=source.provider_label,
        connection_state=source.connection_state,
        credential_state=source.credential_state,
        sync_state=source.sync_state,
        selected_calendar_count=source.selected_calendar_count,
        sync_horizon_end=source.sync_horizon_end,
        last_successful_sync_at=source.last_successful_sync_at,
        safe_error_code=source.last_safe_error_code,
    )


def _calendar_summary(calendar: ExternalCalendar) -> ExternalCalendarSummary:
    return ExternalCalendarSummary(
        calendar_id=calendar.provider_calendar_id,
        display_label=calendar.display_label,
        selected=calendar.selected,
        color=calendar.color,
        visibility=calendar.visibility,
    )


async def _source_response(
    db: AsyncSession | None, source: CalendarSource
) -> CalendarSourceResponse:
    calendars = await calendars_for_source(require_db(db), source.id)
    return CalendarSourceResponse(
        source=_source_summary(source),
        calendars=[_calendar_summary(calendar) for calendar in calendars],
    )


def _event_title_state(event: CalendarEventSnapshot) -> str:
    title_state = str(
        (event.provider_extras_json or {}).get("title_state")
        or ("available" if event.safe_to_show_in_list else "policy_hidden")
    )
    return (
        title_state
        if title_state in {"available", "private_redacted", "free_busy_only", "policy_hidden"}
        else "policy_hidden"
    )


def _event_summary(event: CalendarEventSnapshot) -> CalendarEventSummary:
    extras = event.provider_extras_json or {}
    conference = event.conference_summary_json or {}
    return CalendarEventSummary(
        event_id=event.id,
        provider_family=extras.get("provider_family") or "calendar",
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        title=event.title if event.safe_to_show_in_list else None,
        title_state=_event_title_state(event),
        meeting_link_present=bool(conference.get("meeting_link_present", False)),
        attendee_count=int(extras.get("participant_count", 0)),
        roster_state=str(extras.get("roster_state", "not_available")),
        recipient_candidate_count=int(extras.get("recipient_candidate_count", 0)),
        privacy_class=event.privacy_class,
    )


def _desktop_event(
    event: CalendarEventSnapshot, *, join_enabled: bool = True, record_enabled: bool = True
) -> DesktopCalendarPromptEvent:
    summary = _event_summary(event)
    open_meeting_url = (event.provider_extras_json or {}).get("open_meeting_url")
    return DesktopCalendarPromptEvent(
        **summary.model_dump(),
        join_prompt_due_at=event.starts_at - timedelta(minutes=1),
        record_prompt_due_at=event.starts_at,
        join_prompt_state="not_due" if join_enabled else "not_available",
        record_prompt_state="not_due" if record_enabled else "not_available",
        open_meeting_url=open_meeting_url if summary.meeting_link_present else None,
    )


@router.get(
    "/calendar/providers",
    response_model=CalendarProviderListResponse,
    dependencies=[PrincipalDependency],
)
async def list_calendar_providers() -> CalendarProviderListResponse:
    return CalendarProviderListResponse(providers=list_provider_presets())


@router.get(
    "/calendar/sources",
    response_model=CalendarSourceListResponse,
    dependencies=[PrincipalDependency],
)
async def list_calendar_sources(
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> CalendarSourceListResponse:
    return CalendarSourceListResponse(
        sources=[
            _source_summary(source) for source in await list_sources(require_db(db), tenant_scope)
        ]
    )


@router.post(
    "/calendar/sources",
    status_code=201,
    response_model=CalendarSourceResponse,
    dependencies=[PrincipalDependency],
)
async def connect_calendar_source(
    payload: ConnectCalendarSourceRequest,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> CalendarSourceResponse:
    credential_input = _connect_credential_input(payload)
    source = await connect_source(
        require_db(db),
        tenant_scope,
        provider_family=payload.provider_family,
        auth_mode=payload.auth_mode,
        display_label=payload.display_label,
        credential_input=credential_input,
        selected_provider_calendar_ids=payload.selected_provider_calendar_ids,
        credential_key=_credential_key(request) if credential_input else None,
    )
    await commit_if_available(db)
    return await _source_response(db, source)


@router.get(
    "/calendar/sources/{source_id}",
    response_model=CalendarSourceResponse,
    dependencies=[PrincipalDependency],
)
async def get_calendar_source(
    source_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> CalendarSourceResponse:
    source = await get_source(require_db(db), tenant_scope, source_id)
    return await _source_response(db, source)


@router.patch(
    "/calendar/sources/{source_id}/selected-calendars",
    response_model=CalendarSourceResponse,
    dependencies=[PrincipalDependency],
)
async def select_calendar_source_calendars(
    source_id: UUID,
    payload: SelectCalendarsRequest,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> CalendarSourceResponse:
    source = await get_source(require_db(db), tenant_scope, source_id)
    await replace_selected_calendars(
        db, tenant_scope, source, payload.selected_provider_calendar_ids
    )
    await commit_if_available(db)
    return await _source_response(db, source)


@router.post(
    "/calendar/sources/{source_id}/sync",
    status_code=202,
    response_model=CalendarSyncResponse,
    dependencies=[PrincipalDependency],
)
async def sync_calendar_source(
    source_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> CalendarSyncResponse:
    source = await request_source_sync(require_db(db), tenant_scope, source_id)
    await commit_if_available(db)
    return CalendarSyncResponse(
        source_id=source.id, sync_state=source.sync_state, accepted=True, event_count=0
    )


@router.post(
    "/calendar/sources/{source_id}/disconnect",
    response_model=CalendarDisconnectResponse,
    dependencies=[PrincipalDependency],
)
async def disconnect_calendar_source_endpoint(
    source_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    result = await disconnect_calendar_source(require_db(db), tenant_scope, source_id)
    await commit_if_available(db)
    return result


@router.get(
    "/calendar/events/upcoming",
    response_model=UpcomingCalendarEventsResponse,
    dependencies=[PrincipalDependency],
)
async def list_upcoming_calendar_events(
    starts_from: Annotated[datetime | None, Query(alias="from")] = None,
    starts_to: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> UpcomingCalendarEventsResponse:
    session = require_db(db)
    preference = await _calendar_settings_preference_or_default(session, tenant_scope)
    events, truncated = await list_upcoming_events(
        session,
        tenant_scope,
        starts_from=starts_from,
        starts_to=starts_to,
        limit=limit,
        preference=preference,
    )
    return UpcomingCalendarEventsResponse(
        events=[_event_summary(event) for event in events], truncated=truncated
    )


@router.get(
    "/desktop/calendar/upcoming",
    response_model=DesktopCalendarPromptResponse,
    dependencies=[PrincipalDependency],
)
async def list_desktop_calendar_upcoming(
    before_minutes: Annotated[int, Query(ge=1, le=1440)] = 15,
    after_minutes: Annotated[int, Query(ge=0, le=1440)] = 60,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> DesktopCalendarPromptResponse:
    now = datetime.now(UTC)
    session = require_db(db)
    preference = await _calendar_settings_preference_or_default(session, tenant_scope)
    events, _truncated = await list_upcoming_events(
        session,
        tenant_scope,
        starts_from=now - timedelta(minutes=before_minutes),
        starts_to=now + timedelta(minutes=after_minutes),
        limit=50,
        preference=preference,
    )
    return DesktopCalendarPromptResponse(
        events=[
            _desktop_event(
                event,
                join_enabled=preference.join_prompt_enabled if preference else True,
                record_enabled=preference.record_prompt_enabled if preference else True,
            )
            for event in dedupe_calendar_events(events)
        ]
    )


@router.put(
    "/meetings/{meeting_id}/calendar-context",
    response_model=MeetingCalendarContextResponse,
    dependencies=[PrincipalDependency],
)
async def put_meeting_calendar_context(
    meeting_id: UUID,
    payload: PutMeetingCalendarContextRequest,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingCalendarContextResponse:
    link = await link_meeting_calendar_context(
        require_db(db),
        tenant_scope,
        meeting_id=meeting_id,
        event_id=payload.event_id,
        context_reason=payload.context_reason,
    )
    await commit_if_available(db)
    return MeetingCalendarContextResponse(
        meeting_id=meeting_id,
        event_id=link.calendar_event_snapshot_id,
        context_state="linked",
        context_confidence=link.context_confidence,
        title_source=link.title_source,
    )


@router.delete(
    "/meetings/{meeting_id}/calendar-context",
    response_model=MeetingCalendarContextResponse,
    dependencies=[PrincipalDependency],
)
async def delete_meeting_calendar_context(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingCalendarContextResponse:
    link = await unlink_meeting_calendar_context(
        require_db(db), tenant_scope, meeting_id=meeting_id
    )
    await commit_if_available(db)
    return MeetingCalendarContextResponse(
        meeting_id=meeting_id,
        event_id=link.calendar_event_snapshot_id if link is not None else None,
        context_state="unlinked",
        context_confidence=link.context_confidence if link is not None else None,
        title_source=link.title_source if link is not None else None,
    )


async def _calendar_settings_preference_or_default(
    db: AsyncSession,
    tenant_scope: TenantScope,
) -> CalendarSettingsPreference:
    return await get_calendar_settings_preferences(db, tenant_scope) or CalendarSettingsPreference(
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=tenant_scope.user_id,
        join_prompt_enabled=True,
        record_prompt_enabled=True,
        show_upcoming_time=True,
        show_upcoming_title=True,
        include_events_without_participants=False,
        include_events_without_link_or_location=False,
        include_all_day_events=False,
        include_private_free_busy_prompt_candidates=False,
    )
