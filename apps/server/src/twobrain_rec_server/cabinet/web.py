from __future__ import annotations

import secrets
from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.calendar import _credential_key as calendar_credential_key
from twobrain_rec_server.api.ingest import get_request_storage
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    AccessState,
    MeetingReviewStatus,
)
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import (
    AUTH_SESSION_COOKIE_NAME,
    DESKTOP_CALENDAR_AUTH_COOKIE_PATH,
    get_principal,
    get_web_owner_tenant_scope,
    require_web_csrf,
    set_desktop_calendar_auth_cookie,
)
from twobrain_rec_server.auth.policy import read_auth_providers
from twobrain_rec_server.auth.providers import build_provider_registry
from twobrain_rec_server.auth.sessions import (
    callback_expiry,
    hash_token,
    issue_auth_session,
)
from twobrain_rec_server.cabinet.access import decide_meeting_access
from twobrain_rec_server.cabinet.queries import (
    get_cabinet_meeting_review,
    get_calendar_settings_surface,
    list_cabinet_meetings,
)
from twobrain_rec_server.cabinet.rendering import (
    _base_path,
    _safe_browser_next_path,
    calendar_connection_result_from_problem,
    calendar_settings_notice_codes,
    render_calendar_settings_fragment,
    render_calendar_settings_page,
    render_deletion_feedback_fragment,
    render_deletion_report_fragment,
    render_deletion_report_page,
    render_email_code_page,
    render_login_page,
    render_meeting_detail_fragment,
    render_meeting_detail_page,
    render_meeting_list_fragment,
    render_meeting_list_page,
    render_signup_page,
)
from twobrain_rec_server.cabinet.templates import (
    cabinet_html_response,
)
from twobrain_rec_server.cabinet.view_models import CALENDAR_PROVIDER_UI
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
from twobrain_rec_server.db.models import (
    AuthCallbackState,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    Meeting,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.tenant_context import (
    AuthCallbackLookupContext,
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
    apply_tenant_scope,
)
from twobrain_rec_server.deletion.service import deletion_report_response, request_meeting_deletion

router = APIRouter(tags=["cabinet-web"])

WebTenantDependency = Depends(get_web_owner_tenant_scope)
PrincipalDependency = Depends(get_principal)
WebCSRFDependency = Depends(require_web_csrf)
StorageDependency = Depends(get_request_storage)
CabinetSearchQuery = Query(default=None, max_length=120)
CabinetStatusQuery = Query(default=None)
CabinetAccessQuery = Query(default=None)
CabinetSortQuery = Query(default="updated_desc")
CabinetLimitQuery = Query(default=50, ge=1, le=100)
CalendarConnectResultQuery = Query(default=None, max_length=48, alias="connect_result")
CalendarPolicyLimitedQuery = Query(default=None, max_length=48, alias="policy_limited")
CalendarSelectionResultQuery = Query(default=None, max_length=48, alias="selection_result")
CalendarPreferencesResultQuery = Query(default=None, max_length=48, alias="preferences_result")
CalendarSyncResultQuery = Query(default=None, max_length=48, alias="sync_result")
CalendarDisconnectResultQuery = Query(default=None, max_length=48, alias="disconnect_result")
CalendarProviderResultQuery = Query(default=None, max_length=48, alias="result")
CalendarProviderFamilyQuery = Query(default=None, max_length=80, alias="provider_family")
LoginWorkspaceQuery = Query(default=None)
LoginNextQuery = Query(default="/meetings", alias="next", max_length=512)
LoginErrorQuery = Query(default=None, max_length=120)
SignupModeQuery = Query(default=None, max_length=32, alias="mode")
LoginEmailForm = Form(..., max_length=240)
LoginCodeForm = Form(..., max_length=32)
LoginStateForm = Form(..., max_length=160)
LoginWorkspaceForm = Form(default=None)
LoginNextForm = Form(default="/meetings", alias="next", max_length=512)
CalendarAccountLabelForm = Form(default=None, max_length=160)
CalendarCalDAVURLForm = Form(default=None, max_length=1000)
CalendarUsernameForm = Form(default=None, max_length=240)
CalendarCredentialForm = Form(default=None, max_length=2000)
EMAIL_LOGIN_PROVIDER = "email"
EMAIL_SIGNUP_PROVIDER = "email_signup"


def _is_hx_request(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


@router.get("/favicon.ico", include_in_schema=False)
@router.get("/apple-touch-icon.png", include_in_schema=False)
@router.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
async def browser_icon_probe() -> Response:
    return Response(status_code=204)


async def get_web_request_db_session(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        await apply_tenant_scope(session, tenant_scope)
        yield session


WebDbDependency = Depends(get_web_request_db_session)


async def get_web_login_db_session(request: Request):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        yield session


LoginDbDependency = Depends(get_web_login_db_session)



@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def browser_login_page(
    request: Request,
    workspace_id: UUID | None = LoginWorkspaceQuery,
    next_path: str = LoginNextQuery,
    error: str | None = LoginErrorQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    providers = []
    load_error = error
    if resolved_workspace_id is not None and db is not None:
        try:
            providers = await _load_browser_login_providers(db, resolved_workspace_id)
        except ProblemDetail as exc:
            load_error = exc.code
    elif resolved_workspace_id is not None and db is None:
        load_error = "auth_dependency_unavailable"
    return HTMLResponse(
        render_login_page(
            workspace_id=resolved_workspace_id,
            providers=providers,
            next_path=safe_next,
            error=load_error,
        )
    )


@router.get("/sign-up", response_class=HTMLResponse, include_in_schema=False)
async def browser_signup_page(
    request: Request,
    workspace_id: UUID | None = LoginWorkspaceQuery,
    next_path: str = LoginNextQuery,
    error: str | None = LoginErrorQuery,
    mode: str | None = SignupModeQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    providers = []
    load_error = error
    if resolved_workspace_id is not None and db is not None:
        try:
            providers = await _load_browser_login_providers(db, resolved_workspace_id)
        except ProblemDetail as exc:
            load_error = exc.code
    elif resolved_workspace_id is not None and db is None:
        load_error = "auth_dependency_unavailable"
    return HTMLResponse(
        render_signup_page(
            workspace_id=resolved_workspace_id,
            providers=providers,
            next_path=safe_next,
            error=load_error,
            mode=mode,
        )
    )


@router.post("/login/email/start", response_class=HTMLResponse, include_in_schema=False)
async def browser_email_login_start(
    request: Request,
    email: str = LoginEmailForm,
    workspace_id: UUID | None = LoginWorkspaceForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    if resolved_workspace_id is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=None,
                providers=[],
                next_path=safe_next,
                error="workspace_required",
            ),
            status_code=400,
        )
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    normalized_email = _normalize_email(email)
    if normalized_email is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="email_invalid",
            ),
            status_code=400,
        )
    workspace, user = await _resolve_email_login_user(
        db,
        workspace_id=resolved_workspace_id,
        email=normalized_email,
    )
    if workspace is None or user is None:
        if workspace is not None:
            await _record_email_login_audit(
                db,
                request=request,
                workspace_id=workspace.id,
                outcome="failure",
                error_code="email_identity_not_found",
            )
            await db.commit()
        return HTMLResponse(
            render_login_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="email_start_unavailable",
            ),
            status_code=400,
        )
    code = _issue_email_login_code()
    ttl_seconds = request.app.state.settings.auth_callback_state_ttl_seconds
    state = await _create_email_login_state(
        db,
        workspace_id=resolved_workspace_id,
        next_path=safe_next,
        code=code,
        ttl_seconds=ttl_seconds,
    )
    dev_code = code if _should_echo_email_code(request) else None
    if dev_code is None:
        try:
            await email_delivery.send_email_login_code(
                settings=request.app.state.settings,
                recipient_email=normalized_email,
                code=code,
                ttl_seconds=ttl_seconds,
            )
        except email_delivery.EmailLoginDeliveryError:
            state.result = "failed"
            state.used_at = datetime.now(UTC)
            state.error_code = "email_delivery_unavailable"
            await _record_email_login_audit(
                db,
                request=request,
                workspace_id=resolved_workspace_id,
                outcome="failure",
                error_code="email_delivery_unavailable",
            )
            await db.commit()
            return HTMLResponse(
                render_login_page(
                    workspace_id=resolved_workspace_id,
                    providers=[],
                    next_path=safe_next,
                    error="email_delivery_unavailable",
                ),
                status_code=503,
            )
    await _record_email_login_audit(
        db,
        request=request,
        workspace_id=resolved_workspace_id,
        outcome="success",
    )
    await db.commit()
    return HTMLResponse(
        render_email_code_page(
            email=normalized_email,
            workspace_id=resolved_workspace_id,
            state_nonce=state.state_nonce,
            next_path=safe_next,
            dev_code=dev_code,
        )
    )


@router.post("/sign-up/email/start", response_class=HTMLResponse, include_in_schema=False)
async def browser_email_signup_start(
    request: Request,
    email: str = LoginEmailForm,
    workspace_id: UUID | None = LoginWorkspaceForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    if resolved_workspace_id is None:
        return HTMLResponse(
            render_signup_page(
                workspace_id=None,
                providers=[],
                next_path=safe_next,
                error="workspace_required",
            ),
            status_code=400,
        )
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    normalized_email = _normalize_email(email)
    if normalized_email is None:
        return HTMLResponse(
            render_signup_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="email_invalid",
            ),
            status_code=400,
        )
    workspace = await _resolve_email_workspace(db, workspace_id=resolved_workspace_id)
    if workspace is None:
        return HTMLResponse(
            render_signup_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="email_start_unavailable",
            ),
            status_code=400,
        )
    code = _issue_email_login_code()
    ttl_seconds = request.app.state.settings.auth_callback_state_ttl_seconds
    state = await _create_email_login_state(
        db,
        workspace_id=resolved_workspace_id,
        next_path=safe_next,
        code=code,
        ttl_seconds=ttl_seconds,
        provider=EMAIL_SIGNUP_PROVIDER,
    )
    dev_code = code if _should_echo_email_code(request) else None
    if dev_code is None:
        try:
            await email_delivery.send_email_login_code(
                settings=request.app.state.settings,
                recipient_email=normalized_email,
                code=code,
                ttl_seconds=ttl_seconds,
            )
        except email_delivery.EmailLoginDeliveryError:
            state.result = "failed"
            state.used_at = datetime.now(UTC)
            state.error_code = "email_delivery_unavailable"
            await _record_email_login_audit(
                db,
                request=request,
                workspace_id=resolved_workspace_id,
                outcome="failure",
                error_code="email_delivery_unavailable",
                metadata={"flow": "registration"},
            )
            await db.commit()
            return HTMLResponse(
                render_signup_page(
                    workspace_id=resolved_workspace_id,
                    providers=[],
                    next_path=safe_next,
                    error="email_delivery_unavailable",
                ),
                status_code=503,
            )
    await _record_email_login_audit(
        db,
        request=request,
        workspace_id=resolved_workspace_id,
        outcome="success",
        metadata={"flow": "registration"},
    )
    await db.commit()
    return HTMLResponse(
        render_email_code_page(
            email=normalized_email,
            workspace_id=resolved_workspace_id,
            state_nonce=state.state_nonce,
            next_path=safe_next,
            dev_code=dev_code,
            flow="signup",
        )
    )


