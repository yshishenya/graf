from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import (
    AUTH_BOOTSTRAP_WORKSPACE_ID,
    ORG_ID,
    PERSONAL_WORKSPACE_ID,
    USER_ID,
    WORKSPACE_ID,
)
from twobrain_rec_server.admin.invitations import (
    create_matching_join_offers_after_login,
    create_workspace_invitation,
)
from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.auth.workspace_onboarding import (
    activate_workspace_session,
    create_or_reuse_join_offer,
    decide_workspace_join_offer,
    ensure_personal_workspace,
    join_offer_is_actionable,
    list_active_workspaces,
    list_workspace_join_offers,
)
from twobrain_rec_server.db.models import (
    AuthSession,
    Organization,
    UserIdentity,
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


def test_active_linked_membership_can_be_listed_and_activated(client) -> None:
    async def exercise() -> tuple[set[UUID], UUID, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            linked = Workspace(
                organization_id=ORG_ID,
                slug="linked-profile-space",
                name="Пространство из другого профиля",
                kind="linked",
                owner_user_id=USER_ID,
            )
            db.add(linked)
            await db.flush()
            db.add(
                WorkspaceMembership(
                    workspace_id=linked.id,
                    user_id=USER_ID,
                    role="member",
                    status="active",
                )
            )
            current = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=WORKSPACE_ID,
                provider="linked-activation-test",
            )
            await db.commit()

            spaces = await list_active_workspaces(
                db,
                organization_id=ORG_ID,
                current_workspace_id=WORKSPACE_ID,
                internal_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                user_id=USER_ID,
            )
            activated = await activate_workspace_session(
                db,
                organization_id=ORG_ID,
                current_workspace_id=WORKSPACE_ID,
                internal_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                user_id=USER_ID,
                current_session_id=current.id,
                target_workspace_id=linked.id,
            )
            await db.commit()
            source = await db.get(AuthSession, current.id)
            assert source is not None
            return (
                {space.id for space in spaces},
                linked.id,
                activated.workspace.kind,
                source.status,
            )

    visible_workspace_ids, linked_id, activated_kind, source_status = asyncio.run(exercise())

    assert PERSONAL_WORKSPACE_ID in visible_workspace_ids
    assert linked_id in visible_workspace_ids
    assert activated_kind == "linked"
    assert source_status == "replaced"


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


def test_personal_workspace_helper_is_idempotent_and_keeps_one_owner_membership(client) -> None:
    async def exercise() -> tuple[Workspace, int, WorkspaceMembership]:
        async with client.app_state["sessionmaker"]() as db:
            first = await ensure_personal_workspace(
                db, organization_id=ORG_ID, user_id=USER_ID
            )
            membership = await db.get(
                WorkspaceMembership,
                {"workspace_id": first.id, "user_id": USER_ID},
            )
            assert membership is not None
            membership.role = "member"
            await db.flush()
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


def test_personal_workspace_helper_converges_under_concurrent_creation(client) -> None:
    concurrent_user_id = UUID("30000000-0000-0000-0000-000000000088")

    async def exercise() -> tuple[set[UUID], int]:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                UserIdentity(
                    id=concurrent_user_id,
                    organization_id=ORG_ID,
                    external_subject="concurrent-personal-owner",
                )
            )
            await db.commit()

        async def create() -> UUID:
            async with client.app_state["sessionmaker"]() as db:
                workspace = await ensure_personal_workspace(
                    db,
                    organization_id=ORG_ID,
                    user_id=concurrent_user_id,
                )
                await db.commit()
                return workspace.id

        workspace_ids = set(await asyncio.gather(create(), create()))
        async with client.app_state["sessionmaker"]() as db:
            memberships = list(
                await db.scalars(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.user_id == concurrent_user_id,
                        WorkspaceMembership.role == "owner",
                        WorkspaceMembership.status == "active",
                    )
                )
            )
        return workspace_ids, len(memberships)

    workspace_ids, membership_count = asyncio.run(exercise())

    assert len(workspace_ids) == 1
    assert membership_count == 1


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


