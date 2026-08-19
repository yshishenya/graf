from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.account_merge import (
    AccountMergeError,
    create_merge_intent,
)
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.dependencies import (
    auth_session_cookie_name,
    auth_session_cookie_secure,
)
from twobrain_rec_server.auth.sessions import callback_expiry, hash_token, issue_auth_session
from twobrain_rec_server.auth.workspace_onboarding import ensure_personal_workspace
from twobrain_rec_server.billing.referral_binding import bind_referral_attribution
from twobrain_rec_server.cabinet.auth_rendering import (
    _safe_browser_next_path,
    render_email_code_page,
)
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
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

EMAIL_LOGIN_PROVIDER = "email"
EMAIL_SIGNUP_PROVIDER = "email_signup"
EMAIL_LINK_PROVIDER = "email_link"


class _AmbiguousEmailIdentityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EmailLoginCompletion:
    organization_id: UUID
    workspace_id: UUID
    user_id: UUID
    auth_session_id: UUID
    token: str
    expires_at: datetime
    requested_redirect: str | None
    registered: bool = False


@dataclass(frozen=True, slots=True)
class EmailRecoveryRequired:
    workspace_id: UUID
    next_path: str
    invitation_flow: bool = False


@dataclass(frozen=True, slots=True)
class EmailLinkCompletion:
    status: str
    intent_id: UUID | None = None


async def _finalize_email_callback(
    db: AsyncSession,
    *,
    state: AuthCallbackState,
    result: str,
    now: datetime,
    error_code: str | None = None,
) -> None:
    """Flush scoped work, then finish exactly this callback under forced RLS."""
    await db.flush()
    await apply_tenant_context(
        db,
        AuthCallbackLookupContext(state_nonce=state.state_nonce),
    )
    state.result = result
    state.used_at = now
    state.error_code = error_code
    await db.flush()


async def _record_email_link_failure(
    db: AsyncSession,
    *,
    request: Request,
    principal: AuthenticatedPrincipal,
    workspace_id: UUID,
    error_code: str,
) -> None:
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace_id,
            organization_id=principal.organization_id,
            user_id=principal.user_id,
            context_kind="auth_bootstrap",
        ),
    )
    await write_auth_audit_event(
        db,
        workspace_id=workspace_id,
        event_type="email_identity_link_failed",
        actor_user_id=principal.user_id,
        user_id=principal.user_id,
        provider=EMAIL_LOGIN_PROVIDER,
        outcome="failure",
        metadata={"error_code": error_code},
        actor_ip=request.client.host if request.client else None,
        request_id=getattr(request.state, "request_id", None),
    )


async def _fail_email_link_callback(
    db: AsyncSession,
    *,
    request: Request,
    principal: AuthenticatedPrincipal,
    state: AuthCallbackState,
    now: datetime,
    email: str,
    state_nonce: str,
    next_path: str,
    flow: str,
    error_code: str,
    result: str = "failed",
) -> HTMLResponse:
    await _record_email_link_failure(
        db,
        request=request,
        principal=principal,
        workspace_id=state.workspace_id,
        error_code=error_code,
    )
    await _finalize_email_callback(
        db,
        state=state,
        result=result,
        now=now,
        error_code=error_code,
    )
    return _email_code_error_response(
        request=request,
        email=email,
        state_nonce=state_nonce,
        next_path=next_path,
        error=error_code,
        flow=flow,
    )


