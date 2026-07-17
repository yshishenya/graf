from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.invitations import (
    create_matching_join_offers_after_login,
)
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.policy import (
    is_provider_enabled_in_policy,
    load_workspace_auth_policy,
)
from twobrain_rec_server.auth.provider_links import (
    ProviderLinkError,
    reject_provider_link,
    store_verified_candidate,
)
from twobrain_rec_server.auth.providers import get_provider_adapter
from twobrain_rec_server.auth.providers.base import (
    ProviderCredentials,
    ProviderHttpClient,
    ProviderVerificationError,
    get_provider_http_client,
)
from twobrain_rec_server.auth.sessions import consume_callback_state, issue_auth_session
from twobrain_rec_server.auth.workspace_onboarding import ensure_personal_workspace
from twobrain_rec_server.db.models import (
    AuthCallbackState,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceAuthPolicy,
    WorkspaceMembership,
)
from twobrain_rec_server.db.tenant_context import (
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
)


@dataclass(frozen=True)
class CallbackProfile:
    organization_id: UUID
    user_id: UUID
    workspace_id: UUID
    auth_session_id: UUID
    provider_subject: str
    external_identity_id: UUID
    token: str
    token_expires_at: datetime
    requested_redirect: str | None = None


class CallbackFlowError(ValueError):
    """Deterministic auth flow error wrapper."""

    def __init__(self, code: str, message: str, workspace_id: UUID | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.workspace_id = workspace_id


async def _record_callback_audit_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_type: str,
    provider: str,
    actor_ip: str | None = None,
    request_id: str | None = None,
    outcome: str = "success",
    user_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    await write_auth_audit_event(
        db,
        workspace_id=workspace_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_ip=actor_ip,
        user_id=user_id,
        provider=provider,
        outcome=outcome,
        metadata=metadata or {},
        request_id=request_id,
    )



def _fingerprint_identity(subject: str, provider: str, workspace_id: UUID) -> str:
    key = f"{workspace_id}|{provider}|{subject}".encode()
    return hashlib.sha256(key).hexdigest()


def _is_external_identity_unique_conflict(exc: IntegrityError) -> bool:
    message = str(exc.orig).lower()
    return (
        "external_identities.provider" in message
        and "external_identities.provider_subject" in message
    ) or "external_identities_provider_provider_subject_key" in message


async def _mark_state_error(state, code: str, now: datetime | None = None) -> None:
    state.used_at = now or datetime.now(UTC)
    state.result = "rejected"
    state.error_code = code


async def assert_workspace_active(db: AsyncSession, workspace_id: UUID) -> Workspace | None:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        return None
    return workspace


async def _user_by_external_identity(
    db: AsyncSession,
    *,
    organization_id: UUID,
    provider: str,
    provider_subject: str,
) -> UserIdentity | None:
    identity = await db.scalar(
        select(ExternalIdentity).where(
            and_(
                ExternalIdentity.provider == provider,
                ExternalIdentity.provider_subject == provider_subject,
            )
        )
    )
    if identity is None:
        return None
    user = await db.get(UserIdentity, identity.user_id)
    if user is None:
        return None
    if user.organization_id != organization_id:
        return None
    return user


async def _load_state_if_exists(
    db: AsyncSession,
    *,
    provider: str,
    state_nonce: str,
) -> AuthCallbackState | None:
    return await db.scalar(
        select(AuthCallbackState).where(
            AuthCallbackState.provider == provider,
            AuthCallbackState.state_nonce == state_nonce,
        )
    )


def _resolve_oauth_denial(query: dict[str, str]) -> None:
    error = (query.get("error") or query.get("error_code") or "").lower()
    if error and error not in {"access_denied", "user_denied", "denied"}:
        raise CallbackFlowError("provider_unavailable", f"provider error: {error}")
    if error:
        raise CallbackFlowError("callback_denied", f"callback denied: {error}")


async def _assert_provider_allowed(db: AsyncSession, workspace_id: UUID, provider: str) -> WorkspaceAuthPolicy:
    policy = await load_workspace_auth_policy(db, workspace_id)
    if not is_provider_enabled_in_policy(policy, provider):
        raise CallbackFlowError("provider_disabled", f"provider {provider} disabled by workspace policy")
    return policy


async def _create_scoped_user(
    db: AsyncSession,
    organization_id: UUID,
    workspace_id: UUID,
    *,
    provider: str,
    provider_subject: str,
    profile: dict[str, str | None],
    role: str | None = None,
) -> UserIdentity:
    try:
        async with db.begin_nested():
            user = UserIdentity(
                organization_id=organization_id,
                external_subject=provider_subject,
                display_name=profile.get("display_name"),
            )
            db.add(user)
            await db.flush()
            await apply_tenant_context(
                db,
                WorkspaceAuthContext(
                    workspace_id=workspace_id,
                    organization_id=organization_id,
                    user_id=user.id,
                    context_kind="auth_bootstrap",
                ),
            )
            if role is not None:
                db.add(
                    WorkspaceMembership(
                        workspace_id=workspace_id,
                        user_id=user.id,
                        role=role,
                        status="active",
                    )
                )
            db.add(
                ExternalIdentity(
                    user_id=user.id,
                    provider=provider,
                    provider_subject=provider_subject,
                    provider_username=profile.get("provider_username"),
                    email=profile.get("email"),
                    phone=profile.get("phone"),
                    display_name=profile.get("display_name"),
                    is_verified=True,
                    subject_issued_at=datetime.now(UTC),
                    last_seen_at=datetime.now(UTC),
                    meta={},
                )
            )
            await db.flush()
    except IntegrityError as exc:
        if _is_external_identity_unique_conflict(exc):
            raise CallbackFlowError(
                "identity_subject_conflict",
                "identity already linked to an account in another organization",
            ) from exc
        raise
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user.id,
            context_kind="auth_bootstrap",
        )
    )
    return user


