from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.policy import (
    is_provider_enabled_in_policy,
    load_workspace_auth_policy,
)
from twobrain_rec_server.db.models import (
    AuthCallbackState,
    AuthSession,
    ExternalIdentity,
    WorkspaceMembership,
    WorkspaceProviderLinkState,
)


class ProviderLinkError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ConfirmedProviderLink:
    def __init__(self, *, provider: str, idempotent: bool) -> None:
        self.provider = provider
        self.idempotent = idempotent


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def scrub_candidate(link: WorkspaceProviderLinkState, *, status: str, resolution: str) -> None:
    link.candidate_identity_subject = None
    link.candidate_email = None
    link.candidate_phone = None
    link.candidate_display_name = None
    link.status = status
    link.resolution = resolution


async def reject_provider_link(
    db: AsyncSession,
    *,
    link: WorkspaceProviderLinkState,
    error_code: str,
    actor_user_id: UUID | None = None,
    event_type: str = "provider_link_rejected",
) -> None:
    status = "expired" if error_code == "provider_link_expired" else "rejected"
    scrub_candidate(link, status=status, resolution=error_code)
    await write_auth_audit_event(
        db,
        workspace_id=link.workspace_id,
        event_type=event_type,
        actor_user_id=actor_user_id or link.initiating_user_id,
        provider=link.candidate_provider,
        outcome="failure",
        metadata={"error_code": error_code},
    )


async def create_link_intent(
    db: AsyncSession,
    *,
    principal: AuthenticatedPrincipal,
    workspace_id: UUID,
    provider: str,
    callback_state: AuthCallbackState,
) -> WorkspaceProviderLinkState:
    if not principal.auth_via_session or principal.session_id is None:
        raise ProviderLinkError("provider_link_session_required")
    if workspace_id not in principal.workspace_ids or principal.session_workspace_id != workspace_id:
        raise ProviderLinkError("workspace_scope_denied")
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    if membership is None:
        raise ProviderLinkError("workspace_scope_denied")
    session = await db.scalar(
        select(AuthSession).where(
            AuthSession.id == principal.session_id,
            AuthSession.user_id == principal.user_id,
            AuthSession.workspace_id == workspace_id,
            AuthSession.status == "active",
        )
    )
    if session is None:
        raise ProviderLinkError("provider_link_session_required")
    source = await db.scalar(
        select(ExternalIdentity).where(
            ExternalIdentity.user_id == principal.user_id,
            ExternalIdentity.provider == session.provider,
        )
    )
    if source is None:
        raise ProviderLinkError("provider_link_source_identity_missing")
    link = WorkspaceProviderLinkState(
        workspace_id=workspace_id,
        initiating_user_id=principal.user_id,
        initiating_auth_session_id=session.id,
        source_provider_identity_id=source.id,
        callback_state_id=callback_state.id,
        candidate_provider=provider,
        status="initiated",
        expires_at=callback_state.expires_at,
    )
    db.add(link)
    await db.flush()
    await write_auth_audit_event(
        db,
        workspace_id=workspace_id,
        event_type="provider_link_started",
        actor_user_id=principal.user_id,
        provider=provider,
        metadata={"link_state_id": str(link.id)},
    )
    return link


async def link_for_callback(
    db: AsyncSession, callback_state_id: UUID
) -> WorkspaceProviderLinkState | None:
    return await db.scalar(
        select(WorkspaceProviderLinkState).where(
            WorkspaceProviderLinkState.callback_state_id == callback_state_id
        )
    )


async def expire_if_needed(
    link: WorkspaceProviderLinkState, *, now: datetime | None = None
) -> bool:
    if _as_aware_utc(link.expires_at) > _as_aware_utc(_now(now)):
        return False
    scrub_candidate(link, status="expired", resolution="expired")
    return True


async def store_verified_candidate(
    db: AsyncSession,
    *,
    link: WorkspaceProviderLinkState,
    provider: str,
    provider_subject: str,
    email: str | None,
    phone: str | None,
    display_name: str | None,
    now: datetime | None = None,
) -> None:
    if link.candidate_provider != provider or link.status != "initiated":
        raise ProviderLinkError("provider_link_reused")
    if await expire_if_needed(link, now=now):
        raise ProviderLinkError("provider_link_expired")
    link.candidate_identity_subject = provider_subject
    link.candidate_email = email
    link.candidate_phone = phone
    link.candidate_display_name = display_name
    link.callback_verified_at = _now(now)
    link.status = "callback_verified"
    await write_auth_audit_event(
        db,
        workspace_id=link.workspace_id,
        event_type="provider_link_callback_verified",
        actor_user_id=link.initiating_user_id,
        provider=provider,
        metadata={"link_state_id": str(link.id)},
    )


async def confirm_provider_link(
    db: AsyncSession,
    *,
    principal: AuthenticatedPrincipal,
    link_state_id: UUID,
    now: datetime | None = None,
) -> ConfirmedProviderLink:
    if not principal.auth_via_session or principal.session_id is None:
        raise ProviderLinkError("provider_link_session_required")
    if principal.session_workspace_id is None:
        raise ProviderLinkError("workspace_scope_denied")

    link = await db.get(WorkspaceProviderLinkState, link_state_id)
    if link is None:
        raise ProviderLinkError("provider_link_not_found")
    if (
        link.workspace_id != principal.session_workspace_id
        or link.initiating_user_id != principal.user_id
        or link.initiating_auth_session_id != principal.session_id
    ):
        raise ProviderLinkError("workspace_scope_denied")

    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == link.workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    session = await db.scalar(
        select(AuthSession).where(
            AuthSession.id == principal.session_id,
            AuthSession.user_id == principal.user_id,
            AuthSession.workspace_id == link.workspace_id,
            AuthSession.status == "active",
        )
    )
    if membership is None:
        raise ProviderLinkError("workspace_scope_denied")
    if session is None:
        raise ProviderLinkError("provider_link_session_required")
    if await expire_if_needed(link, now=now):
        await write_auth_audit_event(
            db,
            workspace_id=link.workspace_id,
            event_type="provider_link_expired",
            actor_user_id=principal.user_id,
            provider=link.candidate_provider,
            outcome="failure",
            metadata={"error_code": "provider_link_expired"},
        )
        raise ProviderLinkError("provider_link_expired")
    if link.status != "callback_verified":
        raise ProviderLinkError("provider_link_reused")
    if link.candidate_provider is None or link.candidate_identity_subject is None:
        await reject_provider_link(db, link=link, error_code="provider_link_candidate_missing")
        raise ProviderLinkError("provider_link_candidate_missing")

    policy = await load_workspace_auth_policy(db, link.workspace_id)
    if not is_provider_enabled_in_policy(policy, link.candidate_provider):
        await reject_provider_link(
            db,
            link=link,
            error_code="provider_disabled",
            actor_user_id=principal.user_id,
        )
        raise ProviderLinkError("provider_disabled")

    identity = await db.scalar(
        select(ExternalIdentity).where(
            and_(
                ExternalIdentity.provider == link.candidate_provider,
                ExternalIdentity.provider_subject == link.candidate_identity_subject,
            )
        )
    )
    idempotent = identity is not None
    if identity is not None and identity.user_id != principal.user_id:
        await reject_provider_link(
            db,
            link=link,
            error_code="provider_link_conflict",
            event_type="provider_link_conflict",
            actor_user_id=principal.user_id,
        )
        raise ProviderLinkError("provider_link_conflict")
    if identity is None:
        try:
            async with db.begin_nested():
                identity = ExternalIdentity(
                    user_id=principal.user_id,
                    provider=link.candidate_provider,
                    provider_subject=link.candidate_identity_subject,
                    email=link.candidate_email,
                    phone=link.candidate_phone,
                    display_name=link.candidate_display_name,
                    is_verified=True,
                    last_seen_at=_now(now),
                )
                db.add(identity)
                await db.flush()
        except IntegrityError as exc:
            identity = await db.scalar(
                select(ExternalIdentity).where(
                    and_(
                        ExternalIdentity.provider == link.candidate_provider,
                        ExternalIdentity.provider_subject == link.candidate_identity_subject,
                    )
                )
            )
            if identity is None or identity.user_id != principal.user_id:
                await reject_provider_link(
                    db,
                    link=link,
                    error_code="provider_link_conflict",
                    event_type="provider_link_conflict",
                    actor_user_id=principal.user_id,
                )
                raise ProviderLinkError("provider_link_conflict") from exc
            idempotent = True

    link.target_provider_identity_id = identity.id
    link.confirmed_at = _now(now)
    scrub_candidate(link, status="confirmed", resolution="idempotent" if idempotent else "confirmed")
    await write_auth_audit_event(
        db,
        workspace_id=link.workspace_id,
        event_type="provider_link_confirmed",
        actor_user_id=principal.user_id,
        provider=identity.provider,
        metadata={"idempotent": idempotent},
    )
    return ConfirmedProviderLink(provider=identity.provider, idempotent=idempotent)
