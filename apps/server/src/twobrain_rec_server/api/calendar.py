from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, Header, Path, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
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
    ResolveRecordingCalendarContextRequest,
    ResolveRecordingCalendarContextResponse,
    SafeClientText,
    SelectCalendarsRequest,
    UpcomingCalendarEventsResponse,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
    require_web_csrf,
)
from twobrain_rec_server.cabinet.queries import get_meeting_calendar_context_read_model
from twobrain_rec_server.calendar.conference_links import safe_open_meeting_url
from twobrain_rec_server.calendar.credentials import (
    calendar_connection_secret,
    generate_credential_key,
    unseal_credential,
)
from twobrain_rec_server.calendar.google import (
    google_oauth_config_from_settings,
)
from twobrain_rec_server.calendar.matching import resolve_recording_calendar_context
from twobrain_rec_server.calendar.providers import CalendarProviderError
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
    validate_provider_connection,
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
WebCSRFDependency = Depends(require_web_csrf)
DeviceDependency = Depends(get_device_context)


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


def _credential_encryption_key(request: Request, *, required: bool = True) -> bytes | None:
    key = getattr(request.app.state, "credential_encryption_key", None)
    if key is None:
        settings = request.app.state.settings
        key_file = getattr(settings, "credential_encryption_key_file", None)
        if key_file is not None:
            try:
                key = key_file.read_text(encoding="utf-8").strip().encode("utf-8")
                Fernet(key)
            except (OSError, ValueError) as exc:
                if not required:
                    return None
                raise ProblemDetail(
                    status=503,
                    code="credential_encryption_key_unavailable",
                    title="Credential encryption key unavailable",
                ) from exc
        elif settings.env.lower() == "production":
            if not required:
                return None
            raise ProblemDetail(
                status=503,
                code="credential_encryption_key_unavailable",
                title="Credential encryption key unavailable",
            )
        else:
            key = generate_credential_key()
        request.app.state.credential_encryption_key = key
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


def _event_summary(
    event: CalendarEventSnapshot, *, show_title: bool = True
) -> CalendarEventSummary:
    extras = event.provider_extras_json or {}
    conference = event.conference_summary_json or {}
    return CalendarEventSummary(
        event_id=event.id,
        provider_family=extras.get("provider_family") or "calendar",
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        title=event.title if event.safe_to_show_in_list and show_title else None,
        title_state=_event_title_state(event) if show_title else "policy_hidden",
        meeting_link_present=bool(conference.get("meeting_link_present", False)),
        attendee_count=int(extras.get("participant_count", 0)),
        roster_state=str(extras.get("roster_state", "not_available")),
        recipient_candidate_count=int(extras.get("recipient_candidate_count", 0)),
        privacy_class=event.privacy_class,
    )


def _desktop_event(
    event: CalendarEventSnapshot,
    *,
    join_enabled: bool = True,
    record_enabled: bool = True,
    show_title: bool = True,
    credential_encryption_key: bytes | None = None,
) -> DesktopCalendarPromptEvent:
    summary = _event_summary(event, show_title=show_title)
    open_meeting_url = _open_meeting_url(event, credential_encryption_key)
    return DesktopCalendarPromptEvent(
        **summary.model_dump(),
        join_prompt_due_at=event.starts_at - timedelta(minutes=1),
        record_prompt_due_at=event.starts_at,
        join_prompt_state="not_due" if join_enabled else "not_available",
        record_prompt_state="not_due" if record_enabled else "not_available",
        open_meeting_url=open_meeting_url if summary.meeting_link_present else None,
    )


def _open_meeting_url(
    event: CalendarEventSnapshot, credential_encryption_key: bytes | None
) -> str | None:
    sealed = (event.provider_extras_json or {}).get("sealed_open_meeting_url")
    if not isinstance(sealed, str) or not sealed or credential_encryption_key is None:
        return None
    try:
        value = unseal_credential(sealed.encode("ascii"), credential_encryption_key)
    except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError, ValueError):
        return None
    return safe_open_meeting_url(value)


