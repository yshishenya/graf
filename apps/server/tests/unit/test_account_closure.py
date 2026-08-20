from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, USER_ID
from tests.fakes.fake_minio import FakeMinioStorage
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.account_closure import (
    account_close_content_workspace_ids,
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


def test_account_close_finalization_revokes_access_and_paid_entitlement(client) -> None:
    async def exercise() -> tuple[
        object,
        WorkspaceSubscription,
        AuthSession,
        RegisteredDevice,
        WorkspaceMembership,
        tuple[object, ...],
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
            )

    result, subscription, session, device, linked_membership, content_workspace_ids = asyncio.run(
        exercise()
    )
    assert result.state == "completed"
    assert subscription.plan_code == "free"
    assert subscription.recurring_allowed is False
    assert session.status == "revoked"
    assert device.status == "revoked"
    assert linked_membership.status == "inactive"
    assert len(content_workspace_ids) == 2


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
                select(MeetingDeletionRequest).where(MeetingDeletionRequest.meeting_id == meeting.id)
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