async def _bind_referral_attribution(
    db: AsyncSession,
    *,
    enabled: bool,
    workspace_id: UUID,
    user_id: UUID,
    token: str | None,
    now: datetime,
) -> bool:
    """Compatibility wrapper for the shared email/OAuth binding helper."""
    return await bind_referral_attribution(
        db,
        enabled=enabled,
        workspace_id=workspace_id,
        user_id=user_id,
        token=token,
        now=now,
    )


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
    email: str,
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
        expected_state=_hash_email_login_code(email=email, code=code),
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
    invitation_flow: bool = False,
) -> HTMLResponse | EmailLoginCompletion | EmailRecoveryRequired:
    now = datetime.now(UTC)
    await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state_nonce))
    state = await db.scalar(
        select(AuthCallbackState)
        .where(
            AuthCallbackState.provider == provider,
            AuthCallbackState.state_nonce == state_nonce,
        )
        .with_for_update()
    )
    flow = (
        "signup"
        if provider == EMAIL_SIGNUP_PROVIDER
        else ("share_invitation" if allow_registration else "login")
    )
    if state is None:
        return _email_code_error_response(
            request=request,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    if workspace_id is not None and state.workspace_id != workspace_id:
        return _email_code_error_response(
            request=request,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    workspace_id = state.workspace_id
    if state.result != "pending":
        await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="email_code_replayed",
        )
        return _email_code_error_response(
            request=request,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    expires_at = state.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="email_code_expired",
        )
        await _finalize_email_callback(
            db,
            state=state,
            result="expired",
            now=now,
            error_code="email_code_expired",
        )
        return _email_code_error_response(
            request=request,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_expired",
            flow=flow,
        )
    if state.expected_state != _hash_email_login_code(email=email, code=code):
        await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="email_identity_not_found",
        )
        await _finalize_email_callback(
            db,
            state=state,
            result="failed",
            now=now,
            error_code="email_code_invalid",
        )
        return _email_code_error_response(
            request=request,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    internal_workspace_id = request.app.state.settings.web_login_workspace_id
    try:
        workspace, user = await _resolve_email_login_user(
            db,
            workspace_id=workspace_id,
            email=email,
            internal_workspace_id=internal_workspace_id,
        )
        registered = False
        if workspace is not None and user is None and allow_registration:
            user, registered = await _ensure_email_registration_user(
                db,
                workspace=workspace,
                email=email,
                now=now,
            )
    except _AmbiguousEmailIdentityError:
        await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="ambiguous_email_recovery_required",
        )
        await _finalize_email_callback(
            db,
            state=state,
            result="failed",
            now=now,
            error_code="ambiguous_email_recovery_required",
        )
        return EmailRecoveryRequired(
            workspace_id=workspace_id,
            next_path=next_path,
            invitation_flow=invitation_flow,
        )
    if workspace is None or user is None:
        await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=workspace_id))
        await _record_email_login_audit(
            db,
            request=request,
            workspace_id=workspace_id,
            outcome="failure",
            error_code="email_code_invalid",
        )
        await _finalize_email_callback(
            db,
            state=state,
            result="failed",
            now=now,
            error_code="email_identity_not_found",
        )
        return _email_code_error_response(
            request=request,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    personal_workspace = await ensure_personal_workspace(
        db,
        organization_id=workspace.organization_id,
        user_id=user.id,
    )
    if allow_registration or workspace.id == internal_workspace_id:
        workspace = personal_workspace
    if registered:
        await _bind_referral_attribution(
            db,
            enabled=bool(request.app.state.settings.billing_checkout_enabled),
            workspace_id=workspace.id,
            user_id=user.id,
            token=request.cookies.get("graf_referral_token"),
            now=now,
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
    # Session/device rows are request-scoped; persist them before the audit and
    # callback each switch to their own narrower RLS context.
    await db.flush()
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
            user_id=user.id,
            context_kind="auth_bootstrap",
        ),
    )
    await _record_email_login_audit(
        db,
        request=request,
        workspace_id=workspace.id,
        outcome="success",
        user_id=user.id,
        metadata=(
            {"flow": "registration"}
            if provider == EMAIL_SIGNUP_PROVIDER
            else ({"flow": "share_invitation"} if allow_registration else None)
        ),
    )
    requested_redirect = state.requested_redirect
    await _finalize_email_callback(
        db,
        state=state,
        result="completed",
        now=now,
    )
    return EmailLoginCompletion(
        organization_id=workspace.organization_id,
        workspace_id=workspace.id,
        user_id=user.id,
        auth_session_id=issued.id,
        token=issued.token,
        expires_at=issued.expires_at,
        requested_redirect=requested_redirect,
        registered=registered,
    )