async def _resolve_browser_login_device(
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
            context_kind="request",
        ),
    )
    device_public_id = f"browser-login:{user.id}"
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
            client_version="browser-login",
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
    device.client_version = "browser-login"
    device.status = "active"
    device.registration_state = "approved"
    device.last_seen_at = now
    return device


def _is_browser_requested_redirect(value: str | None) -> bool:
    if value is None:
        return False
    stripped = value.strip()
    return bool(stripped and stripped.startswith("/") and not stripped.startswith("//") and "\r" not in stripped and "\n" not in stripped)


async def _get_or_create_user_from_provider_claims(
    db: AsyncSession,
    *,
    organization_id: UUID,
    workspace_id: UUID,
    provider: str,
    provider_subject: str,
    provider_username: str | None,
    email: str | None,
    phone: str | None,
    display_name: str | None,
) -> UserIdentity:
    user = await _user_by_external_identity(
        db,
        organization_id=organization_id,
        provider=provider,
        provider_subject=provider_subject,
    )
    if user is not None:
        if user.status != "active":
            raise CallbackFlowError("identity_user_inactive", "identity owner account is not active")
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=workspace_id,
                organization_id=organization_id,
                user_id=user.id,
                context_kind="auth_bootstrap",
            ),
        )
        await create_matching_join_offers_after_login(
            db,
            organization_id=organization_id,
            bootstrap_workspace_id=workspace_id,
            user_id=user.id,
            provider=provider,
            provider_subject=provider_subject,
            provider_username=provider_username,
            email=email,
            phone=phone,
        )
        return user

    existing_identity = await db.scalar(
        select(ExternalIdentity).where(
            and_(
                ExternalIdentity.provider == provider,
                ExternalIdentity.provider_subject == provider_subject,
            )
        )
    )
    if existing_identity is not None:
        raise CallbackFlowError(
            "identity_subject_conflict",
            "identity already linked to an account in another organization",
        )

    profile = {
        "provider_username": provider_username,
        "email": email,
        "phone": phone,
        "display_name": display_name,
    }
    user = await _create_scoped_user(
        db,
        organization_id=organization_id,
        workspace_id=workspace_id,
        provider=provider,
        provider_subject=provider_subject,
        profile=profile,
    )
    await create_matching_join_offers_after_login(
        db,
        organization_id=organization_id,
        bootstrap_workspace_id=workspace_id,
        user_id=user.id,
        provider=provider,
        provider_subject=provider_subject,
        provider_username=provider_username,
        email=email,
        phone=phone,
    )
    return user