@router.post("/login/email/verify", include_in_schema=False, response_model=None)
async def browser_email_login_verify(
    request: Request,
    email: str = LoginEmailForm,
    code: str = LoginCodeForm,
    state: str = LoginStateForm,
    workspace_id: UUID | None = LoginWorkspaceForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
):
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    normalized_email = _normalize_email(email)
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    if resolved_workspace_id is None or normalized_email is None:
        return HTMLResponse(
            render_email_code_page(
                email=normalized_email or "",
                workspace_id=resolved_workspace_id,
                state_nonce=state,
                next_path=safe_next,
                error="email_code_invalid",
            ),
            status_code=400,
        )
    result = await _consume_email_login_code(
        db,
        request=request,
        workspace_id=resolved_workspace_id,
        email=normalized_email,
        code=code,
        state_nonce=state,
        next_path=safe_next,
    )
    if isinstance(result, HTMLResponse):
        return result
    redirect = RedirectResponse(safe_next, status_code=303)
    _set_browser_auth_cookie(redirect, token=result.token, expires_at=result.expires_at)
    return redirect


@router.post("/sign-up/email/verify", include_in_schema=False, response_model=None)
async def browser_email_signup_verify(
    request: Request,
    email: str = LoginEmailForm,
    code: str = LoginCodeForm,
    state: str = LoginStateForm,
    workspace_id: UUID | None = LoginWorkspaceForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
):
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    normalized_email = _normalize_email(email)
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    if resolved_workspace_id is None or normalized_email is None:
        return HTMLResponse(
            render_email_code_page(
                email=normalized_email or "",
                workspace_id=resolved_workspace_id,
                state_nonce=state,
                next_path=safe_next,
                error="email_code_invalid",
                flow="signup",
            ),
            status_code=400,
        )
    result = await _consume_email_login_code(
        db,
        request=request,
        workspace_id=resolved_workspace_id,
        email=normalized_email,
        code=code,
        state_nonce=state,
        next_path=safe_next,
        provider=EMAIL_SIGNUP_PROVIDER,
        allow_registration=True,
    )
    if isinstance(result, HTMLResponse):
        return result
    redirect = RedirectResponse(safe_next, status_code=303)
    _set_browser_auth_cookie(redirect, token=result.token, expires_at=result.expires_at)
    return redirect


