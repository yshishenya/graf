from __future__ import annotations

import secrets
from datetime import UTC, datetime
from html import escape
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.ingest import get_request_storage
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    AccessState,
    ArtifactDeletionState,
    ArtifactEgressState,
    DeletionVerificationReport,
    LocalPurgeTask,
    MeetingListItem,
    MeetingListResponse,
    MeetingReviewResponse,
    MeetingReviewStatus,
    NotesActionCategoryState,
    TranscriptSegmentView,
)
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import (
    AUTH_SESSION_COOKIE_NAME,
    get_principal,
    get_web_owner_tenant_scope,
    require_web_csrf,
)
from twobrain_rec_server.auth.policy import read_auth_providers
from twobrain_rec_server.auth.providers import build_provider_registry
from twobrain_rec_server.auth.sessions import (
    callback_expiry,
    hash_token,
    issue_auth_session,
)
from twobrain_rec_server.cabinet import view_models as cabinet_view_models
from twobrain_rec_server.cabinet.access import decide_meeting_access
from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review, list_cabinet_meetings
from twobrain_rec_server.cabinet.templates import (
    cabinet_html_response,
    render_icon,
    render_template,
    trusted_component_html,
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
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
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
LoginWorkspaceQuery = Query(default=None)
LoginNextQuery = Query(default="/meetings", alias="next", max_length=512)
LoginErrorQuery = Query(default=None, max_length=120)
SignupModeQuery = Query(default=None, max_length=32, alias="mode")
LoginEmailForm = Form(..., max_length=240)
LoginCodeForm = Form(..., max_length=32)
LoginStateForm = Form(..., max_length=160)
LoginWorkspaceForm = Form(default=None)
LoginNextForm = Form(default="/meetings", alias="next", max_length=512)
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
            render_template(
                "cabinet/fragments/deletion_feedback.html",
                report_url=report_url,
            ),
            status_code=202,
            hx_request=True,
        )
    return RedirectResponse(report_url, status_code=303)


def _login_provider_actions(providers: list) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for provider in providers:
        provider_id = str(getattr(provider, "provider", "") or "").strip()
        label = _login_provider_label(provider_id, str(getattr(provider, "label", "") or provider_id))
        mark = _login_provider_mark(provider_id, label)
        actions.append({"label": label, "mark": mark})
    return actions


def _login_provider_label(provider_id: str, fallback: str) -> str:
    labels = {
        "yandex": "Продолжить через Яндекс ID",
        "vk": "Продолжить через VK ID",
        "telegram": "Продолжить через Telegram",
    }
    return labels.get(provider_id, f"Продолжить через {fallback}")


def _login_provider_mark(provider_id: str, label: str) -> str:
    marks = {
        "yandex": "Я",
        "vk": "VK",
        "telegram": "TG",
    }
    return marks.get(provider_id, label[:2].upper())


