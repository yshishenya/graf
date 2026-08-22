from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, USER_ID
from twobrain_rec_server.auth.account_closure import finalize_account_close
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.auth.workspace_onboarding import ensure_personal_workspace
from twobrain_rec_server.billing.trial import require_trial_activation
from twobrain_rec_server.cabinet.web_routes.settings import _unlink_account_provider
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    AuthAuditEvent,
    AuthSession,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    RegisteredDevice,
    TrialActivation,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope


async def _issue_web_session(
    client,
    *,
    user_id: UUID,
    workspace_id: UUID,
    device_id: UUID,
    provider: str = "email",
) -> tuple[str, UUID]:
    async with client.app_state["sessionmaker"]() as db:
        issued = await issue_auth_session(
            db,
            user_id=user_id,
            workspace_id=workspace_id,
            device_id=device_id,
            provider=provider,
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
    return {
        "X-CSRF-Token": issue_csrf_token(
            session_id=session_id, secret=str(client.app.state.web_csrf_secret)
        )
    }


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

    async def seed_verified_identity() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                ExternalIdentity(
                    user_id=USER_ID,
                    provider="email",
                    provider_subject=f"verified-{USER_ID}",
                    email="verified@example.test",
                    is_verified=True,
                    is_active=True,
                )
            )
            await db.commit()

    asyncio.run(seed_verified_identity())
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
        _issue_web_session(
            client, user_id=USER_ID, workspace_id=other_workspace_id, device_id=other_device_id
        )
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
            return len(
                (
                    await db.scalars(
                        select(TrialActivation).where(TrialActivation.user_id == USER_ID)
                    )
                ).all()
            )

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
    assert '<h2 id="billing-plan-title">Free</h2>' in response.text
    assert "Пробный период активирован" not in response.text


def test_trial_cannot_replace_an_active_paid_subscription(client) -> None:
    workspace_id, device_id = asyncio.run(_seed_personal_workspace(client))

    async def seed_paid_subscription() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                ExternalIdentity(
                    user_id=USER_ID,
                    provider="email",
                    provider_subject=f"paid-trial-guard-{USER_ID}",
                    email="paid-trial-guard@example.test",
                    is_verified=True,
                    is_active=True,
                )
            )
            db.add(
                WorkspaceSubscription(
                    workspace_id=workspace_id,
                    billing_owner_id=USER_ID,
                    state="personal",
                    plan_code="personal",
                    cycle="month",
                    paid_through=datetime.now(UTC) + timedelta(days=30),
                    capacity_bytes=2_000_000_000,
                    recurring_allowed=True,
                    recurring_authority_version=4,
                )
            )
            await db.commit()

    asyncio.run(seed_paid_subscription())
    token, session_id = asyncio.run(
        _issue_web_session(client, user_id=USER_ID, workspace_id=workspace_id, device_id=device_id)
    )
    headers = _bind_web_session(client, token=token, session_id=session_id)
    response = client.post(
        "/billing/trial/activate",
        headers=headers,
        data={"confirmation": "start_trial"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].endswith("trial=unavailable")

    async def load_subscription() -> WorkspaceSubscription:
        async with client.app_state["sessionmaker"]() as db:
            row = await db.scalar(
                select(WorkspaceSubscription).where(
                    WorkspaceSubscription.workspace_id == workspace_id
                )
            )
            assert row is not None
            return row

    unchanged = asyncio.run(load_subscription())
    assert unchanged.plan_code == "personal"
    assert unchanged.state == "personal"
    assert unchanged.recurring_allowed is True
    assert unchanged.capacity_bytes == 2_000_000_000


def test_account_close_owner_cooling_cancel_and_finalization_revoke_access(client) -> None:
    workspace_id, device_id = asyncio.run(_seed_personal_workspace(client))
    token, session_id = asyncio.run(
        _issue_web_session(
            client,
            user_id=USER_ID,
            workspace_id=workspace_id,
            device_id=device_id,
        )
    )
    headers = _bind_web_session(client, token=token, session_id=session_id)

    async def seed_subscription() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                WorkspaceSubscription(
                    workspace_id=workspace_id,
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
                .where(AccountClosureRequest.workspace_id == workspace_id)
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
                    WorkspaceMembership.workspace_id == workspace_id,
                    WorkspaceMembership.user_id == USER_ID,
                )
            )
            subscription = await db.get(WorkspaceSubscription, workspace_id)
            auth_session = await db.get(AuthSession, session_id)
            assert identity is not None and identity.status == "closed"
            assert membership is not None and membership.status == "inactive"
            assert subscription is not None and subscription.plan_code == "free"
            assert subscription.recurring_allowed is False
            assert auth_session is not None and auth_session.status == "revoked"

    asyncio.run(assert_revoked())


