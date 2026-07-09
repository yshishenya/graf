from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import callback_expiry, hash_token, issue_auth_session
from twobrain_rec_server.cabinet.auth_rendering import (
    _safe_browser_next_path,
    render_email_code_page,
)
from twobrain_rec_server.cabinet.web_routes.support import product_analytics_provider_for_page
from twobrain_rec_server.db.models import (
    AuthCallbackState,
    AuthSessionDeviceBinding,
    ExternalIdentity,
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
)

EMAIL_LOGIN_PROVIDER = "email"
EMAIL_SIGNUP_PROVIDER = "email_signup"


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
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
            product_analytics_provider=product_analytics_provider_for_page(request, "login_signup"),
        )
    if workspace_id is not None and state.workspace_id != workspace_id:
        return _email_code_error_response(
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
            product_analytics_provider=product_analytics_provider_for_page(request, "login_signup"),
        )
    workspace_id = state.workspace_id
    if state.result != "pending":
        return _email_code_error_response(
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
            product_analytics_provider=product_analytics_provider_for_page(request, "login_signup"),
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
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_expired",
            flow=flow,
            product_analytics_provider=product_analytics_provider_for_page(request, "login_signup"),
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
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
            product_analytics_provider=product_analytics_provider_for_page(request, "login_signup"),
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
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
            product_analytics_provider=product_analytics_provider_for_page(request, "login_signup"),
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
    state_nonce: str,
    next_path: str,
    error: str,
    flow: str = "login",
    product_analytics_provider: dict[str, object] | None = None,
) -> HTMLResponse:
    return HTMLResponse(
        render_email_code_page(
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error=error,
            flow=flow,
            product_analytics_provider=product_analytics_provider,
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