async def consume_email_link_code(
    db: AsyncSession,
    *,
    request: Request,
    principal: AuthenticatedPrincipal,
    workspace_id: UUID,
    email: str,
    code: str,
    state_nonce: str,
) -> EmailLinkCompletion | HTMLResponse:
    """Consume an authenticated passwordless link proof.

    The current session proves the survivor account and the one-use email code
    proves control of the second method.  Existing dataful accounts are never
    silently joined; they produce a proof-bound merge intent instead.
    """
    embedded = request.url.path.startswith("/desktop/")
    next_path = "/desktop/settings/account" if embedded else "/settings/account"
    flow = "desktop_link" if embedded else "link"
    if not principal.auth_via_session or principal.session_workspace_id != workspace_id:
        return _email_code_error_response(
            request=request,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error="provider_link_session_required",
            flow=flow,
        )
    now = datetime.now(UTC)
    await apply_tenant_context(db, AuthCallbackLookupContext(state_nonce=state_nonce))
    state = await db.scalar(
        select(AuthCallbackState)
        .where(
            AuthCallbackState.provider == EMAIL_LINK_PROVIDER,
            AuthCallbackState.state_nonce == state_nonce,
        )
        .with_for_update()
    )
    if state is None or state.workspace_id != workspace_id or state.result != "pending":
        error_code = (
            "email_code_replayed"
            if state is not None and state.workspace_id == workspace_id
            else "email_code_invalid"
        )
        await _record_email_link_failure(
            db,
            request=request,
            principal=principal,
            workspace_id=workspace_id,
            error_code=error_code,
        )
        return _email_code_error_response(
            request=request,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error="email_code_invalid",
            flow=flow,
        )
    expires_at = (
        state.expires_at if state.expires_at.tzinfo else state.expires_at.replace(tzinfo=UTC)
    )
    if expires_at <= now:
        return await _fail_email_link_callback(
            db,
            request=request,
            principal=principal,
            state=state,
            now=now,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            flow=flow,
            error_code="email_code_expired",
            result="expired",
        )
    if state.expected_state != _hash_email_login_code(email=email, code=code):
        return await _fail_email_link_callback(
            db,
            request=request,
            principal=principal,
            state=state,
            now=now,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            flow=flow,
            error_code="email_code_invalid",
        )

    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=principal.organization_id,
            workspace_id=workspace_id,
            user_id=principal.user_id,
            device_id=principal.session_device_id,
            auth_session_id=principal.session_id,
        ),
    )
    candidates = list(
        await db.execute(
            select(ExternalIdentity, UserIdentity)
            .join(UserIdentity, UserIdentity.id == ExternalIdentity.user_id)
            .where(
                UserIdentity.organization_id == principal.organization_id,
                UserIdentity.status == "active",
                or_(
                    ExternalIdentity.is_active.is_(True),
                    ExternalIdentity.provider == EMAIL_LOGIN_PROVIDER,
                ),
                func.lower(ExternalIdentity.email) == email,
            )
        )
    )
    candidate_users = {user.id: (identity, user) for identity, user in candidates}
    other_candidates = {
        user_id: item for user_id, item in candidate_users.items() if user_id != principal.user_id
    }
    if len(other_candidates) > 1:
        return await _fail_email_link_callback(
            db,
            request=request,
            principal=principal,
            state=state,
            now=now,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            flow=flow,
            error_code="ambiguous_email_recovery_required",
        )

    other = next(iter(other_candidates.values()), None)
    if other is None:
        current_email_identity = next(
            (
                identity
                for identity, user in candidates
                if user.id == principal.user_id and identity.provider == EMAIL_LOGIN_PROVIDER
            ),
            None,
        )
        if current_email_identity is None:
            reserved_identity = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.provider == EMAIL_LOGIN_PROVIDER,
                    ExternalIdentity.provider_subject == email,
                )
            )
            if reserved_identity is not None:
                return await _fail_email_link_callback(
                    db,
                    request=request,
                    principal=principal,
                    state=state,
                    now=now,
                    email=email,
                    state_nonce=state_nonce,
                    next_path=next_path,
                    flow=flow,
                    error_code="provider_link_conflict",
                )
            try:
                async with db.begin_nested():
                    db.add(
                        ExternalIdentity(
                            user_id=principal.user_id,
                            provider=EMAIL_LOGIN_PROVIDER,
                            provider_subject=email,
                            provider_username=email,
                            email=email,
                            is_verified=True,
                            last_seen_at=now,
                            meta={"flow": "authenticated_link"},
                        )
                    )
                    await db.flush()
            except IntegrityError:
                concurrent_identity = await db.scalar(
                    select(ExternalIdentity).where(
                        ExternalIdentity.provider == EMAIL_LOGIN_PROVIDER,
                        ExternalIdentity.provider_subject == email,
                    )
                )
                if concurrent_identity is None or concurrent_identity.user_id != principal.user_id:
                    return await _fail_email_link_callback(
                        db,
                        request=request,
                        principal=principal,
                        state=state,
                        now=now,
                        email=email,
                        state_nonce=state_nonce,
                        next_path=next_path,
                        flow=flow,
                        error_code="provider_link_conflict",
                    )
                concurrent_identity.is_active = True
                concurrent_identity.is_verified = True
                concurrent_identity.last_seen_at = now
        else:
            current_email_identity.is_active = True
            current_email_identity.is_verified = True
            current_email_identity.last_seen_at = now
        await write_auth_audit_event(
            db,
            workspace_id=workspace_id,
            event_type="email_identity_linked",
            actor_user_id=principal.user_id,
            user_id=principal.user_id,
            provider=EMAIL_LOGIN_PROVIDER,
            metadata={"method": "email_code"},
        )
        await _finalize_email_callback(
            db,
            state=state,
            result="completed",
            now=now,
        )
        return EmailLinkCompletion(status="identity_linked")

    _, source_user = other
    try:
        async with db.begin_nested():
            intent, preview = await create_merge_intent(
                db,
                workspace_id=workspace_id,
                survivor_user_id=principal.user_id,
                source_user_id=source_user.id,
                email_proof_state="verified",
                oauth_proof_state="verified",
                now=now,
                actor_user_id=principal.user_id,
            )
            await db.flush()
        if preview.blocker_codes:
            await _record_email_link_failure(
                db,
                request=request,
                principal=principal,
                workspace_id=workspace_id,
                error_code="merge_blocked",
            )
            await _finalize_email_callback(
                db,
                state=state,
                result="failed",
                now=now,
                error_code="merge_blocked",
            )
            return EmailLinkCompletion(
                status="merge_blocked",
                intent_id=intent.id,
            )
        await _finalize_email_callback(
            db,
            state=state,
            result="completed",
            now=now,
        )
        return EmailLinkCompletion(
            status="merge_preview_ready",
            intent_id=intent.id,
        )
    except AccountMergeError as exc:
        return await _fail_email_link_callback(
            db,
            request=request,
            principal=principal,
            state=state,
            now=now,
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            flow=flow,
            error_code=exc.code,
        )


