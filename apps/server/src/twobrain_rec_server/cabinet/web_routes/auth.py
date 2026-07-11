from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.auth import build_provider_callback_url
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.policy import read_auth_providers
from twobrain_rec_server.auth.providers import build_provider_registry, get_provider_adapter
from twobrain_rec_server.auth.sessions import (
    create_callback_state,
)
from twobrain_rec_server.cabinet.auth_rendering import (
    _safe_browser_next_path,
    render_email_code_page,
    render_login_page,
    render_signup_page,
)
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import (
    EMAIL_SIGNUP_PROVIDER,
    _consume_email_login_code,
    _create_email_login_state,
    _issue_email_login_code,
    _normalize_email,
    _record_email_login_audit,
    _resolve_email_login_user,
    _resolve_email_workspace,
    _set_browser_auth_cookie,
    _should_echo_email_code,
)
from twobrain_rec_server.cabinet.web_routes.support import (
    LoginDbDependency,
    PrincipalDependency,
    WebCSRFDependency,
)
from twobrain_rec_server.db.models import AuthSession
from twobrain_rec_server.db.tenant_context import (
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
)

router = APIRouter(tags=["cabinet-web"])

LoginWorkspaceQuery = Query(default=None)
LoginNextQuery = Query(default="/meetings", alias="next", max_length=512)
LoginErrorQuery = Query(default=None, max_length=120)
SignupModeQuery = Query(default=None, max_length=32, alias="mode")
LoginAuthProviderQuery = Query(default=None, alias="auth_provider", max_length=32)
LoginEmailForm = Form(..., max_length=240)
LoginCodeForm = Form(..., max_length=32)
LoginStateForm = Form(..., max_length=160)
LoginWorkspaceForm = Form(default=None)
LoginNextForm = Form(default="/meetings", alias="next", max_length=512)
LogoutNextForm = Form(default="/login?next=/meetings", alias="next", max_length=512)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def browser_login_page(
    request: Request,
    workspace_id: UUID | None = LoginWorkspaceQuery,
    next_path: str = LoginNextQuery,
    error: str | None = LoginErrorQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse:
    resolved_workspace_id, providers, safe_next, load_error = await _load_browser_auth_page_context(
        request,
        workspace_id=workspace_id,
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
    resolved_workspace_id, providers, safe_next, load_error = await _load_browser_auth_page_context(
        request,
        workspace_id=workspace_id,
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
        email=normalized_email,
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
    snapshot = await read_auth_providers(db, resolved_workspace_id, adapters=build_provider_registry())
    if not snapshot.allow_provider_self_enrollment:
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=resolved_workspace_id,
            outcome="failure",
            error_code="workspace_enrollment_required",
            metadata={"flow": "registration"},
        )
        await db.commit()
        return HTMLResponse(
            render_signup_page(
                workspace_id=resolved_workspace_id,
                providers=[],
                next_path=safe_next,
                error="workspace_enrollment_required",
            ),
            status_code=403,
        )
    code = _issue_email_login_code()
    ttl_seconds = request.app.state.settings.auth_callback_state_ttl_seconds
    state = await _create_email_login_state(
        db,
        workspace_id=resolved_workspace_id,
        email=normalized_email,
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
    if principal.auth_via_session and principal.session_id is not None and principal.session_workspace_id is not None:
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
        key=AUTH_SESSION_COOKIE_NAME,
        path="/",
        secure=True,
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
    auth_provider: str | None = LoginAuthProviderQuery,
    db: AsyncSession | None = LoginDbDependency,
) -> HTMLResponse | RedirectResponse:
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
            ),
            status_code=503,
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
            ),
            status_code=403,
        )
    state = create_callback_state(
        db,
        provider=normalized_provider,
        workspace_id=resolved_workspace_id,
        requested_redirect=safe_next,
        ttl_seconds=request.app.state.settings.auth_callback_state_ttl_seconds,
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
        workspace_id=str(resolved_workspace_id),
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
    return RedirectResponse(authorization_url, status_code=303)


async def _load_browser_auth_page_context(
    request: Request,
    *,
    workspace_id: UUID | None,
    next_path: str,
    error: str | None,
    db: AsyncSession | None,
) -> tuple[UUID | None, list, str, str | None]:
    safe_next = _safe_browser_next_path(next_path)
    resolved_workspace_id = _resolve_browser_login_workspace_id(request, workspace_id)
    providers = []
    load_error = error
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


def _resolve_browser_login_workspace_id(request: Request, workspace_id: UUID | None) -> UUID | None:
    if workspace_id is not None:
        return workspace_id
    settings = request.app.state.settings
    configured = getattr(settings, "web_login_workspace_id", None)
    if configured is not None:
        return configured
    return None
