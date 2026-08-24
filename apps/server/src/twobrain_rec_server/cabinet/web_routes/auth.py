from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.auth import (
    _set_browser_auth_state_cookie,
    build_provider_callback_url,
)
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.dependencies import (
    auth_session_cookie_name,
    auth_session_cookie_secure,
)
from twobrain_rec_server.auth.policy import read_auth_providers
from twobrain_rec_server.auth.providers import build_provider_registry, get_provider_adapter
from twobrain_rec_server.auth.rate_limit import enforce_auth_rate_limits
from twobrain_rec_server.auth.sessions import (
    create_callback_state,
    issue_callback_nonce,
)
from twobrain_rec_server.cabinet.access import share_invitation_continuation_matches
from twobrain_rec_server.cabinet.auth_rendering import (
    _safe_browser_next_path,
    render_email_code_page,
    render_login_page,
    render_signup_page,
)
from twobrain_rec_server.cabinet.auth_return import resolve_browser_auth_return_path
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import (
    EMAIL_SIGNUP_PROVIDER,
    EmailCodeRetryResponse,
    EmailLoginCompletion,
    EmailRecoveryRequired,
    _AmbiguousEmailIdentityError,
    _clear_email_auth_browser_cookie,
    _consume_email_login_code,
    _create_email_login_state,
    _finalize_email_callback,
    _issue_email_auth_browser_nonce,
    _issue_email_login_code,
    _normalize_email,
    _record_email_login_audit,
    _resolve_email_login_user,
    _resolve_email_workspace,
    _set_browser_auth_cookie,
    _set_email_auth_browser_cookie,
    _should_echo_email_code,
)
from twobrain_rec_server.cabinet.web_routes.support import (
    LoginDbDependency,
    PrincipalDependency,
    WebCSRFDependency,
)
from twobrain_rec_server.db.models import AuthSession
from twobrain_rec_server.db.tenant_context import (
    ShareInvitationLookupContext,
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])

LoginNextQuery = Query(default="/meetings", alias="next", max_length=512)
LoginErrorQuery = Query(default=None, max_length=120)
SignupModeQuery = Query(default=None, max_length=32, alias="mode")
LoginAuthProviderQuery = Query(default=None, alias="auth_provider", max_length=32)
LoginEmailForm = Form(..., max_length=240)
LoginCodeForm = Form(..., max_length=32)
LoginStateForm = Form(..., max_length=160)
LoginNextForm = Form(default="/meetings", alias="next", max_length=512)
LogoutNextForm = Form(default="/login?next=/meetings", alias="next", max_length=512)


def _auth_rate_limit_headers(retry_after: int) -> dict[str, str]:
    return {"Retry-After": str(max(1, retry_after))}


def _request_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _parse_share_invitation_next(next_path: str) -> tuple[UUID, str] | None:
    try:
        parsed = urlsplit(next_path)
    except ValueError:
        return None
    if parsed.path != "/share-invitations/continue" or parsed.scheme or parsed.netloc:
        return None
    query = parse_qs(parsed.query, keep_blank_values=True)
    workspace_values = query.get("workspace_id", [])
    state_values = query.get("state", [])
    if len(workspace_values) != 1 or len(state_values) != 1:
        return None
    state = state_values[0]
    if not 16 <= len(state) <= 128:
        return None
    try:
        workspace_id = UUID(workspace_values[0])
    except ValueError:
        return None
    return workspace_id, state


