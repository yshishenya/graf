from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class AdminPermissionOutcome(StrEnum):
    ALLOWED = "allowed"
    DENIED_UNAUTHENTICATED = "denied_unauthenticated"
    DENIED_MEMBER = "denied_member"
    DENIED_CROSS_WORKSPACE = "denied_cross_workspace"
    DENIED_ADMIN_CANNOT_MANAGE_OWNER_ADMIN = "denied_admin_cannot_manage_owner_admin"
    DENIED_LAST_OWNER = "denied_last_owner"
    DENIED_INACTIVE_MEMBERSHIP = "denied_inactive_membership"
    DENIED_AUDIT_UNAVAILABLE = "denied_audit_unavailable"


@dataclass(frozen=True, slots=True)
class AdminActor:
    user_id: UUID
    workspace_id: UUID
    role: str
    status: str = "active"
    authenticated: bool = True


@dataclass(frozen=True, slots=True)
class AdminPermissionDecision:
    outcome: AdminPermissionOutcome

    @property
    def allowed(self) -> bool:
        return self.outcome == AdminPermissionOutcome.ALLOWED


def admin_access_decision(
    actor: AdminActor | None,
    *,
    target_workspace_id: UUID,
    audit_available: bool = True,
) -> AdminPermissionDecision:
    base = _base_admin_decision(actor, target_workspace_id=target_workspace_id)
    if not base.allowed:
        return base
    if not audit_available:
        return AdminPermissionDecision(AdminPermissionOutcome.DENIED_AUDIT_UNAVAILABLE)
    return base


def invitation_role_decision(
    actor: AdminActor | None,
    *,
    invited_role: str,
    audit_available: bool = True,
) -> AdminPermissionDecision:
    base = admin_access_decision(
        actor,
        target_workspace_id=actor.workspace_id if actor else UUID(int=0),
        audit_available=audit_available,
    )
    if not base.allowed:
        return base
    assert actor is not None
    if actor.role == "admin" and invited_role != "member":
        return AdminPermissionDecision(
            AdminPermissionOutcome.DENIED_ADMIN_CANNOT_MANAGE_OWNER_ADMIN
        )
    return AdminPermissionDecision(AdminPermissionOutcome.ALLOWED)


def membership_mutation_decision(
    actor: AdminActor | None,
    *,
    target_role: str,
    target_status: str,
    requested_role: str | None,
    requested_status: str | None,
    active_owner_count: int,
    removes_membership: bool = False,
    audit_available: bool = True,
) -> AdminPermissionDecision:
    base = admin_access_decision(
        actor,
        target_workspace_id=actor.workspace_id if actor else UUID(int=0),
        audit_available=audit_available,
    )
    if not base.allowed:
        return base
    assert actor is not None
    if actor.role == "admin" and (target_role != "member" or requested_role in {"owner", "admin"}):
        return AdminPermissionDecision(
            AdminPermissionOutcome.DENIED_ADMIN_CANNOT_MANAGE_OWNER_ADMIN
        )
    if _would_remove_last_owner(
        target_role=target_role,
        target_status=target_status,
        requested_role=requested_role,
        requested_status=requested_status,
        removes_membership=removes_membership,
        active_owner_count=active_owner_count,
    ):
        return AdminPermissionDecision(AdminPermissionOutcome.DENIED_LAST_OWNER)
    return AdminPermissionDecision(AdminPermissionOutcome.ALLOWED)


def _base_admin_decision(
    actor: AdminActor | None,
    *,
    target_workspace_id: UUID,
) -> AdminPermissionDecision:
    if actor is None or not actor.authenticated:
        return AdminPermissionDecision(AdminPermissionOutcome.DENIED_UNAUTHENTICATED)
    if actor.workspace_id != target_workspace_id:
        return AdminPermissionDecision(AdminPermissionOutcome.DENIED_CROSS_WORKSPACE)
    if actor.status != "active":
        return AdminPermissionDecision(AdminPermissionOutcome.DENIED_INACTIVE_MEMBERSHIP)
    if actor.role not in {"owner", "admin"}:
        return AdminPermissionDecision(AdminPermissionOutcome.DENIED_MEMBER)
    return AdminPermissionDecision(AdminPermissionOutcome.ALLOWED)


def _would_remove_last_owner(
    *,
    target_role: str,
    target_status: str,
    requested_role: str | None,
    requested_status: str | None,
    removes_membership: bool,
    active_owner_count: int,
) -> bool:
    if target_role != "owner" or target_status != "active" or active_owner_count > 1:
        return False
    if removes_membership:
        return True
    next_role = requested_role or target_role
    next_status = requested_status or target_status
    return next_role != "owner" or next_status != "active"
