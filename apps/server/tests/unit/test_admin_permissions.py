from __future__ import annotations

from uuid import UUID

from twobrain_rec_server.admin.permissions import (
    AdminActor,
    AdminPermissionOutcome,
    admin_access_decision,
    corporate_admin_workspace_decision,
    invitation_role_decision,
    membership_mutation_decision,
)

WORKSPACE_ID = UUID("64000000-0000-0000-0000-000000000002")
OTHER_WORKSPACE_ID = UUID("64000000-0000-0000-0000-000000000003")
OWNER_ID = UUID("64000000-0000-0000-0000-000000000011")
ADMIN_ID = UUID("64000000-0000-0000-0000-000000000013")
MEMBER_ID = UUID("64000000-0000-0000-0000-000000000014")


def _actor(role: str, *, status: str = "active", workspace_id: UUID = WORKSPACE_ID) -> AdminActor:
    return AdminActor(
        user_id=OWNER_ID if role == "owner" else ADMIN_ID,
        workspace_id=workspace_id,
        role=role,
        status=status,
    )


def test_owner_and_admin_can_open_admin_for_same_workspace() -> None:
    owner = admin_access_decision(_actor("owner"), target_workspace_id=WORKSPACE_ID)
    admin = admin_access_decision(_actor("admin"), target_workspace_id=WORKSPACE_ID)

    assert owner.outcome == AdminPermissionOutcome.ALLOWED
    assert owner.allowed is True
    assert admin.outcome == AdminPermissionOutcome.ALLOWED
    assert admin.allowed is True


def test_personal_workspace_is_not_an_admin_team_surface() -> None:
    assert corporate_admin_workspace_decision("corporate").allowed is True
    assert corporate_admin_workspace_decision("personal").outcome == (
        AdminPermissionOutcome.DENIED_PERSONAL_WORKSPACE
    )


def test_member_inactive_cross_workspace_and_missing_audit_are_denied() -> None:
    assert admin_access_decision(_actor("member"), target_workspace_id=WORKSPACE_ID).outcome == AdminPermissionOutcome.DENIED_MEMBER
    assert admin_access_decision(_actor("owner", status="inactive"), target_workspace_id=WORKSPACE_ID).outcome == AdminPermissionOutcome.DENIED_INACTIVE_MEMBERSHIP
    assert admin_access_decision(_actor("owner"), target_workspace_id=OTHER_WORKSPACE_ID).outcome == AdminPermissionOutcome.DENIED_CROSS_WORKSPACE
    assert admin_access_decision(_actor("owner"), target_workspace_id=WORKSPACE_ID, audit_available=False).outcome == AdminPermissionOutcome.DENIED_AUDIT_UNAVAILABLE
    assert admin_access_decision(None, target_workspace_id=WORKSPACE_ID).outcome == AdminPermissionOutcome.DENIED_UNAUTHENTICATED


def test_admin_can_invite_and_manage_members_only() -> None:
    assert invitation_role_decision(_actor("admin"), invited_role="member").allowed is True
    assert invitation_role_decision(_actor("admin"), invited_role="admin").outcome == AdminPermissionOutcome.DENIED_ADMIN_CANNOT_MANAGE_OWNER_ADMIN
    assert membership_mutation_decision(
        _actor("admin"),
        target_role="member",
        target_status="active",
        requested_role="member",
        requested_status="blocked",
        active_owner_count=1,
    ).allowed is True
    assert membership_mutation_decision(
        _actor("admin"),
        target_role="owner",
        target_status="active",
        requested_role="member",
        requested_status="active",
        active_owner_count=2,
    ).outcome == AdminPermissionOutcome.DENIED_ADMIN_CANNOT_MANAGE_OWNER_ADMIN


def test_last_active_owner_cannot_be_downgraded_blocked_revoked_or_removed() -> None:
    for requested_role, requested_status, removes_membership in [
        ("admin", "active", False),
        ("owner", "inactive", False),
        ("owner", "blocked", False),
        ("owner", "revoked", False),
        (None, None, True),
    ]:
        decision = membership_mutation_decision(
            _actor("owner"),
            target_role="owner",
            target_status="active",
            requested_role=requested_role,
            requested_status=requested_status,
            removes_membership=removes_membership,
            active_owner_count=1,
        )
        assert decision.outcome == AdminPermissionOutcome.DENIED_LAST_OWNER


def test_owner_can_manage_owner_admin_member_when_last_owner_safety_holds() -> None:
    decision = membership_mutation_decision(
        _actor("owner"),
        target_role="admin",
        target_status="active",
        requested_role="owner",
        requested_status="active",
        active_owner_count=2,
    )

    assert decision.allowed is True
