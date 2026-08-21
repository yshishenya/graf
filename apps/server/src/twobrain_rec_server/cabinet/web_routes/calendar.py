from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.calendar import _credential_encryption_key
from twobrain_rec_server.api.ingest import get_request_storage
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.queries import (
    get_account_profile_view,
    get_cabinet_meeting_review,
    get_calendar_settings_surface,
)
from twobrain_rec_server.cabinet.rendering import (
    calendar_connection_result_from_problem,
    calendar_settings_notice_codes,
    render_calendar_settings_fragment,
    render_calendar_settings_page,
    render_meeting_detail_fragment,
)
from twobrain_rec_server.cabinet.templates import (
    cabinet_html_response,
)
from twobrain_rec_server.cabinet.view_models import CALENDAR_PROVIDER_UI
from twobrain_rec_server.cabinet.web_routes.calendar_helpers import (
    calendar_disconnect_result,
    calendar_form_checkbox,
    calendar_manual_sync_result,
    calendar_provider_method_category,
    calendar_settings_redirect,
    record_calendar_connect_result,
    record_calendar_connect_start,
    record_calendar_source_event,
    safe_calendar_provider_result,
)
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
    _is_hx_request,
)
from twobrain_rec_server.calendar.credentials import calendar_connection_secret
from twobrain_rec_server.calendar.google import (
    GoogleCalendarAdapter,
    GoogleOAuthConfig,
    build_google_authorization_url,
    google_oauth_config_from_settings,
)
from twobrain_rec_server.calendar.providers import CalendarProviderError
from twobrain_rec_server.calendar.service import (
    connect_source,
    disconnect_calendar_source,
    get_source,
    link_meeting_calendar_context,
    replace_selected_calendars,
    request_source_sync,
    save_calendar_settings_preferences,
    unlink_meeting_calendar_context,
    validate_provider_connection,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
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
CalendarOAuthStateQuery = Query(default=None, max_length=512, alias="state")
CalendarOAuthCodeQuery = Query(default=None, max_length=4096, alias="code")

CalendarAccountLabelForm = Form(default=None, max_length=160)
CalendarCalDAVURLForm = Form(default=None, max_length=1000)
CalendarUsernameForm = Form(default=None, max_length=240)
CalendarCredentialForm = Form(default=None, max_length=2000)
CalendarContextEventIdForm = Form()
CalendarContextReasonForm = Form(default="ambiguity_resolution", max_length=40)

GOOGLE_STATE_COOKIE = "graf_google_calendar_oauth_state"
GOOGLE_STATE_MAX_AGE_SECONDS = 600
GOOGLE_STATE_COOKIE_LIMIT = 4


def _google_oauth_config(request: Request) -> GoogleOAuthConfig | None:
    return google_oauth_config_from_settings(request.app.state.settings)


def _google_state(
    request: Request, tenant_scope: TenantScope, principal: AuthenticatedPrincipal
) -> str:
    return_path = (
        "/desktop/settings/integrations/calendar"
        if request.url.path.startswith("/desktop/")
        else "/settings/integrations/calendar"
    )
    payload = "|".join(
        (
            secrets.token_urlsafe(24),
            str(int(time.time())),
            str(tenant_scope.workspace_id),
            str(principal.user_id),
            return_path,
        )
    )
    secret = str(request.app.state.settings.web_csrf_secret).encode("utf-8")
    signature = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}|{signature}"


def _verify_google_state(
    request: Request, state: str, cookie_state: str | None
) -> tuple[str, str, str] | None:
    cookie_states = _google_cookie_states(cookie_state)
    if not state or not any(hmac.compare_digest(state, item) for item in cookie_states):
        return None
    parts = state.split("|")
    if len(parts) != 6:
        return None
    nonce, issued_at, workspace_id, user_id, return_path, signature = parts
    payload = "|".join((nonce, issued_at, workspace_id, user_id, return_path))
    secret = str(request.app.state.settings.web_csrf_secret).encode("utf-8")
    expected = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    try:
        fresh = time.time() - int(issued_at) <= GOOGLE_STATE_MAX_AGE_SECONDS
    except ValueError:
        fresh = False
    if not hmac.compare_digest(signature, expected) or not fresh:
        return None
    if return_path not in {
        "/settings/integrations/calendar",
        "/desktop/settings/integrations/calendar",
    }:
        return None
    return return_path, workspace_id, user_id


def _google_cookie_states(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [value]
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str) and item][:GOOGLE_STATE_COOKIE_LIMIT]


def _set_google_state_cookie(response: Response, request: Request, states: list[str]) -> None:
    if not states:
        response.delete_cookie(GOOGLE_STATE_COOKIE, path="/")
        return
    response.set_cookie(
        GOOGLE_STATE_COOKIE,
        json.dumps(states[-GOOGLE_STATE_COOKIE_LIMIT:], separators=(",", ":")),
        max_age=GOOGLE_STATE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )


def _consume_google_state(response: Response, request: Request, state: str | None) -> None:
    states = _google_cookie_states(request.cookies.get(GOOGLE_STATE_COOKIE))
    _set_google_state_cookie(response, request, [item for item in states if item != state])


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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    surface = await get_calendar_settings_surface(
        db,
        tenant_scope,
        settings=request.app.state.settings,
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
            render_calendar_settings_fragment(
                surface, csrf_token=_csrf_token_for_principal(request, principal)
            ),
            hx_request=True,
        )
    profile = await get_account_profile_view(db, tenant_scope)
    return cabinet_html_response(
        render_calendar_settings_page(
            surface,
            csrf_token=_csrf_token_for_principal(request, principal),
            profile=profile,
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "settings",
                principal=principal,
                tenant_scope=tenant_scope,
            ),
        )
    )


@router.post(
    "/meetings/{meeting_id}/calendar-context/choose",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/meetings/{meeting_id}/calendar-context/choose",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def choose_meeting_calendar_context(
    request: Request,
    meeting_id: UUID,
    event_id: UUID = CalendarContextEventIdForm,
    context_reason: str = CalendarContextReasonForm,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503,
            code="cabinet_store_unavailable",
            title="Cabinet store unavailable",
        )
    await link_meeting_calendar_context(
        db,
        tenant_scope,
        meeting_id=meeting_id,
        event_id=event_id,
        context_reason=context_reason,
    )
    await db.commit()
    return await _calendar_context_review_response(
        request,
        meeting_id=meeting_id,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


@router.post(
    "/meetings/{meeting_id}/calendar-context/continue-without",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/meetings/{meeting_id}/calendar-context/continue-without",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def continue_without_meeting_calendar_context(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    return await _clear_meeting_calendar_context(
        request,
        meeting_id=meeting_id,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


@router.post(
    "/meetings/{meeting_id}/calendar-context/clear",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/meetings/{meeting_id}/calendar-context/clear",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def clear_meeting_calendar_context(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    return await _clear_meeting_calendar_context(
        request,
        meeting_id=meeting_id,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


async def _clear_meeting_calendar_context(
    request: Request,
    *,
    meeting_id: UUID,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    db: AsyncSession | None,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503,
            code="cabinet_store_unavailable",
            title="Cabinet store unavailable",
        )
    await unlink_meeting_calendar_context(db, tenant_scope, meeting_id=meeting_id)
    await db.commit()
    return await _calendar_context_review_response(
        request,
        meeting_id=meeting_id,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


async def _calendar_context_review_response(
    request: Request,
    *,
    meeting_id: UUID,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    db: AsyncSession,
) -> Response:
    embedded = request.url.path.startswith("/desktop/")
    meeting_path = f"{'/desktop' if embedded else ''}/meetings/{meeting_id}"
    if not _is_hx_request(request):
        return RedirectResponse(url=meeting_path, status_code=303)
    review = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
        storage=get_request_storage(request),
        external_invitations_enabled=request.app.state.settings.share_external_invitations_enabled,
    )
    if review is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return cabinet_html_response(
        render_meeting_detail_fragment(
            review,
            embedded=embedded,
            focus_calendar_context=True,
            csrf_token=_csrf_token_for_principal(
                request,
                principal,
                tenant_scope=tenant_scope if embedded else None,
            ),
        ),
        hx_request=True,
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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    provider_copy = CALENDAR_PROVIDER_UI.get(provider_family)
    if provider_copy is None:
        await record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family=provider_family,
            method_category="unknown",
            outcome="failed",
            safe_reason_code="unsupported_calendar_provider",
        )
        await db.commit()
        return calendar_settings_redirect(request, connect_result="failed")
    provider_label, method_category, _ = provider_copy
    await record_calendar_connect_start(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        provider_family=provider_family,
        method_category=method_category,
    )
    if method_category == "provider_specific_limited":
        await record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family=provider_family,
            method_category=method_category,
            outcome="blocked",
            safe_reason_code="provider_limited",
        )
        await db.commit()
        return calendar_settings_redirect(request, policy_limited="provider_limited")
    if method_category == "oauth" and provider_family == "google_calendar":
        config = _google_oauth_config(request)
        if config is None:
            await record_calendar_connect_result(
                db,
                tenant_scope=tenant_scope,
                principal=principal,
                provider_family=provider_family,
                method_category=method_category,
                outcome="blocked",
                safe_reason_code="dependency_missing",
            )
            await db.commit()
            return calendar_settings_redirect(request, connect_result="dependency_missing")
        state = _google_state(request, tenant_scope, principal)
        authorization_url = build_google_authorization_url(config, state=state)
        response = RedirectResponse(authorization_url, status_code=303)
        _set_google_state_cookie(
            response,
            request,
            [*_google_cookie_states(request.cookies.get(GOOGLE_STATE_COOKIE)), state],
        )
        await db.commit()
        return response
    secret_payload = calendar_connection_secret(
        method_category=method_category,
        caldav_url=caldav_url,
        username=username,
        credential_input=credential_input,
    )
    if secret_payload is None:
        await record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family=provider_family,
            method_category=method_category,
            outcome="failed",
            safe_reason_code="missing_required_fields",
        )
        await db.commit()
        return calendar_settings_redirect(request, connect_result="failed")
    try:
        provider_factory = getattr(request.app.state, "calendar_provider_factory", None)
        provider = provider_factory(provider_family) if callable(provider_factory) else None
        validation = await validate_provider_connection(
            provider_family,
            secret_payload,
            provider=provider,
        )
        source = await connect_source(
            db,
            tenant_scope,
            provider_family=provider_family,
            auth_mode="manual_url" if method_category == "manual_url" else "app_password",
            display_label=(account_label or "").strip() or provider_label,
            credential_input=secret_payload,
            selected_provider_calendar_ids=[],
            credential_encryption_key=_credential_encryption_key(request),
            validated_calendars=validation.calendars,
            account_subject=validation.account_subject,
            granted_scopes=validation.granted_scopes,
        )
    except (CalendarProviderError, ProblemDetail) as exc:
        safe_code = getattr(exc, "safe_code", None) or getattr(exc, "code", None)
        result = calendar_connection_result_from_problem(safe_code)
        await record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family=provider_family,
            method_category=method_category,
            outcome="failed",
            safe_reason_code=safe_code,
        )
        await db.commit()
        return calendar_settings_redirect(request, connect_result=result)
    await record_calendar_connect_result(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        provider_family=provider_family,
        method_category=method_category,
        outcome="completed",
        source_id=source.id,
    )
    await db.commit()
    return calendar_settings_redirect(request, connect_result="success")


