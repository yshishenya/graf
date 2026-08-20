from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, USER_ID
from tests.fakes.fake_minio import FakeMinioStorage
from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.admin.users import update_workspace_membership
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.account_closure import (
    account_close_content_workspace_ids,
    begin_account_close_finalization,
    cancel_account_close,
    finalize_account_close,
    schedule_account_close,
)
from twobrain_rec_server.auth.workspace_onboarding import ensure_personal_workspace
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    AuthSession,
    Meeting,
    MeetingDeletionRequest,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.deletion.service import fanout_account_close_deletions

pytestmark = pytest.mark.skipif(
    not os.getenv("TWOBRAIN_DATABASE_URL"),
    reason="account-close DB lifecycle tests require TWOBRAIN_DATABASE_URL",
)


def test_account_close_rejects_linked_workspace_even_for_sole_owner() -> None:
    workspace_id = uuid4()
    user_id = uuid4()
    linked = Workspace(
        id=workspace_id,
        organization_id=uuid4(),
        slug="linked-close-denied",
        name="Пространство из другого профиля",
        kind="linked",
        owner_user_id=user_id,
    )
    membership = WorkspaceMembership(
        workspace_id=workspace_id,
        user_id=user_id,
        role="owner",
        status="active",
    )

    class FakeDb:
        def __init__(self) -> None:
            self.values = iter((linked, membership, 1, None, None))

        async def scalar(self, _statement):
            return next(self.values)

        def add(self, _row) -> None:
            return None

        async def flush(self) -> None:
            return None

    with (
        patch("twobrain_rec_server.auth.account_closure.lock_storage_workspace", AsyncMock()),
        pytest.raises(ProblemDetail) as error,
    ):
        asyncio.run(
            schedule_account_close(
                FakeDb(),
                workspace_id=workspace_id,
                user_id=user_id,
                now=datetime(2026, 8, 7, 10, tzinfo=UTC),
            )
        )

    assert error.value.code == "account_close_owner_required"


def test_account_close_schedules_idempotently_disables_renewal_and_can_cancel(client) -> None:
    async def exercise() -> tuple[object, object, WorkspaceSubscription | None]:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
            subscription = WorkspaceSubscription(
                workspace_id=personal.id,
                billing_owner_id=USER_ID,
                state="active",
                plan_code="personal",
                cycle="monthly",
                recurring_allowed=True,
            )
            db.add(subscription)
            await db.flush()
            now = datetime(2026, 8, 7, 10, tzinfo=UTC)
            first = await schedule_account_close(
                db,
                workspace_id=personal.id,
                user_id=USER_ID,
                now=now,
                request_key="close-1",
            )
            second = await schedule_account_close(
                db,
                workspace_id=personal.id,
                user_id=USER_ID,
                now=now + timedelta(minutes=1),
                request_key="close-2",
            )
            assert first.finalize_at == second.finalize_at
            assert subscription.recurring_allowed is False
            canceled = await cancel_account_close(
                db,
                workspace_id=personal.id,
                user_id=USER_ID,
                now=now + timedelta(days=1),
            )
            await db.commit()
            return first, canceled, subscription

    first, canceled, subscription = asyncio.run(exercise())
    assert first.state == "scheduled"
    assert canceled.state == "canceled"
    assert subscription.recurring_allowed is False


def test_account_close_requires_sole_active_member(client) -> None:
    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
            other_user = UserIdentity(
                id=uuid4(), organization_id=ORG_ID, external_subject="account-close-member"
            )
            db.add(other_user)
            await db.flush()
            db.add(
                WorkspaceMembership(
                    workspace_id=personal.id,
                    user_id=other_user.id,
                    role="member",
                    status="active",
                )
            )
            await db.flush()
            with pytest.raises(ProblemDetail) as error:
                await schedule_account_close(
                    db,
                    workspace_id=personal.id,
                    user_id=USER_ID,
                    now=datetime.now(UTC),
                )
            assert error.value.code == "account_close_transfer_required"
            await db.rollback()

    asyncio.run(exercise())


