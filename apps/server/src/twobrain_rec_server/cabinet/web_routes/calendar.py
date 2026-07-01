from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.calendar import _credential_encryption_key
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.queries import (
    get_calendar_settings_surface,
)
from twobrain_rec_server.cabinet.rendering import (
    calendar_connection_result_from_problem,
    calendar_settings_notice_codes,
    render_calendar_settings_fragment,
    render_calendar_settings_page,
)
from twobrain_rec_server.cabinet.templates import (
    cabinet_html_response,
)
from twobrain_rec_server.cabinet.view_models import CALENDAR_PROVIDER_UI
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
    _is_hx_request,
)
from twobrain_rec_server.calendar.audit import write_calendar_audit_event
from twobrain_rec_server.calendar.credentials import calendar_connection_secret
from twobrain_rec_server.calendar.service import (
    connect_source,
    disconnect_calendar_source,
    get_source,
    replace_selected_calendars,
    request_source_sync,
    save_calendar_settings_preferences,
)

router = APIRouter(tags=["cabinet-web"])

CalendarConnectResultQuery = Query(default=None, max_length=48, alias="connect_result")
CalendarPolicyLimitedQuery = Query(default=None, max_length=48, alias="policy_limited")
CalendarSelectionResultQuery = Query(default=None, max_length=48, alias="selection_result")
CalendarPreferencesResultQuery = Query(default=None, max_length=48, alias="preferences_result")
CalendarSyncResultQuery = Query(default=None, max_length=48, alias="sync_result")
CalendarDisconnectResultQuery = Query(default=None, max_length=48, alias="disconnect_result")
CalendarProviderResultQuery = Query(default=None, max_length=48, alias="result")
CalendarProviderFamilyQuery = Query(default=None, max_length=80, alias="provider_family")

CalendarAccountLabelForm = Form(default=None, max_length=160)
CalendarCalDAVURLForm = Form(default=None, max_length=1000)
CalendarUsernameForm = Form(default=None, max_length=240)
CalendarCredentialForm = Form(default=None, max_length=2000)


@router.get("/settings/integrations/calendar", response_class=HTMLResponse, include_in_schema=False)
async def calendar_settings_page(
    request: Request,
    connect_result: str | None = CalendarConnectResultQuery,
    policy_limited: str | None = CalendarPolicyLimitedQuery,
    selection_result: str | None = CalendarSelectionResultQuery,
    preferences_result: str | None = CalendarPreferencesResultQuery,
    sync_result: str | None = CalendarSyncResultQuery,
    disconnect_result: str | None = CalendarDisconnectResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    surface = await get_calendar_settings_surface(
        db,
        tenant_scope,
        notice_codes=calendar_settings_notice_codes(
            connect_result=connect_result,
            policy_limited=policy_limited,
            selection_result=selection_result,
            preferences_result=preferences_result,
            sync_result=sync_result,
            disconnect_result=disconnect_result,
        ),
    )
    if _is_hx_request(request):
        return cabinet_html_response(
            render_calendar_settings_fragment(surface, csrf_token=_csrf_token_for_principal(request, principal)),
            hx_request=True,
        )
    return cabinet_html_response(
        render_calendar_settings_page(
            surface,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )

@router.post(
    "/settings/integrations/calendar/providers/{provider_family}/connect",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/settings/integrations/calendar/providers/{provider_family}/connect",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def calendar_provider_connect(
    request: Request,
    provider_family: str,
    account_label: str | None = CalendarAccountLabelForm,
    caldav_url: str | None = CalendarCalDAVURLForm,
    username: str | None = CalendarUsernameForm,
    credential_input: str | None = CalendarCredentialForm,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    provider_copy = CALENDAR_PROVIDER_UI.get(provider_family)
    if provider_copy is None:
        await _record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family=provider_family,
            method_category="unknown",
            outcome="failed",
            safe_reason_code="unsupported_calendar_provider",
        )
        await db.commit()
        return _calendar_settings_redirect(request, connect_result="failed")
    provider_label, method_category, _ = provider_copy
    await _record_calendar_connect_start(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        provider_family=provider_family,
        method_category=method_category,
    )
    if method_category == "provider_specific_limited":
        await _record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family=provider_family,
            method_category=method_category,
            outcome="blocked",
            safe_reason_code="provider_limited",
        )
        await db.commit()
        return _calendar_settings_redirect(request, policy_limited="provider_limited")
    secret_payload = calendar_connection_secret(
        method_category=method_category,
        caldav_url=caldav_url,
        username=username,
        credential_input=credential_input,
    )
    if secret_payload is None:
        await _record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family=provider_family,
            method_category=method_category,
            outcome="failed",
            safe_reason_code="missing_required_fields",
        )
        await db.commit()
        return _calendar_settings_redirect(request, connect_result="failed")
    try:
        source = await connect_source(
            db,
            tenant_scope,
            provider_family=provider_family,
            auth_mode="manual_url" if method_category == "manual_url" else "app_password",
            display_label=(account_label or "").strip() or provider_label,
            credential_input=secret_payload,
            selected_provider_calendar_ids=[],
            credential_encryption_key=_credential_encryption_key(request),
        )
    except ProblemDetail as exc:
        result = calendar_connection_result_from_problem(exc.code)
        await _record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family=provider_family,
            method_category=method_category,
            outcome="failed",
            safe_reason_code=exc.code,
        )
        await db.commit()
        return _calendar_settings_redirect(request, connect_result=result)
    await _record_calendar_connect_result(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        provider_family=provider_family,
        method_category=method_category,
        outcome="completed",
        source_id=source.id,
    )
    await db.commit()
    return _calendar_settings_redirect(request, connect_result="success")