@router.get("/login/{provider}/start", include_in_schema=False, response_model=None)
async def browser_login_provider_start(
    provider: str,
    request: Request,
    workspace_id: UUID | None = LoginWorkspaceQuery,
    next_path: str = LoginNextQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    _ = provider
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    if resolved_workspace_id is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=None,
                providers=[],
                next_path=safe_next,
                error="workspace_required",
            ),
            status_code=400,
        )
    providers = []
    if db is not None:
        try:
            providers = await _load_browser_login_providers(db, resolved_workspace_id)
        except ProblemDetail:
            providers = []
    return HTMLResponse(
        render_login_page(
            workspace_id=resolved_workspace_id,
            providers=providers,
            next_path=safe_next,
            error="provider_future",
        ),
        status_code=501,
    )


@router.get("/meetings", response_class=HTMLResponse, include_in_schema=False)
async def meeting_list_page(
    request: Request,
    q: str | None = CabinetSearchQuery,
    status: MeetingReviewStatus | None = CabinetStatusQuery,
    access: AccessState | None = CabinetAccessQuery,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await list_cabinet_meetings(
        db,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=principal.user_id,
        q=q,
        status=status,
        access=access,
        sort=sort,
        limit=limit,
    )
    if _is_hx_request(request):
        return cabinet_html_response(
            render_meeting_list_fragment(response),
            hx_request=True,
        )
    return cabinet_html_response(
        render_meeting_list_page(
            response,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )


@router.get("/meetings/{meeting_id}", response_class=HTMLResponse, include_in_schema=False)
async def meeting_detail_page(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if response is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if _is_hx_request(request):
        return cabinet_html_response(
            render_meeting_detail_fragment(response),
            hx_request=True,
        )
    return cabinet_html_response(
        render_meeting_detail_page(
            response,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )


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
            credential_key=calendar_credential_key(request),
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


@router.get(
    "/meetings/{meeting_id}/deletion-report",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def meeting_deletion_report_page(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting = await _authorized_lifecycle_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    report = await deletion_report_response(db, meeting=meeting)
    meeting_title = meeting.title or "Deleted meeting"
    if _is_hx_request(request):
        return cabinet_html_response(
            render_deletion_report_fragment(meeting_title, report),
            hx_request=True,
        )
    return cabinet_html_response(
        render_deletion_report_page(
            meeting_title,
            report,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )


@router.get("/desktop/meetings", response_class=HTMLResponse, include_in_schema=False)
async def embedded_meeting_list_page(
    request: Request,
    q: str | None = CabinetSearchQuery,
    status: MeetingReviewStatus | None = CabinetStatusQuery,
    access: AccessState | None = CabinetAccessQuery,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await list_cabinet_meetings(
        db,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=principal.user_id,
        q=q,
        status=status,
        access=access,
        sort=sort,
        limit=limit,
    )
    if _is_hx_request(request):
        return cabinet_html_response(
            render_meeting_list_fragment(response, embedded=True),
            hx_request=True,
        )
    return cabinet_html_response(
        render_meeting_list_page(
            response,
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )


@router.get("/desktop/meetings/{meeting_id}", response_class=HTMLResponse, include_in_schema=False)
async def embedded_meeting_detail_page(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if response is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if _is_hx_request(request):
        return cabinet_html_response(
            render_meeting_detail_fragment(response, embedded=True),
            hx_request=True,
        )
    return cabinet_html_response(
        render_meeting_detail_page(
            response,
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )


@router.get("/desktop/settings/integrations/calendar", response_class=HTMLResponse, include_in_schema=False)
async def embedded_calendar_settings_page(
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
        response = cabinet_html_response(
            render_calendar_settings_fragment(
                surface,
                embedded=True,
                csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
            ),
            hx_request=True,
        )
        set_desktop_calendar_auth_cookie(
            response,
            request=request,
            principal=principal,
            tenant_scope=tenant_scope,
        )
        return response
    response = cabinet_html_response(
        render_calendar_settings_page(
            surface,
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        )
    )
    set_desktop_calendar_auth_cookie(
        response,
        request=request,
        principal=principal,
        tenant_scope=tenant_scope,
    )
    return response


@router.get(
    "/desktop/meetings/{meeting_id}/deletion-report",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def embedded_meeting_deletion_report_page(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting = await _authorized_lifecycle_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    report = await deletion_report_response(db, meeting=meeting)
    meeting_title = meeting.title or "Deleted meeting"
    if _is_hx_request(request):
        return cabinet_html_response(
            render_deletion_report_fragment(meeting_title, report, embedded=True),
            hx_request=True,
        )
    return cabinet_html_response(
        render_deletion_report_page(
            meeting_title,
            report,
            embedded=True,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    )


@router.post(
    "/meetings/{meeting_id}/deletion-requests",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/meetings/{meeting_id}/deletion-requests",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def meeting_deletion_request_page(
    request: Request,
    meeting_id: UUID,
    confirmation_boundary: str = Form(...),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    _ensure_lifecycle_manager(decision)
    response = await request_meeting_deletion(
        db,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=principal.session_device_id,
        confirmation_boundary=confirmation_boundary,
        storage=storage,
    )
    await db.commit()
    embedded = request.url.path.startswith("/desktop/")
    report_url = f"{_base_path(embedded)}/{response.meeting_id}/deletion-report"
    if _is_hx_request(request):
        return cabinet_html_response(
            render_deletion_feedback_fragment(report_url=report_url),
            status_code=202,
            hx_request=True,
        )
    return RedirectResponse(report_url, status_code=303)


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
    if source.connection_state in {"disconnected"} or source.disconnected_at is not None:
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


def _csrf_token_for_principal(
    request: Request,
    principal: AuthenticatedPrincipal,
    *,
    tenant_scope: TenantScope | None = None,
) -> str | None:
    csrf_subject_id = principal.session_id
    if not principal.auth_via_session:
        if tenant_scope is None or not request.url.path.startswith(DESKTOP_CALENDAR_AUTH_COOKIE_PATH):
            return None
        csrf_subject_id = tenant_scope.device_id
    if csrf_subject_id is None:
        return None
    secret = getattr(request.app.state, "web_csrf_secret", None)
    if not secret:
        raise ProblemDetail(
            status=503,
            code="csrf_secret_unavailable",
            title="CSRF protection unavailable",
        )
    return issue_csrf_token(session_id=csrf_subject_id, secret=str(secret))


async def _load_browser_login_providers(db: AsyncSession, workspace_id: UUID) -> list:
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
    snapshot = await read_auth_providers(db, workspace_id, adapters=build_provider_registry())
    return list(snapshot.providers)


async def _record_email_login_audit(
    db: AsyncSession,
    *,
    request: Request,
    workspace_id: UUID,
    outcome: str = "success",
    user_id: UUID | None = None,
    error_code: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    audit_metadata = {"flow": "email_login"}
    if metadata:
        audit_metadata.update(metadata)
    if error_code is not None:
        audit_metadata["error_code"] = error_code
    await write_auth_audit_event(
        db,
        workspace_id=workspace_id,
        event_type="email_auth_started" if user_id is None else "email_auth_completed",
        provider="email",
        outcome=outcome,
        actor_ip=request.client.host if request.client else None,
        request_id=getattr(request.state, "request_id", None),
        user_id=user_id,
        actor_user_id=user_id,
        metadata=audit_metadata,
    )


async def _create_email_login_state(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    next_path: str,
    code: str,
    ttl_seconds: int,
    provider: str = EMAIL_LOGIN_PROVIDER,
) -> AuthCallbackState:
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
    state = AuthCallbackState(
        provider=provider,
        state_nonce=secrets.token_urlsafe(24),
        workspace_id=workspace_id,
        requested_redirect=_safe_browser_next_path(next_path),
        expected_state=hash_token(_normalize_email_code(code)),
        expires_at=callback_expiry(ttl_seconds=ttl_seconds),
        result="pending",
    )
    db.add(state)
    await db.flush()
    await db.refresh(state)
    return state


async def _consume_email_login_code(
    db: AsyncSession,
    *,
    request: Request,
    workspace_id: UUID | None,
    email: str,
    code: str,
    state_nonce: str,
    next_path: str,
    provider: str = EMAIL_LOGIN_PROVIDER,
    allow_registration: bool = False,
):
    now = datetime.now(UTC)
    await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state_nonce))
    state = await db.scalar(
        select(AuthCallbackState).where(
            AuthCallbackState.provider == provider,
            AuthCallbackState.state_nonce == state_nonce,
        )
    )
    flow = "signup" if allow_registration else "login"
    if state is None:
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    if workspace_id is not None and state.workspace_id != workspace_id:
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    workspace_id = state.workspace_id
    if state.result != "pending":
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    expires_at = state.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        state.result = "expired"
        state.used_at = now
        state.error_code = "email_code_expired"
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="email_code_expired",
        )
        await db.commit()
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_expired",
            flow=flow,
        )
    if state.expected_state != hash_token(_normalize_email_code(code)):
        state.result = "failed"
        state.used_at = now
        state.error_code = "email_code_invalid"
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="email_code_invalid",
        )
        await db.commit()
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    workspace, user = await _resolve_email_login_user(db, workspace_id=workspace_id, email=email)
    if workspace is not None and user is None and allow_registration:
        user = await _ensure_email_registration_user(
            db,
            workspace=workspace,
            email=email,
            now=now,
        )
    if workspace is None or user is None:
        state.result = "failed"
        state.used_at = now
        state.error_code = "email_identity_not_found"
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="email_code_invalid",
        )
        await db.commit()
        return _email_code_error_response(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    device = await _resolve_email_browser_device(db, workspace=workspace, user=user, now=now)
    issued = await issue_auth_session(
        db,
        user_id=user.id,
        workspace_id=workspace.id,
        device_id=device.id,
        provider="email",
        ttl_seconds=request.app.state.settings.auth_session_ttl_seconds,
        claims_fingerprint=hash_token(f"email:{email}:{workspace.id}"),
        now=now,
    )
    db.add(
        AuthSessionDeviceBinding(
            auth_session_id=issued.id,
            registered_device_id=device.id,
            device_state="trusted",
            last_heartbeat_at=now,
        )
    )
    state.result = "completed"
    state.used_at = now
    await _record_email_login_audit(
        db,
        request=request,
        workspace_id=workspace.id,
        outcome="success",
        user_id=user.id,
        metadata={"flow": "registration"} if allow_registration else None,
    )
    await db.commit()
    return issued


async def _resolve_email_login_user(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    email: str,
) -> tuple[Workspace | None, UserIdentity | None]:
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        return None, None
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
            context_kind="auth_bootstrap",
        ),
    )
    candidates = (
        await db.execute(
            select(ExternalIdentity, UserIdentity)
            .join(UserIdentity, UserIdentity.id == ExternalIdentity.user_id)
            .where(
                UserIdentity.organization_id == workspace.organization_id,
                UserIdentity.status == "active",
                func.lower(ExternalIdentity.email) == email,
            )
            .order_by(ExternalIdentity.created_at.asc())
        )
    ).all()
    for identity, user in candidates:
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=workspace.id,
                organization_id=workspace.organization_id,
                user_id=user.id,
                context_kind="auth_bootstrap",
            ),
        )
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.user_id == identity.user_id,
                WorkspaceMembership.status == "active",
            )
        )
        if membership is not None:
            return workspace, user
    return workspace, None


async def _resolve_email_workspace(db: AsyncSession, *, workspace_id: UUID) -> Workspace | None:
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
    return await db.get(Workspace, workspace_id)


async def _ensure_email_registration_user(
    db: AsyncSession,
    *,
    workspace: Workspace,
    email: str,
    now: datetime,
) -> UserIdentity:
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
            context_kind="auth_bootstrap",
        ),
    )
    existing = (
        await db.execute(
            select(ExternalIdentity, UserIdentity)
            .join(UserIdentity, UserIdentity.id == ExternalIdentity.user_id)
            .where(
                UserIdentity.organization_id == workspace.organization_id,
                UserIdentity.status == "active",
                func.lower(ExternalIdentity.email) == email,
            )
            .order_by(ExternalIdentity.created_at.asc())
        )
    ).first()
    if existing is not None:
        identity, user = existing
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=workspace.id,
                organization_id=workspace.organization_id,
                user_id=user.id,
                context_kind="auth_bootstrap",
            ),
        )
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.user_id == identity.user_id,
            )
        )
        if membership is None:
            db.add(
                WorkspaceMembership(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role="member",
                    status="active",
                )
            )
            await db.flush()
        else:
            membership.status = "active"
        identity.is_verified = True
        identity.last_seen_at = now
        return user

    display_name = email.partition("@")[0].replace(".", " ").replace("_", " ").title() or email
    user = UserIdentity(
        organization_id=workspace.organization_id,
        external_subject=f"email:{email}",
        display_name=display_name,
        status="active",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
            user_id=user.id,
            context_kind="auth_bootstrap",
        ),
    )
    db.add(
        WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=user.id,
            role="member",
            status="active",
        )
    )
    db.add(
        ExternalIdentity(
            user_id=user.id,
            provider=EMAIL_LOGIN_PROVIDER,
            provider_subject=email,
            provider_username=email,
            email=email,
            display_name=display_name,
            is_verified=True,
            subject_issued_at=now,
            last_seen_at=now,
            meta={"flow": "browser_registration"},
        )
    )
    await db.flush()
    return user


