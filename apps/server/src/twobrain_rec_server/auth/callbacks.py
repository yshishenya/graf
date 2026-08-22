from __future__ import annotations

import asyncio
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
from twobrain_rec_server.auth.redirects import safe_first_party_path
from twobrain_rec_server.auth.sessions import (
    consume_callback_state,
    fingerprint_identity,
    issue_auth_session,
)
from twobrain_rec_server.auth.workspace_onboarding import ensure_personal_workspace
from twobrain_rec_server.billing.referral_binding import bind_referral_attribution
from twobrain_rec_server.db.models import (
    AuthCallbackState,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceAuthPolicy,
    WorkspaceMembership,
    WorkspaceProviderLinkState,
)
from twobrain_rec_server.db.tenant_context import (
    AuthCallbackLookupContext,
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
    registered: bool = False
    browser_bound: bool = False


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
    await db.flush()
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=workspace_id,
            user_id=actor_user_id,
            context_kind="auth_bootstrap",
        ),
    )
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


def _is_external_identity_unique_conflict(exc: IntegrityError) -> bool:
    message = str(exc.orig).lower()
    constraint_name = str(getattr(exc.orig, "constraint_name", "")).lower()
    known_constraint_names = frozenset(
        {
            "external_identities_provider_provider_subject_key",
            "uq_external_identities_provider",
        }
    )
    return (
        (
            "external_identities.provider" in message
            and "external_identities.provider_subject" in message
        )
        or constraint_name in known_constraint_names
        or any(known_constraint in message for known_constraint in known_constraint_names)
    )


async def _mark_state_error(
    db: AsyncSession,
    state: AuthCallbackState,
    code: str,
    now: datetime | None = None,
) -> None:
    await apply_tenant_context(
        db,
        AuthCallbackLookupContext(state_nonce=state.state_nonce),
    )
    state.used_at = now or datetime.now(UTC)
    state.result = "rejected"
    state.error_code = code
    await db.flush()


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
                ExternalIdentity.is_active.is_(True),
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


async def _verify_provider_callback(
    *,
    provider: str,
    query: dict[str, str],
    state_nonce: str,
    provider_credentials: ProviderCredentials,
    provider_http_client: ProviderHttpClient | None,
    now: datetime,
):
    adapter = get_provider_adapter(provider)
    http_client = provider_http_client or get_provider_http_client()
    # ponytail: keep native sync adapters; the bounded default executor caps provider I/O.
    return await asyncio.to_thread(
        adapter.verify_callback,
        query,
        expected_state=state_nonce,
        credentials=provider_credentials,
        http_client=http_client,
        now=now,
    )


async def _assert_provider_allowed(
    db: AsyncSession, workspace_id: UUID, provider: str
) -> WorkspaceAuthPolicy:
    policy = await load_workspace_auth_policy(db, workspace_id)
    if not is_provider_enabled_in_policy(policy, provider):
        raise CallbackFlowError(
            "provider_disabled", f"provider {provider} disabled by workspace policy"
        )
    return policy


async def _create_scoped_user(
    db: AsyncSession,
    organization_id: UUID,
    workspace_id: UUID,
    *,
    provider: str,
    provider_subject: str,
    profile: dict[str, str | bool | None],
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
            db.add(
                ExternalIdentity(
                    user_id=user.id,
                    provider=provider,
                    provider_subject=provider_subject,
                    provider_username=profile.get("provider_username"),
                    email=profile.get("email"),
                    phone=profile.get("phone"),
                    display_name=profile.get("display_name"),
                    is_verified=bool(profile.get("email")) and bool(profile.get("is_verified")),
                    subject_issued_at=datetime.now(UTC),
                    last_seen_at=datetime.now(UTC),
                    meta={},
                )
            )
            await db.flush()
    except IntegrityError as exc:
        if _is_external_identity_unique_conflict(exc):
            existing_identity = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.provider == provider,
                    ExternalIdentity.provider_subject == provider_subject,
                )
            )
            if existing_identity is not None:
                if not existing_identity.is_active:
                    raise CallbackFlowError(
                        "identity_subject_inactive",
                        "identity is no longer linked to an active account",
                    ) from exc
                existing_user = await db.get(UserIdentity, existing_identity.user_id)
                if (
                    existing_identity.is_active
                    and existing_user is not None
                    and existing_user.organization_id == organization_id
                ):
                    await apply_tenant_context(
                        db,
                        WorkspaceAuthContext(
                            workspace_id=workspace_id,
                            organization_id=organization_id,
                            user_id=existing_user.id,
                            context_kind="auth_bootstrap",
                        ),
                    )
                    return existing_user
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
        ),
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
    return safe_first_party_path(value) is not None