@router.get(
    "/settings/integrations/calendar/google/callback",
    response_class=HTMLResponse,
    include_in_schema=False,
)
@router.get(
    "/desktop/settings/integrations/calendar/google/callback",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def google_calendar_oauth_callback(
    request: Request,
    state: str | None = CalendarOAuthStateQuery,
    code: str | None = CalendarOAuthCodeQuery,
    error: str | None = Query(default=None, max_length=80),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    state_claims = _verify_google_state(
        request, state or "", request.cookies.get(GOOGLE_STATE_COOKIE)
    )
    if state_claims is not None and (
        state_claims[1] != str(tenant_scope.workspace_id)
        or state_claims[2] != str(principal.user_id)
    ):
        state_claims = None
    return_path = state_claims[0] if state_claims else None
    response_kwargs = {"return_path": return_path} if return_path else {}
    if return_path is None:
        response = calendar_settings_redirect(request, connect_result="failed")
        _consume_google_state(response, request, state)
        return response
    if error or not code:
        await record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family="google_calendar",
            method_category="oauth",
            outcome="cancelled" if error in {"access_denied", "cancelled"} else "failed",
            safe_reason_code="cancelled"
            if error in {"access_denied", "cancelled"}
            else "missing_code",
        )
        await db.commit()
        response = calendar_settings_redirect(
            request,
            connect_result="cancelled" if error in {"access_denied", "cancelled"} else "failed",
            **response_kwargs,
        )
        _consume_google_state(response, request, state)
        return response
    config = _google_oauth_config(request)
    if config is None:
        response = calendar_settings_redirect(
            request, connect_result="dependency_missing", **response_kwargs
        )
        _consume_google_state(response, request, state)
        return response
    try:
        adapter = GoogleCalendarAdapter(config)
        token_set = await adapter.exchange_code(code)
        if not token_set.refresh_token:
            raise CalendarProviderError("provider_policy_denied")
        validation = await adapter.validate(token_set.access_token)
        source = await connect_source(
            db,
            tenant_scope,
            provider_family="google_calendar",
            auth_mode="oauth",
            display_label="Google Calendar",
            credential_input=token_set.refresh_token,
            selected_provider_calendar_ids=[],
            credential_encryption_key=_credential_encryption_key(request),
            validated_calendars=validation.calendars,
            account_subject=validation.account_subject,
            granted_scopes=token_set.scope or validation.granted_scopes,
        )
    except (CalendarProviderError, ProblemDetail) as exc:
        safe_reason = getattr(exc, "safe_code", None) or getattr(
            exc, "code", "provider_unavailable"
        )
        await record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family="google_calendar",
            method_category="oauth",
            outcome="failed",
            safe_reason_code=safe_reason,
        )
        await db.commit()
        response = calendar_settings_redirect(request, connect_result="failed", **response_kwargs)
        _consume_google_state(response, request, state)
        return response
    await record_calendar_connect_result(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        provider_family="google_calendar",
        method_category="oauth",
        outcome="completed",
        source_id=source.id,
    )
    await db.commit()
    response = calendar_settings_redirect(request, connect_result="success", **response_kwargs)
    _consume_google_state(response, request, state)
    return response


