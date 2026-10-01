from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
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
    CalendarJoinTargetResponse,
    CalendarOverviewResponse,
    CalendarProviderListResponse,
    CalendarSeriesOccurrencesResponse,
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
from twobrain_rec_server.calendar.owner_content import owner_event_content
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


def _event_summary(
    event: CalendarEventSnapshot,
    *,
    show_title: bool = True,
    credential_encryption_key: bytes | None = None,
) -> CalendarEventSummary:
    extras = event.provider_extras_json or {}
    conference = event.conference_summary_json or {}
    content = owner_event_content(event, credential_encryption_key)
    title = content.get("title")
    # An available row with no title means the provider supplied no title.
    # Preserve the deployed Swift enum without claiming that GRAF hid content.
    title_state = (
        "free_busy_only" if not title and event.privacy_class == "free_busy_only" else "available"
    )
    return CalendarEventSummary(
        all_day=bool(event.all_day),
        is_recurring=bool(event.recurring_series_id),
        event_id=event.id,
        provider_family=extras.get("provider_family") or "calendar",
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        title=title if show_title else None,
        title_state=title_state if show_title else "policy_hidden",
        description=content.get("description"),
        location=content.get("location"),
        participants=content.get("participants") or [],
        attachments=content.get("attachments") or [],
        conference_links=content.get("conference_links") or [],
        provider_extras=content.get("provider_extras") or {},
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
    summary = _event_summary(
        event, show_title=show_title, credential_encryption_key=credential_encryption_key
    )
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
    event, url = await _resolve_join_target(event_id, request, tenant_scope, require_db(db))
    return RedirectResponse(url, status_code=303, headers={"Cache-Control": "no-store"})


async def _resolve_join_target(event_id, request, tenant_scope, db):
    from twobrain_rec_server.calendar.series import authorized_events

    event = await db.scalar(
        authorized_events(tenant_scope).where(CalendarEventSnapshot.id == event_id)
    )
    url = (
        _open_meeting_url(event, _credential_encryption_key(request, required=False))
        if event
        else None
    )
    if url is None:
        raise ProblemDetail(
            status=404,
            code="calendar_meeting_link_unavailable",
            title="Calendar meeting link unavailable",
        )
    return event, url


@router.post(
    "/calendar/events/{event_id}/join-target",
    response_model=CalendarJoinTargetResponse,
    dependencies=[PrincipalDependency, WebCSRFDependency],
)
@router.get(
    "/calendar/events/{event_id}/join-target",
    response_model=CalendarJoinTargetResponse,
    dependencies=[PrincipalDependency],
)
async def calendar_join_target(
    event_id: UUID,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
):
    from fastapi.responses import JSONResponse

    event, url = await _resolve_join_target(event_id, request, tenant_scope, require_db(db))
    return JSONResponse(
        {
            "event_id": str(event.id),
            "provider_family": (event.provider_extras_json or {}).get(
                "provider_family", "calendar"
            ),
            "https_url": url,
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/calendar/events/upcoming",
    response_model=UpcomingCalendarEventsResponse,
    dependencies=[PrincipalDependency],
)
async def list_upcoming_calendar_events(
    request: Request,
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
            _event_summary(
                event,
                show_title=preference.show_upcoming_title,
                credential_encryption_key=_credential_encryption_key(request, required=False),
            )
            for event in events
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
        notification_owner_id=str(tenant_scope.user_id),
        notification_workspace_id=str(tenant_scope.workspace_id),
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


def _series_event_payload(event, scope, preference, key):
    from twobrain_rec_server.calendar.owner_content import owner_event_title
    from twobrain_rec_server.calendar.series import series_key

    show_title = preference.show_upcoming_title if preference else True
    show_time = preference.show_upcoming_time if preference else True
    return {
        "event_id": str(event.id),
        "series_key": series_key(event, scope.user_id),
        "is_recurring": bool(event.recurring_series_id),
        "title": (owner_event_title(event, key) or "Без названия")
        if show_title
        else "Название скрыто настройкой",
        "starts_at": event.starts_at.isoformat() if show_time else None,
        "ends_at": event.ends_at.isoformat() if show_time else None,
        "all_day": event.all_day,
        "cancelled": event.source_status == "cancelled" or event.source_deleted_at is not None,
        "open_meeting_available": event.source_status != "cancelled"
        and event.source_deleted_at is None
        and _open_meeting_url(event, key) is not None,
    }


@router.get(
    "/calendar/overview",
    response_model=CalendarOverviewResponse,
    dependencies=[PrincipalDependency],
)
async def calendar_overview(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=50)] = 4,
    cursor: str | None = None,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
):
    from fastapi.responses import JSONResponse

    from twobrain_rec_server.calendar.series import (
        decode_overview_cursor,
        encode_cursor,
        overview_events,
    )

    session = require_db(db)
    preference = await _calendar_settings_preference_or_default(session, tenant_scope)
    now = datetime.now(UTC)
    context = {
        "owner": str(tenant_scope.user_id),
        "session": str(tenant_scope.auth_session_id or tenant_scope.device_id),
        "workspace": str(tenant_scope.workspace_id),
        "series": "overview",
    }
    secret = request.app.state.settings.web_csrf_secret
    try:
        if cursor:
            now, after, context = decode_overview_cursor(cursor, context, secret)
        else:
            after = None
            context = {
                **context,
                "anchor": now.isoformat(),
                "from": now.date().isoformat(),
                "to": (now + timedelta(days=30)).date().isoformat(),
            }
    except ValueError as error:
        raise ProblemDetail(
            status=422, code="invalid_calendar_cursor", title="Invalid calendar cursor"
        ) from error
    events, more = await overview_events(
        session, tenant_scope, preference, now=now, limit=limit, after=after
    )
    key = _credential_encryption_key(request, required=False)
    next_cursor = (
        encode_cursor(context, (events[-1].starts_at.isoformat(), str(events[-1].id)), secret)
        if more and events
        else None
    )
    return JSONResponse(
        {
            "cards": [_series_event_payload(e, tenant_scope, preference, key) for e in events],
            "partial": more,
            "coverage_range": {"from": context["from"], "to": context["to"]},
            "next_cursor": next_cursor,
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/calendar/series/{series_key}/occurrences",
    response_model=CalendarSeriesOccurrencesResponse,
    dependencies=[PrincipalDependency],
)
async def calendar_series_occurrences(
    series_key: str,
    request: Request,
    starts_from: Annotated[datetime | None, Query(alias="from")] = None,
    starts_to: Annotated[datetime | None, Query(alias="to")] = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    view: Literal["all", "upcoming", "history"] = "all",
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
):
    import re

    from fastapi.responses import JSONResponse

    from twobrain_rec_server.calendar.series import (
        authorized_events,
        decode_occurrence_cursor,
        encode_cursor,
        series_key_expression,
        series_occurrences,
    )

    session = require_db(db)
    context = {
        "owner": str(tenant_scope.user_id),
        "session": str(tenant_scope.auth_session_id or tenant_scope.device_id),
        "workspace": str(tenant_scope.workspace_id),
        "series": series_key,
    }
    secret = request.app.state.settings.web_csrf_secret
    anchor = datetime.now(UTC)
    if view != "all":
        context["view"] = view
    after = None
    if cursor:
        try:
            start, end, after, context = decode_occurrence_cursor(
                cursor, context, secret, starts_from=starts_from, starts_to=starts_to
            )
            if view != "all":
                anchor = datetime.fromisoformat(context["anchor"])
        except ValueError as error:
            raise ProblemDetail(
                status=422, code="invalid_calendar_cursor", title="Invalid calendar cursor"
            ) from error
    else:
        # Stable half-open day boundaries include the overview's entire thirtieth day.
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        start, end = (
            starts_from or today - timedelta(days=180),
            starts_to or today + timedelta(days=31),
        )
        if (
            start.tzinfo is None
            or end.tzinfo is None
            or not timedelta(0) < end - start <= timedelta(days=366)
        ):
            raise ProblemDetail(
                status=422, code="invalid_calendar_range", title="Invalid calendar range"
            )
        context = {**context, "from": start.isoformat(), "to": end.isoformat()}
        if view != "all":
            context["anchor"] = anchor.isoformat()
    if not re.fullmatch(r"v2-[0-9a-f]{64}", series_key):
        raise ProblemDetail(
            status=404, code="calendar_series_unavailable", title="Calendar series unavailable"
        )
    exists = await session.scalar(
        authorized_events(tenant_scope, include_cancelled=True)
        .with_only_columns(CalendarEventSnapshot.id)
        .where(
            CalendarEventSnapshot.recurring_series_id.is_not(None),
            series_key_expression(tenant_scope.user_id) == series_key,
        )
        .limit(1)
    )
    if exists is None:
        raise ProblemDetail(
            status=404, code="calendar_series_unavailable", title="Calendar series unavailable"
        )
    preference = await _calendar_settings_preference_or_default(session, tenant_scope)
    events, more = await series_occurrences(
        session,
        tenant_scope,
        preference,
        series_key,
        start,
        end,
        limit=limit,
        after=after,
        view=view,
        anchor=anchor,
    )
    key = _credential_encryption_key(request, required=False)
    records, records_partial = await _series_recordings(
        session, tenant_scope, [e.id for e in events]
    )
    payload = [
        {
            **_series_event_payload(e, tenant_scope, preference, key),
            "recordings": records.get(e.id, []),
            "recordings_partial": records_partial,
            "temporal_state": (
                "history"
                if e.ends_at <= anchor
                else "ongoing"
                if e.starts_at <= anchor
                else "upcoming"
            ),
        }
        for e in events
    ]
    next_cursor = (
        encode_cursor(context, (events[-1].starts_at.isoformat(), str(events[-1].id)), secret)
        if more and events
        else None
    )
    return JSONResponse(
        {
            "occurrences": payload,
            "next_cursor": next_cursor,
            "coverage_range": {"from": start.isoformat(), "to": end.isoformat()},
            "partial": more or records_partial,
            "coverage_note": "Показаны сохранённые доступные даты и ограниченная выборка записей. Все доступные записи можно открыть в общем списке встреч. Полная история календаря может быть недоступна.",
        },
        headers={"Cache-Control": "no-store"},
    )


SERIES_RECORDING_CANDIDATE_LIMIT = 200


async def _series_recordings(db, scope, event_ids):
    from twobrain_rec_server.cabinet.access import decide_meeting_access
    from twobrain_rec_server.cabinet.queries import _prefetch_meeting_list_reads
    from twobrain_rec_server.db.models import Meeting, RecordingCalendarContextLink

    if not event_ids:
        return {}, False
    rows = list(
        await db.execute(
            select(RecordingCalendarContextLink.calendar_event_snapshot_id, Meeting)
            .join(Meeting, RecordingCalendarContextLink.meeting_id == Meeting.id)
            .where(
                RecordingCalendarContextLink.workspace_id == scope.workspace_id,
                RecordingCalendarContextLink.calendar_event_snapshot_id.in_(event_ids),
                RecordingCalendarContextLink.context_state.in_(["matched_auto", "matched_user"]),
                RecordingCalendarContextLink.unlinked_at.is_(None),
                Meeting.workspace_id == scope.workspace_id,
                Meeting.deleted_at.is_(None),
                Meeting.deletion_state == "none",
            )
            .order_by(Meeting.started_at.desc(), Meeting.id)
            .limit(SERIES_RECORDING_CANDIDATE_LIMIT)
        )
    )
    from twobrain_rec_server.cabinet.read_prefetch import clear_read_prefetch

    result = {}
    try:
        for offset in range(0, len(rows), 100):
            chunk = rows[offset : offset + 100]
            await _prefetch_meeting_list_reads(
                db,
                workspace_id=scope.workspace_id,
                viewer_user_id=scope.user_id,
                meetings=[m for _, m in chunk],
            )
            for event_id, meeting in chunk:
                access = await decide_meeting_access(
                    db, meeting, workspace_id=scope.workspace_id, viewer_user_id=scope.user_id
                )
                if access.can_view:
                    result.setdefault(event_id, []).append({"meeting_id": str(meeting.id)})
    finally:
        clear_read_prefetch(db)
    # Do not derive this public flag from the number of hidden candidates. This
    # endpoint always offers a bounded preview; the meeting list is authoritative.
    return result, True
