from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.admin.invitations import create_matching_join_offers_after_login
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.workspace_onboarding import (
    can_transition_join_offer,
    create_or_reuse_join_offer,
    decide_workspace_join_offer,
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
from twobrain_rec_server.db.tenant_context import (
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
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
        workspace_name="Команда",
        invited_role="member",
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
        workspace_name="Команда",
        invited_role="member",
        status="offered",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    assert not join_offer_is_actionable(offer)


def test_join_offer_helper_is_idempotent_and_active_spaces_exclude_revoked(client) -> None:
    async def exercise() -> tuple[WorkspaceJoinOffer, WorkspaceJoinOffer, tuple[object, ...]]:
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
                workspace_name=personal.name,
                invited_role=invitation.invited_role,
                expires_at=invitation.expires_at,
            )
            second = await create_or_reuse_join_offer(
                db,
                workspace_id=personal.id,
                user_id=USER_ID,
                invitation_id=invitation.id,
                workspace_name=personal.name,
                invited_role=invitation.invited_role,
                expires_at=invitation.expires_at,
            )
            active_spaces = await list_active_workspaces(
                db,
                organization_id=ORG_ID,
                current_workspace_id=WORKSPACE_ID,
                user_id=USER_ID,
            )
            await db.commit()
            return first, second, active_spaces

    first, second, active_spaces = asyncio.run(exercise())

    assert first.id == second.id
    assert {workspace.id for workspace in active_spaces} >= {first.workspace_id}


def test_matching_invitations_create_distinct_offers_without_membership_and_replay_is_safe(client) -> None:
    async def exercise() -> tuple[tuple[WorkspaceJoinOffer, ...], tuple[WorkspaceJoinOffer, ...], int]:
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                WorkspaceAuthContext(
                    workspace_id=WORKSPACE_ID,
                    organization_id=ORG_ID,
                    user_id=USER_ID,
                    context_kind="auth_bootstrap",
                ),
            )
            first_workspace = Workspace(
                organization_id=ORG_ID,
                slug="offer-team-one",
                name="Команда один",
                kind="corporate",
            )
            second_workspace = Workspace(
                organization_id=ORG_ID,
                slug="offer-team-two",
                name="Команда два",
                kind="corporate",
            )
            db.add_all((first_workspace, second_workspace))
            await db.flush()
            db.add_all(
                (
                    WorkspaceInvitation(
                        workspace_id=first_workspace.id,
                        target_contact="member@example.test",
                        invited_role="member",
                        created_by_user_id=USER_ID,
                        expires_at=datetime.now(UTC) + timedelta(days=1),
                    ),
                    WorkspaceInvitation(
                        workspace_id=second_workspace.id,
                        target_contact="member@example.test",
                        invited_role="admin",
                        created_by_user_id=USER_ID,
                        expires_at=datetime.now(UTC) + timedelta(days=1),
                    ),
                )
            )
            await db.flush()
            first = await create_matching_join_offers_after_login(
                db,
                organization_id=ORG_ID,
                bootstrap_workspace_id=WORKSPACE_ID,
                user_id=USER_ID,
                provider="yandex",
                provider_subject="unrelated-subject",
                provider_username=None,
                email="member@example.test",
                phone=None,
            )
            second = await create_matching_join_offers_after_login(
                db,
                organization_id=ORG_ID,
                bootstrap_workspace_id=WORKSPACE_ID,
                user_id=USER_ID,
                provider="yandex",
                provider_subject="unrelated-subject",
                provider_username=None,
                email="member@example.test",
                phone=None,
            )
            memberships = list(
                await db.scalars(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.user_id == USER_ID,
                        WorkspaceMembership.workspace_id.in_((first_workspace.id, second_workspace.id)),
                    )
                )
            )
            await db.commit()
            return first, second, len(memberships)

    first, second, membership_count = asyncio.run(exercise())

    assert len(first) == 2
    assert {offer.id for offer in first} == {offer.id for offer in second}
    assert membership_count == 0


def test_expired_or_revoked_offer_never_creates_membership(client) -> None:
    async def exercise() -> tuple[str, str, int]:
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_context(
                db,
                WorkspaceAuthContext(
                    workspace_id=WORKSPACE_ID,
                    organization_id=ORG_ID,
                    user_id=USER_ID,
                    context_kind="auth_bootstrap",
                ),
            )
            expired_workspace = Workspace(
                organization_id=ORG_ID,
                slug="expired-offer-team",
                name="Истекшая команда",
                kind="corporate",
            )
            revoked_workspace = Workspace(
                organization_id=ORG_ID,
                slug="revoked-offer-team",
                name="Отозванная команда",
                kind="corporate",
            )
            db.add_all((expired_workspace, revoked_workspace))
            await db.flush()
            expired_invitation = WorkspaceInvitation(
                workspace_id=expired_workspace.id,
                target_contact="member@example.test",
                invited_role="member",
                created_by_user_id=USER_ID,
                expires_at=datetime.now(UTC) - timedelta(seconds=1),
            )
            revoked_invitation = WorkspaceInvitation(
                workspace_id=revoked_workspace.id,
                target_contact="member@example.test",
                invited_role="member",
                status="revoked",
                created_by_user_id=USER_ID,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
            db.add_all((expired_invitation, revoked_invitation))
            await db.flush()
            expired_offer = await create_or_reuse_join_offer(
                db,
                workspace_id=expired_workspace.id,
                user_id=USER_ID,
                invitation_id=expired_invitation.id,
                workspace_name=expired_workspace.name,
                invited_role=expired_invitation.invited_role,
                expires_at=expired_invitation.expires_at,
            )
            revoked_offer = await create_or_reuse_join_offer(
                db,
                workspace_id=revoked_workspace.id,
                user_id=USER_ID,
                invitation_id=revoked_invitation.id,
                workspace_name=revoked_workspace.name,
                invited_role=revoked_invitation.invited_role,
                expires_at=revoked_invitation.expires_at,
            )
            await db.commit()

            for offer in (expired_offer, revoked_offer):
                with pytest.raises(ProblemDetail) as error:
                    await decide_workspace_join_offer(
                        db,
                        organization_id=ORG_ID,
                        current_workspace_id=WORKSPACE_ID,
                        user_id=USER_ID,
                        offer_id=offer.id,
                        action="accept",
                    )
                assert error.value.code == "workspace_join_offer_unavailable"
                await db.commit()

            await apply_tenant_context(
                db,
                TenantDatabaseContext(
                    organization_id=ORG_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                ),
            )
            expired = await db.get(WorkspaceJoinOffer, expired_offer.id)
            revoked = await db.get(WorkspaceJoinOffer, revoked_offer.id)
            memberships = list(
                await db.scalars(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.user_id == USER_ID,
                        WorkspaceMembership.workspace_id.in_(
                            (expired_workspace.id, revoked_workspace.id)
                        ),
                    )
                )
            )
            assert expired is not None
            assert revoked is not None
            return expired.status, revoked.status, len(memberships)

    expired_status, revoked_status, membership_count = asyncio.run(exercise())

    assert expired_status == "expired"
    assert revoked_status == "revoked"
    assert membership_count == 0