def test_account_close_requires_owned_linked_workspaces_to_be_sole_member(client) -> None:
    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
            other_user = UserIdentity(
                id=uuid4(), organization_id=ORG_ID, external_subject=f"linked-member-{uuid4()}"
            )
            linked = Workspace(
                id=uuid4(),
                organization_id=ORG_ID,
                slug=f"linked-close-member-{uuid4()}",
                name="Сохранённое пространство",
                kind="linked",
                owner_user_id=USER_ID,
            )
            db.add_all((other_user, linked))
            await db.flush()
            db.add_all(
                (
                    WorkspaceMembership(
                        workspace_id=linked.id,
                        user_id=USER_ID,
                        role="owner",
                        status="active",
                    ),
                    WorkspaceMembership(
                        workspace_id=linked.id,
                        user_id=other_user.id,
                        role="member",
                        status="active",
                    ),
                )
            )
            await db.flush()

            with pytest.raises(ProblemDetail) as error:
                await schedule_account_close(
                    db,
                    workspace_id=personal.id,
                    user_id=USER_ID,
                    now=datetime.now(UTC),
                )

            assert error.value.code == "account_close_transfer_required"
            assert await db.scalar(select(AccountClosureRequest.id)) is None
            await db.rollback()

    asyncio.run(exercise())


def test_account_close_requires_transfer_of_other_owned_workspace(client) -> None:
    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
            corporate = Workspace(
                id=uuid4(),
                organization_id=ORG_ID,
                slug=f"owned-corporate-{uuid4()}",
                name="Командное пространство",
                kind="corporate",
                owner_user_id=USER_ID,
            )
            db.add(corporate)
            await db.flush()
            db.add(
                WorkspaceMembership(
                    workspace_id=corporate.id,
                    user_id=USER_ID,
                    role="owner",
                    status="active",
                )
            )
            await db.flush()

            with pytest.raises(ProblemDetail) as error:
                await schedule_account_close(
                    db,
                    workspace_id=personal.id,
                    user_id=USER_ID,
                    now=datetime.now(UTC),
                )

            assert error.value.code == "account_close_transfer_required"
            assert await db.scalar(select(AccountClosureRequest.id)) is None
            await db.rollback()

    asyncio.run(exercise())


def test_account_close_content_scope_rechecks_linked_members_before_fanout(client) -> None:
    async def exercise() -> None:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
            other_user = UserIdentity(
                id=uuid4(), organization_id=ORG_ID, external_subject=f"late-linked-member-{uuid4()}"
            )
            linked = Workspace(
                id=uuid4(),
                organization_id=ORG_ID,
                slug=f"linked-close-late-member-{uuid4()}",
                name="Сохранённое пространство",
                kind="linked",
                owner_user_id=USER_ID,
            )
            db.add_all((other_user, linked))
            await db.flush()
            db.add(
                WorkspaceMembership(
                    workspace_id=linked.id,
                    user_id=USER_ID,
                    role="owner",
                    status="active",
                )
            )
            await db.flush()
            await schedule_account_close(
                db,
                workspace_id=personal.id,
                user_id=USER_ID,
                now=datetime.now(UTC),
            )
            db.add(
                WorkspaceMembership(
                    workspace_id=linked.id,
                    user_id=other_user.id,
                    role="member",
                    status="active",
                )
            )
            await db.flush()

            with pytest.raises(ProblemDetail) as error:
                await account_close_content_workspace_ids(
                    db,
                    primary_workspace_id=personal.id,
                    user_id=USER_ID,
                )

            assert error.value.code == "account_close_transfer_required"
            request = await db.scalar(select(AccountClosureRequest))
            assert request is not None
            with pytest.raises(ProblemDetail) as finalize_error:
                await finalize_account_close(
                    db,
                    request_id=request.id,
                    now=datetime.now(UTC) + timedelta(days=8),
                )
            assert finalize_error.value.code == "account_close_transfer_required"
            await db.refresh(request)
            await db.refresh(linked)
            assert request.state == "scheduled"
            memberships = list(
                await db.scalars(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.workspace_id == linked.id,
                    )
                )
            )
            assert {membership.status for membership in memberships} == {"active"}
            await db.rollback()

    asyncio.run(exercise())