async def _get_or_create_user_from_provider_claims(
    db: AsyncSession,
    *,
    organization_id: UUID,
    workspace_id: UUID,
    auth_bootstrap_workspace_id: UUID,
    provider: str,
    provider_subject: str,
    provider_username: str | None,
    email: str | None,
    phone: str | None,
    display_name: str | None,
    is_verified: bool,
) -> tuple[UserIdentity, bool]:
    user = await _user_by_external_identity(
        db,
        organization_id=organization_id,
        provider=provider,
        provider_subject=provider_subject,
    )
    if user is not None:
        if user.status != "active":
            raise CallbackFlowError(
                "identity_user_inactive", "identity owner account is not active"
            )
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=workspace_id,
                organization_id=organization_id,
                user_id=user.id,
                context_kind="auth_bootstrap",
            ),
        )
        identity = await db.scalar(
            select(ExternalIdentity).where(
                ExternalIdentity.provider == provider,
                ExternalIdentity.provider_subject == provider_subject,
                ExternalIdentity.user_id == user.id,
            )
        )
        if identity is not None:
            previous_email = identity.email
            identity.email = email or previous_email
            identity.phone = phone or identity.phone
            identity.provider_username = provider_username or identity.provider_username
            identity.display_name = display_name or identity.display_name
            if email and email != previous_email:
                identity.is_verified = is_verified
            elif email and is_verified:
                identity.is_verified = True
            identity.last_seen_at = datetime.now(UTC)
        await create_matching_join_offers_after_login(
            db,
            organization_id=organization_id,
            bootstrap_workspace_id=auth_bootstrap_workspace_id,
            user_id=user.id,
            provider=provider,
            provider_subject=provider_subject,
            provider_username=provider_username,
            email=email,
            phone=phone,
        )
        return user, False

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
        "is_verified": bool(email) and is_verified,
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
        bootstrap_workspace_id=auth_bootstrap_workspace_id,
        user_id=user.id,
        provider=provider,
        provider_subject=provider_subject,
        provider_username=provider_username,
        email=email,
        phone=phone,
    )
    return user, True


