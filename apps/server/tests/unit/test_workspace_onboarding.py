from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, USER_ID
from twobrain_rec_server.auth.workspace_onboarding import (
    can_transition_join_offer,
    create_or_reuse_join_offer,
    ensure_personal_workspace,
    join_offer_is_actionable,
    list_active_workspaces,
)
from twobrain_rec_server.db.models import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceJoinOffer,
    WorkspaceMembership,
)


def test_personal_workspace_carries_its_owner_marker() -> None:
    owner_id = uuid4()

    workspace = Workspace(
        organization_id=uuid4(),
        slug="personal-owner",
        name="Личное пространство",
        kind="personal",
        owner_user_id=owner_id,
    )

    assert workspace.kind == "personal"
    assert workspace.owner_user_id == owner_id


def test_join_offer_is_bound_to_one_user_and_invitation() -> None:
    now = datetime.now(UTC)
    offer = WorkspaceJoinOffer(
        workspace_id=uuid4(),
        user_id=uuid4(),
        invitation_id=uuid4(),
        status="offered",
        expires_at=now + timedelta(days=1),
    )

    assert offer.status == "offered"
    assert offer.expires_at > now


def test_join_offer_transition_is_terminal_after_acceptance_or_rejection() -> None:
    assert can_transition_join_offer("offered", "accepted")
    assert can_transition_join_offer("offered", "rejected")
    assert not can_transition_join_offer("accepted", "offered")
    assert not can_transition_join_offer("rejected", "accepted")


def test_personal_workspace_helper_is_idempotent_and_keeps_one_owner_membership(client) -> None:
    async def exercise() -> tuple[Workspace, int, WorkspaceMembership]:
        async with client.app_state["sessionmaker"]() as db:
            first = await ensure_personal_workspace(
                db, organization_id=ORG_ID, user_id=USER_ID
            )
            second = await ensure_personal_workspace(
                db, organization_id=ORG_ID, user_id=USER_ID
            )
            memberships = list(
                await db.scalars(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.workspace_id == first.id,
                        WorkspaceMembership.user_id == USER_ID,
                    )
                )
            )
            await db.commit()
            return first, int(first.id == second.id), memberships[0]

    workspace, same_workspace, membership = asyncio.run(exercise())

    assert workspace.kind == "personal"
    assert same_workspace == 1
    assert membership.role == "owner"
    assert membership.status == "active"


def test_join_offer_is_not_actionable_after_expiry() -> None:
    offer = WorkspaceJoinOffer(
        workspace_id=uuid4(),
        user_id=uuid4(),
        invitation_id=uuid4(),
        status="offered",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    assert not join_offer_is_actionable(offer)


def test_join_offer_helper_is_idempotent_and_active_spaces_exclude_revoked(client) -> None:
    async def exercise() -> tuple[WorkspaceJoinOffer, WorkspaceJoinOffer, list[Workspace]]:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(
                db, organization_id=ORG_ID, user_id=USER_ID
            )
            invitation = WorkspaceInvitation(
                workspace_id=personal.id,
                target_contact="offer-test@example.test",
                invited_role="member",
                created_by_user_id=USER_ID,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
            db.add(invitation)
            await db.flush()
            first = await create_or_reuse_join_offer(
                db,
                workspace_id=personal.id,
                user_id=USER_ID,
                invitation_id=invitation.id,
                expires_at=invitation.expires_at,
            )
            second = await create_or_reuse_join_offer(
                db,
                workspace_id=personal.id,
                user_id=USER_ID,
                invitation_id=invitation.id,
                expires_at=invitation.expires_at,
            )
            active_spaces = await list_active_workspaces(db, user_id=USER_ID)
            await db.commit()
            return first, second, active_spaces

    first, second, active_spaces = asyncio.run(exercise())

    assert first.id == second.id
    assert {workspace.id for workspace in active_spaces} >= {first.workspace_id}
