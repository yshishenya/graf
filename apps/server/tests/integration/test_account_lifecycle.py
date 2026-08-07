from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.auth.account_closure import finalize_account_close
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.auth.workspace_onboarding import ensure_personal_workspace
from twobrain_rec_server.billing.trial import require_trial_activation
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    AuthSession,
    AuthSessionDeviceBinding,
    RegisteredDevice,
    TrialActivation,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)


async def _issue_web_session(client, *, user_id: UUID, workspace_id: UUID, device_id: UUID) -> tuple[str, UUID]:
    async with client.app_state["sessionmaker"]() as db:
        issued = await issue_auth_session(
            db,
            user_id=user_id,
            workspace_id=workspace_id,
            device_id=device_id,
            provider="email",
        )
        db.add(
            AuthSessionDeviceBinding(
                auth_session_id=issued.id,
                registered_device_id=device_id,
                device_state="trusted",
            )
        )
        await db.commit()
        return issued.token, issued.id


def _bind_web_session(client, *, token: str, session_id: UUID) -> dict[str, str]:
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, token)
    return {"X-CSRF-Token": issue_csrf_token(session_id=session_id, secret=str(client.app.state.web_csrf_secret))}


async def _seed_personal_workspace(client) -> tuple[UUID, UUID]:
    device_id = uuid4()
    async with client.app_state["sessionmaker"]() as db:
        workspace = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
        db.add(
            RegisteredDevice(
                id=device_id,
                workspace_id=workspace.id,
                user_id=USER_ID,
                device_public_id=f"trial-device-{device_id}",
                platform="web",
                client_version="test",
                status="active",
                registration_state="approved",
                trusted_by=USER_ID,
            )
        )
        await db.commit()
        return workspace.id, device_id


def test_trial_requires_explicit_confirmation_and_is_one_per_identity(client) -> None:
    workspace_id, device_id = asyncio.run(_seed_personal_workspace(client))
    token, session_id = asyncio.run(
        _issue_web_session(client, user_id=USER_ID, workspace_id=workspace_id, device_id=device_id)
    )
    headers = _bind_web_session(client, token=token, session_id=session_id)

    missing_confirmation = client.post(
        "/billing/trial/activate", headers=headers, follow_redirects=False
    )
    assert missing_confirmation.status_code == 303
    assert missing_confirmation.headers["location"].endswith("trial=confirmation_required")

    activated = client.post(
        "/billing/trial/activate",
        headers=headers,
        data={"confirmation": "start_trial"},
        follow_redirects=False,
    )
    assert activated.status_code == 303
    assert activated.headers["location"].endswith("trial=activated")

    # A second workspace context for the same identity cannot consume a second
    # trial, even if the workspace itself is not eligible for trial activation.
    other_workspace_id = uuid4()
    other_device_id = uuid4()

    async def seed_other_workspace() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                Workspace(
                    id=other_workspace_id,
                    organization_id=ORG_ID,
                    owner_user_id=USER_ID,
                    kind="corporate",
                    slug=f"trial-corporate-{other_workspace_id.hex[:12]}",
                    name="Trial corporate context",
                )
            )
            db.add(
                WorkspaceMembership(
                    workspace_id=other_workspace_id,
                    user_id=USER_ID,
                    role="owner",
                    status="active",
                )
            )
            await db.flush()
            db.add(
                RegisteredDevice(
                    id=other_device_id,
                    workspace_id=other_workspace_id,
                    user_id=USER_ID,
                    device_public_id=f"trial-device-{other_device_id}",
                    platform="web",
                    client_version="test",
                    status="active",
                    registration_state="approved",
                    trusted_by=USER_ID,
                )
            )
            await db.commit()

    asyncio.run(seed_other_workspace())
    token, session_id = asyncio.run(
        _issue_web_session(client, user_id=USER_ID, workspace_id=other_workspace_id, device_id=other_device_id)
    )
    headers = _bind_web_session(client, token=token, session_id=session_id)
    already_used = client.post(
        "/billing/trial/activate",
        headers=headers,
        data={"confirmation": "start_trial"},
        follow_redirects=False,
    )
    assert already_used.status_code == 303
    assert already_used.headers["location"].endswith("trial=already")

    async def count_trials() -> int:
        async with client.app_state["sessionmaker"]() as db:
            return len((await db.scalars(select(TrialActivation).where(TrialActivation.user_id == USER_ID))).all())

    assert asyncio.run(count_trials()) == 1