def test_join_offer_listing_includes_only_actionable_corporate_workspaces(client) -> None:
    other_organization_id = UUID("10000000-0000-0000-0000-000000000099")

    async def exercise() -> tuple[tuple[object, ...], str]:
        async with client.app_state["sessionmaker"]() as db:
            other_organization = Organization(
                id=other_organization_id,
                slug="other-offer-org",
                name="Other Offer Org",
            )
            actionable_workspace = Workspace(
                organization_id=ORG_ID,
                slug="actionable-offer-team",
                name="Доступная команда",
                kind="corporate",
            )
            expired_workspace = Workspace(
                organization_id=ORG_ID,
                slug="expired-listed-offer-team",
                name="Истёкшая команда",
                kind="corporate",
            )
            foreign_workspace = Workspace(
                organization_id=other_organization_id,
                slug="foreign-offer-team",
                name="Чужая команда",
                kind="corporate",
            )
            db.add_all(
                (
                    other_organization,
                    actionable_workspace,
                    expired_workspace,
                    foreign_workspace,
                )
            )
            await db.flush()

            workspace_cases = (
                (actionable_workspace, datetime.now(UTC) + timedelta(days=1)),
                (expired_workspace, datetime.now(UTC) - timedelta(seconds=1)),
                (
                    await db.get(Workspace, PERSONAL_WORKSPACE_ID),
                    datetime.now(UTC) + timedelta(days=1),
                ),
                (
                    await db.get(Workspace, AUTH_BOOTSTRAP_WORKSPACE_ID),
                    datetime.now(UTC) + timedelta(days=1),
                ),
                (foreign_workspace, datetime.now(UTC) + timedelta(days=1)),
            )
            offers: list[WorkspaceJoinOffer] = []
            for index, (workspace, expires_at) in enumerate(workspace_cases):
                assert workspace is not None
                invitation = WorkspaceInvitation(
                    workspace_id=workspace.id,
                    target_contact=f"listed-offer-{index}@example.test",
                    invited_role="member",
                    created_by_user_id=USER_ID,
                    expires_at=expires_at,
                )
                db.add(invitation)
                await db.flush()
                offer = WorkspaceJoinOffer(
                    workspace_id=workspace.id,
                    user_id=USER_ID,
                    invitation_id=invitation.id,
                    workspace_name=workspace.name,
                    invited_role=invitation.invited_role,
                    expires_at=expires_at,
                )
                db.add(offer)
                offers.append(offer)
            await db.flush()

            listed = await list_workspace_join_offers(
                db,
                organization_id=ORG_ID,
                current_workspace_id=WORKSPACE_ID,
                internal_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                user_id=USER_ID,
            )
            await db.flush()
            expired_status = offers[1].status
            await db.commit()
            return listed, expired_status

    listed, expired_status = asyncio.run(exercise())

    assert [offer.workspace_name for offer in listed] == ["Доступная команда"]
    assert expired_status == "expired"


def test_workspace_activation_serializes_competing_replacements(client) -> None:
    async def exercise() -> tuple[list[str], str, int]:
        async with client.app_state["sessionmaker"]() as db:
            current = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=WORKSPACE_ID,
                provider="activation-race-test",
            )
            await db.commit()

        async def activate() -> str:
            async with client.app_state["sessionmaker"]() as db:
                try:
                    await activate_workspace_session(
                        db,
                        organization_id=ORG_ID,
                        current_workspace_id=WORKSPACE_ID,
                        internal_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                        user_id=USER_ID,
                        current_session_id=current.id,
                        target_workspace_id=PERSONAL_WORKSPACE_ID,
                    )
                    await db.commit()
                    return "activated"
                except ProblemDetail as exc:
                    await db.rollback()
                    return exc.code

        results = await asyncio.gather(activate(), activate())
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(AuthSession, current.id)
            assert source is not None
            replacements = list(
                await db.scalars(
                    select(AuthSession).where(
                        AuthSession.user_id == USER_ID,
                        AuthSession.workspace_id == PERSONAL_WORKSPACE_ID,
                        AuthSession.provider == "activation-race-test",
                        AuthSession.status == "active",
                    )
                )
            )
            return results, source.status, len(replacements)

    results, source_status, replacement_count = asyncio.run(exercise())

    assert sorted(results) == ["activated", "auth_session_invalid"]
    assert source_status == "replaced"
    assert replacement_count == 1


def test_stale_membership_cannot_list_or_activate_another_users_personal_workspace(
    client,
) -> None:
    other_user_id = UUID("30000000-0000-0000-0000-000000000089")

    async def exercise() -> tuple[set[UUID], str]:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                UserIdentity(
                    id=other_user_id,
                    organization_id=ORG_ID,
                    external_subject="other-personal-owner",
                )
            )
            await db.flush()
            other_personal = Workspace(
                organization_id=ORG_ID,
                owner_user_id=other_user_id,
                slug="other-users-personal",
                name="Моё пространство",
                kind="personal",
            )
            db.add(other_personal)
            await db.flush()
            db.add_all(
                (
                    WorkspaceMembership(
                        workspace_id=other_personal.id,
                        user_id=other_user_id,
                        role="owner",
                        status="active",
                    ),
                    WorkspaceMembership(
                        workspace_id=other_personal.id,
                        user_id=USER_ID,
                        role="member",
                        status="active",
                    ),
                )
            )
            current = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=WORKSPACE_ID,
                provider="stale-personal-membership-test",
            )
            await db.commit()

            spaces = await list_active_workspaces(
                db,
                organization_id=ORG_ID,
                current_workspace_id=WORKSPACE_ID,
                internal_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                user_id=USER_ID,
            )
            try:
                await activate_workspace_session(
                    db,
                    organization_id=ORG_ID,
                    current_workspace_id=WORKSPACE_ID,
                    internal_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                    user_id=USER_ID,
                    current_session_id=current.id,
                    target_workspace_id=other_personal.id,
                )
            except ProblemDetail as exc:
                activation_code = exc.code
            else:
                activation_code = "activated"
            await db.rollback()
            return {space.id for space in spaces}, activation_code

    visible_workspace_ids, activation_code = asyncio.run(exercise())

    assert activation_code == "workspace_activation_unavailable"
    assert visible_workspace_ids == {WORKSPACE_ID, PERSONAL_WORKSPACE_ID}