async def _active_share_invitation_next(
    db: AsyncSession,
    next_path: str,
    *,
    address: str | None = None,
) -> tuple[UUID, str] | None:
    target = _parse_share_invitation_next(next_path)
    if target is None:
        return None
    workspace_id, state = target
    await apply_tenant_context(
        db,
        ShareInvitationLookupContext(
            workspace_id=workspace_id,
            continuation_nonce=state,
        ),
    )
    if not await share_invitation_continuation_matches(
        db,
        workspace_id=workspace_id,
        nonce=state,
        address=address,
    ):
        return None
    return target


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def browser_login_page(
    request: Request,
    next_path: str = LoginNextQuery,
    error: str | None = LoginErrorQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    resolved_workspace_id, providers, safe_next, load_error = await _load_browser_auth_page_context(
        request,
        next_path=next_path,
        error=error,
        db=db,
    )
    return HTMLResponse(
        render_login_page(
            workspace_id=resolved_workspace_id,
            providers=providers,
            next_path=safe_next,
            error=load_error,
            invitation_flow=_parse_share_invitation_next(safe_next) is not None,
            product_analytics_provider=build_request_browser_provider_context(
                request, "login_signup"
            ),
        )
    )


@router.get("/sign-up", response_class=HTMLResponse, include_in_schema=False)
async def browser_signup_page(
    request: Request,
    next_path: str = LoginNextQuery,
    error: str | None = LoginErrorQuery,
    mode: str | None = SignupModeQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    resolved_workspace_id, providers, safe_next, load_error = await _load_browser_auth_page_context(
        request,
        next_path=next_path,
        error=error,
        db=db,
    )
    return HTMLResponse(
        render_signup_page(
            workspace_id=resolved_workspace_id,
            providers=providers,
            next_path=safe_next,
            error=load_error,
            mode=mode,
            product_analytics_provider=build_request_browser_provider_context(
                request, "login_signup"
            ),
        )
    )


@router.post("/login/email/start", response_class=HTMLResponse, include_in_schema=False)
async def browser_email_login_start(
    request: Request,
    email: str = LoginEmailForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    safe_next = _safe_browser_next_path(next_path)
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    invitation_target = _parse_share_invitation_next(safe_next)
    invitation_context = await _active_share_invitation_next(db, safe_next)
    invitation_flow = invitation_target is not None
    if invitation_flow and invitation_context is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=None,
                providers=[],
                next_path=safe_next,
                error="share_invitation_unavailable",
                invitation_flow=True,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    resolved_workspace_id = (
        invitation_context[0]
        if invitation_context is not None
        else _resolve_browser_login_workspace_id(request)
    )
    if resolved_workspace_id is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=None,
                providers=[],
                next_path=safe_next,
                error="workspace_required",
                invitation_flow=invitation_flow,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    normalized_email = _normalize_email(email)
    if normalized_email is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="email_invalid",
                invitation_flow=invitation_flow,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    if (
        invitation_context is not None
        and await _active_share_invitation_next(
            db,
            safe_next,
            address=normalized_email,
        )
        is None
    ):
        return HTMLResponse(
            render_login_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="share_invitation_email_required",
                invitation_flow=True,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    retry_after = await enforce_auth_rate_limits(
        db,
        workspace_id=resolved_workspace_id,
        scopes=(
            ("email_code_start_address", normalized_email),
            ("email_code_start_ip", _request_ip(request)),
            *(
                (("email_code_start_invitation", invitation_context[1]),)
                if invitation_context is not None
                else ()
            ),
        ),
        sessionmaker=getattr(request.app.state, "db_sessionmaker", None),
        scope_secret=request.app.state.settings.share_identity_hash_secret,
    )
    if retry_after is not None:
        return HTMLResponse(
            render_login_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="auth_rate_limited",
                invitation_flow=invitation_flow,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=429,
            headers=_auth_rate_limit_headers(retry_after),
        )
    try:
        workspace, user = await _resolve_email_login_user(
            db,
            workspace_id=resolved_workspace_id,
            email=normalized_email,
            internal_workspace_id=request.app.state.settings.web_login_workspace_id,
        )
    except _AmbiguousEmailIdentityError:
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=resolved_workspace_id,
            outcome="failure",
            error_code="ambiguous_email_recovery_required",
        )
        response = await _ambiguous_email_recovery_response(
            request,
            db=db,
            workspace_id=resolved_workspace_id,
            next_path=safe_next,
            invitation_flow=invitation_flow,
        )
        await db.commit()
        return response
    if workspace is None or (user is None and invitation_context is None):
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
                invitation_flow=invitation_flow,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    code = _issue_email_login_code(request.app.state.settings)
    browser_nonce = _issue_email_auth_browser_nonce()
    ttl_seconds = request.app.state.settings.auth_callback_state_ttl_seconds
    state = await _create_email_login_state(
        db,
        workspace_id=resolved_workspace_id,
        next_path=safe_next,
        email=normalized_email,
        code=code,
        ttl_seconds=ttl_seconds,
        browser_nonce=browser_nonce,
        secret=request.app.state.web_csrf_secret,
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
            await _finalize_email_callback(
                db,
                state=state,
                result="failed",
                now=datetime.now(UTC),
                error_code="email_delivery_unavailable",
            )
            await apply_tenant_context(
                db, WorkspaceAuthContext(workspace_id=resolved_workspace_id)
            )
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
                    invitation_flow=invitation_flow,
                    product_analytics_provider=build_request_browser_provider_context(
                        request, "login_signup"
                    ),
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
    response = HTMLResponse(
        render_email_code_page(
            email=normalized_email,
            state_nonce=state.state_nonce,
            next_path=safe_next,
            dev_code=dev_code,
            flow="share_invitation" if invitation_context is not None else "login",
            product_analytics_provider=build_request_browser_provider_context(
                request, "login_signup"
            ),
        )
    )
    _set_email_auth_browser_cookie(
        request,
        response,
        state_nonce=state.state_nonce,
        browser_nonce=browser_nonce,
        max_age=ttl_seconds,
    )
    return response


@router.post("/sign-up/email/start", response_class=HTMLResponse, include_in_schema=False)
async def browser_email_signup_start(
    request: Request,
    email: str = LoginEmailForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request)
    if resolved_workspace_id is None:
        return HTMLResponse(
            render_signup_page(
                workspace_id=None,
                providers=[],
                next_path=safe_next,
                error="workspace_required",
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
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
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    retry_after = await enforce_auth_rate_limits(
        db,
        workspace_id=resolved_workspace_id,
        scopes=(
            ("email_code_start_address", normalized_email),
            ("email_code_start_ip", _request_ip(request)),
        ),
        sessionmaker=getattr(request.app.state, "db_sessionmaker", None),
        scope_secret=request.app.state.settings.share_identity_hash_secret,
    )
    if retry_after is not None:
        return HTMLResponse(
            render_signup_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="auth_rate_limited",
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=429,
            headers=_auth_rate_limit_headers(retry_after),
        )
    workspace = await _resolve_email_workspace(db, workspace_id=resolved_workspace_id)
    if workspace is None:
        return HTMLResponse(
            render_signup_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="email_start_unavailable",
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    code = _issue_email_login_code(request.app.state.settings)
    browser_nonce = _issue_email_auth_browser_nonce()
    ttl_seconds = request.app.state.settings.auth_callback_state_ttl_seconds
    state = await _create_email_login_state(
        db,
        workspace_id=resolved_workspace_id,
        next_path=safe_next,
        email=normalized_email,
        code=code,
        ttl_seconds=ttl_seconds,
        provider=EMAIL_SIGNUP_PROVIDER,
        browser_nonce=browser_nonce,
        secret=request.app.state.web_csrf_secret,
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
            await _finalize_email_callback(
                db,
                state=state,
                result="failed",
                now=datetime.now(UTC),
                error_code="email_delivery_unavailable",
            )
            await apply_tenant_context(
                db, WorkspaceAuthContext(workspace_id=resolved_workspace_id)
            )
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
                    product_analytics_provider=build_request_browser_provider_context(
                        request, "login_signup"
                    ),
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
    response = HTMLResponse(
        render_email_code_page(
            email=normalized_email,
            state_nonce=state.state_nonce,
            next_path=safe_next,
            dev_code=dev_code,
            flow="signup",
            product_analytics_provider=build_request_browser_provider_context(
                request, "login_signup"
            ),
        )
    )
    _set_email_auth_browser_cookie(
        request,
        response,
        state_nonce=state.state_nonce,
        browser_nonce=browser_nonce,
        max_age=ttl_seconds,
    )
    return response


@router.post("/login/email/verify", include_in_schema=False, response_model=None)
async def browser_email_login_verify(
    request: Request,
    email: str = LoginEmailForm,
    code: str = LoginCodeForm,
    state: str = LoginStateForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
):
    safe_next = _safe_browser_next_path(next_path)
    normalized_email = _normalize_email(email)
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    invitation_target = _parse_share_invitation_next(safe_next)
    invitation_context = await _active_share_invitation_next(db, safe_next)
    invitation_flow = invitation_target is not None
    if invitation_flow and invitation_context is None:
        return HTMLResponse(
            render_email_code_page(
                email=normalized_email or "",
                state_nonce=state,
                next_path=safe_next,
                error="share_invitation_unavailable",
                flow="share_invitation",
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    resolved_workspace_id = (
        invitation_context[0]
        if invitation_context is not None
        else _resolve_browser_login_workspace_id(request)
    )
    if resolved_workspace_id is None or normalized_email is None:
        return HTMLResponse(
            render_email_code_page(
                email=normalized_email or "",
                state_nonce=state,
                next_path=safe_next,
                error="email_code_invalid",
                flow="share_invitation" if invitation_flow else "login",
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    retry_after = await enforce_auth_rate_limits(
        db,
        workspace_id=resolved_workspace_id,
        scopes=(
            ("email_code_verify_address", normalized_email or ""),
            ("email_code_verify_ip", _request_ip(request)),
            ("email_code_verify_state", state),
        ),
        sessionmaker=getattr(request.app.state, "db_sessionmaker", None),
        scope_secret=request.app.state.settings.share_identity_hash_secret,
    )
    if retry_after is not None:
        return HTMLResponse(
            render_email_code_page(
                email=normalized_email,
                state_nonce=state,
                next_path=safe_next,
                error="auth_rate_limited",
                flow="share_invitation" if invitation_flow else "login",
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=429,
            headers=_auth_rate_limit_headers(retry_after),
        )
    try:
        result = await _consume_email_login_code(
            db,
            request=request,
            workspace_id=resolved_workspace_id,
            email=normalized_email,
            code=code,
            state_nonce=state,
            next_path=safe_next,
            allow_registration=invitation_context is not None,
            invitation_flow=invitation_flow,
        )
        response = await _prepare_email_auth_response(request, db=db, result=result)
        if not isinstance(result, EmailCodeRetryResponse):
            _clear_email_auth_browser_cookie(request, response, state_nonce=state)
        await db.commit()
        return response
    except Exception:
        await db.rollback()
        raise


@router.post("/logout", include_in_schema=False, response_model=None)
async def browser_logout(
    request: Request,
    next_path: str = LogoutNextForm,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    _csrf: None = WebCSRFDependency,
    db: AsyncSession | None = LoginDbDependency,
):
    return await logout_current_browser_session(
        request,
        next_path=next_path,
        principal=principal,
        db=db,
    )


async def logout_current_browser_session(
    request: Request,
    *,
    next_path: str,
    principal: AuthenticatedPrincipal,
    db: AsyncSession | None,
) -> RedirectResponse:
    safe_next = _safe_browser_next_path(next_path)
    if db is None:
        raise ProblemDetail(
            status=503,
            code="auth_dependency_unavailable",
            title="Authentication DB dependency unavailable",
        )
    if (
        principal.auth_via_session
        and principal.session_id is not None
        and principal.session_workspace_id is not None
    ):
        await apply_tenant_context(
            db,
            TenantDatabaseContext(
                organization_id=principal.organization_id,
                workspace_id=principal.session_workspace_id,
                user_id=principal.user_id,
                device_id=principal.session_device_id,
                auth_session_id=principal.session_id,
            ),
        )
        auth_session = await db.get(AuthSession, principal.session_id)
        if (
            auth_session is not None
            and auth_session.workspace_id == principal.session_workspace_id
            and auth_session.user_id == principal.user_id
        ):
            auth_session.status = "revoked"
            auth_session.last_seen_at = datetime.now(UTC)
            await write_auth_audit_event(
                db,
                workspace_id=principal.session_workspace_id,
                event_type="browser_logout",
                actor_user_id=principal.user_id,
                user_id=principal.user_id,
                provider=auth_session.provider,
                actor_ip=request.client.host if request.client else None,
                request_id=getattr(request.state, "request_id", None),
            )
        await db.commit()
    redirect = RedirectResponse(safe_next, status_code=303)
    redirect.delete_cookie(
        key=auth_session_cookie_name(request),
        path="/",
        secure=auth_session_cookie_secure(request),
        httponly=True,
        samesite="lax",
    )
    return redirect


@router.post("/sign-up/email/verify", include_in_schema=False, response_model=None)
async def browser_email_signup_verify(
    request: Request,
    email: str = LoginEmailForm,
    code: str = LoginCodeForm,
    state: str = LoginStateForm,
    next_path: str = LoginNextForm,
    db: AsyncSession | None = LoginDbDependency,
):
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request)
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
                state_nonce=state,
                next_path=safe_next,
                error="email_code_invalid",
                flow="signup",
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    retry_after = await enforce_auth_rate_limits(
        db,
        workspace_id=resolved_workspace_id,
        scopes=(
            ("email_code_verify_address", normalized_email or ""),
            ("email_code_verify_ip", _request_ip(request)),
            ("email_code_verify_state", state),
        ),
        sessionmaker=getattr(request.app.state, "db_sessionmaker", None),
        scope_secret=request.app.state.settings.share_identity_hash_secret,
    )
    if retry_after is not None:
        return HTMLResponse(
            render_email_code_page(
                email=normalized_email,
                state_nonce=state,
                next_path=safe_next,
                error="auth_rate_limited",
                flow="signup",
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=429,
            headers=_auth_rate_limit_headers(retry_after),
        )
    try:
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
        response = await _prepare_email_auth_response(
            request,
            db=db,
            result=result,
            clear_referral_on_registration=True,
        )
        if not isinstance(result, EmailCodeRetryResponse):
            _clear_email_auth_browser_cookie(request, response, state_nonce=state)
        await db.commit()
        return response
    except Exception:
        await db.rollback()
        raise


@router.get("/login/{provider}/start", include_in_schema=False, response_model=None)
async def browser_login_provider_start(
    provider: str,
    request: Request,
    next_path: str = LoginNextQuery,
    auth_provider: str | None = LoginAuthProviderQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse | RedirectResponse:
    safe_next = _safe_browser_next_path(next_path)
    invitation_target = _parse_share_invitation_next(safe_next)
    invitation_context = None
    if invitation_target is not None:
        if db is None:
            return HTMLResponse(
                render_login_page(
                    workspace_id=None,
                    providers=[],
                    next_path=safe_next,
                    error="auth_dependency_unavailable",
                    invitation_flow=True,
                    product_analytics_provider=build_request_browser_provider_context(
                        request, "login_signup"
                    ),
                ),
                status_code=503,
            )
        invitation_context = await _active_share_invitation_next(db, safe_next)
        if invitation_context is None:
            return HTMLResponse(
                render_login_page(
                    workspace_id=None,
                    providers=[],
                    next_path=safe_next,
                    error="share_invitation_unavailable",
                    invitation_flow=True,
                    product_analytics_provider=build_request_browser_provider_context(
                        request, "login_signup"
                    ),
                ),
                status_code=400,
            )
    resolved_workspace_id = (
        invitation_context[0]
        if invitation_context is not None
        else _resolve_browser_login_workspace_id(request)
    )
    invitation_flow = invitation_target is not None
    if resolved_workspace_id is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=None,
                providers=[],
                next_path=safe_next,
                error="workspace_required",
                invitation_flow=invitation_flow,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=400,
        )
    normalized_provider = provider.strip().lower()
    if normalized_provider not in {"yandex", "vk"}:
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
                invitation_flow=invitation_flow,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=501,
        )
    if db is None:
        return HTMLResponse(
            render_login_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="auth_dependency_unavailable",
                invitation_flow=invitation_flow,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=503,
        )
    retry_after = await enforce_auth_rate_limits(
        db,
        workspace_id=resolved_workspace_id,
        scopes=(
            ("provider_start_ip", _request_ip(request)),
        ),
        sessionmaker=getattr(request.app.state, "db_sessionmaker", None),
        scope_secret=request.app.state.settings.share_identity_hash_secret,
    )
    if retry_after is not None:
        return HTMLResponse(
            render_login_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="auth_rate_limited",
                invitation_flow=invitation_flow,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=429,
            headers=_auth_rate_limit_headers(retry_after),
        )
    providers = []
    try:
        await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=resolved_workspace_id))
        adapter = get_provider_adapter(normalized_provider)
        snapshot = await read_auth_providers(
            db,
            resolved_workspace_id,
            adapters=build_provider_registry(),
            persist_defaults=True,
        )
        providers = list(snapshot.providers)
        provider_policy = next(
            (entry for entry in snapshot.providers if entry.provider == normalized_provider), None
        )
        if provider_policy is None or not provider_policy.enabled:
            await write_auth_audit_event(
                db,
                workspace_id=resolved_workspace_id,
                event_type="provider_auth_started",
                actor_ip=request.client.host if request.client else None,
                provider=normalized_provider,
                outcome="failure",
                metadata={"error_code": "provider_disabled"},
                request_id=getattr(request.state, "request_id", None),
            )
            await db.commit()
            return HTMLResponse(
                render_login_page(
                    workspace_id=resolved_workspace_id,
                    providers=providers,
                    next_path=safe_next,
                    error="provider_disabled",
                    invitation_flow=invitation_flow,
                    product_analytics_provider=build_request_browser_provider_context(
                        request, "login_signup"
                    ),
                ),
                status_code=403,
            )
    except ValueError:
        return HTMLResponse(
            render_login_page(
                workspace_id=resolved_workspace_id,
                providers=providers,
                next_path=safe_next,
                error="provider_missing",
                invitation_flow=invitation_flow,
                product_analytics_provider=build_request_browser_provider_context(
                    request, "login_signup"
                ),
            ),
            status_code=403,
        )
    browser_state_nonce = issue_callback_nonce()
    state_ttl_seconds = request.app.state.settings.auth_callback_state_ttl_seconds
    state = create_callback_state(
        db,
        provider=normalized_provider,
        workspace_id=resolved_workspace_id,
        requested_redirect=safe_next,
        browser_state_nonce=browser_state_nonce,
        ttl_seconds=state_ttl_seconds,
    )
    settings = request.app.state.settings
    callback_url = build_provider_callback_url(request, normalized_provider)
    client_secret = _provider_client_secret(settings, normalized_provider)
    authorization_url = adapter.build_authorization_url(
        client_id=getattr(settings, f"{normalized_provider}_client_id"),
        client_secret=client_secret,
        redirect_uri=callback_url,
        state=state.state_nonce,
        return_url=safe_next,
        workspace_id="public",
        auth_provider=_safe_vk_auth_provider(auth_provider)
        if normalized_provider == "vk"
        else None,
    )
    await write_auth_audit_event(
        db,
        workspace_id=resolved_workspace_id,
        event_type="provider_auth_started",
        actor_ip=request.client.host if request.client else None,
        provider=normalized_provider,
        metadata={"state_nonce": state.state_nonce},
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    response = RedirectResponse(authorization_url, status_code=303)
    _set_browser_auth_state_cookie(response, nonce=browser_state_nonce, max_age=state_ttl_seconds)
    return response


async def _load_browser_auth_page_context(
    request: Request,
    *,
    next_path: str,
    error: str | None,
    db: AsyncSession | None,
) -> tuple[UUID | None, list, str, str | None]:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request)
    providers = []
    load_error = error
    if _parse_share_invitation_next(safe_next) is not None:
        if db is None:
            load_error = load_error or "auth_dependency_unavailable"
        else:
            invitation_context = await _active_share_invitation_next(db, safe_next)
            if invitation_context is not None:
                resolved_workspace_id = invitation_context[0]
            else:
                load_error = load_error or "share_invitation_unavailable"
    if resolved_workspace_id is not None and db is not None:
        try:
            providers = await _load_browser_login_providers(db, resolved_workspace_id)
        except ProblemDetail as exc:
            load_error = exc.code
    elif resolved_workspace_id is not None:
        load_error = "auth_dependency_unavailable"
    return resolved_workspace_id, providers, safe_next, load_error


async def _load_browser_login_providers(db: AsyncSession, workspace_id: UUID) -> list:
    await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
    snapshot = await read_auth_providers(db, workspace_id, adapters=build_provider_registry())
    return list(snapshot.providers)


async def _ambiguous_email_recovery_response(
    request: Request,
    *,
    db: AsyncSession,
    workspace_id: UUID,
    next_path: str,
    invitation_flow: bool,
) -> HTMLResponse:
    try:
        providers = await _load_browser_login_providers(db, workspace_id)
    except ProblemDetail:
        providers = []
    has_recovery_provider = any(
        getattr(provider, "provider", None) in {"yandex", "vk"}
        and bool(getattr(provider, "enabled", False))
        for provider in providers
    )
    recovery_next = (
        next_path
        if invitation_flow
        else (
            "/desktop/settings/account"
            if next_path.startswith("/desktop/")
            else "/settings/account"
        )
    )
    return HTMLResponse(
        render_login_page(
            workspace_id=workspace_id,
            providers=providers,
            next_path=recovery_next,
            error=(
                "ambiguous_email_recovery_required"
                if has_recovery_provider
                else "ambiguous_email_recovery_unavailable"
            ),
            invitation_flow=invitation_flow,
            recovery_mode=True,
            product_analytics_provider=build_request_browser_provider_context(
                request, "login_signup"
            ),
        ),
        status_code=400,
    )


async def _prepare_email_auth_response(
    request: Request,
    *,
    db: AsyncSession,
    result: HTMLResponse | EmailLoginCompletion | EmailRecoveryRequired,
    clear_referral_on_registration: bool = False,
) -> HTMLResponse | RedirectResponse:
    if isinstance(result, HTMLResponse):
        return result
    if isinstance(result, EmailRecoveryRequired):
        return await _ambiguous_email_recovery_response(
            request,
            db=db,
            workspace_id=result.workspace_id,
            next_path=result.next_path,
            invitation_flow=result.invitation_flow,
        )
    if not isinstance(result, EmailLoginCompletion):
        raise TypeError(f"Unsupported email authentication result: {type(result).__name__}")
    redirect_path = await resolve_browser_auth_return_path(
        db,
        requested_redirect=result.requested_redirect,
        organization_id=result.organization_id,
        workspace_id=result.workspace_id,
        user_id=result.user_id,
        auth_session_id=result.auth_session_id,
    )
    response = RedirectResponse(redirect_path or "/meetings", status_code=303)
    _set_browser_auth_cookie(
        request,
        response,
        token=result.token,
        expires_at=result.expires_at,
    )
    if clear_referral_on_registration and result.registered:
        response.delete_cookie(
            key="graf_referral_token",
            path="/",
            secure=True,
            httponly=True,
            samesite="lax",
        )
    return response


def _safe_vk_auth_provider(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    return normalized if normalized in {"vkid", "mail_ru", "ok_ru"} else None


def _provider_client_secret(settings, provider: str) -> str | None:
    path = getattr(settings, f"{provider}_client_secret_file", None)
    if path is None:
        return None
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _resolve_browser_login_workspace_id(request: Request):
    """Use the deployment bootstrap internally; public routes never accept it."""
    settings = request.app.state.settings
    configured = getattr(settings, "web_login_workspace_id", None)
    if configured is not None:
        return configured
    return None