def test_trial_expiry_projects_free_without_grace_period(client) -> None:
    workspace_id, device_id = asyncio.run(_seed_personal_workspace(client))
    token, session_id = asyncio.run(
        _issue_web_session(client, user_id=USER_ID, workspace_id=workspace_id, device_id=device_id)
    )
    _bind_web_session(client, token=token, session_id=session_id)

    async def expire_trial() -> None:
        async with client.app_state["sessionmaker"]() as db:
            ended_at = datetime.now(UTC) - timedelta(seconds=1)
            db.add(
                TrialActivation(
                    user_id=USER_ID,
                    workspace_id=workspace_id,
                    starts_at=ended_at - timedelta(days=7),
                    ends_at=ended_at,
                    policy_version="trial-v1",
                )
            )
            db.add(
                WorkspaceSubscription(
                    workspace_id=workspace_id,
                    billing_owner_id=USER_ID,
                    state="trial",
                    plan_code="trial",
                    capacity_bytes=500_000_000,
                    trial_ends_at=ended_at,
                )
            )
            await db.commit()

    asyncio.run(expire_trial())
    response = client.get("/billing")
    assert response.status_code == 200
    assert "<h2 id=\"billing-plan-title\">Free</h2>" in response.text
    assert "Пробный период активирован" not in response.text


def test_account_close_owner_cooling_cancel_and_finalization_revoke_access(client) -> None:
    token, session_id = asyncio.run(
        _issue_web_session(client, user_id=USER_ID, workspace_id=WORKSPACE_ID, device_id=DEVICE_ID)
    )
    headers = _bind_web_session(client, token=token, session_id=session_id)

    async def seed_subscription() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                WorkspaceSubscription(
                    workspace_id=WORKSPACE_ID,
                    billing_owner_id=USER_ID,
                    state="personal",
                    plan_code="personal",
                    cycle="month",
                    capacity_bytes=2_000_000_000,
                    recurring_allowed=True,
                    recurring_authority_version=3,
                )
            )
            await db.commit()

    asyncio.run(seed_subscription())
    scheduled = client.post(
        "/settings/account/close",
        headers=headers,
        data={"confirm_close": "Закрыть аккаунт"},
        follow_redirects=False,
    )
    assert scheduled.status_code == 303
    assert scheduled.headers["location"].endswith("account_close=scheduled")

    async def load_request() -> AccountClosureRequest:
        async with client.app_state["sessionmaker"]() as db:
            row = await db.scalar(
                select(AccountClosureRequest)
                .where(AccountClosureRequest.workspace_id == WORKSPACE_ID)
                .order_by(AccountClosureRequest.requested_at.desc())
            )
            assert row is not None
            return row

    request = asyncio.run(load_request())
    assert request.state == "scheduled"

    canceled = client.post(
        "/settings/account/close/cancel", headers=headers, follow_redirects=False
    )
    assert canceled.status_code == 303
    assert canceled.headers["location"].endswith("account_close=canceled")

    scheduled_again = client.post(
        "/settings/account/close",
        headers=headers,
        data={"confirm_close": "Закрыть аккаунт"},
        follow_redirects=False,
    )
    assert scheduled_again.status_code == 303
    request = asyncio.run(load_request())

    async def finalize_due() -> None:
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(AccountClosureRequest, request.id, with_for_update=True)
            assert row is not None
            row.finalize_at = datetime.now(UTC) - timedelta(seconds=1)
            await finalize_account_close(db, request_id=request.id, now=datetime.now(UTC))
            await db.commit()

    asyncio.run(finalize_due())

    async def assert_revoked() -> None:
        async with client.app_state["sessionmaker"]() as db:
            identity = await db.get(UserIdentity, USER_ID)
            membership = await db.scalar(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == WORKSPACE_ID,
                    WorkspaceMembership.user_id == USER_ID,
                )
            )
            subscription = await db.get(WorkspaceSubscription, WORKSPACE_ID)
            auth_session = await db.get(AuthSession, session_id)
            assert identity is not None and identity.status == "closed"
            assert membership is not None and membership.status == "inactive"
            assert subscription is not None and subscription.plan_code == "free"
            assert subscription.recurring_allowed is False
            assert auth_session is not None and auth_session.status == "revoked"

    asyncio.run(assert_revoked())


def test_trial_verification_gate_rejects_unverified_identity() -> None:
    with pytest.raises(PermissionError):
        require_trial_activation(
            identity_status="pending",
            membership_role="owner",
            workspace_kind="personal",
            already_used=False,
        )