def test_join_offer_decision_serializes_opposite_actions_and_replays_winner(client) -> None:
    async def exercise() -> tuple[list[str], str, bool, int]:
        async with client.app_state["sessionmaker"]() as db:
            workspace = Workspace(
                organization_id=ORG_ID,
                slug="decision-race-team",
                name="Команда решения",
                kind="corporate",
            )
            db.add(workspace)
            await db.flush()
            invitation = WorkspaceInvitation(
                workspace_id=workspace.id,
                target_contact="decision-race@example.test",
                invited_role="member",
                created_by_user_id=USER_ID,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
            db.add(invitation)
            await db.flush()
            offer = WorkspaceJoinOffer(
                workspace_id=workspace.id,
                user_id=USER_ID,
                invitation_id=invitation.id,
                workspace_name=workspace.name,
                invited_role=invitation.invited_role,
                expires_at=invitation.expires_at,
            )
            db.add(offer)
            await db.commit()
            offer_id = offer.id
            workspace_id = workspace.id

        async def decide(action: str) -> str:
            async with client.app_state["sessionmaker"]() as db:
                try:
                    decided, _ = await decide_workspace_join_offer(
                        db,
                        organization_id=ORG_ID,
                        current_workspace_id=WORKSPACE_ID,
                        internal_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                        user_id=USER_ID,
                        offer_id=offer_id,
                        action=action,
                    )
                    await db.commit()
                    return decided.status
                except ProblemDetail as exc:
                    await db.rollback()
                    return exc.code

        results = await asyncio.gather(decide("accept"), decide("reject"))
        async with client.app_state["sessionmaker"]() as db:
            terminal_offer = await db.get(WorkspaceJoinOffer, offer_id)
            assert terminal_offer is not None
            replay_action = "accept" if terminal_offer.status == "accepted" else "reject"
            _, idempotent = await decide_workspace_join_offer(
                db,
                organization_id=ORG_ID,
                current_workspace_id=WORKSPACE_ID,
                internal_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                user_id=USER_ID,
                offer_id=offer_id,
                action=replay_action,
            )
            membership = await db.get(
                WorkspaceMembership,
                {"workspace_id": workspace_id, "user_id": USER_ID},
            )
            await db.commit()
            return results, terminal_offer.status, idempotent, int(membership is not None)

    results, terminal_status, replay_idempotent, membership_count = asyncio.run(exercise())

    assert "workspace_join_offer_unavailable" in results
    assert terminal_status in {"accepted", "rejected"}
    assert replay_idempotent is True
    assert membership_count == int(terminal_status == "accepted")


def test_personal_workspace_cannot_be_an_invitation_target(client) -> None:
    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            with pytest.raises(ProblemDetail) as error:
                await create_workspace_invitation(
                    db,
                    context=AdminWorkspaceContext(
                        workspace_id=PERSONAL_WORKSPACE_ID,
                        workspace_name="Моё пространство",
                        actor_user_id=USER_ID,
                        actor_role="owner",
                    ),
                    target_contact="member@example.test",
                    invited_role="member",
                )
            assert error.value.code == "workspace_invitation_unavailable"

    asyncio.run(exercise())


def test_join_offer_helper_is_idempotent_and_active_spaces_exclude_revoked(client) -> None:
    async def exercise() -> tuple[WorkspaceJoinOffer, WorkspaceJoinOffer, tuple[object, ...]]:
        async with client.app_state["sessionmaker"]() as db:
            corporate = Workspace(
                organization_id=ORG_ID,
                slug="offer-helper-team",
                name="Команда для предложения",
                kind="corporate",
            )
            db.add(corporate)
            await db.flush()
            invitation = WorkspaceInvitation(
                workspace_id=corporate.id,
                target_contact="offer-test@example.test",
                invited_role="member",
                created_by_user_id=USER_ID,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
            db.add(invitation)
            await db.flush()
            first = await create_or_reuse_join_offer(
                db,
                workspace_id=corporate.id,
                user_id=USER_ID,
                invitation_id=invitation.id,
                workspace_name=corporate.name,
                invited_role=invitation.invited_role,
                expires_at=invitation.expires_at,
            )
            second = await create_or_reuse_join_offer(
                db,
                workspace_id=corporate.id,
                user_id=USER_ID,
                invitation_id=invitation.id,
                workspace_name=corporate.name,
                invited_role=invitation.invited_role,
                expires_at=invitation.expires_at,
            )
            active_spaces = await list_active_workspaces(
                db,
                organization_id=ORG_ID,
                current_workspace_id=WORKSPACE_ID,
                internal_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                user_id=USER_ID,
            )
            await db.commit()
            return first, second, active_spaces

    first, second, active_spaces = asyncio.run(exercise())

    assert first.id == second.id
    assert first.workspace_id not in {workspace.id for workspace in active_spaces}


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
                bootstrap_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
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
                bootstrap_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
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
                        internal_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
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
