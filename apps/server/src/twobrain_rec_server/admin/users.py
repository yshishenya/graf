from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.audit import write_admin_audit_event
from twobrain_rec_server.admin.permissions import (
    AdminActor,
    AdminPermissionOutcome,
    membership_mutation_decision,
)
from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.db.models import (
    AdminAuditEvent,
    AuthSession,
    BillingAuditEvent,
    Meeting,
    RegisteredDevice,
    UserIdentity,
    UserUsageDaily,
    WorkspaceInvitation,
    WorkspaceMembership,
    WorkspaceSubscription,
)


async def list_workspace_users(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    search: str | None = None,
    role: str | None = None,
    status: str | None = None,
    invitation_status: str | None = None,
    limit: int = 50,
) -> dict[str, object]:
    member_stmt = (
        select(WorkspaceMembership, UserIdentity)
        .join(UserIdentity, UserIdentity.id == WorkspaceMembership.user_id)
        .where(WorkspaceMembership.workspace_id == context.workspace_id)
    )
    if role:
        member_stmt = member_stmt.where(WorkspaceMembership.role == role)
    if status:
        member_stmt = member_stmt.where(WorkspaceMembership.status == status)
    if search:
        pattern = f"%{search.strip().lower()}%"
        member_stmt = member_stmt.where(
            or_(
                func.lower(UserIdentity.display_name).like(pattern),
                func.lower(UserIdentity.external_subject).like(pattern),
            )
        )
    member_rows = (
        await db.execute(
            member_stmt.order_by(WorkspaceMembership.role, UserIdentity.display_name).limit(limit)
        )
    ).all()
    invitation_stmt = select(WorkspaceInvitation).where(
        WorkspaceInvitation.workspace_id == context.workspace_id
    )
    if invitation_status:
        invitation_stmt = invitation_stmt.where(WorkspaceInvitation.status == invitation_status)
    if search:
        invitation_stmt = invitation_stmt.where(
            func.lower(WorkspaceInvitation.target_contact).like(pattern)
        )
    invitations = (
        (
            await db.execute(
                invitation_stmt.order_by(WorkspaceInvitation.created_at.desc()).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return {
        "members": [_membership_row_to_dict(membership, user) for membership, user in member_rows],
        "invitations": [
            {
                "id": str(invitation.id),
                "target_contact": invitation.target_contact,
                "target_provider": invitation.target_provider,
                "invited_role": invitation.invited_role,
                "status": invitation.status,
                "source": invitation.source,
                "created_by_user_id": str(invitation.created_by_user_id),
                "expires_at": invitation.expires_at.isoformat(),
            }
            for invitation in invitations
        ],
        "filters": {
            "search": search,
            "role": role,
            "status": status,
            "invitation_status": invitation_status,
        },
    }


async def get_workspace_user_detail(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    user_id: UUID,
) -> dict[str, object]:
    row = await db.execute(
        select(WorkspaceMembership, UserIdentity)
        .join(UserIdentity, UserIdentity.id == WorkspaceMembership.user_id)
        .where(
            WorkspaceMembership.workspace_id == context.workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
    )
    result = row.first()
    if result is None:
        raise ProblemDetail(status=404, code="admin_user_not_found", title="Admin user not found")
    membership, user = result
    session_count = int(
        await db.scalar(
            select(func.count())
            .select_from(AuthSession)
            .where(
                AuthSession.workspace_id == context.workspace_id,
                AuthSession.user_id == user_id,
                AuthSession.status == "active",
            )
        )
        or 0
    )
    sessions = (
        (
            await db.execute(
                select(AuthSession)
                .where(
                    AuthSession.workspace_id == context.workspace_id, AuthSession.user_id == user_id
                )
                .order_by(AuthSession.issued_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    devices = (
        (
            await db.execute(
                select(RegisteredDevice)
                .where(
                    RegisteredDevice.workspace_id == context.workspace_id,
                    RegisteredDevice.user_id == user_id,
                )
                .order_by(RegisteredDevice.updated_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    file_count = int(
        await db.scalar(
            select(func.count())
            .select_from(Meeting)
            .where(
                Meeting.workspace_id == context.workspace_id, Meeting.created_by_user_id == user_id
            )
        )
        or 0
    )
    usage = (
        (
            await db.execute(
                select(UserUsageDaily).where(
                    UserUsageDaily.workspace_id == context.workspace_id,
                    UserUsageDaily.user_id == user_id,
                )
            )
        )
        .scalars()
        .all()
    )
    audit = (
        (
            await db.execute(
                select(AdminAuditEvent)
                .where(
                    AdminAuditEvent.workspace_id == context.workspace_id,
                    or_(
                        AdminAuditEvent.actor_user_id == user_id,
                        AdminAuditEvent.target_id == str(user_id),
                    ),
                )
                .order_by(AdminAuditEvent.created_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    return _membership_row_to_dict(membership, user) | {
        "devices": [
            {
                "device_id": str(device.id),
                "device_public_id": device.device_public_id,
                "platform": device.platform,
                "status": device.status,
                "registration_state": device.registration_state,
                "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
            }
            for device in devices
        ],
        "sessions": {
            "active": session_count,
            "recent": [
                {
                    "session_id": str(session.id),
                    "provider": session.provider,
                    "status": session.status,
                    "device_id": str(session.device_id) if session.device_id else None,
                    "issued_at": session.issued_at.isoformat() if session.issued_at else None,
                    "expires_at": session.expires_at.isoformat(),
                }
                for session in sessions
            ],
        },
        "files": {"server_known": file_count},
        "usage": {
            "recording_minutes": sum(row.recording_minutes for row in usage),
            "storage_bytes": sum(row.storage_bytes for row in usage),
            "processing_jobs": sum(row.processing_jobs for row in usage),
        },
        "recent_audit": [
            {"action": event.action, "outcome": event.outcome, "target_kind": event.target_kind}
            for event in audit
        ],
    }


async def update_workspace_membership(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    target_user_id: UUID,
    requested_role: str | None,
    requested_status: str | None,
    reason_code: str | None,
) -> dict[str, object]:
    membership = await db.get(
        WorkspaceMembership,
        {"workspace_id": context.workspace_id, "user_id": target_user_id},
    )
    if membership is None:
        raise ProblemDetail(status=404, code="admin_user_not_found", title="Admin user not found")
    if requested_role is None and requested_status is None:
        return {
            "user_id": str(target_user_id),
            "role": membership.role,
            "status": membership.status,
        }
    previous_role = membership.role
    previous_status = membership.status
    active_owner_count = int(
        await db.scalar(
            select(func.count())
            .select_from(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == context.workspace_id,
                WorkspaceMembership.role == "owner",
                WorkspaceMembership.status == "active",
            )
        )
        or 0
    )
    decision = membership_mutation_decision(
        AdminActor(
            user_id=context.actor_user_id,
            workspace_id=context.workspace_id,
            role=context.actor_role,
        ),
        target_role=membership.role,
        target_status=membership.status,
        requested_role=requested_role,
        requested_status=requested_status,
        active_owner_count=active_owner_count,
    )
    if decision.outcome == AdminPermissionOutcome.DENIED_LAST_OWNER:
        raise ProblemDetail(
            status=409, code="last_owner_protection", title="Last active owner is protected"
        )
    if decision.outcome == AdminPermissionOutcome.DENIED_ADMIN_CANNOT_MANAGE_OWNER_ADMIN:
        raise ProblemDetail(
            status=403,
            code="admin_role_authority_forbidden",
            title="Admin cannot manage owner or admin authority",
        )
    if not decision.allowed:
        raise ProblemDetail(status=403, code="admin_forbidden", title="Admin access is restricted")
    if requested_role is not None:
        membership.role = requested_role
    if requested_status is not None:
        membership.status = requested_status
    was_active_billing_owner = previous_role == "owner" and previous_status == "active"
    is_active_billing_owner = membership.role == "owner" and membership.status == "active"
    if was_active_billing_owner and not is_active_billing_owner:
        subscription = await db.scalar(
            select(WorkspaceSubscription)
            .where(WorkspaceSubscription.workspace_id == context.workspace_id)
            .with_for_update()
        )
        if subscription is not None and subscription.billing_owner_id == target_user_id:
            # Keep the historical owner id for referral/refund attribution; recurring authority is revoked.
            subscription.recurring_allowed = False
            subscription.recurring_authority_version += 1
            subscription.application_version += 1
            db.add(
                BillingAuditEvent(
                    workspace_id=context.workspace_id,
                    actor_user_id=context.actor_user_id,
                    action="billing.owner_authority_revoked",
                    target_kind="workspace_subscription",
                    target_ref=str(context.workspace_id),
                    outcome="success",
                    reason_code="owner_membership_changed",
                    metadata_json={"recurring_allowed": "false"},
                )
            )
    await write_admin_audit_event(
        db,
        workspace_id=context.workspace_id,
        actor_user_id=context.actor_user_id,
        actor_role=context.actor_role,
        action="membership_updated",
        target_kind="user",
        target_id=str(target_user_id),
        outcome="completed",
        reason_code=reason_code,
        metadata={"role": membership.role, "status": membership.status},
    )
    return {
        "user_id": str(target_user_id),
        "role": membership.role,
        "status": membership.status,
    }


def _membership_row_to_dict(
    membership: WorkspaceMembership, user: UserIdentity
) -> dict[str, object]:
    return {
        "user_id": str(user.id),
        "display_name": user.display_name,
        "role": membership.role,
        "status": membership.status,
    }