@router.get("/settings/integrations/calendar/provider-result", response_class=HTMLResponse, include_in_schema=False)
@router.get("/desktop/settings/integrations/calendar/provider-result", response_class=HTMLResponse, include_in_schema=False)
async def calendar_provider_result(
    request: Request,
    result: str | None = CalendarProviderResultQuery,
    provider_family: str | None = CalendarProviderFamilyQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    safe_result = _safe_calendar_provider_result(result)
    provider = provider_family or "unknown"
    method_category = _calendar_provider_method_category(provider)
    if safe_result == "success":
        await _record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family=provider,
            method_category=method_category,
            outcome="blocked",
            safe_reason_code="provider_limited",
        )
        await db.commit()
        return _calendar_settings_redirect(request, policy_limited="provider_limited")
    await _record_calendar_connect_result(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        provider_family=provider,
        method_category=method_category,
        outcome=safe_result,
        safe_reason_code=safe_result,
    )
    await db.commit()
    return _calendar_settings_redirect(request, connect_result=safe_result)


@router.post(
    "/settings/integrations/calendar/sources/{source_id}/calendars",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/settings/integrations/calendar/sources/{source_id}/calendars",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def calendar_source_calendar_selection(
    request: Request,
    source_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    form = await request.form()
    selected_ids = [str(value) for value in form.getlist("selected_provider_calendar_ids") if str(value).strip()]
    source = await get_source(db, tenant_scope, source_id)
    await replace_selected_calendars(db, tenant_scope, source, selected_ids, allow_missing=False)
    await db.commit()
    return _calendar_settings_redirect(
        request,
        selection_result="saved" if source.selected_calendar_count else "empty",
    )


@router.post(
    "/settings/integrations/calendar/sources/{source_id}/sync",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/settings/integrations/calendar/sources/{source_id}/sync",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def calendar_source_manual_sync(
    request: Request,
    source_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    source = await get_source(db, tenant_scope, source_id)
    await _record_calendar_source_event(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        source_id=source.id,
        event_type="calendar_manual_sync_requested",
        outcome="accepted",
    )
    requested_at = datetime.now(UTC)
    source = await request_source_sync(db, tenant_scope, source.id)
    result = _calendar_manual_sync_result(source, requested_at=requested_at)
    await _record_calendar_source_event(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        source_id=source.id,
        event_type="calendar_manual_sync_result",
        outcome="accepted" if result == "accepted" else result,
        safe_reason_code=None if result == "accepted" else result,
    )
    await db.commit()
    return _calendar_settings_redirect(request, sync_result=result)


@router.post(
    "/settings/integrations/calendar/sources/{source_id}/disconnect",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/settings/integrations/calendar/sources/{source_id}/disconnect",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def calendar_source_disconnect(
    request: Request,
    source_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    source = await get_source(db, tenant_scope, source_id)
    await _record_calendar_source_event(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        source_id=source.id,
        event_type="calendar_disconnect_confirmed",
        outcome="accepted",
    )
    try:
        result = await disconnect_calendar_source(db, tenant_scope, source.id)
    except ProblemDetail:
        await _record_calendar_source_event(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            source_id=source.id,
            event_type="calendar_disconnect_result",
            outcome="failed",
            safe_reason_code="failed",
        )
        await db.commit()
        return _calendar_settings_redirect(request, disconnect_result="failed")
    disconnect_result = _calendar_disconnect_result(result)
    await _record_calendar_source_event(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        source_id=source.id,
        event_type="calendar_disconnect_result",
        outcome="completed" if disconnect_result == "success" else disconnect_result,
        safe_reason_code=None if disconnect_result == "success" else disconnect_result,
    )
    await db.commit()
    return _calendar_settings_redirect(request, disconnect_result=disconnect_result)


@router.post(
    "/settings/integrations/calendar/preferences",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/settings/integrations/calendar/preferences",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def calendar_settings_preferences(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    form = await request.form()
    await save_calendar_settings_preferences(
        db,
        tenant_scope,
        join_prompt_enabled=_calendar_form_checkbox(form, "join_prompt_enabled"),
        record_prompt_enabled=_calendar_form_checkbox(form, "record_prompt_enabled"),
        show_upcoming_time=_calendar_form_checkbox(form, "show_upcoming_time"),
        show_upcoming_title=_calendar_form_checkbox(form, "show_upcoming_title"),
        include_events_without_participants=_calendar_form_checkbox(form, "include_events_without_participants"),
        include_events_without_link_or_location=_calendar_form_checkbox(form, "include_events_without_link_or_location"),
        include_all_day_events=_calendar_form_checkbox(form, "include_all_day_events"),
        include_private_free_busy_prompt_candidates=_calendar_form_checkbox(
            form,
            "include_private_free_busy_prompt_candidates",
        ),
    )
    await db.commit()
    return _calendar_settings_redirect(request, preferences_result="saved")

def _calendar_settings_redirect(
    request: Request,
    *,
    connect_result: str | None = None,
    policy_limited: str | None = None,
    selection_result: str | None = None,
    preferences_result: str | None = None,
    sync_result: str | None = None,
    disconnect_result: str | None = None,
) -> RedirectResponse:
    embedded = request.url.path.startswith("/desktop/")
    params = {}
    if connect_result:
        params["connect_result"] = connect_result
    if policy_limited:
        params["policy_limited"] = policy_limited
    if selection_result:
        params["selection_result"] = selection_result
    if preferences_result:
        params["preferences_result"] = preferences_result
    if sync_result:
        params["sync_result"] = sync_result
    if disconnect_result:
        params["disconnect_result"] = disconnect_result
    suffix = f"?{urlencode(params)}" if params else ""
    path = "/desktop/settings/integrations/calendar" if embedded else "/settings/integrations/calendar"
    return RedirectResponse(f"{path}{suffix}", status_code=303)


def _safe_calendar_provider_result(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"success", "cancelled", "denied", "failed", "no_readable_calendars"}:
        return normalized
    return "failed"


def _calendar_provider_method_category(provider_family: str) -> str:
    provider_copy = CALENDAR_PROVIDER_UI.get(provider_family)
    if provider_copy is None:
        return "unknown"
    return provider_copy[1]


def _calendar_form_checkbox(form: object, key: str) -> bool:
    value = form.get(key) if hasattr(form, "get") else None
    return value is not None and str(value).strip().lower() not in {"", "0", "false", "off"}


def _calendar_manual_sync_result(source, *, requested_at: datetime | None = None) -> str:
    if source.connection_state == "disconnected" or source.disconnected_at is not None:
        return "unavailable"
    if source.connection_state in {"disabled", "disabled_by_policy"}:
        return "unavailable"
    if source.connection_state in {"needs_action", "error"} or source.sync_state == "credential_failed":
        return "reconnect_required"
    if source.sync_state in {"queued", "syncing"}:
        if (
            requested_at is not None
            and source.last_sync_started_at is not None
            and source.last_sync_started_at >= requested_at
        ):
            return "accepted"
        return "already_running"
    if source.sync_state in {"failed", "failed_closed", "provider_unavailable", "rate_limited"}:
        return "failed"
    return "accepted"


def _calendar_disconnect_result(result: dict[str, object]) -> str:
    if result.get("connection_state") != "disconnected":
        return "failed"
    if result.get("credentials_purged") is not True or result.get("unmatched_future_cache_purged") is not True:
        return "partial"
    return "success"


async def _record_calendar_connect_start(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    provider_family: str,
    method_category: str,
) -> None:
    await write_calendar_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        actor_user_id=principal.user_id,
        device_id=tenant_scope.device_id,
        event_type="calendar_connect_start",
        outcome="accepted",
        metadata={"provider_family": provider_family, "method_category": method_category},
    )


async def _record_calendar_connect_result(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    provider_family: str,
    method_category: str,
    outcome: str,
    safe_reason_code: str | None = None,
    source_id: UUID | None = None,
) -> None:
    await write_calendar_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        actor_user_id=principal.user_id,
        device_id=tenant_scope.device_id,
        calendar_source_id=source_id,
        event_type="calendar_connect_result",
        outcome=outcome,
        safe_reason_code=safe_reason_code,
        metadata={
            "provider_family": provider_family,
            "method_category": method_category,
            "result_category": safe_reason_code or outcome,
        },
    )


async def _record_calendar_source_event(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    source_id: UUID,
    event_type: str,
    outcome: str,
    safe_reason_code: str | None = None,
) -> None:
    await write_calendar_audit_event(
        db,
        workspace_id=tenant_scope.workspace_id,
        actor_user_id=principal.user_id,
        device_id=tenant_scope.device_id,
        calendar_source_id=source_id,
        event_type=event_type,
        outcome=outcome,
        safe_reason_code=safe_reason_code,
        metadata={"result_category": safe_reason_code or outcome},
    )