def test_account_close_rejects_header_session_even_when_cookie_is_absent(client) -> None:
    workspace_id, device_id = asyncio.run(_seed_personal_workspace(client))
    token, _ = asyncio.run(
        _issue_web_session(client, user_id=USER_ID, workspace_id=workspace_id, device_id=device_id)
    )
    client.cookies.clear()

    response = client.post(
        "/settings/account/close",
        headers={"X-Auth-Session": token},
        data={"confirm_close": "Закрыть аккаунт"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("account_close=reauth_required")

    async def load_request() -> AccountClosureRequest | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(AccountClosureRequest).where(
                    AccountClosureRequest.workspace_id == workspace_id
                )
            )

    assert asyncio.run(load_request()) is None


def test_account_preferences_persist_and_provider_unlink_keeps_recovery_path(client) -> None:
    workspace_id, device_id = asyncio.run(_seed_personal_workspace(client))
    token, session_id = asyncio.run(
        _issue_web_session(client, user_id=USER_ID, workspace_id=workspace_id, device_id=device_id)
    )
    headers = _bind_web_session(client, token=token, session_id=session_id)

    preferences = client.post(
        "/settings/account/preferences",
        headers=headers,
        data={"locale": "en-US", "timezone": "UTC", "theme": "dark"},
        follow_redirects=False,
    )
    assert preferences.status_code == 303
    assert preferences.headers["location"].endswith("/settings/account?preferences=saved")

    identity_ids: list[UUID] = []

    async def seed_identities() -> None:
        async with client.app_state["sessionmaker"]() as db:
            for provider, subject in (("yandex", "prefs-yandex"), ("vk", "prefs-vk")):
                identity = ExternalIdentity(
                    user_id=USER_ID,
                    provider=provider,
                    provider_subject=subject,
                    email=f"{subject}@example.test",
                    is_verified=True,
                    is_active=True,
                )
                db.add(identity)
                await db.flush()
                identity_ids.append(identity.id)
            await db.commit()

    asyncio.run(seed_identities())
    unlinked = client.post(
        f"/settings/account/providers/{identity_ids[0]}/unlink",
        headers=headers,
        follow_redirects=False,
    )
    assert unlinked.status_code == 303
    assert unlinked.headers["location"].endswith("/settings/account?provider_unlink=success")

    blocked = client.post(
        f"/settings/account/providers/{identity_ids[1]}/unlink",
        headers=headers,
        follow_redirects=False,
    )
    assert blocked.status_code == 303
    assert blocked.headers["location"].endswith(
        "/settings/account?provider_unlink=recovery_path_required"
    )

    async def assert_persisted() -> None:
        async with client.app_state["sessionmaker"]() as db:
            user = await db.get(UserIdentity, USER_ID)
            first = await db.get(ExternalIdentity, identity_ids[0])
            second = await db.get(ExternalIdentity, identity_ids[1])
            assert user is not None
            assert (user.locale, user.timezone, user.theme) == ("en-US", "UTC", "dark")
            assert first is not None and first.is_active is False and first.is_verified is False
            assert second is not None and second.is_active is True and second.is_verified is True

    asyncio.run(assert_persisted())


def test_telegram_identity_never_counts_as_the_remaining_recovery_path(client) -> None:
    workspace_id, device_id = asyncio.run(_seed_personal_workspace(client))
    token, session_id = asyncio.run(
        _issue_web_session(client, user_id=USER_ID, workspace_id=workspace_id, device_id=device_id)
    )
    headers = _bind_web_session(client, token=token, session_id=session_id)

    async def seed_identities() -> tuple[UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            email = ExternalIdentity(
                user_id=USER_ID,
                provider="email",
                provider_subject="recovery@example.test",
                email="recovery@example.test",
                is_verified=True,
                is_active=True,
            )
            telegram = ExternalIdentity(
                user_id=USER_ID,
                provider="telegram",
                provider_subject="telegram-only-non-login",
                is_verified=True,
                is_active=True,
            )
            db.add_all([email, telegram])
            await db.commit()
            return email.id, telegram.id

    email_id, telegram_id = asyncio.run(seed_identities())
    blocked = client.post(
        f"/settings/account/providers/{email_id}/unlink",
        headers=headers,
        follow_redirects=False,
    )
    assert blocked.status_code == 303
    assert blocked.headers["location"].endswith(
        "/settings/account?provider_unlink=recovery_path_required"
    )

    unlinked = client.post(
        f"/settings/account/providers/{telegram_id}/unlink",
        headers=headers,
        follow_redirects=False,
    )
    assert unlinked.status_code == 303
    assert unlinked.headers["location"].endswith("provider_unlink=success")


def test_provider_unlink_revokes_provider_sessions_and_recovers_current_login(client) -> None:
    workspace_id, device_id = asyncio.run(_seed_personal_workspace(client))
    current_token, current_session_id = asyncio.run(
        _issue_web_session(
            client,
            user_id=USER_ID,
            workspace_id=workspace_id,
            device_id=device_id,
            provider="yandex",
        )
    )
    stolen_token, stolen_session_id = asyncio.run(
        _issue_web_session(
            client,
            user_id=USER_ID,
            workspace_id=workspace_id,
            device_id=device_id,
            provider="yandex",
        )
    )
    other_provider_token, other_provider_session_id = asyncio.run(
        _issue_web_session(
            client,
            user_id=USER_ID,
            workspace_id=workspace_id,
            device_id=device_id,
            provider="email",
        )
    )
    headers = _bind_web_session(
        client,
        token=current_token,
        session_id=current_session_id,
    )

    async def seed_identities() -> UUID:
        async with client.app_state["sessionmaker"]() as db:
            target = ExternalIdentity(
                user_id=USER_ID,
                provider="yandex",
                provider_subject="unlink-session-yandex",
                is_verified=True,
                is_active=True,
            )
            db.add_all(
                [
                    target,
                    ExternalIdentity(
                        user_id=USER_ID,
                        provider="email",
                        provider_subject="unlink-session-recovery@example.test",
                        email="unlink-session-recovery@example.test",
                        is_verified=True,
                        is_active=True,
                    ),
                ]
            )
            await db.commit()
            return target.id

    identity_id = asyncio.run(seed_identities())
    response = client.post(
        f"/settings/account/providers/{identity_id}/unlink",
        headers=headers,
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith(
        "/login?next=/settings/account&error=auth_session_invalid"
    )
    assert AUTH_SESSION_COOKIE_NAME in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]

    client.cookies.clear()
    stolen = client.get(
        "/settings/account",
        headers={"X-Auth-Session": stolen_token},
        follow_redirects=False,
    )
    assert stolen.status_code == 303
    assert "error=auth_session_invalid" in stolen.headers["location"]

    other_provider = client.get(
        "/settings/account",
        headers={"X-Auth-Session": other_provider_token},
        follow_redirects=False,
    )
    assert other_provider.status_code == 200

    async def assert_revoked() -> None:
        async with client.app_state["sessionmaker"]() as db:
            sessions = {
                session.id: session
                for session in await db.scalars(
                    select(AuthSession).where(
                        AuthSession.id.in_(
                            [current_session_id, stolen_session_id, other_provider_session_id]
                        )
                    )
                )
            }
            bindings = {
                binding.auth_session_id: binding
                for binding in await db.scalars(
                    select(AuthSessionDeviceBinding).where(
                        AuthSessionDeviceBinding.auth_session_id.in_(sessions)
                    )
                )
            }
            identity = await db.get(ExternalIdentity, identity_id)
            audit = await db.scalar(
                select(AuthAuditEvent)
                .where(AuthAuditEvent.event_type == "provider_unlinked")
                .order_by(AuthAuditEvent.created_at.desc())
            )
            assert sessions[current_session_id].status == "revoked"
            assert sessions[stolen_session_id].status == "revoked"
            assert sessions[other_provider_session_id].status == "active"
            for session_id in (current_session_id, stolen_session_id):
                assert bindings[session_id].device_state == "blocked"
                assert bindings[session_id].revocation_reason == "provider_unlinked"
            assert bindings[other_provider_session_id].device_state == "trusted"
            assert identity is not None and identity.is_active is False
            assert audit is not None
            assert audit.metadata_json == {"revoked_session_count": 2, "provider": "yandex"}

    asyncio.run(assert_revoked())


def test_provider_unlink_revokes_sessions_across_authorized_workspaces(client) -> None:
    current_workspace_id, current_device_id = asyncio.run(_seed_personal_workspace(client))
    other_workspace_id = uuid4()
    other_device_id = uuid4()
    identity_id = uuid4()

    async def seed_other_workspace_and_identities() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    Workspace(
                        id=other_workspace_id,
                        organization_id=ORG_ID,
                        owner_user_id=USER_ID,
                        slug=f"unlink-cross-{other_workspace_id.hex[:12]}",
                        name="Unlink cross-workspace",
                        kind="linked",
                    ),
                    ExternalIdentity(
                        id=identity_id,
                        user_id=USER_ID,
                        provider="yandex",
                        provider_subject="unlink-cross-workspace-yandex",
                        is_verified=True,
                        is_active=True,
                    ),
                    ExternalIdentity(
                        user_id=USER_ID,
                        provider="email",
                        provider_subject="unlink-cross-workspace-recovery@example.test",
                        email="unlink-cross-workspace-recovery@example.test",
                        is_verified=True,
                        is_active=True,
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=other_workspace_id,
                        user_id=USER_ID,
                        role="owner",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=other_device_id,
                        workspace_id=other_workspace_id,
                        user_id=USER_ID,
                        device_public_id=f"unlink-cross-{other_device_id}",
                        platform="web",
                        client_version="test",
                        status="active",
                        registration_state="approved",
                        trusted_by=USER_ID,
                    ),
                ]
            )
            await db.commit()

    asyncio.run(seed_other_workspace_and_identities())
    _, current_session_id = asyncio.run(
        _issue_web_session(
            client,
            user_id=USER_ID,
            workspace_id=current_workspace_id,
            device_id=current_device_id,
            provider="yandex",
        )
    )
    _, other_session_id = asyncio.run(
        _issue_web_session(
            client,
            user_id=USER_ID,
            workspace_id=other_workspace_id,
            device_id=other_device_id,
            provider="yandex",
        )
    )
    _, preserved_session_id = asyncio.run(
        _issue_web_session(
            client,
            user_id=USER_ID,
            workspace_id=other_workspace_id,
            device_id=other_device_id,
            provider="email",
        )
    )
    principal = AuthenticatedPrincipal(
        user_id=USER_ID,
        organization_id=ORG_ID,
        workspace_ids=frozenset({current_workspace_id, other_workspace_id}),
        subject=str(USER_ID),
        session_id=current_session_id,
        auth_via_session=True,
        session_workspace_id=current_workspace_id,
        session_device_id=current_device_id,
    )
    tenant_scope = TenantScope(
        organization_id=ORG_ID,
        workspace_id=current_workspace_id,
        user_id=USER_ID,
        device_id=current_device_id,
        auth_session_id=current_session_id,
    )

    async def unlink_and_assert_context_restored() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await apply_tenant_scope(db, tenant_scope)
            current_revoked = await _unlink_account_provider(
                db,
                identity_id=identity_id,
                principal=principal,
                tenant_scope=tenant_scope,
                internal_workspace_id=client.app.state.settings.web_login_workspace_id,
            )
            assert current_revoked is True
            assert db.info["tenant_context"]["app.context_kind"] == "request"
            assert db.info["tenant_context"]["app.workspace_id"] == str(current_workspace_id)

    asyncio.run(unlink_and_assert_context_restored())

    async def assert_cross_workspace_result() -> None:
        async with client.app_state["sessionmaker"]() as db:
            current = await db.get(AuthSession, current_session_id)
            other = await db.get(AuthSession, other_session_id)
            preserved = await db.get(AuthSession, preserved_session_id)
            other_binding = await db.scalar(
                select(AuthSessionDeviceBinding).where(
                    AuthSessionDeviceBinding.auth_session_id == other_session_id
                )
            )
            assert current is not None and current.status == "revoked"
            assert other is not None and other.status == "revoked"
            assert preserved is not None and preserved.status == "active"
            assert other_binding is not None and other_binding.device_state == "blocked"
            assert other_binding.revocation_reason == "provider_unlinked"

    asyncio.run(assert_cross_workspace_result())


