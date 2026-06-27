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
from twobrain_rec_server.db.models import UserIdentity, WorkspaceInvitation, WorkspaceMembership


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


async def complete_workspace_invitation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    invitation_id: UUID,
    completed_user_id: UUID,
    provider: str | None,
    login_contacts: Iterable[str],
) -> WorkspaceInvitation:
    invitation = await _load_invitation(db, workspace_id, invitation_id)
    await _ensure_invitation_completable(invitation, provider=provider)
    contacts = {normalize_invitation_target(value) for value in login_contacts if value}
    if invitation.target_contact not in contacts:
        raise ProblemDetail(
            status=403, code="invitation_identity_mismatch", title="Invitation identity mismatch"
        )
    user = await db.get(UserIdentity, completed_user_id)
    if user is None or user.status != "active":
        raise ProblemDetail(
            status=403, code="invitation_identity_mismatch", title="Invitation identity mismatch"
        )
    membership = await db.get(
        WorkspaceMembership, {"workspace_id": workspace_id, "user_id": completed_user_id}
    )
    if membership is None:
        membership = WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=completed_user_id,
            role=invitation.invited_role,
            status="active",
        )
        db.add(membership)
    invitation.status = "completed"
    invitation.completed_by_user_id = completed_user_id
    invitation.completed_membership_id = f"{workspace_id}:{completed_user_id}"
    invitation.completed_at = datetime.now(UTC)
    completed_role = membership.role
    await write_admin_audit_event(
        db,
        workspace_id=workspace_id,
        actor_user_id=completed_user_id,
        actor_role=completed_role,
        action="invite_completed",
        target_kind="invitation",
        target_id=str(invitation.id),
        outcome="completed",
        metadata={"role": completed_role, "source": "admin", "status": membership.status},
    )
    return invitation


async def complete_matching_invitation_after_login(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    provider: str,
    provider_subject: str | None,
    provider_username: str | None,
    email: str | None,
    phone: str | None,
) -> WorkspaceInvitation | None:
    contacts = matching_invitation_contacts(
        provider_subject=provider_subject,
        provider_username=provider_username,
        email=email,
        phone=phone,
    )
    if not contacts:
        return None
    invitation = await find_matching_pending_invitation(
        db,
        workspace_id=workspace_id,
        provider=provider,
        contacts=contacts,
    )
    if invitation is None:
        return None
    return await complete_workspace_invitation(
        db,
        workspace_id=workspace_id,
        invitation_id=invitation.id,
        completed_user_id=user_id,
        provider=provider,
        login_contacts=contacts,
    )


async def find_matching_pending_invitation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    provider: str,
    contacts: Iterable[str],
) -> WorkspaceInvitation | None:
    normalized_contacts = {normalize_invitation_target(value) for value in contacts if value}
    invitations = (
        (
            await db.execute(
                select(WorkspaceInvitation).where(
                    WorkspaceInvitation.workspace_id == workspace_id,
                    WorkspaceInvitation.status == "pending",
                )
            )
        )
        .scalars()
        .all()
    )
    for invitation in invitations:
        if invitation_runtime_status(invitation) == "expired":
            invitation.status = "expired"
            continue
        if invitation.target_contact in normalized_contacts and invitation.target_provider in {
            None,
            provider,
        }:
            return invitation
    return None


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


async def _ensure_invitation_completable(
    invitation: WorkspaceInvitation, *, provider: str | None
) -> None:
    status = invitation_runtime_status(invitation)
    if status == "expired":
        invitation.status = "expired"
        raise ProblemDetail(status=409, code="invitation_expired", title="Invitation expired")
    if status == "revoked":
        raise ProblemDetail(status=409, code="invitation_revoked", title="Invitation revoked")
    if status == "completed":
        raise ProblemDetail(
            status=409, code="invitation_already_completed", title="Invitation already completed"
        )
    if invitation.target_provider is not None and provider != invitation.target_provider:
        raise ProblemDetail(
            status=403, code="invitation_identity_mismatch", title="Invitation identity mismatch"
        )