async def resolve_callback_to_user(
    db: AsyncSession,
    *,
    provider: str,
    query: dict[str, str],
    state_nonce: str,
    provider_credentials: ProviderCredentials,
    session_ttl_seconds: int,
    actor_ip: str | None = None,
    request_id: str | None = None,
    provider_http_client: ProviderHttpClient | None = None,
    browser_state_nonce: str | None = None,
    now: datetime | None = None,
) -> CallbackProfile:
    now = now or datetime.now(UTC)
    try:
        state = await consume_callback_state(
            db,
            provider=provider,
            state_nonce=state_nonce,
            browser_state_nonce=browser_state_nonce,
            now=now,
        )
    except ValueError as exc:
        message = str(exc)
        if "already consumed" in message:
            state = await _load_state_if_exists(db, provider=provider, state_nonce=state_nonce)
            if state is not None:
                await _mark_state_error(state, "callback_state_reused", now=now)
                await _record_callback_audit_event(
                    db,
                    workspace_id=state.workspace_id,
                    event_type="provider_callback_failed",
                    provider=provider,
                    actor_ip=actor_ip,
                    request_id=request_id,
                    outcome="failure",
                    metadata={"error_code": "callback_state_reused", "state_nonce": state_nonce},
                )
            raise CallbackFlowError("callback_state_reused", "callback state already consumed") from exc
        if "expired" in message:
            state = await _load_state_if_exists(db, provider=provider, state_nonce=state_nonce)
            if state is not None:
                await _mark_state_error(state, "callback_state_expired", now=now)
                await _record_callback_audit_event(
                    db,
                    workspace_id=state.workspace_id,
                    event_type="provider_callback_failed",
                    provider=provider,
                    actor_ip=actor_ip,
                    request_id=request_id,
                    outcome="failure",
                    metadata={"error_code": "callback_state_expired", "state_nonce": state_nonce},
                )
            raise CallbackFlowError("callback_state_expired", "callback state expired") from exc
        raise CallbackFlowError("callback_state_invalid", "callback state invalid") from exc

    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=state.workspace_id,
            context_kind="auth_bootstrap",
        ),
    )

    try:
        _resolve_oauth_denial(query)
        adapter = get_provider_adapter(provider)
        identity = adapter.verify_callback(
            query,
            expected_state=state_nonce,
            credentials=provider_credentials,
            http_client=provider_http_client or get_provider_http_client(),
            now=now,
        )
    except ProviderVerificationError as exc:
        await _mark_state_error(state, "provider_unavailable", now=now)
        await _record_callback_audit_event(
            db,
            workspace_id=state.workspace_id,
            event_type="provider_callback_failed",
            provider=provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            metadata={"error_code": "provider_unavailable", "reason": "verification_unavailable"},
        )
        raise CallbackFlowError("provider_unavailable", "provider callback verification unavailable") from exc
    except CallbackFlowError as exc:
        await _mark_state_error(state, exc.code, now=now)
        await _record_callback_audit_event(
            db,
            workspace_id=state.workspace_id,
            event_type="provider_callback_failed",
            provider=provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            metadata={"error_code": exc.code, "state_nonce": state_nonce},
        )
        raise
    except ValueError as exc:
        await _mark_state_error(state, "callback_parse_error", now=now)
        await _record_callback_audit_event(
            db,
            workspace_id=state.workspace_id,
            event_type="provider_callback_failed",
            provider=provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            metadata={"error_code": "callback_parse_error", "state_nonce": state_nonce},
        )
        raise CallbackFlowError("callback_parse_error", "unable to parse callback payload") from exc

    try:
        await _assert_provider_allowed(db, state.workspace_id, identity.provider)
        workspace = await assert_workspace_active(db, state.workspace_id)
    except CallbackFlowError as exc:
        await _mark_state_error(state, exc.code, now=now)
        await _record_callback_audit_event(
            db,
            workspace_id=state.workspace_id,
            event_type="provider_callback_failed",
            provider=provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            metadata={
                "error_code": exc.code,
                "state_nonce": state_nonce,
            },
        )
        raise
    if workspace is None:
        await _mark_state_error(state, "workspace_not_found", now=now)
        await _record_callback_audit_event(
            db,
            workspace_id=state.workspace_id,
            event_type="provider_callback_failed",
            provider=provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            metadata={"error_code": "workspace_not_found", "state_nonce": state_nonce},
        )
        raise CallbackFlowError("workspace_not_found", "workspace from callback not found")

    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
            context_kind="auth_bootstrap",
        ),
    )
    state.result = "completed"

    try:
        user = await _get_or_create_user_from_provider_claims(
            db,
            organization_id=workspace.organization_id,
            workspace_id=workspace.id,
            provider=identity.provider,
            provider_subject=identity.normalized_subject(),
            provider_username=identity.provider_username,
            email=identity.email,
            phone=identity.phone,
            display_name=identity.display_name,
        )
    except CallbackFlowError as exc:
        await _mark_state_error(state, exc.code, now=now)
        await _record_callback_audit_event(
            db,
            workspace_id=workspace.id,
            event_type="provider_callback_failed",
            provider=provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            metadata={"error_code": exc.code, "state_nonce": state_nonce},
        )
        raise

    personal_workspace = await ensure_personal_workspace(
        db,
        organization_id=workspace.organization_id,
        user_id=user.id,
    )
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == user.id,
            WorkspaceMembership.status == "active",
        )
    )
    if membership is None:
        workspace = personal_workspace
    browser_device = None
    if _is_browser_requested_redirect(state.requested_redirect):
        browser_device = await _resolve_browser_login_device(
            db,
            workspace=workspace,
            user=user,
            now=now,
        )
    issued = await issue_auth_session(
        db,
        user_id=user.id,
        workspace_id=workspace.id,
        device_id=browser_device.id if browser_device is not None else None,
        provider=identity.provider,
        ttl_seconds=session_ttl_seconds,
        claims_fingerprint=_fingerprint_identity(
            identity.provider_subject,
            identity.provider,
            workspace.id,
        ),
    )
    if browser_device is not None:
        db.add(
            AuthSessionDeviceBinding(
                auth_session_id=issued.id,
                registered_device_id=browser_device.id,
                device_state="trusted",
                last_heartbeat_at=now,
            )
        )
    ext = await db.scalar(
        select(ExternalIdentity).where(
            and_(
                ExternalIdentity.provider == identity.provider,
                ExternalIdentity.provider_subject == identity.provider_subject,
                ExternalIdentity.user_id == user.id,
            )
        )
    )
    if ext is None:
        await _record_callback_audit_event(
            db,
            workspace_id=workspace.id,
            event_type="provider_callback_failed",
            provider=identity.provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            metadata={"error_code": "identity_persistence_failed", "state_nonce": state_nonce},
        )
        raise CallbackFlowError("identity_persistence_failed", "identity persistence failed", workspace_id=workspace.id)

    await _record_callback_audit_event(
        db,
        workspace_id=workspace.id,
        event_type="provider_callback_success",
        provider=identity.provider,
        actor_ip=actor_ip,
        request_id=request_id,
        outcome="success",
        actor_user_id=user.id,
        user_id=user.id,
        metadata={
            "state_nonce": state_nonce,
            "identity_subject_fingerprint": _fingerprint_identity(
                identity.provider_subject,
                identity.provider,
                workspace.id,
            ),
        },
    )

    return CallbackProfile(
        organization_id=workspace.organization_id,
        user_id=user.id,
        workspace_id=workspace.id,
        auth_session_id=issued.id,
        provider_subject=identity.provider_subject,
        external_identity_id=ext.id,
        token=issued.token,
        token_expires_at=issued.expires_at,
        requested_redirect=state.requested_redirect,
    )