async def _resolve_email_login_user(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    email: str,
    internal_workspace_id: UUID | None = None,
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
                ExternalIdentity.is_active.is_(True),
                func.lower(ExternalIdentity.email) == email,
            )
            .order_by(ExternalIdentity.created_at.asc())
        )
    ).all()
    candidates_by_user: dict[UUID, tuple[ExternalIdentity, UserIdentity]] = {}
    for identity, user in candidates:
        candidates_by_user.setdefault(user.id, (identity, user))
    if len(candidates_by_user) > 1:
        raise _AmbiguousEmailIdentityError
    if not candidates_by_user:
        return workspace, None
    identity, user = next(iter(candidates_by_user.values()))
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
            user_id=user.id,
            context_kind="auth_bootstrap",
        ),
    )
    if workspace.id != internal_workspace_id:
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.user_id == identity.user_id,
                WorkspaceMembership.status == "active",
            )
        )
        if membership is not None:
            return workspace, user
    personal_workspace = await db.scalar(
        select(Workspace)
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Workspace.id,
        )
        .where(
            Workspace.organization_id == workspace.organization_id,
            Workspace.kind == "personal",
            Workspace.owner_user_id == user.id,
            WorkspaceMembership.user_id == user.id,
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
        )
    )
    if personal_workspace is not None:
        return personal_workspace, user
    if workspace.id == internal_workspace_id:
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
) -> tuple[UserIdentity, bool]:
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
                (
                    ExternalIdentity.is_active.is_(True)
                    | (
                        (ExternalIdentity.provider == EMAIL_LOGIN_PROVIDER)
                        & ExternalIdentity.is_active.is_(False)
                    )
                ),
            )
            .order_by(ExternalIdentity.is_active.desc(), ExternalIdentity.created_at.asc())
        )
    ).all()
    candidates_by_user: dict[UUID, list[tuple[ExternalIdentity, UserIdentity]]] = {}
    for identity, user in candidates:
        candidates_by_user.setdefault(user.id, []).append((identity, user))
    if len(candidates_by_user) > 1:
        raise _AmbiguousEmailIdentityError
    if candidates_by_user:
        identity, user = next(iter(candidates_by_user.values()))[0]
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=workspace.id,
                organization_id=workspace.organization_id,
                user_id=user.id,
                context_kind="auth_bootstrap",
            ),
        )
        identity.is_active = True
        identity.is_verified = True
        identity.last_seen_at = now
        return user, False

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
    return user, True


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
    request: Request,
    email: str,
    state_nonce: str,
    next_path: str,
    error: str,
    flow: str = "login",
) -> HTMLResponse:
    return HTMLResponse(
        render_email_code_page(
            email=email,
            state_nonce=state_nonce,
            next_path=next_path,
            error=error,
            flow=flow,
            product_analytics_provider=build_request_browser_provider_context(
                request, "login_signup"
            ),
        ),
        status_code=400,
    )


def _set_browser_auth_cookie(
    request: Request, response, *, token: str, expires_at: datetime
) -> None:
    token_expires_at = expires_at
    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(tzinfo=UTC)
    max_age = max(0, int((token_expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        key=auth_session_cookie_name(request),
        value=token,
        max_age=max_age,
        path="/",
        secure=auth_session_cookie_secure(request),
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


def _issue_email_login_code(settings=None) -> str:
    fixed_code = getattr(settings, "local_email_login_code", None)
    if (
        fixed_code
        and getattr(settings, "env", "production").lower() != "production"
        and getattr(settings, "local_http_auth_cookie_enabled", False)
    ):
        return fixed_code
    return f"{secrets.randbelow(1_000_000):06d}"


def _normalize_email_code(value: str) -> str:
    return "".join(char for char in value.strip() if char.isdigit())


def _hash_email_login_code(*, email: str, code: str) -> str:
    return hash_token(f"{email}\0{_normalize_email_code(code)}")


def _should_echo_email_code(request: Request) -> bool:
    return request.app.state.settings.env.lower() != "production"