async def resolve_callback_to_user(
    db: AsyncSession,
    *,
    provider: str,
    query: dict[str, str],
    state_nonce: str,
    provider_credentials: ProviderCredentials,
    auth_bootstrap_workspace_id: UUID,
    session_ttl_seconds: int,
    actor_ip: str | None = None,
    request_id: str | None = None,
    provider_http_client: ProviderHttpClient | None = None,
    browser_state_nonce: str | None = None,
    referral_token: str | None = None,
    referral_enabled: bool,
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
        await db.flush()
    except ValueError as exc:
        message = str(exc)
        if "already consumed" in message:
            state = await _load_state_if_exists(db, provider=provider, state_nonce=state_nonce)
            if state is not None:
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
            raise CallbackFlowError(
                "callback_state_reused", "callback state already consumed"
            ) from exc
        if "expired" in message:
            state = await _load_state_if_exists(db, provider=provider, state_nonce=state_nonce)
            if state is not None:
                await _mark_state_error(db, state, "callback_state_expired", now=now)
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
        identity = await _verify_provider_callback(
            provider=provider,
            query=query,
            state_nonce=state_nonce,
            provider_credentials=provider_credentials,
            provider_http_client=provider_http_client,
            now=now,
        )
    except ProviderVerificationError as exc:
        await _mark_state_error(db, state, "provider_unavailable", now=now)
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
        raise CallbackFlowError(
            "provider_unavailable", "provider callback verification unavailable"
        ) from exc
    except CallbackFlowError as exc:
        await _mark_state_error(db, state, exc.code, now=now)
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
        await _mark_state_error(db, state, "callback_parse_error", now=now)
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
        await _mark_state_error(db, state, exc.code, now=now)
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
        await _mark_state_error(db, state, "workspace_not_found", now=now)
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
        user, registered = await _get_or_create_user_from_provider_claims(
            db,
            organization_id=workspace.organization_id,
            workspace_id=workspace.id,
            auth_bootstrap_workspace_id=auth_bootstrap_workspace_id,
            provider=identity.provider,
            provider_subject=identity.normalized_subject(),
            provider_username=identity.provider_username,
            email=identity.email,
            phone=identity.phone,
            display_name=identity.display_name,
            is_verified=identity.is_verified,
        )
    except CallbackFlowError as exc:
        await _mark_state_error(db, state, exc.code, now=now)
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
    if workspace.id == auth_bootstrap_workspace_id:
        workspace = personal_workspace
    else:
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.user_id == user.id,
                WorkspaceMembership.status == "active",
            )
        )
        if membership is None:
            # Provider claims never create corporate access. An accepted join
            # offer is the only customer enrollment path.
            workspace = personal_workspace
    if registered:
        await bind_referral_attribution(
            db,
            enabled=referral_enabled,
            workspace_id=workspace.id,
            user_id=user.id,
            token=referral_token,
            now=now,
        )
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
        claims_fingerprint=fingerprint_identity(
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
        raise CallbackFlowError(
            "identity_persistence_failed", "identity persistence failed", workspace_id=workspace.id
        )

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
            "identity_subject_fingerprint": fingerprint_identity(
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
        registered=registered,
        browser_bound=state.expected_state != state.state_nonce,
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

    async def reject_pending(error_code: str) -> None:
        await apply_tenant_context(
            db,
            AuthCallbackLookupContext(state_nonce=state_nonce),
        )
        current_link = await db.scalar(
            select(WorkspaceProviderLinkState)
            .where(WorkspaceProviderLinkState.id == link_state.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if current_link is not None and current_link.status == "initiated":
            await apply_tenant_context(
                db,
                WorkspaceAuthContext(
                    workspace_id=current_link.workspace_id,
                    user_id=current_link.initiating_user_id,
                    context_kind="auth_bootstrap",
                ),
            )
            await reject_provider_link(db, link=current_link, error_code=error_code)

    try:
        callback_state = await consume_callback_state(
            db,
            provider=provider,
            state_nonce=state_nonce,
            browser_state_nonce=browser_state_nonce,
            now=now,
        )
        await db.flush()
        if callback_state.id != link_state.callback_state_id:
            raise ProviderLinkError("provider_link_callback_mismatch")
        _resolve_oauth_denial(query)
        identity = await _verify_provider_callback(
            provider=provider,
            query=query,
            state_nonce=state_nonce,
            provider_credentials=provider_credentials,
            provider_http_client=provider_http_client,
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
        workspace = await assert_workspace_active(db, link_state.workspace_id)
        if workspace is None:
            raise ProviderLinkError("workspace_scope_denied")
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=link_state.workspace_id,
                organization_id=workspace.organization_id,
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
        candidate_identity = await db.scalar(
            select(ExternalIdentity).where(
                ExternalIdentity.provider == identity.provider,
                ExternalIdentity.provider_subject == identity.normalized_subject(),
                ExternalIdentity.is_active.is_(True),
            )
        )
        await db.flush()
        if candidate_identity is not None:
            await apply_tenant_context(
                db,
                AuthCallbackLookupContext(state_nonce=callback_state.state_nonce),
            )
            callback_state.verified_external_identity_id = candidate_identity.id
            await db.flush()
    except CallbackFlowError as exc:
        if callback_state is not None:
            await _mark_state_error(db, callback_state, exc.code, now=now)
        await reject_pending(exc.code)
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
            await _mark_state_error(db, callback_state, "provider_unavailable", now=now)
        await reject_pending("provider_unavailable")
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
        raise CallbackFlowError(
            "provider_unavailable", "provider callback verification unavailable"
        ) from exc
    except ProviderLinkError as exc:
        if callback_state is not None:
            await _mark_state_error(db, callback_state, exc.code, now=now)
        await reject_pending(exc.code)
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
            await _mark_state_error(db, callback_state, error_code, now=now)
        await reject_pending(error_code)
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