async def _resolve_email_browser_device(
    db: AsyncSession,
    *,
    workspace: Workspace,
    user: UserIdentity,
    now: datetime,
) -> RegisteredDevice:
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=workspace.organization_id,
            workspace_id=workspace.id,
            user_id=user.id,
        ),
    )
    device_public_id = f"browser-email:{user.id}"
    device = await db.scalar(
        select(RegisteredDevice).where(
            RegisteredDevice.workspace_id == workspace.id,
            RegisteredDevice.user_id == user.id,
            RegisteredDevice.device_public_id == device_public_id,
        )
    )
    if device is None:
        device = RegisteredDevice(
            workspace_id=workspace.id,
            user_id=user.id,
            device_public_id=device_public_id,
            platform="web",
            client_version="email-login",
            status="active",
            registration_state="approved",
            trusted_by=user.id,
            last_seen_at=now,
        )
        db.add(device)
        await db.flush()
        await db.refresh(device)
        return device
    device.platform = "web"
    device.client_version = "email-login"
    device.status = "active"
    device.registration_state = "approved"
    device.last_seen_at = now
    return device


def _email_code_error_response(
    *,
    email: str,
    workspace_id: UUID | None,
    state_nonce: str,
    next_path: str,
    error: str,
    flow: str = "login",
) -> HTMLResponse:
    return HTMLResponse(
        render_email_code_page(
            email=email,
            workspace_id=workspace_id,
            state_nonce=state_nonce,
            next_path=next_path,
            error=error,
            flow=flow,
        ),
        status_code=400,
    )


