from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, USER_ID
from tests.fakes.fake_minio import FakeMinioStorage
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.account_closure import (
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
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.deletion.service import fanout_account_close_deletions

pytestmark = pytest.mark.skipif(
    not os.getenv("TWOBRAIN_DATABASE_URL"),
    reason="account-close DB lifecycle tests require TWOBRAIN_DATABASE_URL",
)


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
    async def exercise() -> tuple[object, WorkspaceSubscription, AuthSession, RegisteredDevice]:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
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
            db.add_all((subscription, session, device))
            await db.flush()
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
            return result, subscription, session, device

    result, subscription, session, device = asyncio.run(exercise())
    assert result.state == "completed"
    assert subscription.plan_code == "free"
    assert subscription.recurring_allowed is False
    assert session.status == "revoked"
    assert device.status == "revoked"


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