@router.get(
    "/settings/integrations/calendar/provider-result",
    response_class=HTMLResponse,
    include_in_schema=False,
)
@router.get(
    "/desktop/settings/integrations/calendar/provider-result",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def calendar_provider_result(
    request: Request,
    result: str | None = CalendarProviderResultQuery,
    provider_family: str | None = CalendarProviderFamilyQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    safe_result = safe_calendar_provider_result(result)
    provider = provider_family or "unknown"
    method_category = calendar_provider_method_category(provider)
    if safe_result == "success":
        await record_calendar_connect_result(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            provider_family=provider,
            method_category=method_category,
            outcome="blocked",
            safe_reason_code="provider_limited",
        )
        await db.commit()
        return calendar_settings_redirect(request, policy_limited="provider_limited")
    await record_calendar_connect_result(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        provider_family=provider,
        method_category=method_category,
        outcome=safe_result,
        safe_reason_code=safe_result,
    )
    await db.commit()
    return calendar_settings_redirect(request, connect_result=safe_result)


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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    form = await request.form()
    selected_ids = [
        str(value) for value in form.getlist("selected_provider_calendar_ids") if str(value).strip()
    ]
    source = await get_source(db, tenant_scope, source_id)
    try:
        await replace_selected_calendars(
            db, tenant_scope, source, selected_ids, allow_missing=False
        )
    except ProblemDetail as error:
        if error.code != "calendar_selection_limit_exceeded":
            raise
        await db.rollback()
        return calendar_settings_redirect(request, selection_result="limit_exceeded")
    await db.commit()
    return calendar_settings_redirect(
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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    source = await get_source(db, tenant_scope, source_id)
    await record_calendar_source_event(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        source_id=source.id,
        event_type="calendar_manual_sync_requested",
        outcome="accepted",
    )
    requested_at = datetime.now(UTC)
    source = await request_source_sync(db, tenant_scope, source.id)
    source = await get_source(db, tenant_scope, source.id)
    result = calendar_manual_sync_result(source, requested_at=requested_at)
    await record_calendar_source_event(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        source_id=source.id,
        event_type="calendar_manual_sync_result",
        outcome="accepted" if result == "accepted" else result,
        safe_reason_code=None if result == "accepted" else result,
    )
    await db.commit()
    return calendar_settings_redirect(request, sync_result=result)


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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    source = await get_source(db, tenant_scope, source_id)
    await record_calendar_source_event(
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
        await record_calendar_source_event(
            db,
            tenant_scope=tenant_scope,
            principal=principal,
            source_id=source.id,
            event_type="calendar_disconnect_result",
            outcome="failed",
            safe_reason_code="failed",
        )
        await db.commit()
        return calendar_settings_redirect(request, disconnect_result="failed")
    disconnect_result = calendar_disconnect_result(result)
    await record_calendar_source_event(
        db,
        tenant_scope=tenant_scope,
        principal=principal,
        source_id=source.id,
        event_type="calendar_disconnect_result",
        outcome="completed" if disconnect_result == "success" else disconnect_result,
        safe_reason_code=None if disconnect_result == "success" else disconnect_result,
    )
    await db.commit()
    return calendar_settings_redirect(request, disconnect_result=disconnect_result)


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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    form = await request.form()
    await save_calendar_settings_preferences(
        db,
        tenant_scope,
        join_prompt_enabled=calendar_form_checkbox(form, "join_prompt_enabled"),
        record_prompt_enabled=calendar_form_checkbox(form, "record_prompt_enabled"),
        show_upcoming_time=calendar_form_checkbox(form, "show_upcoming_time"),
        show_upcoming_title=calendar_form_checkbox(form, "show_upcoming_title"),
        include_events_without_participants=calendar_form_checkbox(
            form, "include_events_without_participants"
        ),
        include_events_without_link_or_location=calendar_form_checkbox(
            form, "include_events_without_link_or_location"
        ),
        include_all_day_events=calendar_form_checkbox(form, "include_all_day_events"),
        include_private_free_busy_prompt_candidates=calendar_form_checkbox(
            form,
            "include_private_free_busy_prompt_candidates",
        ),
    )
    await db.commit()
    return calendar_settings_redirect(request, preferences_result="saved")