@router.get(
    "/calendar/providers",
    response_model=CalendarProviderListResponse,
    dependencies=[PrincipalDependency],
)
async def list_calendar_providers(request: Request) -> CalendarProviderListResponse:
    return CalendarProviderListResponse(
        providers=list_provider_presets(
            google_available=google_oauth_config_from_settings(request.app.state.settings)
            is not None,
            allow_uncertified_google=request.app.state.settings.env.lower() == "development",
            allow_uncertified_yandex=(
                request.app.state.settings.env.lower() == "development"
                and request.app.state.settings.calendar_allow_uncertified_yandex
            ),
        )
    )


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
    dependencies=[PrincipalDependency, WebCSRFDependency],
)
async def connect_calendar_source(
    payload: ConnectCalendarSourceRequest,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> CalendarSourceResponse:
    credential_input = _connect_credential_input(payload)
    provider_factory = getattr(request.app.state, "calendar_provider_factory", None)
    provider = provider_factory(payload.provider_family) if callable(provider_factory) else None
    try:
        validation = await validate_provider_connection(
            payload.provider_family,
            credential_input,
            provider=provider,
        )
    except CalendarProviderError as exc:
        status = 429 if exc.safe_code == "rate_limited" else 502
        raise ProblemDetail(
            status=status,
            code=exc.safe_code,
            title="Calendar provider could not be verified",
        ) from exc
    source = await connect_source(
        require_db(db),
        tenant_scope,
        provider_family=payload.provider_family,
        auth_mode=payload.auth_mode,
        display_label=payload.display_label,
        credential_input=credential_input,
        selected_provider_calendar_ids=payload.selected_provider_calendar_ids,
        credential_encryption_key=_credential_encryption_key(request) if credential_input else None,
        validated_calendars=validation.calendars,
        account_subject=validation.account_subject,
        granted_scopes=validation.granted_scopes,
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
    dependencies=[PrincipalDependency, WebCSRFDependency],
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
    dependencies=[PrincipalDependency, WebCSRFDependency],
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
    dependencies=[PrincipalDependency, WebCSRFDependency],
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
    "/calendar/events/{event_id}/open",
    dependencies=[PrincipalDependency],
)
async def open_calendar_meeting(
    event_id: UUID,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> RedirectResponse:
    event = await require_db(db).scalar(
        select(CalendarEventSnapshot)
        .join(ExternalCalendar, CalendarEventSnapshot.external_calendar_id == ExternalCalendar.id)
        .join(CalendarSource, CalendarEventSnapshot.calendar_source_id == CalendarSource.id)
        .where(
            CalendarEventSnapshot.id == event_id,
            CalendarEventSnapshot.workspace_id == tenant_scope.workspace_id,
            CalendarEventSnapshot.source_deleted_at.is_(None),
            ExternalCalendar.workspace_id == tenant_scope.workspace_id,
            ExternalCalendar.selected.is_(True),
            CalendarSource.workspace_id == tenant_scope.workspace_id,
            CalendarSource.owner_user_id == tenant_scope.user_id,
            CalendarSource.disconnected_at.is_(None),
            CalendarSource.connection_state != "disconnected",
        )
    )
    url = (
        _open_meeting_url(event, _credential_encryption_key(request, required=False))
        if event is not None
        else None
    )
    if url is None:
        raise ProblemDetail(
            status=404,
            code="calendar_meeting_link_unavailable",
            title="Calendar meeting link unavailable",
        )
    return RedirectResponse(url, status_code=303)


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
        events=[
            _event_summary(event, show_title=preference.show_upcoming_title) for event in events
        ],
        truncated=truncated,
        show_upcoming_time=preference.show_upcoming_time,
        show_upcoming_title=preference.show_upcoming_title,
    )


@router.get(
    "/desktop/calendar/upcoming",
    response_model=DesktopCalendarPromptResponse,
    dependencies=[PrincipalDependency],
)
async def list_desktop_calendar_upcoming(
    request: Request,
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
        # `before_minutes` remains part of the client contract, but a desktop
        # upcoming projection must not keep an event after its end time.
        # Calendar context matching has its own overlap window.
        starts_from=now,
        starts_to=now + timedelta(minutes=after_minutes),
        limit=50,
        preference=preference,
    )
    return DesktopCalendarPromptResponse(
        show_upcoming_time=preference.show_upcoming_time,
        show_upcoming_title=preference.show_upcoming_title,
        events=[
            _desktop_event(
                event,
                join_enabled=preference.join_prompt_enabled if preference else True,
                record_enabled=preference.record_prompt_enabled if preference else True,
                show_title=preference.show_upcoming_title,
                credential_encryption_key=_credential_encryption_key(request, required=False),
            )
            for event in dedupe_calendar_events(events)
        ],
    )


@router.post(
    "/desktop/recordings/{local_recording_id}/calendar-context/resolve",
    operation_id="resolveRecordingCalendarContext",
    response_model=ResolveRecordingCalendarContextResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def resolve_desktop_recording_calendar_context(
    local_recording_id: Annotated[
        SafeClientText,
        Path(min_length=1, max_length=240),
    ],
    payload: ResolveRecordingCalendarContextRequest,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=240),
    ],
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> ResolveRecordingCalendarContextResponse:
    attempt = await resolve_recording_calendar_context(
        require_db(db),
        tenant_scope,
        local_recording_id=local_recording_id,
        idempotency_key=idempotency_key,
        recording_started_at=payload.recording_started_at,
        decision_intent=payload.decision_intent,
        selected_event_id=payload.event_id,
    )
    await commit_if_available(db)
    expires_at = (
        attempt.expires_at.replace(tzinfo=UTC)
        if attempt.expires_at.tzinfo is None
        else attempt.expires_at.astimezone(UTC)
    )
    return ResolveRecordingCalendarContextResponse(
        attempt_id=attempt.id,
        context_state=attempt.attempt_state,
        reason_code=attempt.safe_reason_code,
        context_confidence=attempt.context_confidence,
        candidate_count=attempt.candidate_count,
        matcher_version=attempt.matcher_version,
        expires_at=expires_at,
    )


@router.put(
    "/meetings/{meeting_id}/calendar-context",
    response_model=MeetingCalendarContextResponse,
    dependencies=[PrincipalDependency, WebCSRFDependency],
)
async def put_meeting_calendar_context(
    meeting_id: UUID,
    payload: PutMeetingCalendarContextRequest,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingCalendarContextResponse:
    session = require_db(db)
    await link_meeting_calendar_context(
        session,
        tenant_scope,
        meeting_id=meeting_id,
        event_id=payload.event_id,
        context_reason=payload.context_reason,
    )
    await commit_if_available(db)
    return await get_meeting_calendar_context_read_model(
        session,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=tenant_scope.user_id,
        meeting_id=meeting_id,
    )


@router.get(
    "/meetings/{meeting_id}/calendar-context",
    response_model=MeetingCalendarContextResponse,
    dependencies=[PrincipalDependency],
)
async def get_meeting_calendar_context(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingCalendarContextResponse:
    return await get_meeting_calendar_context_read_model(
        require_db(db),
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=tenant_scope.user_id,
        meeting_id=meeting_id,
    )


@router.delete(
    "/meetings/{meeting_id}/calendar-context",
    response_model=MeetingCalendarContextResponse,
    dependencies=[PrincipalDependency, WebCSRFDependency],
)
async def delete_meeting_calendar_context(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingCalendarContextResponse:
    session = require_db(db)
    await unlink_meeting_calendar_context(session, tenant_scope, meeting_id=meeting_id)
    await commit_if_available(db)
    return await get_meeting_calendar_context_read_model(
        session,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=tenant_scope.user_id,
        meeting_id=meeting_id,
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