def test_account_close_finalization_revokes_access_and_paid_entitlement(client) -> None:
    async def exercise() -> tuple[
        object,
        WorkspaceSubscription,
        AuthSession,
        RegisteredDevice,
        WorkspaceMembership,
        tuple[object, ...],
        UUID,
        UUID,
    ]:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
            linked_id = uuid4()
            linked = Workspace(
                id=linked_id,
                organization_id=ORG_ID,
                slug=f"linked-close-{uuid4()}",
                name="Сохранённое пространство",
                kind="linked",
                owner_user_id=USER_ID,
            )
            linked_membership = WorkspaceMembership(
                workspace_id=linked_id,
                user_id=USER_ID,
                role="owner",
                status="active",
            )
            subscription = WorkspaceSubscription(
                workspace_id=personal.id,
                billing_owner_id=USER_ID,
                state="active",
                plan_code="personal",
                cycle="monthly",
                capacity_bytes=2_000_000_000,
                recurring_allowed=True,
            )
            session = AuthSession(
                user_id=USER_ID,
                workspace_id=personal.id,
                provider="email",
                session_token_hash="account-close-session",
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
            device = RegisteredDevice(
                workspace_id=personal.id,
                user_id=USER_ID,
                device_public_id="account-close-device",
                platform="web",
            )
            db.add_all((linked, linked_membership, subscription, session, device))
            await db.flush()
            content_workspace_ids = await account_close_content_workspace_ids(
                db,
                primary_workspace_id=personal.id,
                user_id=USER_ID,
            )
            now = datetime(2026, 8, 7, 10, tzinfo=UTC)
            await schedule_account_close(
                db,
                workspace_id=personal.id,
                user_id=USER_ID,
                now=now,
            )
            request = await db.scalar(select(AccountClosureRequest))
            assert request is not None
            result = await finalize_account_close(
                db,
                request_id=request.id,
                now=now + timedelta(days=7, seconds=1),
            )
            await db.commit()
            await db.refresh(linked_membership)
            return (
                result,
                subscription,
                session,
                device,
                linked_membership,
                content_workspace_ids,
                personal.id,
                linked.id,
            )

    (
        result,
        subscription,
        session,
        device,
        linked_membership,
        content_workspace_ids,
        personal_id,
        linked_id,
    ) = asyncio.run(exercise())
    assert result.state == "completed"
    assert subscription.plan_code == "free"
    assert subscription.recurring_allowed is False
    assert session.status == "revoked"
    assert device.status == "revoked"
    assert linked_membership.status == "inactive"
    assert content_workspace_ids == tuple(sorted((personal_id, linked_id), key=str))


def test_account_close_finalization_freezes_scope_before_fanout_commit(client) -> None:
    async def exercise() -> tuple[str, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
            corporate_owner = UserIdentity(
                id=uuid4(), organization_id=ORG_ID, external_subject=f"corp-owner-{uuid4()}"
            )
            corporate = Workspace(
                id=uuid4(),
                organization_id=ORG_ID,
                slug=f"account-close-corporate-{uuid4()}",
                name="Командное пространство",
                kind="corporate",
                owner_user_id=corporate_owner.id,
            )
            corporate_membership = WorkspaceMembership(
                workspace_id=corporate.id,
                user_id=USER_ID,
                role="member",
                status="active",
            )
            device = RegisteredDevice(
                workspace_id=personal.id,
                user_id=USER_ID,
                device_public_id=f"account-close-race-{uuid4()}",
            )
            db.add_all((corporate_owner, corporate, corporate_membership, device))
            await db.flush()
            db.add(
                Meeting(
                    workspace_id=personal.id,
                    created_by_user_id=USER_ID,
                    device_id=device.id,
                    local_recording_id=f"account-close-race-{uuid4()}",
                    duration_seconds=1,
                    status="ready",
                )
            )
            now = datetime(2026, 8, 7, 10, tzinfo=UTC)
            await schedule_account_close(
                db,
                workspace_id=personal.id,
                user_id=USER_ID,
                now=now,
            )
            request = await db.scalar(select(AccountClosureRequest))
            assert request is not None
            request_id = request.id
            personal_id = personal.id
            corporate_id = corporate.id
            await db.commit()

        async with client.app_state["sessionmaker"]() as db:
            view, workspace_ids = await begin_account_close_finalization(
                db,
                request_id=request_id,
                now=now + timedelta(days=8),
            )
            assert view.state == "finalizing"
            assert workspace_ids == (personal_id,)
            await db.commit()
            await fanout_account_close_deletions(
                db,
                workspace_id=personal_id,
                storage=FakeMinioStorage(),
            )

        async with client.app_state["sessionmaker"]() as db:
            identity = await db.get(UserIdentity, USER_ID)
            assert identity is not None
            assert identity.status == "closed"
            with pytest.raises(ProblemDetail) as error:
                await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
            assert error.value.code == "account_close_finalizing"
            await db.rollback()

        async with client.app_state["sessionmaker"]() as db:
            result = await finalize_account_close(
                db,
                request_id=request_id,
                now=now + timedelta(days=8),
            )
            await db.commit()
            membership = await db.get(
                WorkspaceMembership,
                {"workspace_id": corporate_id, "user_id": USER_ID},
            )
            request = await db.get(AccountClosureRequest, request_id)
            assert membership is not None
            assert request is not None
            assert membership.status == "inactive"
            assert request.state == "completed"

        async with client.app_state["sessionmaker"]() as db:
            with pytest.raises(ProblemDetail) as error:
                await update_workspace_membership(
                    db,
                    context=AdminWorkspaceContext(
                        workspace_id=corporate_id,
                        workspace_name="Командное пространство",
                        actor_user_id=corporate_owner.id,
                        actor_role="owner",
                    ),
                    target_user_id=USER_ID,
                    requested_role=None,
                    requested_status="active",
                    reason_code="account_close_race",
                )
            assert error.value.code == "account_membership_activation_unavailable"
            await db.rollback()
            membership = await db.get(
                WorkspaceMembership,
                {"workspace_id": corporate_id, "user_id": USER_ID},
            )
            request = await db.get(AccountClosureRequest, request_id)
            assert membership is not None
            assert request is not None
            return result.state, membership.status, request.state

    result_state, membership_status, request_state = asyncio.run(exercise())
    assert result_state == "completed"
    assert membership_status == "inactive"
    assert request_state == "completed"


def test_account_close_deletion_fanout_fails_closed_without_storage() -> None:
    class UnusedDb:
        async def scalars(self, *_args, **_kwargs):
            return (uuid4(),)

    async def exercise() -> None:
        with pytest.raises(ProblemDetail) as error:
            await fanout_account_close_deletions(
                UnusedDb(),
                workspace_id=uuid4(),
                storage=object(),
            )
        assert error.value.code == "deletion_storage_unavailable"

    asyncio.run(exercise())


def test_account_close_deletion_fanout_reuses_meeting_purge_path(client) -> None:
    async def exercise() -> tuple[object, str, str, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
            device = RegisteredDevice(
                workspace_id=personal.id,
                user_id=USER_ID,
                device_public_id=f"account-close-fanout-{uuid4()}",
            )
            db.add(device)
            await db.flush()
            meeting = Meeting(
                workspace_id=personal.id,
                created_by_user_id=USER_ID,
                device_id=device.id,
                local_recording_id=f"account-close-meeting-{uuid4()}",
                duration_seconds=1,
                status="ready",
            )
            db.add(meeting)
            await db.flush()
            accepted = await fanout_account_close_deletions(
                db,
                workspace_id=personal.id,
                storage=FakeMinioStorage(),
            )
            request = await db.scalar(
                select(MeetingDeletionRequest).where(
                    MeetingDeletionRequest.meeting_id == meeting.id
                )
            )
            assert request is not None
            await db.commit()
            return (
                accepted,
                meeting.deletion_state,
                meeting.deleted_at.isoformat(),
                request.request_source,
                request.reason_code,
            )

    accepted, deletion_state, deleted_at, request_source, reason_code = asyncio.run(exercise())
    assert len(accepted) == 1
    assert deletion_state == "active_purge_complete"
    assert deleted_at
    assert request_source == "account_close"
    assert reason_code == "account_close"