def test_provider_unlink_rejects_header_session_without_mutating_identity(client) -> None:
    workspace_id, device_id = asyncio.run(_seed_personal_workspace(client))
    token, _ = asyncio.run(
        _issue_web_session(client, user_id=USER_ID, workspace_id=workspace_id, device_id=device_id)
    )
    identity_id = uuid4()

    async def seed_identity() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                ExternalIdentity(
                    id=identity_id,
                    user_id=USER_ID,
                    provider="yandex",
                    provider_subject="header-only-unlink",
                    email="header-only-unlink@example.test",
                    is_verified=True,
                    is_active=True,
                )
            )
            await db.commit()

    asyncio.run(seed_identity())
    client.cookies.clear()
    response = client.post(
        f"/settings/account/providers/{identity_id}/unlink",
        headers={"X-Auth-Session": token},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("provider_unlink=reauth_required")

    async def assert_unchanged() -> None:
        async with client.app_state["sessionmaker"]() as db:
            identity = await db.get(ExternalIdentity, identity_id)
            assert (
                identity is not None and identity.is_active is True and identity.is_verified is True
            )

    asyncio.run(assert_unchanged())


def test_account_security_bulk_actions_revoke_only_other_sessions_and_devices(client) -> None:
    workspace_id, current_device_id = asyncio.run(_seed_personal_workspace(client))
    current_token, current_session_id = asyncio.run(
        _issue_web_session(
            client,
            user_id=USER_ID,
            workspace_id=workspace_id,
            device_id=current_device_id,
        )
    )
    other_device_id = uuid4()
    far_device_id = uuid4()

    async def seed_devices() -> None:
        async with client.app_state["sessionmaker"]() as db:
            for device_id, label in ((other_device_id, "other"), (far_device_id, "far")):
                db.add(
                    RegisteredDevice(
                        id=device_id,
                        workspace_id=workspace_id,
                        user_id=USER_ID,
                        device_public_id=f"bulk-{label}-{device_id}",
                        platform="web",
                        client_version="test",
                        status="active",
                        registration_state="approved",
                        trusted_by=USER_ID,
                    )
                )
            await db.commit()

    asyncio.run(seed_devices())
    _, other_session_id = asyncio.run(
        _issue_web_session(
            client,
            user_id=USER_ID,
            workspace_id=workspace_id,
            device_id=other_device_id,
        )
    )
    _, far_session_id = asyncio.run(
        _issue_web_session(
            client,
            user_id=USER_ID,
            workspace_id=workspace_id,
            device_id=far_device_id,
        )
    )
    headers = _bind_web_session(client, token=current_token, session_id=current_session_id)

    client.cookies.clear()
    header_only = client.post(
        "/settings/account/sessions/revoke-others",
        headers={"X-Auth-Session": current_token},
        follow_redirects=False,
    )
    assert header_only.status_code == 303
    assert header_only.headers["location"].endswith("session=reauth_required")

    headers = _bind_web_session(client, token=current_token, session_id=current_session_id)

    sessions_response = client.post(
        "/settings/account/sessions/revoke-others",
        headers=headers,
        follow_redirects=False,
    )
    assert sessions_response.status_code == 303
    assert sessions_response.headers["location"].endswith("session=others_revoked")

    async def assert_other_sessions_revoked() -> None:
        async with client.app_state["sessionmaker"]() as db:
            current = await db.get(AuthSession, current_session_id)
            other = await db.get(AuthSession, other_session_id)
            far = await db.get(AuthSession, far_session_id)
            audit = await db.scalar(
                select(AuthAuditEvent)
                .where(
                    AuthAuditEvent.workspace_id == workspace_id,
                    AuthAuditEvent.event_type == "auth_sessions_revoked",
                )
                .order_by(AuthAuditEvent.created_at.desc())
            )
            assert current is not None and current.status == "active"
            assert other is not None and other.status == "revoked"
            assert far is not None and far.status == "revoked"
            assert audit is not None and audit.metadata_json["scope"] == "other_sessions"

    asyncio.run(assert_other_sessions_revoked())

    devices_response = client.post(
        "/settings/account/devices/revoke-others",
        headers=headers,
        follow_redirects=False,
    )
    assert devices_response.status_code == 303
    assert devices_response.headers["location"].endswith("device_revoke=others_revoked")

    async def assert_other_devices_revoked() -> None:
        async with client.app_state["sessionmaker"]() as db:
            current_device = await db.get(RegisteredDevice, current_device_id)
            other_device = await db.get(RegisteredDevice, other_device_id)
            far_device = await db.get(RegisteredDevice, far_device_id)
            current = await db.get(AuthSession, current_session_id)
            other_binding = await db.scalar(
                select(AuthSessionDeviceBinding).where(
                    AuthSessionDeviceBinding.auth_session_id == other_session_id
                )
            )
            far_binding = await db.scalar(
                select(AuthSessionDeviceBinding).where(
                    AuthSessionDeviceBinding.auth_session_id == far_session_id
                )
            )
            audit = await db.scalar(
                select(AuthAuditEvent)
                .where(
                    AuthAuditEvent.workspace_id == workspace_id,
                    AuthAuditEvent.event_type == "auth_devices_revoked",
                )
                .order_by(AuthAuditEvent.created_at.desc())
            )
            assert current_device is not None and current_device.status == "active"
            assert other_device is not None and other_device.status == "revoked"
            assert far_device is not None and far_device.status == "revoked"
            assert current is not None and current.status == "active"
            assert other_binding is not None and other_binding.device_state == "blocked"
            assert far_binding is not None and far_binding.device_state == "blocked"
            assert audit is not None and audit.metadata_json["scope"] == "other_devices"

    asyncio.run(assert_other_devices_revoked())


def test_trial_verification_gate_rejects_unverified_identity() -> None:
    with pytest.raises(PermissionError):
        require_trial_activation(
            identity_status="pending",
            membership_role="owner",
            workspace_kind="personal",
            already_used=False,
        )
