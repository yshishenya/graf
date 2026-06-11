from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.policy import (
    is_provider_enabled_in_policy,
    load_workspace_auth_policy,
)
from twobrain_rec_server.auth.providers import get_provider_adapter
from twobrain_rec_server.auth.providers.base import (
    ProviderCredentials,
    ProviderHttpClient,
    ProviderVerificationError,
    get_provider_http_client,
)
from twobrain_rec_server.auth.sessions import consume_callback_state, issue_auth_session
from twobrain_rec_server.db.models import (
    AuthCallbackState,
    ExternalIdentity,
    UserIdentity,
    Workspace,
    WorkspaceAuthPolicy,
    WorkspaceMembership,
)


@dataclass(frozen=True)
class CallbackProfile:
    user_id: UUID
    workspace_id: UUID
    auth_session_id: UUID
    provider_subject: str
    external_identity_id: UUID
    token: str
    token_expires_at: datetime


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
) -> UserIdentity:
    user = UserIdentity(
        organization_id=organization_id,
        external_subject=provider_subject,
        display_name=profile.get("display_name"),
    )
    db.add(user)
    await db.flush()
    db.add(
        WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=user.id,
            role="member",
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
    return user


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
    allow_provider_self_enrollment: bool,
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
        membership = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user.id,
            )
        )
        if membership is None:
            if not allow_provider_self_enrollment:
                raise CallbackFlowError(
                    "workspace_enrollment_required",
                    "workspace policy requires invite or pre-existing membership",
                    workspace_id=workspace_id,
                )
            db.add(
                WorkspaceMembership(
                    workspace_id=workspace_id,
                    user_id=user.id,
                    role="member",
                    status="active",
                )
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
    if not allow_provider_self_enrollment:
        raise CallbackFlowError(
            "workspace_enrollment_required",
            "workspace policy requires invite or pre-existing membership",
            workspace_id=workspace_id,
        )
    return await _create_scoped_user(
        db,
        organization_id=organization_id,
        workspace_id=workspace_id,
        provider=provider,
        provider_subject=provider_subject,
        profile=profile,
    )


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
    now: datetime | None = None,
) -> CallbackProfile:
    now = now or datetime.now(UTC)
    try:
        state = await consume_callback_state(db, provider=provider, state_nonce=state_nonce, now=now)
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
        policy = await _assert_provider_allowed(db, state.workspace_id, identity.provider)
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
            allow_provider_self_enrollment=policy.allow_provider_self_enrollment,
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

    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.user_id == user.id,
        )
    )
    if membership is None:
        if not policy.allow_provider_self_enrollment:
            await _mark_state_error(state, "workspace_enrollment_required", now=now)
            await _record_callback_audit_event(
                db,
                workspace_id=workspace.id,
                event_type="provider_callback_failed",
                provider=provider,
                actor_ip=actor_ip,
                request_id=request_id,
                outcome="failure",
                metadata={"error_code": "workspace_enrollment_required", "state_nonce": state_nonce},
            )
            raise CallbackFlowError(
                "workspace_enrollment_required",
                "workspace policy requires invite or pre-existing membership",
                workspace_id=workspace.id,
            )
        db.add(
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user.id,
                role="member",
                status="active",
            )
        )
    issued = await issue_auth_session(
        db,
        user_id=user.id,
        workspace_id=workspace.id,
        provider=identity.provider,
        ttl_seconds=session_ttl_seconds,
        claims_fingerprint=_fingerprint_identity(
            identity.provider_subject,
            identity.provider,
            workspace.id,
        ),
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
        user_id=user.id,
        workspace_id=workspace.id,
        auth_session_id=issued.id,
        provider_subject=identity.provider_subject,
        external_identity_id=ext.id,
        token=issued.token,
        token_expires_at=issued.expires_at,
    )