async def resolve_callback_to_provider_link(
    db: AsyncSession,
    *,
    provider: str,
    query: dict[str, str],
    state_nonce: str,
    link_state,
    provider_credentials: ProviderCredentials,
    actor_ip: str | None = None,
    request_id: str | None = None,
    provider_http_client: ProviderHttpClient | None = None,
    browser_state_nonce: str | None = None,
    now: datetime | None = None,
) -> None:
    """Verify a bound provider-link callback without changing login state."""
    now = now or datetime.now(UTC)
    callback_state: AuthCallbackState | None = None
    try:
        callback_state = await consume_callback_state(
            db,
            provider=provider,
            state_nonce=state_nonce,
            browser_state_nonce=browser_state_nonce,
            now=now,
        )
        if callback_state.id != link_state.callback_state_id:
            raise ProviderLinkError("provider_link_callback_mismatch")
        _resolve_oauth_denial(query)
        identity = get_provider_adapter(provider).verify_callback(
            query,
            expected_state=state_nonce,
            credentials=provider_credentials,
            http_client=provider_http_client or get_provider_http_client(),
            now=now,
        )
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=link_state.workspace_id,
                user_id=link_state.initiating_user_id,
                context_kind="auth_bootstrap",
            ),
        )
        await _assert_provider_allowed(db, link_state.workspace_id, identity.provider)
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == link_state.workspace_id,
                WorkspaceMembership.user_id == link_state.initiating_user_id,
                WorkspaceMembership.status == "active",
            )
        )
        if membership is None:
            raise ProviderLinkError("workspace_scope_denied")
        await store_verified_candidate(
            db,
            link=link_state,
            provider=identity.provider,
            provider_subject=identity.normalized_subject(),
            email=identity.email,
            phone=identity.phone,
            display_name=identity.display_name,
            now=now,
        )
    except CallbackFlowError as exc:
        if callback_state is not None:
            await _mark_state_error(callback_state, exc.code, now=now)
        await reject_provider_link(db, link=link_state, error_code=exc.code)
        await _record_callback_audit_event(
            db,
            workspace_id=link_state.workspace_id,
            event_type="provider_link_callback_rejected",
            provider=provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            actor_user_id=link_state.initiating_user_id,
            metadata={"error_code": exc.code},
        )
        raise
    except ProviderVerificationError as exc:
        if callback_state is not None:
            await _mark_state_error(callback_state, "provider_unavailable", now=now)
        await reject_provider_link(db, link=link_state, error_code="provider_unavailable")
        await _record_callback_audit_event(
            db,
            workspace_id=link_state.workspace_id,
            event_type="provider_link_callback_rejected",
            provider=provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            actor_user_id=link_state.initiating_user_id,
            metadata={"error_code": "provider_unavailable"},
        )
        raise CallbackFlowError("provider_unavailable", "provider callback verification unavailable") from exc
    except ProviderLinkError as exc:
        if callback_state is not None:
            await _mark_state_error(callback_state, exc.code, now=now)
        await reject_provider_link(db, link=link_state, error_code=exc.code)
        await _record_callback_audit_event(
            db,
            workspace_id=link_state.workspace_id,
            event_type="provider_link_callback_rejected",
            provider=provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            actor_user_id=link_state.initiating_user_id,
            metadata={"error_code": exc.code},
        )
        raise CallbackFlowError(exc.code, "provider link callback rejected") from exc
    except ValueError as exc:
        message = str(exc)
        error_code = (
            "callback_state_reused"
            if "already consumed" in message
            else "callback_state_expired"
            if "expired" in message
            else "callback_state_invalid"
        )
        if callback_state is not None:
            await _mark_state_error(callback_state, error_code, now=now)
        await reject_provider_link(db, link=link_state, error_code=error_code)
        await _record_callback_audit_event(
            db,
            workspace_id=link_state.workspace_id,
            event_type="provider_link_callback_rejected",
            provider=provider,
            actor_ip=actor_ip,
            request_id=request_id,
            outcome="failure",
            actor_user_id=link_state.initiating_user_id,
            metadata={"error_code": error_code},
        )
        raise CallbackFlowError(error_code, "callback state invalid") from exc