def _set_browser_auth_cookie(response, *, token: str, expires_at: datetime) -> None:
    token_expires_at = expires_at
    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(tzinfo=UTC)
    max_age = max(0, int((token_expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        key=AUTH_SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _normalize_email(value: str) -> str | None:
    normalized = value.strip().lower()
    if not normalized or "@" not in normalized or len(normalized) > 240:
        return None
    local, _, domain = normalized.partition("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        return None
    return normalized


def _issue_email_login_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _normalize_email_code(value: str) -> str:
    return "".join(char for char in value.strip() if char.isdigit())


def _should_echo_email_code(request: Request) -> bool:
    return request.app.state.settings.env.lower() != "production"


def _resolve_browser_login_workspace_id(request: Request, workspace_id: UUID | None) -> UUID | None:
    if workspace_id is not None:
        return workspace_id
    settings = request.app.state.settings
    configured = getattr(settings, "web_login_workspace_id", None)
    if configured is not None:
        return configured
    return None

async def _authorized_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
):
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == meeting_id,
        )
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=viewer_user_id,
    )
    if not decision.can_view:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting, decision


def _ensure_lifecycle_manager(decision) -> None:
    if decision.state != "owner" and decision.role not in {"owner", "admin"}:
        raise ProblemDetail(status=403, code="deletion_forbidden", title="Deletion is not available")


async def _authorized_lifecycle_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
) -> Meeting:
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == meeting_id,
        )
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == viewer_user_id,
            WorkspaceMembership.status == "active",
        )
    )
    role = membership.role if membership is not None else None
    if meeting.created_by_user_id != viewer_user_id and role not in {"owner", "admin"}:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting
