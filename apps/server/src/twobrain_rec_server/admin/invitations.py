from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.audit import write_admin_audit_event
from twobrain_rec_server.admin.permissions import (
    AdminActor,
    AdminPermissionOutcome,
    invitation_role_decision,
)
from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.audit import write_onboarding_audit_event
from twobrain_rec_server.auth.workspace_onboarding import create_or_reuse_join_offer
from twobrain_rec_server.db.models import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceJoinOffer,
)
from twobrain_rec_server.db.tenant_context import WorkspaceAuthContext, apply_tenant_context


def normalize_invitation_target(value: str) -> str:
    return " ".join(value.strip().lower().split())


def matching_invitation_contacts(
    *,
    provider_subject: str | None,
    provider_username: str | None,
    email: str | None,
    phone: str | None,
) -> set[str]:
    return {
        normalized
        for normalized in (
            normalize_invitation_target(value)
            for value in (provider_subject, provider_username, email, phone)
            if value
        )
        if normalized
    }


def invitation_runtime_status(
    invitation: WorkspaceInvitation, *, now: datetime | None = None
) -> str:
    now = now or datetime.now(UTC)
    if invitation.status != "pending":
        return invitation.status
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    if expires_at <= now:
        return "expired"
    return "pending"


async def create_workspace_invitation(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    target_contact: str,
    invited_role: str,
    target_provider: str | None = None,
    expires_at: datetime | None = None,
) -> WorkspaceInvitation:
    _ensure_role_allowed(context, invited_role)
    workspace = await db.get(Workspace, context.workspace_id)
    if workspace is None or workspace.kind != "corporate":
        raise ProblemDetail(
            status=403,
            code="workspace_invitation_unavailable",
            title="Workspace invitation unavailable",
        )
    normalized = normalize_invitation_target(target_contact)
    if not normalized:
        raise ProblemDetail(
            status=422, code="invalid_invitation_target", title="Invalid invitation target"
        )
    await _expire_stale_pending_invitations(
        db, workspace_id=context.workspace_id, target_contact=normalized
    )
    duplicate = await db.scalar(
        select(WorkspaceInvitation).where(
            WorkspaceInvitation.workspace_id == context.workspace_id,
            WorkspaceInvitation.target_contact == normalized,
            WorkspaceInvitation.status == "pending",
        )
    )
    if duplicate is not None:
        raise ProblemDetail(
            status=409, code="invitation_duplicate_active", title="Active invitation already exists"
        )
    invitation = WorkspaceInvitation(
        workspace_id=context.workspace_id,
        target_contact=normalized,
        target_provider=target_provider,
        invited_role=invited_role,
        status="pending",
        source="admin",
        created_by_user_id=context.actor_user_id,
        expires_at=expires_at or (datetime.now(UTC) + timedelta(days=7)),
        metadata_json={"source": "admin"},
    )
    db.add(invitation)
    await db.flush()
    await write_admin_audit_event(
        db,
        workspace_id=context.workspace_id,
        actor_user_id=context.actor_user_id,
        actor_role=context.actor_role,
        action="invite_created",
        target_kind="invitation",
        target_id=str(invitation.id),
        outcome="completed",
        metadata={"role": invited_role, "source": "admin"},
    )
    return invitation


async def revoke_workspace_invitation(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    invitation_id: UUID,
    reason_code: str | None,
) -> WorkspaceInvitation:
    invitation = await _load_invitation(db, context.workspace_id, invitation_id)
    if invitation.status == "completed":
        raise ProblemDetail(
            status=409, code="invitation_already_completed", title="Invitation already completed"
        )
    if invitation.status == "revoked":
        return invitation
    invitation.status = "revoked"
    invitation.revoked_by_user_id = context.actor_user_id
    invitation.revoked_at = datetime.now(UTC)
    invitation.revocation_reason = reason_code
    await write_admin_audit_event(
        db,
        workspace_id=context.workspace_id,
        actor_user_id=context.actor_user_id,
        actor_role=context.actor_role,
        action="invite_revoked",
        target_kind="invitation",
        target_id=str(invitation.id),
        outcome="completed",
        reason_code=reason_code,
    )
    return invitation


async def resend_workspace_invitation(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    invitation_id: UUID,
) -> WorkspaceInvitation:
    """Renew a valid invitation and record a generic sign-in reminder."""
    invitation = await _load_invitation(db, context.workspace_id, invitation_id)
    now = datetime.now(UTC)
    status = invitation_runtime_status(invitation, now=now)
    if status == "expired":
        invitation.status = "expired"
        raise ProblemDetail(status=409, code="invitation_expired", title="Invitation expired")
    if status != "pending":
        raise ProblemDetail(
            status=409,
            code="invitation_resend_unavailable",
            title="Invitation resend unavailable",
        )
    invitation.expires_at = max(invitation.expires_at, now + timedelta(days=7))
    await write_admin_audit_event(
        db,
        workspace_id=context.workspace_id,
        actor_user_id=context.actor_user_id,
        actor_role=context.actor_role,
        action="invite_resent",
        target_kind="invitation",
        target_id=str(invitation.id),
        outcome="completed",
        metadata={"source": "admin"},
    )
    return invitation


async def create_matching_join_offers_after_login(
    db: AsyncSession,
    *,
    organization_id: UUID,
    bootstrap_workspace_id: UUID,
    user_id: UUID,
    provider: str,
    provider_subject: str | None,
    provider_username: str | None,
    email: str | None,
    phone: str | None,
) -> tuple[WorkspaceJoinOffer, ...]:
    """Create opaque, user-bound offers after a verified identity match.

    A callback may prove an identity, but it must never create a corporate
    membership by itself. The resulting offer is the only state the browser
    needs before the person explicitly accepts it.
    """
    contacts = matching_invitation_contacts(
        provider_subject=provider_subject,
        provider_username=provider_username,
        email=email,
        phone=phone,
    )
    if not contacts:
        return ()
    invitations = await find_matching_pending_invitations(
        db,
        organization_id=organization_id,
        provider=provider,
        contacts=contacts,
    )
    offers: list[WorkspaceJoinOffer] = []
    for invitation in invitations:
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                workspace_id=invitation.workspace_id,
                organization_id=organization_id,
                user_id=user_id,
                context_kind="auth_bootstrap",
            ),
        )
        workspace = await db.get(Workspace, invitation.workspace_id)
        if (
            workspace is None
            or workspace.kind != "corporate"
            or workspace.id == bootstrap_workspace_id
        ):
            continue
        existing_offer = await db.scalar(
            select(WorkspaceJoinOffer).where(
                WorkspaceJoinOffer.user_id == user_id,
                WorkspaceJoinOffer.invitation_id == invitation.id,
            )
        )
        offer = await create_or_reuse_join_offer(
            db,
            workspace_id=invitation.workspace_id,
            user_id=user_id,
            invitation_id=invitation.id,
            workspace_name=workspace.name,
            invited_role=invitation.invited_role,
            expires_at=invitation.expires_at,
        )
        if existing_offer is None:
            await write_onboarding_audit_event(
                db,
                workspace_id=invitation.workspace_id,
                user_id=user_id,
                event_type="workspace_join_offer_created",
                metadata={"offer_id": str(offer.id), "invitation_id": str(invitation.id)},
            )
        offers.append(offer)
    await apply_tenant_context(
        db,
        WorkspaceAuthContext(
            workspace_id=bootstrap_workspace_id,
            organization_id=organization_id,
            user_id=user_id,
            context_kind="auth_bootstrap",
        ),
    )
    return tuple(offers)


async def find_matching_pending_invitations(
    db: AsyncSession,
    *,
    organization_id: UUID | None,
    provider: str,
    contacts: Iterable[str],
    workspace_id: UUID | None = None,
) -> tuple[WorkspaceInvitation, ...]:
    normalized_contacts = {normalize_invitation_target(value) for value in contacts if value}
    if not normalized_contacts:
        return ()
    statement = select(WorkspaceInvitation).where(WorkspaceInvitation.status == "pending")
    if workspace_id is not None:
        statement = statement.where(WorkspaceInvitation.workspace_id == workspace_id)
    if organization_id is not None:
        statement = statement.join(Workspace).where(Workspace.organization_id == organization_id)
    invitations = (await db.execute(statement)).scalars().all()
    matches: list[WorkspaceInvitation] = []
    for invitation in invitations:
        if invitation_runtime_status(invitation) == "expired":
            continue
        if invitation.target_contact in normalized_contacts and invitation.target_provider in {
            None,
            provider,
        }:
            matches.append(invitation)
    return tuple(matches)


def invitation_to_dict(invitation: WorkspaceInvitation) -> dict[str, object]:
    return {
        "id": str(invitation.id),
        "workspace_id": str(invitation.workspace_id),
        "target_contact": invitation.target_contact,
        "target_provider": invitation.target_provider,
        "invited_role": invitation.invited_role,
        "status": invitation.status,
        "source": invitation.source,
        "created_by_user_id": str(invitation.created_by_user_id),
        "expires_at": invitation.expires_at.isoformat(),
        "completed_by_user_id": str(invitation.completed_by_user_id)
        if invitation.completed_by_user_id
        else None,
        "revoked_by_user_id": str(invitation.revoked_by_user_id)
        if invitation.revoked_by_user_id
        else None,
    }


def _ensure_role_allowed(context: AdminWorkspaceContext, invited_role: str) -> None:
    decision = invitation_role_decision(
        AdminActor(
            user_id=context.actor_user_id,
            workspace_id=context.workspace_id,
            role=context.actor_role,
        ),
        invited_role=invited_role,
    )
    if decision.outcome == AdminPermissionOutcome.DENIED_ADMIN_CANNOT_MANAGE_OWNER_ADMIN:
        raise ProblemDetail(
            status=403,
            code="admin_role_authority_forbidden",
            title="Admin cannot grant owner or admin authority",
        )
    if not decision.allowed:
        raise ProblemDetail(status=403, code="admin_forbidden", title="Admin access is restricted")


async def _expire_stale_pending_invitations(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    target_contact: str,
) -> None:
    now = datetime.now(UTC)
    invitations = (
        (
            await db.execute(
                select(WorkspaceInvitation).where(
                    WorkspaceInvitation.workspace_id == workspace_id,
                    WorkspaceInvitation.target_contact == target_contact,
                    WorkspaceInvitation.status == "pending",
                )
            )
        )
        .scalars()
        .all()
    )
    for invitation in invitations:
        if invitation_runtime_status(invitation, now=now) == "expired":
            invitation.status = "expired"


async def _load_invitation(
    db: AsyncSession, workspace_id: UUID, invitation_id: UUID
) -> WorkspaceInvitation:
    invitation = await db.get(WorkspaceInvitation, invitation_id)
    if invitation is None or invitation.workspace_id != workspace_id:
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
    return invitation
