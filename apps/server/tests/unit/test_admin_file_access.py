from __future__ import annotations

from uuid import UUID

from twobrain_rec_server.admin.files import AdminFileAccessOutcome, admin_file_access_decision

WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000001")
OTHER_WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000016")


def test_admin_file_access_allows_same_workspace_owner_or_admin() -> None:
    owner = admin_file_access_decision(
        actor_role="owner",
        actor_workspace_id=WORKSPACE_ID,
        meeting_workspace_id=WORKSPACE_ID,
    )
    admin = admin_file_access_decision(
        actor_role="admin",
        actor_workspace_id=WORKSPACE_ID,
        meeting_workspace_id=WORKSPACE_ID,
    )

    assert owner.outcome == AdminFileAccessOutcome.ALLOWED
    assert admin.outcome == AdminFileAccessOutcome.ALLOWED


def test_admin_file_access_denies_cross_workspace_and_member() -> None:
    assert (
        admin_file_access_decision(
            actor_role="admin",
            actor_workspace_id=WORKSPACE_ID,
            meeting_workspace_id=OTHER_WORKSPACE_ID,
        ).outcome
        == AdminFileAccessOutcome.DENIED_CROSS_WORKSPACE
    )
    assert (
        admin_file_access_decision(
            actor_role="member",
            actor_workspace_id=WORKSPACE_ID,
            meeting_workspace_id=WORKSPACE_ID,
        ).outcome
        == AdminFileAccessOutcome.DENIED_NOT_ADMIN
    )


def test_admin_file_access_reports_truthful_unavailable_states() -> None:
    assert (
        admin_file_access_decision(
            actor_role="admin",
            actor_workspace_id=WORKSPACE_ID,
            meeting_workspace_id=WORKSPACE_ID,
            artifact_available=False,
        ).outcome
        == AdminFileAccessOutcome.UNAVAILABLE_MISSING_ARTIFACT
    )
    assert (
        admin_file_access_decision(
            actor_role="admin",
            actor_workspace_id=WORKSPACE_ID,
            meeting_workspace_id=WORKSPACE_ID,
            deletion_active=True,
        ).outcome
        == AdminFileAccessOutcome.UNAVAILABLE_DELETION_ACTIVE
    )
    assert (
        admin_file_access_decision(
            actor_role="admin",
            actor_workspace_id=WORKSPACE_ID,
            meeting_workspace_id=WORKSPACE_ID,
            retention_or_lifecycle_block=True,
        ).outcome
        == AdminFileAccessOutcome.UNAVAILABLE_RETENTION_OR_LIFECYCLE_BLOCK
    )
    assert (
        admin_file_access_decision(
            actor_role="admin",
            actor_workspace_id=WORKSPACE_ID,
            meeting_workspace_id=WORKSPACE_ID,
            post_egress_limit=True,
        ).outcome
        == AdminFileAccessOutcome.UNAVAILABLE_POST_EGRESS_LIMIT
    )
