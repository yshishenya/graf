from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, USER_ID
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
    RegisteredDevice,
    UserIdentity,
    WorkspaceMembership,
    WorkspaceSubscription,
)

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