def render_login_page(
    *,
    workspace_id: UUID | None,
    providers: list,
    next_path: str = "/meetings",
    error: str | None = None,
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    content = render_template(
        "cabinet/auth/login.html",
        workspace_configured=workspace_id is not None,
        providers=_login_provider_actions(providers),
        next_path=safe_next,
        login_sso_href=f"/login/sso/start?{urlencode({'next': safe_next})}",
        signup_href=f"/sign-up?{urlencode({'next': safe_next})}",
        error_message=_login_error_message(error),
    )
    return _standalone_page("Вход", content)


def render_signup_page(
    *,
    workspace_id: UUID | None,
    providers: list,
    next_path: str = "/meetings",
    error: str | None = None,
    mode: str | None = None,
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    email_mode = str(mode or "").lower() == "email"
    content = render_template(
        "cabinet/auth/signup.html",
        workspace_configured=workspace_id is not None,
        providers=_login_provider_actions(providers),
        next_path=safe_next,
        email_mode=email_mode,
        error_message=_login_error_message(error),
        login_href=f"/login?{urlencode({'next': safe_next})}",
        signup_href=f"/sign-up?{urlencode({'next': safe_next})}",
        signup_email_href=f"/sign-up?{urlencode({'next': safe_next, 'mode': 'email'})}",
    )
    return _standalone_page("Регистрация", content)


def render_email_code_page(
    *,
    email: str,
    workspace_id: UUID | None,
    state_nonce: str,
    next_path: str,
    dev_code: str | None = None,
    error: str | None = None,
    flow: str = "login",
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    verify_path = "/sign-up/email/verify" if flow == "signup" else "/login/email/verify"
    resend_path = "/sign-up/email/start" if flow == "signup" else "/login/email/start"
    back_path = "/sign-up" if flow == "signup" else "/login"
    page_title = "Подтвердите почту" if flow == "signup" else "Подтвердите вход"
    subtitle = (
        f"Проверьте {email}: мы отправили 6-значный код для создания аккаунта."
        if flow == "signup"
        else f"Проверьте {email}: мы отправили 6-значный код для входа."
    )
    content = render_template(
        "cabinet/auth/email_code.html",
        page_title=page_title,
        subtitle=subtitle,
        verify_path=verify_path,
        resend_path=resend_path,
        back_href=f"{back_path}?{urlencode({'next': safe_next})}",
        email=email,
        state_nonce=state_nonce,
        next_path=safe_next,
        dev_code=dev_code,
        error_message=_login_error_message(error),
    )
    return _standalone_page("Код входа", content)


def render_meeting_list_page(
    response: MeetingListResponse,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
) -> str:
    return _page_shell(
        "Мои встречи",
        embedded=embedded,
        page_template="cabinet/pages/desktop_meetings.html" if embedded else "cabinet/pages/meetings.html",
        csrf_token=csrf_token,
        content_template="cabinet/pages/meeting_list_content.html",
        filter_action=_base_path(embedded),
        list_region=trusted_component_html(
            _render_meeting_list_region(response, embedded=embedded, csrf_token=csrf_token),
            source="meeting_list.region",
        ),
        delete_dialog=trusted_component_html(_render_list_delete_dialog(), source="meeting_list.delete_dialog"),
        sort_label=_sort_label(response.filters.sort),
        query_value=response.filters.q or "",
        status_value=response.filters.status or "",
        access_value=response.filters.access or "",
        sort_value=response.filters.sort,
        visible_total=len(response.items),
    )


def render_meeting_list_fragment(response: MeetingListResponse, *, embedded: bool = False) -> str:
    return _render_meeting_list_region(response, embedded=embedded)


def _render_meeting_list_region(
    response: MeetingListResponse,
    *,
    embedded: bool,
    csrf_token: str | None = None,
) -> str:
    rows = "\n".join(
        _render_meeting_row(item, embedded=embedded, csrf_token=csrf_token)
        for item in response.items
    )
    if not rows:
        rows = '<div class="empty-state">Нет встреч для выбранного фильтра.</div>'
    content = f"""
      <section class="list-card cabinet-card" aria-label="Записи встреч" data-meeting-list>
        {rows}
      </section>
    """
    return render_template(
        "cabinet/fragments/meeting_list.html",
        content=trusted_component_html(content, source="meeting_list.rows"),
    )


def render_meeting_detail_page(
    review: MeetingReviewResponse,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
) -> str:
    content = _render_meeting_detail_content(review, embedded=embedded)
    return _page_shell(
        review.meeting.title,
        content,
        embedded=embedded,
        page_template="cabinet/pages/meeting_detail.html",
        csrf_token=csrf_token,
        content_source="meeting_detail.content",
    )


def render_meeting_detail_fragment(review: MeetingReviewResponse, *, embedded: bool = False) -> str:
    return render_template(
        "cabinet/fragments/meeting_detail.html",
        content=trusted_component_html(
            _render_meeting_detail_content(review, embedded=embedded),
            source="meeting_detail.content",
        ),
    )


def _render_meeting_detail_content(review: MeetingReviewResponse, *, embedded: bool) -> str:
    transcript = trusted_component_html(_render_transcript(review.transcript.segments), source="meeting_detail.transcript")
    if not review.transcript.available:
        transcript = trusted_component_html(
            f"""
            <div class="empty-state">
              <div>
                <strong>{escape(_empty_title(review))}</strong>
                <div class="muted">{escape(_empty_body(review))}</div>
              </div>
            </div>
            """,
            source="meeting_detail.empty_transcript",
        )
    recording_tab = "Расшифровка" if embedded else "Запись и расшифровка"
    return render_template(
        "cabinet/pages/meeting_detail_content.html",
        base_path=_base_path(embedded),
        meeting_title=review.meeting.title,
        status_label=_ui_text(review.meeting.status_label),
        media_revision_id=str(review.provenance.media_revision_id or ""),
        local_media_revision_id=review.provenance.local_media_revision_id or "",
        recording_tab=recording_tab,
        access_chip=trusted_component_html(_render_access_chip(review.meeting.access), source="meeting_detail.access_chip"),
        top_actions=trusted_component_html(_render_top_actions(review, embedded=embedded), source="meeting_detail.top_actions"),
        outcomes=trusted_component_html(_render_notes_outcomes(review), source="meeting_detail.outcomes"),
        transcript=transcript,
        revision_status=trusted_component_html(_render_revision_status(review), source="meeting_detail.revision_status"),
        access_summary=trusted_component_html(_render_access_summary(review), source="meeting_detail.access_summary"),
        share_panel=trusted_component_html(_render_share_panel(review), source="meeting_detail.share_panel"),
        artifacts=trusted_component_html(_render_artifacts(review), source="meeting_detail.artifacts"),
        deletion_truth_copy=review.deletion_truth_copy or "",
        deletion_truth_text=_ui_text(review.deletion_truth_copy or ""),
        delete_confirmation=trusted_component_html(
            _render_delete_confirmation(review, embedded=embedded),
            source="meeting_detail.delete_confirmation",
        ),
        speaker_lanes=trusted_component_html(_render_speaker_lanes(review), source="meeting_detail.speaker_lanes"),
        governance=trusted_component_html(_render_governance(review), source="meeting_detail.governance"),
        activity=trusted_component_html(_render_activity(review), source="meeting_detail.activity"),
        assistant_label=_ui_text(review.assistant.label),
        template_label=_ui_text(review.template.label),
        playback=trusted_component_html(_render_playback(review), source="meeting_detail.playback"),
    )


def render_deletion_report_page(
    meeting_title: str,
    report: DeletionVerificationReport,
    *,
    embedded: bool = False,
    csrf_token: str | None = None,
) -> str:
    content = _render_deletion_report_content(meeting_title, report, embedded=embedded)
    return _page_shell(
        "Отчет удаления",
        content,
        embedded=embedded,
        page_template="cabinet/pages/meeting_detail.html",
        csrf_token=csrf_token,
        content_source="deletion_report.content",
    )


def render_deletion_report_fragment(
    meeting_title: str,
    report: DeletionVerificationReport,
    *,
    embedded: bool = False,
) -> str:
    return render_template(
        "cabinet/fragments/deletion_report.html",
        content=trusted_component_html(
            _render_deletion_report_content(meeting_title, report, embedded=embedded),
            source="deletion_report.content",
        ),
    )


def _render_deletion_report_content(
    meeting_title: str,
    report: DeletionVerificationReport,
    *,
    embedded: bool,
) -> str:
    return render_template(
        "cabinet/pages/deletion_report_content.html",
        base_path=_base_path(embedded),
        meeting_title=meeting_title,
        overall_state_label=_ui_text(report.overall_state.value),
        bounded_copy=report.bounded_copy,
        bounded_copy_text=_ui_text(report.bounded_copy),
        artifact_band=trusted_component_html(
            _render_report_band("Файлы под контролем 2brain Rec", report.artifact_states),
            source="deletion_report.band",
        ),
        backup_band=trusted_component_html(
            _render_report_band("Резервные копии", [report.backup]),
            source="deletion_report.band",
        ),
        dependencies_band=trusted_component_html(
            _render_report_band("Внешние зависимости", report.dependencies),
            source="deletion_report.band",
        ),
        egress_limits_band=trusted_component_html(
            _render_report_band("Ограничения после выгрузки", report.post_egress_limits),
            source="deletion_report.band",
        ),
        local_purge=trusted_component_html(_render_local_purge_tasks(report.local_purge), source="deletion_report.local_purge"),
        activity=trusted_component_html(_render_lifecycle_activity(report.activity), source="deletion_report.activity"),
    )


def _page_shell(
    title: str,
    content: str | None = None,
    *,
    embedded: bool,
    page_template: str = "cabinet/pages/meetings.html",
    csrf_token: str | None = None,
    content_source: str = "cabinet.shell",
    **context,
) -> str:
    if content is not None:
        context["content"] = trusted_component_html(content, source=content_source)
    shell = render_template(
        page_template,
        embedded=embedded,
        navigation=cabinet_view_models.cabinet_navigation(active="meetings"),
        **context,
    )
    return render_template(
        "cabinet/base.html",
        title=title,
        surface_mode="desktop_embedded" if embedded else "standalone_browser",
        csrf_token=csrf_token,
        content=trusted_component_html(shell, source="cabinet.shell"),
    )


def _standalone_page(title: str, content: str, *, csrf_token: str | None = None) -> str:
    return render_template(
        "cabinet/base.html",
        title=title,
        surface_mode="auth",
        csrf_token=csrf_token,
        content=trusted_component_html(content, source="auth.shell"),
    )


def _csrf_token_for_principal(request: Request, principal: AuthenticatedPrincipal) -> str | None:
    if not principal.auth_via_session or principal.session_id is None:
        return None
    secret = getattr(request.app.state, "web_csrf_secret", None)
    if not secret:
        raise ProblemDetail(
            status=503,
            code="csrf_secret_unavailable",
            title="CSRF protection unavailable",
        )
    return issue_csrf_token(session_id=principal.session_id, secret=str(secret))


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


def _safe_browser_next_path(value: str | None) -> str:
    if value is None:
        return "/meetings"
    stripped = value.strip()
    if not stripped or not stripped.startswith("/") or stripped.startswith("//"):
        return "/meetings"
    if any(char in stripped for char in "\r\n"):
        return "/meetings"
    return stripped


def _login_error_message(error: str | None) -> str | None:
    if not error:
        return None
    messages = {
        "missing_auth_context": "Нужен вход, чтобы открыть кабинет встреч.",
        "auth_session_invalid": "Сессия не найдена. Войдите снова.",
        "auth_session_expired": "Сессия истекла. Войдите снова.",
        "device_revoked": "Доступ этого устройства отозван. Войдите с доверенного браузера.",
        "workspace_required": "Нужен workspace id для входа в self-hosted кабинет.",
        "provider_missing": "Этот способ входа не настроен.",
        "provider_disabled": "Этот способ входа выключен политикой кабинета.",
        "provider_future": "Этот способ входа появится позже. Сейчас используйте вход по email.",
        "auth_dependency_unavailable": "Сервис входа временно недоступен.",
        "email_invalid": "Введите корректный email.",
        "email_start_unavailable": "Не удалось отправить код для этого кабинета. Проверьте workspace id и email.",
        "email_delivery_unavailable": "Почтовая доставка временно недоступна. Попробуйте запросить код еще раз.",
        "email_code_invalid": "Код не подошел. Проверьте письмо и попробуйте еще раз.",
        "email_code_expired": "Код истек. Запросите новый код.",
    }
    return messages.get(error, "Не удалось открыть сессию кабинета. Попробуйте войти снова.")
UI_TEXT: dict[str, str] = {
    "Access": "Доступ",
    "Access state is unavailable.": "Статус доступа недоступен.",
    "Action Items": "Действия",
    "Assistant": "Ассистент",
    "Available": "Доступно",
    "Can view": "Может смотреть",
    "Blocked": "Заблокировано",
    "Copy link": "Ссылка",
    "Decisions": "Решения",
    "Delete planned": "Удаление запланировано",
    "Delete this meeting everywhere 2brain Rec controls": "Удалить встречу в системах 2brain Rec",
    "Delete this meeting everywhere 2brain Rec controls.": "Удалить встречу везде, где ее контролирует 2brain Rec.",
    "Disabled": "Выключено",
    "Disabled by policy": "Заблокировано",
    "Download": "Скачать",
    "Evidence": "Фрагменты",
    "Export": "Экспорт",
    "Export package": "Экспорт",
    "Export ready": "Экспорт готов",
    "Failed": "Сбой",
    "Files already downloaded or exported are outside 2brain Rec deletion control.": "Уже скачанные или экспортированные файлы находятся вне последующего удаления в 2brain Rec.",
    "Files already downloaded or exported are outside later 2brain Rec revocation. Deleting a meeting can remove what 2brain Rec controls, not copies already saved elsewhere.": "Уже скачанные или экспортированные файлы находятся вне последующего отзыва в 2brain Rec. Удаление встречи может убрать то, что контролирует 2brain Rec, но не копии, уже сохраненные где-то еще.",
    "Follow-ups": "Продолжение",
    "Incoming system": "Входящий звук",
    "Key points": "Ключевое",
    "Local only": "Только локально",
    "Local microphone": "Микрофон",
    "Meeting processing needs operator review before outcomes can be trusted.": "Обработку встречи нужно проверить оператору, прежде чем доверять итогам.",
    "More": "Еще",
    "No access activity yet.": "Событий доступа пока нет.",
    "No active user grants.": "Активных доступов для пользователей нет.",
    "No exportable artifacts yet.": "Файлы для выгрузки пока недоступны.",
    "No lifecycle activity yet.": "Событий жизненного цикла пока нет.",
    "No lifecycle rows yet.": "Строк жизненного цикла пока нет.",
    "No local purge acknowledgement has been received yet.": "Подтверждение локальной очистки еще не получено.",
    "Not available": "Недоступно",
    "Notes": "Итоги",
    "On": "Вкл",
    "Off": "Выкл",
    "Open in browser": "Открыть в браузере",
    "Outcome deferred": "Итоги отложены",
    "Outcome source": "Источник итогов",
    "Outcomes blocked": "Итоги заблокированы",
    "Outcomes deferred": "Итоги отложены",
    "Outcomes processing": "Итоги готовятся",
    "Outcomes unavailable": "Итоги недоступны",
    "Owner": "Владелец",
    "owner": "владелец",
    "Partial": "Частично готово",
    "Processing": "Расшифровка",
    "Processing result could not be imported safely.": "Результат обработки не удалось безопасно импортировать.",
    "Public links": "Публичные ссылки",
    "Questions": "Вопросы",
    "Ready": "Готово",
    "Report": "Отчет",
    "Request deletion": "Запросить удаление",
    "Retention policy planned": "Правила хранения",
    "Retention controls will show policy truth before activation.": "Правила хранения появятся после активации политики.",
    "Risks": "Риски",
    "Share": "Поделиться",
    "Sharing is unavailable for this meeting.": "Поделиться этой встречей сейчас нельзя.",
    "Speaker lanes are reserved until diarization is available.": "Спикеры появятся после диаризации.",
    "Star": "Избранное",
    "Submitted": "Загружено",
    "Summary": "Кратко",
    "Summary unavailable": "Краткое резюме недоступно",
    "Tag": "Тег",
    "Team": "Команда",
    "Team visibility": "Видимость для команды",
    "Template": "Шаблон",
    "Transcript": "Расшифровка",
    "Transcript and generated outcomes may still be processing.": "Расшифровка и итоги еще могут обрабатываться.",
    "Transcript is still processing.": "Расшифровка еще готовится.",
    "Transcript review is available, but generated meeting outcomes are not part of this stored result.": "Расшифровка доступна, но сгенерированные итоги не входят в этот сохраненный результат.",
    "Uploading": "Загружается",
    "Unavailable": "Недоступно",
    "You own this meeting.": "Это ваша встреча.",
    "accepted": "принято",
    "acknowledged": "подтверждено",
    "active": "активен",
    "artifact lifecycle state": "состояние файла",
    "auth required": "нужен вход",
    "auth_required": "нужен вход",
    "allowed": "разрешено",
    "available": "доступно",
    "backup expiry pending": "ожидает срока хранения резервной копии",
    "backup_expiry_pending": "ожидает срока хранения резервной копии",
    "completed": "готово",
    "delete requested": "удаление запрошено",
    "delete_requested": "удаление запрошено",
    "deletion requested": "удаление запрошено",
    "deletion_requested": "удаление запрошено",
    "Desktop device": "Десктоп",
    "dependency unconfirmed": "зависимость не подтверждена",
    "dependency_unconfirmed": "зависимость не подтверждена",
    "disabled": "выключено",
    "disabled by default": "выключено по умолчанию",
    "disabled_by_default": "выключено по умолчанию",
    "download completed": "скачивание завершено",
    "download requested": "скачивание запрошено",
    "enabled": "включено",
    "external deletion support is not confirmed": "удаление во внешнем сервисе не подтверждено",
    "External deletion support is not confirmed": "Удаление во внешнем сервисе не подтверждено",
    "local purge acknowledged": "локальная очистка подтверждена",
    "local_purge_acknowledged": "локальная очистка подтверждена",
    "local buffers purged": "локальные буферы очищены",
    "local_buffers_purged": "локальные буферы очищены",
    "metadata only": "только метаданные",
    "Owner/Admin": "Владелец/админ",
    "outside 2brain rec control": "вне контроля 2brain Rec",
    "outside_control": "вне контроля 2brain Rec",
    "pending": "ожидает",
    "Planned; this does not promise deletion outside 2brain Rec control.": "Запланировано; это не обещает удаление вне контроля 2brain Rec.",
    "policy blocked": "по политике",
    "policy_blocked": "по политике",
    "processing": "обработка",
    "purge_local_buffers": "локальные буферы",
    "purge_local_exports": "локальные экспорты",
    "confirm_local_expiry": "подтвердить локальное истечение",
    "Server audio purge requested": "Очистка серверного аудио запрошена",
    "unreachable": "недоступно",
    "Workspace policy disables this artifact egress.": "Политика рабочего пространства запрещает выгрузку этого файла.",
    "You": "Вы",
}


def _ui_text(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.replace("_", " ")
    return UI_TEXT.get(value, UI_TEXT.get(normalized, normalized))


def _speaker_display_label(label: str) -> str:
    if label.startswith("Speaker "):
        suffix = label.removeprefix("Speaker ").strip()
        return f"Спикер {suffix}" if suffix else "Спикер"
    return _ui_text(label)


def _notes_source_label(source_basis: str) -> str:
    return {
        "blocked": "заблокировано",
        "not_supported": "не поддерживается",
        "policy_deferral": "отложено политикой",
        "processing_status": "статус обработки",
        "stored_output": "сохраненные итоги",
    }.get(source_basis, _ui_text(source_basis))


def _notes_title(title: str) -> str:
    return {
        "Summary": "Кратко",
        "Key points": "Ключевое",
        "Decisions": "Решения",
        "Action Items": "Действия",
        "Follow-ups": "Продолжение",
        "Risks": "Риски",
        "Questions": "Вопросы",
        "Evidence": "Фрагменты",
    }.get(title, _ui_text(title))


def _ui_icon(name: str) -> str:
    return render_icon(name)


def _render_meeting_row(
    item: MeetingListItem,
    *,
    embedded: bool,
    selected: bool = False,
    csrf_token: str | None = None,
) -> str:
    href = f"{_base_path(embedded)}/{item.meeting_id}"
    delete_action = f"{href}/deletion-requests"
    selected_class = " is-selected" if selected else ""
    source_icon, source_label = _meeting_media_icon(item)
    title = escape(item.title)
    csrf_field = f'<input type="hidden" name="csrf_token" value="{escape(csrf_token)}">' if csrf_token else ""
    return f"""
      <article class="meeting-row cabinet-row{selected_class}" data-meeting-row data-meeting-id="{item.meeting_id}" data-meeting-title="{title}">
        <input class="row-check" type="checkbox" data-meeting-select aria-label="Выбрать запись {title}">
        <span class="row-icon" data-media-kind="{source_label}" aria-label="{source_label}" title="{source_label}">{source_icon}</span>
        <a class="meeting-title" href="{href}">
          <span class="row-title">{title} <span class="muted">{_duration(item.duration_seconds)}</span></span>
          <span class="row-meta"><span>{escape(_ui_text(item.status_label))}</span></span>
        </a>
        <form class="row-delete-form" method="post" action="{delete_action}" data-row-delete-form
          data-hx-post="{delete_action}"
          data-hx-target="#delete-feedback-region"
          data-hx-select="[data-cabinet-fragment='deletion-feedback']"
          data-hx-swap="innerHTML">
          {csrf_field}
          <input type="hidden" name="confirmation_boundary" value="{escape(BOUNDED_DELETE_COPY)}">
          <button class="row-delete icon-button" type="button" data-row-delete aria-label="Удалить запись {title}" title="Удалить">{_ui_icon("trash")}</button>
          <noscript><button class="row-delete-noscript" type="submit">Удалить</button></noscript>
        </form>
        <span class="meeting-date">{_date_label(item)}</span>
      </article>
    """


def _meeting_media_icon(item: MeetingListItem) -> tuple[str, str]:
    kind = cabinet_view_models.meeting_media_kind(item)
    return _ui_icon(kind), cabinet_view_models.meeting_media_label(item)


def _render_list_delete_dialog() -> str:
    bounded_copy = "Запись будет удалена везде, где ее контролирует 2brain Rec. Уже скачанные или экспортированные копии могут оставаться вне контроля 2brain Rec."
    return f"""
      <dialog class="delete-dialog" data-delete-dialog data-title-one="Удалить запись?" data-title-many="Удалить записи?">
        <h2 data-delete-title>Удалить запись?</h2>
        <p><span data-delete-count>Вы удаляете 1 запись.</span> Это действие нельзя отменить.</p>
        <p class="truth-copy" data-bounded-delete-copy="{escape(BOUNDED_DELETE_COPY)}">{escape(bounded_copy)}</p>
        <div class="dialog-actions">
          <button type="button" class="quiet" data-delete-cancel>Отмена</button>
          <button type="button" class="danger-button" data-delete-confirm>Удалить</button>
        </div>
        <div class="dialog-error" data-delete-error hidden>Не удалось удалить запись. Попробуйте еще раз.</div>
      </dialog>
    """


def _render_transcript(segments: list[TranscriptSegmentView]) -> str:
    return "\n".join(
        f"""
          <article class="segment">
            {_render_timestamp(segment)}
            <div class="speaker"><span class="dot"></span>{escape(_speaker_display_label(segment.speaker_label))}</div>
            <div class="text">{escape(segment.text)}</div>
          </article>
        """
        for segment in segments
    )


def _render_timestamp(segment: TranscriptSegmentView) -> str:
    if segment.seekable and segment.seek_seconds is not None:
        return (
            f'<button class="timestamp timestamp-seek" type="button" '
            f'data-seek-seconds="{escape(str(segment.seek_seconds))}">{escape(segment.timestamp_label)}</button>'
        )
    return f'<div class="timestamp">{escape(segment.timestamp_label)}</div>'


def _render_playback(review: MeetingReviewResponse) -> str:
    if review.playback.available and review.playback.playback_path:
        speed_options = ",".join(f"{speed:g}" for speed in review.playback.speed_options)
        return f"""
          <section class="playback-bar detail-playback" data-playback-shell data-source-mode="{escape(review.playback.source_mode)}">
            <audio class="playback-audio" data-playback-player preload="metadata" src="{escape(review.playback.playback_path)}"></audio>
            <div class="playback-controls" aria-label="Управление воспроизведением">
              <button type="button" class="playback-round" data-playback-skip="-15" aria-label="Назад на 15 секунд">15</button>
              <button type="button" class="playback-round primary-play" data-playback-toggle aria-label="Воспроизвести">Play</button>
              <button type="button" class="playback-round" data-playback-skip="15" aria-label="Вперед на 15 секунд">15</button>
              <button type="button" class="playback-speed" data-playback-speed-toggle data-speed-options="{escape(speed_options)}">1x</button>
            </div>
            <div class="playback-progress-row">
              <span class="playback-time" data-playback-current>00:00</span>
              <input class="playback-progress" data-playback-progress type="range" min="0" max="{review.playback.duration_seconds}" step="0.1" value="0" aria-label="Позиция записи">
              <span class="playback-time" data-playback-duration>{_timecode(review.playback.duration_seconds)}</span>
            </div>
            {_render_playback_speaker_timeline(review)}
          </section>
        """
    return f"""
      <section class="playback-bar detail-playback is-unavailable" data-source-mode="{escape(review.playback.source_mode)}">
        <span>{escape(review.playback.policy_label)}</span>
        <span>{_duration(review.playback.duration_seconds)}</span>
      </section>
    """


def _render_playback_speaker_timeline(review: MeetingReviewResponse) -> str:
    if not review.speakers.available:
        return '<div class="speaker-timeline" data-speaker-timeline></div>'
    duration = max(1, review.playback.duration_seconds)
    lanes = []
    for speaker in review.speakers.speakers:
        speaker_label = _speaker_display_label(speaker.label)
        segments = []
        for segment in speaker.segments:
            start = max(0.0, float(segment.start_seconds))
            end = min(float(duration), max(start, float(segment.end_seconds)))
            left = min(100.0, max(0.0, start / duration * 100))
            width = min(100.0 - left, max(0.2, (end - start) / duration * 100))
            segment_label = f"{speaker_label} {_timecode(int(start))}-{_timecode(int(end))}"
            segments.append(
                f'<span class="timeline-segment" data-lane-segment title="{escape(segment_label)}" '
                f'aria-label="{escape(segment_label)}" style="left:{left:.2f}%;width:{width:.2f}%"></span>'
            )
        lanes.append(
            f"""
            <div class="timeline-lane" data-speaker-lane="{escape(speaker.speaker_key)}">
              <span class="timeline-label">{escape(speaker_label)}</span>
              <span class="timeline-track">{"".join(segments)}</span>
              <span class="timeline-share">{speaker.talk_time_percent}%</span>
            </div>
            """
        )
    return f'<div class="speaker-timeline" data-speaker-timeline>{"".join(lanes)}</div>'


def _render_speaker_lanes(review: MeetingReviewResponse) -> str:
    if not review.speakers.available:
        return f'<div class="muted">{escape(_ui_text("Speaker lanes are reserved until diarization is available."))}</div>'
    return "\n".join(
        f"""
        <div class="speaker-lane">
          <div class="row-meta"><strong>{escape(_speaker_display_label(speaker.label))}</strong><span>{speaker.talk_time_percent}%</span></div>
          <div class="lane-track"><div class="lane-fill" style="width:{speaker.talk_time_percent}%"></div></div>
        </div>
        """
        for speaker in review.speakers.speakers
    )


def _render_revision_status(review: MeetingReviewResponse) -> str:
    media_revision_id = escape(str(review.provenance.media_revision_id or ""))
    local_media_revision_id = escape(review.provenance.local_media_revision_id or "")
    label = escape(_ui_text(review.meeting.status_label))
    reason = escape(_ui_text(review.processing.reason_label or review.processing.reason_code) or "Текущая медиа-ревизия")
    return f"""
      <section class="revision-status" aria-label="Статус медиа-ревизии" data-media-revision-id="{media_revision_id}" data-local-media-revision-id="{local_media_revision_id}">
        <span class="chip {escape(review.meeting.status)}">{label}</span>
        <span class="row-meta"><span>Медиа-ревизия</span><span>{reason}</span></span>
      </section>
    """


def _render_access_chip(access) -> str:
    if access is None:
        return ""
    return f'<span class="chip {escape(access.state)}">{escape(_ui_text(access.label))}</span>'


def _render_access_summary(review: MeetingReviewResponse) -> str:
    access = review.access
    if access is None:
        return f'<div class="muted">{escape(_ui_text("Access state is unavailable."))}</div>'
    reason = f'<div class="muted">{escape(_ui_text(access.reason))}</div>' if access.reason else ""
    capabilities = [
        ("Поделиться", access.can_share),
        ("Скачать", access.can_download),
        ("Экспорт", access.can_export),
    ]
    capability_rows = "".join(
        f'<div class="state-row"><span>{escape(label)}</span><span class="chip {"available" if enabled else "disabled"}">{escape(_ui_text("On" if enabled else "Off"))}</span></div>'
        for label, enabled in capabilities
    )
    return f"""
      <div class="state-list">
        <div class="state-row"><strong>{escape(_ui_text(access.label))}</strong><span class="chip {escape(access.state)}">{escape(_ui_text(access.state))}</span></div>
        {reason}
        {capability_rows}
      </div>
    """


def _render_share_panel(review: MeetingReviewResponse) -> str:
    share = review.share
    if share is None:
        return f'<div class="muted">{escape(_ui_text("Sharing is unavailable for this meeting."))}</div>'
    grants = "".join(
        f"""
        <div class="state-row">
          <span><strong>{escape(grant.display_name)}</strong><br><span class="muted">{escape(_ui_text(grant.role_label))}</span></span>
          <span class="chip {escape(grant.status)}">{escape(_ui_text(grant.status))}</span>
        </div>
        """
        for grant in share.active_grants
    )
    if not grants:
        grants = f'<div class="muted">{escape(_ui_text("No active user grants."))}</div>'
    return f"""
      <div class="state-list">
        <div class="state-row"><span>{escape(_ui_text("Team visibility"))}</span><span class="chip {escape(share.team_visibility)}">{escape(_ui_text(share.team_visibility))}</span></div>
        <div class="state-row"><span>{escape(_ui_text("Copy link"))}</span><span class="chip {escape(share.copy_link_state)}">{escape(_ui_text(share.copy_link_state))}</span></div>
        <div class="state-row"><span>{escape(_ui_text("Public links"))}</span><span class="chip {escape(share.public_link_state)}">{escape(_ui_text(share.public_link_state))}</span></div>
        {grants}
      </div>
    """


def _render_artifacts(review: MeetingReviewResponse) -> str:
    if not review.artifacts:
        return f'<div class="muted">{escape(_ui_text("No exportable artifacts yet."))}</div>'
    rows = "".join(_render_artifact_state(review, artifact) for artifact in review.artifacts)
    return f'<div class="state-list">{rows}</div>'


def _render_artifact_state(review: MeetingReviewResponse, artifact: ArtifactEgressState) -> str:
    label = escape(_ui_text(artifact.label))
    reason = f'<span class="muted">{escape(_ui_text(artifact.reason))}</span>' if artifact.reason else ""
    if artifact.state == "available" and artifact.artifact_class != "package":
        action = (
            f'<a class="mini-link" href="/api/v1/cabinet/meetings/{review.meeting.meeting_id}/downloads/'
            f'{escape(artifact.artifact_class)}">{escape(_ui_text("Download"))}</a>'
        )
    elif artifact.state == "available":
        action = f'<span class="chip available">{escape(_ui_text("Export ready"))}</span>'
    else:
        action = f'<span class="chip {escape(artifact.state)}">{escape(_ui_text(artifact.state))}</span>'
    return f"""
      <div class="state-row">
        <span><strong>{label}</strong><br>{reason}</span>
        {action}
      </div>
    """


def _render_delete_confirmation(review: MeetingReviewResponse, *, embedded: bool) -> str:
    report_href = f"{_base_path(embedded)}/{review.meeting.meeting_id}/deletion-report"
    return f"""
      <div class="delete-confirmation">
        <strong>{escape(_ui_text("Delete this meeting everywhere 2brain Rec controls"))}</strong>
        <div class="truth-copy" data-boundary-copy="{escape(BOUNDED_DELETE_COPY)}">{escape(_ui_text(BOUNDED_DELETE_COPY))}</div>
        <div class="state-row">
          <span class="muted">Резервные копии, локальные буферы, метаданные провайдера и уже переданные копии показываются отдельно.</span>
          <a class="mini-link" href="{report_href}">{escape(_ui_text("Report"))}</a>
        </div>
        <button type="button" disabled>{escape(_ui_text("Request deletion"))}</button>
      </div>
    """


def _render_report_band(title: str, rows: list[ArtifactDeletionState]) -> str:
    rendered = "".join(_render_report_artifact_row(row) for row in rows)
    if not rendered:
        rendered = f'<div class="muted">{escape(_ui_text("No lifecycle rows yet."))}</div>'
    return f"""
      <div class="report-band">
        <h3>{escape(title)}</h3>
        <div class="state-list">{rendered}</div>
      </div>
    """


def _render_report_artifact_row(row: ArtifactDeletionState) -> str:
    reason = row.safe_reason or row.label
    return f"""
      <div class="state-row">
        <span><strong>{escape(_ui_text(row.label))}</strong><br><span class="muted">{escape(_ui_text(reason))}</span></span>
        <span class="chip {escape(row.state.value)}">{escape(_ui_text(row.state.value))}</span>
      </div>
    """


def _render_local_purge_tasks(tasks: list[LocalPurgeTask]) -> str:
    if not tasks:
        return f'<div class="muted">{escape(_ui_text("No local purge acknowledgement has been received yet."))}</div>'
    return '<div class="state-list">' + "".join(_render_local_purge_task(task) for task in tasks) + "</div>"


def _render_local_purge_task(task: LocalPurgeTask) -> str:
    return f"""
      <div class="state-row">
        <span><strong>{escape(_ui_text(task.task_type.value))}</strong><br><span class="muted">{escape(_ui_text(task.safe_reason or "metadata only"))}</span></span>
        <span class="chip {escape(task.state.value)}">{escape(_ui_text(task.state.value))}</span>
      </div>
    """


def _render_lifecycle_activity(activity: list) -> str:
    if not activity:
        return f'<div class="muted">{escape(_ui_text("No lifecycle activity yet."))}</div>'
    rows = "".join(
        f"""
        <div class="state-row">
          <span><strong>{escape(_ui_text(item.event_type))}</strong><br><span class="muted">{escape(_ui_text(item.actor_label))} · {escape(_ui_text(item.safe_reason or "metadata only"))}</span></span>
          <span class="chip {escape(item.outcome)}">{escape(_ui_text(item.outcome))}</span>
        </div>
        """
        for item in activity
    )
    return f'<div class="state-list">{rows}</div>'


def _render_activity(review: MeetingReviewResponse) -> str:
    activity = review.activity
    if activity is None or not activity.items:
        return f'<div class="muted">{escape(_ui_text("No access activity yet."))}</div>'
    rows = "".join(
        f"""
        <div class="activity-item">
          <div class="state-row"><strong>{escape(_ui_text(item.event_type))}</strong><span class="chip {escape(item.outcome)}">{escape(_ui_text(item.outcome))}</span></div>
          <div class="muted">{escape(_ui_text(item.actor_label))} · {escape(item.created_at.strftime("%Y-%m-%d %H:%M"))}</div>
        </div>
        """
        for item in activity.items[:6]
    )
    return f'<div class="activity-list">{rows}</div>'


def _render_governance(review: MeetingReviewResponse) -> str:
    actions = [
        review.governance.share,
        review.governance.export,
        review.governance.download,
        review.governance.retention,
        review.governance.delete,
    ]
    return "\n".join(
        f'<button type="button" title="{escape(_ui_text(action.reason or action.label))}" {"disabled" if action.state != "available" else ""}>{escape(_ui_text(action.label))}</button>'
        for action in actions
    )


def _render_notes_outcomes(review: MeetingReviewResponse) -> str:
    outcomes = [
        ("summary", "Summary", review.notes_action_truth.summary),
        ("key_points", "Key points", review.notes_action_truth.key_points),
        ("decisions", "Decisions", review.notes_action_truth.decisions),
        ("action_items", "Action Items", review.notes_action_truth.action_items),
        ("followups", "Follow-ups", review.notes_action_truth.followups),
        ("risks", "Risks", review.notes_action_truth.risks),
        ("questions", "Questions", review.notes_action_truth.questions),
        ("evidence", "Evidence", review.notes_action_truth.evidence),
    ]
    rows = "".join(_render_notes_outcome_row(category, title, state) for category, title, state in outcomes)
    source = escape(_notes_source_label(review.notes_action_truth.source_basis))
    source_basis = escape(review.notes_action_truth.source_basis)
    return f"""
      <div class="notes" data-outcome-source-basis="{source_basis}">
        <h3>{escape(_ui_text("Итоги встречи"))}</h3>
        <div class="state-list notes-outcomes">
          {rows}
        </div>
        <div class="muted">{escape(_ui_text("Outcome source"))}: {source}</div>
      </div>
    """


def _render_notes_outcome_row(category: str, title: str, state: NotesActionCategoryState) -> str:
    state_name = escape(state.state)
    items = "".join(_render_outcome_item(item) for item in state.items)
    return f"""
      <div class="state-row notes-outcome-row" data-outcome-category="{escape(category)}" data-outcome-state="{state_name}">
        <span><strong>{escape(_notes_title(title))}</strong><br><span class="muted">{escape(_ui_text(state.reason))}</span></span>
        <span class="chip {state_name}">{escape(_ui_text(state.label))}</span>
        {items}
      </div>
    """


def _render_outcome_item(item) -> str:
    text = escape(item.text or "")
    if not text:
        return ""
    refs = ", ".join(
        _timecode(int(ref.start_seconds or 0))
        for ref in item.source_refs[:2]
        if ref.start_seconds is not None
    )
    refs_html = f'<span class="muted">Источник: {escape(refs)}</span>' if refs else ""
    return f'<div class="outcome-item"><span>{text}</span>{refs_html}</div>'


def _render_top_actions(review: MeetingReviewResponse, *, embedded: bool) -> str:
    if embedded:
        return f'<button type="button" disabled>{escape(_ui_text("Open in browser"))}</button>'
    export_disabled = "disabled" if review.governance.export.state != "available" else ""
    share_disabled = "disabled" if review.governance.share.state != "available" else ""
    return f"""
      <button type="button" disabled>{escape(_ui_text(review.template.label))}</button>
      <button type="button" {export_disabled}>{escape(_ui_text(review.governance.export.label))}</button>
      <button type="button" {share_disabled}>{escape(_ui_text(review.governance.share.label))}</button>
      <button type="button" disabled>{escape(_ui_text("More"))}</button>
    """


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


def _empty_title(review: MeetingReviewResponse) -> str:
    if review.processing.state in {"processing", "submitted"}:
        return "Транскрипт готовится"
    if review.processing.state == "failed":
        return "Обработка остановилась"
    if review.processing.state == "blocked":
        return "Обработка требует проверки"
    return "Транскрипт недоступен"


def _empty_body(review: MeetingReviewResponse) -> str:
    if review.processing.reason_label:
        return _ui_text(review.processing.reason_label)
    if review.processing.state in {"processing", "submitted"}:
        return "Мы показываем только подтвержденные данные и не создаем фальшивый текст."
    return "Проверьте статус обработки позже."


def _timecode(seconds: int) -> str:
    minutes, second = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{second:02d}"


def _duration(seconds: int) -> str:
    return cabinet_view_models.format_duration(seconds)


def _date_label(item: MeetingListItem) -> str:
    return cabinet_view_models.date_label(item)


def _sort_label(sort: str) -> str:
    return cabinet_view_models.sort_label(sort)


def _base_path(embedded: bool) -> str:
    return "/desktop/meetings" if embedded else "/meetings"
