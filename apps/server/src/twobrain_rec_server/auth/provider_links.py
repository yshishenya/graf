from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
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


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def scrub_candidate(link: WorkspaceProviderLinkState, *, status: str, resolution: str) -> None:
    link.candidate_identity_subject = None
    link.candidate_email = None
    link.candidate_phone = None
    link.candidate_display_name = None
    link.status = status
    link.resolution = resolution


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
    if link.expires_at > _now(now):
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
