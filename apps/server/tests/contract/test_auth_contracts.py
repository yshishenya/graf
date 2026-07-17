import hashlib
import hmac
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fakes.auth_providers import fake_provider_map
from twobrain_rec_server.api.auth import router as auth_api_router
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.policy import requires_explicit_corporate_enrollment
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.auth.workspace_onboarding import ensure_personal_workspace
from twobrain_rec_server.db.models import (
    AuthAuditEvent,
    AuthCallbackState,
    AuthSession,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceAuthPolicy,
    WorkspaceConsentCopy,
    WorkspaceInvitation,
    WorkspaceJoinOffer,
    WorkspaceMembership,
    WorkspaceProviderLinkState,
)


class FakeProviderHttpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def post_form(
        self,
        url: str,
        data: dict[str, str],
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        _ = headers
        self.calls.append(("POST", url, data))
        if "id.vk.ru/oauth2/auth" in url:
            if data["code"] != "VALID-VK-CODE":
                return {"error": "invalid_grant"}
            return {
                "access_token": "verified-vk-token",
                "user_id": "VK-USER-42",
                "state": data["state"],
                "scope": "email phone",
            }
        if "id.vk.ru/oauth2/user_info" in url:
            assert data["access_token"] == "verified-vk-token"
            return {
                "user": {
                    "user_id": "VK-USER-42",
                    "first_name": "Verified",
                    "last_name": "VK",
                    "email": "verified-vk@example.ru",
                    "phone": "+79990001111",
                }
            }
        if data["code"] != "VALID-YANDEX-CODE":
            return {"error": "invalid_grant"}
        return {"access_token": "verified-yandex-token", "token_type": "bearer"}

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("GET", url, params or {}))
        if "oauth.vk.com/access_token" in url:
            assert params is not None
            if params.get("code") != "VALID-VK-CODE":
                return {"error": "invalid_grant"}
            return {"access_token": "verified-vk-token", "user_id": "VK-USER-42", "email": "verified-vk@example.ru"}
        if "api.vk.com/method/users.get" in url:
            assert params is not None
            assert params["access_token"] == "verified-vk-token"
            return {
                "response": [
                    {
                        "id": 42,
                        "screen_name": "verified_vk",
                        "first_name": "Verified",
                        "last_name": "VK",
                    }
                ]
            }
        if "login.yandex.ru/info" in url:
            assert headers == {"Authorization": "OAuth verified-yandex-token"}
            return {
                "id": "YANDEX-USER-42",
                "login": "verified-user",
                "client_id": "twobrain-yandex-client-id",
                "default_email": "verified@example.ru",
                "display_name": "Verified User",
            }
        raise AssertionError(f"unexpected provider URL: {url}")


def test_authenticated_auth_mutation_routes_require_web_csrf_dependency() -> None:
    expected_paths = {
        "/api/v1/auth/policy",
        "/api/v1/auth/link",
        "/api/v1/auth/providers/{provider}/link/start",
        "/api/v1/auth/provider-links/{link_state_id}/confirm",
        "/api/v1/auth/devices/register",
        "/api/v1/auth/devices/{device_id}/revoke",
    }
    route_dependencies = {}
    for route in auth_api_router.routes:
        if not isinstance(route, APIRoute) or not (route.methods or set()) & {"POST", "PUT", "PATCH", "DELETE"}:
            continue
        route_dependencies[route.path] = {
            getattr(dependency.call, "__name__", "")
            for dependency in route.dependant.dependencies
            if dependency.call is not None
        }

    missing = sorted(path for path in expected_paths if "require_web_csrf" not in route_dependencies.get(path, set()))
    assert missing == []


def _write_secret_file(client: TestClient, tmp_path, provider: str, value: str) -> None:
    path = tmp_path / f"{provider}-secret.txt"
    path.write_text(value, encoding="utf-8")
    setattr(client.app.state.settings, f"{provider}_client_secret_file", path)


def _telegram_hash(payload: dict[str, str], bot_token: str) -> str:
    data_check_string = "\n".join(f"{key}={payload[key]}" for key in sorted(payload))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()


def auth_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": str(ORG_ID),
        "X-Workspace-Id": str(WORKSPACE_ID),
        "X-User-Id": str(USER_ID),
        "X-Device-Id": str(DEVICE_ID),
    }


def _set_provider_self_enrollment(client: TestClient, enabled: bool) -> None:
    async def update_policy() -> None:
        async with client.app_state["sessionmaker"]() as db:
            policy = await db.scalar(
                select(WorkspaceAuthPolicy).where(WorkspaceAuthPolicy.workspace_id == WORKSPACE_ID)
            )
            if policy is None:
                policy = WorkspaceAuthPolicy(workspace_id=WORKSPACE_ID)
                db.add(policy)
            policy.allow_provider_self_enrollment = enabled
            await db.commit()

    import asyncio

    asyncio.run(update_policy())


def _patch_fake_providers(monkeypatch, client: TestClient, *, allow_self_enrollment: bool = True) -> None:
    provider_map = fake_provider_map()
    monkeypatch.setattr("twobrain_rec_server.api.auth.build_provider_registry", lambda: provider_map)
    monkeypatch.setattr("twobrain_rec_server.auth.callbacks.get_provider_adapter", lambda provider: provider_map[provider])
    monkeypatch.setattr("twobrain_rec_server.api.auth.get_provider_adapter", lambda provider: provider_map[provider])
    # keep compatibility with direct import of provider resolver
    monkeypatch.setattr("twobrain_rec_server.auth.providers.get_provider_adapter", lambda provider: provider_map[provider])
    _set_provider_self_enrollment(client, allow_self_enrollment)


def _load_auth_audit_events(client: TestClient) -> list[AuthAuditEvent]:
    async def load() -> list[AuthAuditEvent]:
        async with client.app_state["sessionmaker"]() as db:
            return list(
                (await db.scalars(select(AuthAuditEvent).order_by(AuthAuditEvent.created_at))).all()
            )

    import asyncio

    return asyncio.run(load())


def test_auth_audit_metadata_hashes_sensitive_values(client: TestClient) -> None:
    async def write_event() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            event = await write_auth_audit_event(
                db,
                workspace_id=WORKSPACE_ID,
                event_type="provider_callback_failed",
                provider="yandex",
                outcome="failure",
                metadata={
                    "error_code": "callback_parse_error",
                    "state_nonce": "state-secret",
                    "code": "provider-code-secret",
                    "device_public_id": "device-public-secret",
                },
            )
            await db.commit()
            await db.refresh(event)
            return event.metadata_json

    import asyncio

    metadata = asyncio.run(write_event())
    assert metadata["error_code"] == "callback_parse_error"
    assert "state_nonce" not in metadata
    assert "code" not in metadata
    assert "device_public_id" not in metadata
    assert len(metadata["state_nonce_sha256"]) == 64
    assert len(metadata["code_sha256"]) == 64
    assert len(metadata["device_public_id_sha256"]) == 64


def test_auth_provider_list_reflects_workspace_policy(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)

    response = client.get(f"/api/v1/auth/providers?workspace_id={WORKSPACE_ID}")
    assert response.status_code == 200
    assert response.json()["consent"]["language"] == "ru"
    assert response.json()["consent"]["version"] == "v1"
    assert "OAuth" in response.json()["consent"]["content_markdown"]
    providers = response.json()["providers"]
    assert {entry["provider"] for entry in providers} >= {"yandex", "vk", "telegram"}
    assert providers[0]["provider"] == "yandex" or providers[1]["provider"] == "yandex"

    patch = client.patch(
        "/api/v1/auth/policy",
        params={"workspace_id": str(WORKSPACE_ID)},
        headers=auth_headers(),
        json={"allow_vk": False},
    )
    assert patch.status_code == 200
    policy_providers = patch.json()["providers"]
    policy_vk_entries = [entry for entry in policy_providers if entry["provider"] == "vk"]
    assert len(policy_vk_entries) == 1
    assert policy_vk_entries[0]["enabled"] is False

    response = client.get(f"/api/v1/auth/providers?workspace_id={WORKSPACE_ID}")
    assert response.status_code == 200
    providers = response.json()["providers"]
    assert "vk" not in {entry["provider"] for entry in providers}

    events = _load_auth_audit_events(client)
    policy_events = [event for event in events if event.event_type == "workspace_auth_policy_updated"]
    assert len(policy_events) == 1
    assert policy_events[0].metadata_json["changed_fields"] == ["allow_vk"]


def test_auth_policy_read_endpoints_do_not_create_rows(client: TestClient) -> None:
    async def count_policy_rows() -> tuple[int, int]:
        async with client.app_state["sessionmaker"]() as db:
            policies = (
                await db.scalars(
                    select(WorkspaceAuthPolicy).where(WorkspaceAuthPolicy.workspace_id == WORKSPACE_ID)
                )
            ).all()
            consent = (
                await db.scalars(
                    select(WorkspaceConsentCopy).where(WorkspaceConsentCopy.workspace_id == WORKSPACE_ID)
                )
            ).all()
            return len(policies), len(consent)

    import asyncio

    assert asyncio.run(count_policy_rows()) == (0, 0)

    providers = client.get(f"/api/v1/auth/providers?workspace_id={WORKSPACE_ID}")
    assert providers.status_code == 200
    assert providers.json()["consent"]["language"] == "ru"

    policy = client.get(
        "/api/v1/auth/policy",
        params={"workspace_id": str(WORKSPACE_ID)},
        headers=auth_headers(),
    )
    assert policy.status_code == 200
    assert policy.json()["consent"]["language"] == "ru"

    assert asyncio.run(count_policy_rows()) == (0, 0)


def test_auth_callback_returns_session_and_me_shapes_primary_link(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200
    start_payload = start.json()
    state_nonce = start_payload["state_nonce"]

    async def load_consent_count() -> int:
        async with client.app_state["sessionmaker"]() as db:
            rows = (
                await db.scalars(
                    select(WorkspaceConsentCopy).where(
                        WorkspaceConsentCopy.workspace_id == WORKSPACE_ID,
                        WorkspaceConsentCopy.language == "ru",
                        WorkspaceConsentCopy.version == "v1",
                    )
                )
            ).all()
            return len(rows)

    import asyncio

    assert asyncio.run(load_consent_count()) == 1

    callback = client.get(
        "/api/v1/auth/callback/yandex",
        params={
            "state": state_nonce,
            "code": "TEST-YA-USER",
        },
    )
    assert callback.status_code == 200
    callback_payload = callback.json()
    assert callback_payload["provider"] == "yandex"
    assert callback_payload["provider_subject"] == "test-ya-user"
    assert callback_payload["session_token"]
    set_cookie = callback.headers["set-cookie"]
    assert f"{AUTH_SESSION_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Domain=" not in set_cookie

    events = _load_auth_audit_events(client)
    assert [event.event_type for event in events] == [
        "provider_auth_started",
        "provider_callback_success",
    ]
    assert events[1].outcome == "success"
    assert "state_nonce" not in events[1].metadata_json
    assert events[1].metadata_json["state_nonce_sha256"]
    assert len(events[1].metadata_json["state_nonce_sha256"]) == 64

    me = client.get(
        "/api/v1/auth/me",
        headers={
            "X-Workspace-Id": callback_payload["workspace_id"],
            "Authorization": f"Bearer {callback_payload['session_token']}",
        },
    )
    assert me.status_code == 200
    me_payload = me.json()
    assert me_payload["active_session_id"] == callback_payload["active_session_id"]
    assert me_payload["policy"]["workspace_id"] == callback_payload["workspace_id"]
    providers = me_payload["linked_providers"]
    assert len(providers) == 1
    assert providers[0]["provider"] == "yandex"
    assert providers[0]["provider_subject"] == "test-ya-user"
    assert providers[0]["is_primary"] is True
    assert providers[0]["confirmed_at"] is not None

    reused = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": state_nonce, "code": "TEST-YA-USER"},
    )
    assert reused.status_code == 400
    assert reused.json()["code"] == "callback_state_reused"

    events = _load_auth_audit_events(client)
    failures = [event for event in events if event.event_type == "provider_callback_failed"]
    assert len(failures) == 1
    assert failures[0].outcome == "failure"
    assert failures[0].metadata_json["error_code"] == "callback_state_reused"
    assert "state_nonce" not in failures[0].metadata_json
    assert len(failures[0].metadata_json["state_nonce_sha256"]) == 64


def test_provider_link_start_requires_session_csrf_and_creates_bound_state(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)
    started = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    callback = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": started.json()["state_nonce"], "code": "TEST-YA-USER"},
    )
    assert callback.status_code == 200
    session_id = UUID(callback.json()["active_session_id"])
    user_id = UUID(callback.json()["user_id"])
    csrf = issue_csrf_token(session_id=session_id, secret=client.app.state.web_csrf_secret)

    response = client.post(
        "/api/v1/auth/providers/vk/link/start",
        params={"workspace_id": callback.json()["workspace_id"]},
        headers={
            "Authorization": f"Bearer {callback.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "vk"
    assert payload["authorization_url"]
    assert "state_nonce" not in payload

    async def load() -> tuple[WorkspaceProviderLinkState, AuthCallbackState]:
        async with client.app_state["sessionmaker"]() as db:
            link = await db.get(WorkspaceProviderLinkState, UUID(payload["link_state_id"]))
            assert link is not None
            state = await db.get(AuthCallbackState, link.callback_state_id)
            assert state is not None
            return link, state

    import asyncio

    link, state = asyncio.run(load())
    assert link.initiating_auth_session_id == session_id
    assert link.initiating_user_id == user_id
    assert link.candidate_provider == "vk"
    assert link.candidate_identity_subject is None
    assert state.result == "pending"


def test_provider_link_start_rechecks_disabled_provider_without_creating_intent(
    monkeypatch, client: TestClient
) -> None:
    _patch_fake_providers(monkeypatch, client)
    started = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    login = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": started.json()["state_nonce"], "code": "TEST-YA-USER"},
    )
    assert login.status_code == 200
    login_workspace_id = UUID(login.json()["workspace_id"])
    session_id = UUID(login.json()["active_session_id"])
    csrf = issue_csrf_token(session_id=session_id, secret=client.app.state.web_csrf_secret)

    async def disable_vk_and_count_intents() -> int:
        async with client.app_state["sessionmaker"]() as db:
            policy = await db.scalar(
                select(WorkspaceAuthPolicy).where(WorkspaceAuthPolicy.workspace_id == login_workspace_id)
            )
            if policy is None:
                policy = WorkspaceAuthPolicy(workspace_id=login_workspace_id)
                db.add(policy)
            policy.allow_vk = False
            await db.commit()
            return len(list(await db.scalars(select(WorkspaceProviderLinkState))))

    import asyncio

    assert asyncio.run(disable_vk_and_count_intents()) == 0
    response = client.post(
        "/api/v1/auth/providers/vk/link/start",
        params={"workspace_id": login.json()["workspace_id"]},
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "provider_disabled"

    async def count_intents() -> int:
        async with client.app_state["sessionmaker"]() as db:
            return len(list(await db.scalars(select(WorkspaceProviderLinkState))))

    assert asyncio.run(count_intents()) == 0


def test_provider_link_callback_stores_candidate_without_changing_login_session(
    monkeypatch, client: TestClient
) -> None:
    _patch_fake_providers(monkeypatch, client)
    started = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    login = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": started.json()["state_nonce"], "code": "TEST-YA-USER"},
    )
    assert login.status_code == 200
    login_workspace_id = UUID(login.json()["workspace_id"])
    session_id = UUID(login.json()["active_session_id"])
    csrf = issue_csrf_token(session_id=session_id, secret=client.app.state.web_csrf_secret)

    link_start = client.post(
        "/api/v1/auth/providers/vk/link/start",
        params={"workspace_id": login.json()["workspace_id"]},
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    assert link_start.status_code == 200
    link_id = UUID(link_start.json()["link_state_id"])
    provider_state = parse_qs(urlparse(link_start.json()["authorization_url"]).query)["state"][0]

    callback = client.get(
        "/api/v1/auth/callback/vk",
        params={"state": provider_state, "code": "vk:linked-user"},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert callback.headers["location"] == f"/settings/provider-links/{link_id}?result=callback_verified"
    assert AUTH_SESSION_COOKIE_NAME not in callback.headers.get("set-cookie", "")

    async def load() -> tuple[WorkspaceProviderLinkState, list[AuthSession], ExternalIdentity | None]:
        async with client.app_state["sessionmaker"]() as db:
            link = await db.get(WorkspaceProviderLinkState, link_id)
            assert link is not None
            sessions = list(
                (
                    await db.scalars(
                        select(AuthSession).where(AuthSession.workspace_id == login_workspace_id)
                    )
                ).all()
            )
            linked_identity = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.provider == "vk",
                    ExternalIdentity.provider_subject == "vk:linked-user",
                )
            )
            return link, sessions, linked_identity

    import asyncio

    link, sessions, linked_identity = asyncio.run(load())
    assert link.status == "callback_verified"
    assert link.callback_verified_at is not None
    assert link.candidate_identity_subject == "vk:linked-user"
    assert link.candidate_provider == "vk"
    assert linked_identity is None
    assert [session.id for session in sessions] == [session_id]

    client.cookies.set(AUTH_SESSION_COOKIE_NAME, login.json()["session_token"])
    missing_csrf = client.post(
        f"/api/v1/auth/provider-links/{link_id}/confirm",
    )
    assert missing_csrf.status_code == 403

    confirmed = client.post(
        f"/api/v1/auth/provider-links/{link_id}/confirm",
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
        json={
            "candidate_provider": "yandex",
            "candidate_provider_subject": "forged-provider-subject",
            "candidate_email": "forged@example.test",
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json() == {"provider": "vk", "status": "confirmed", "idempotent": False}

    async def load_confirmed() -> tuple[WorkspaceProviderLinkState, ExternalIdentity, list[AuthSession]]:
        async with client.app_state["sessionmaker"]() as db:
            link = await db.get(WorkspaceProviderLinkState, link_id)
            assert link is not None
            identity = await db.get(ExternalIdentity, link.target_provider_identity_id)
            assert identity is not None
            sessions = list(
                (
                    await db.scalars(
                        select(AuthSession).where(AuthSession.workspace_id == login_workspace_id)
                    )
                ).all()
            )
            return link, identity, sessions

    link, identity, sessions = asyncio.run(load_confirmed())
    assert link.status == "confirmed"
    assert link.candidate_identity_subject is None
    assert identity.user_id == UUID(login.json()["user_id"])
    assert identity.provider == "vk"
    assert [session.id for session in sessions] == [session_id]

    repeat_start = client.post(
        "/api/v1/auth/providers/vk/link/start",
        params={"workspace_id": login.json()["workspace_id"]},
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    repeat_link_id = UUID(repeat_start.json()["link_state_id"])
    repeat_state = parse_qs(urlparse(repeat_start.json()["authorization_url"]).query)["state"][0]
    repeat_callback = client.get(
        "/api/v1/auth/callback/vk",
        params={"state": repeat_state, "code": "vk:linked-user"},
        follow_redirects=False,
    )
    assert repeat_callback.status_code == 303
    idempotent = client.post(
        f"/api/v1/auth/provider-links/{repeat_link_id}/confirm",
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    assert idempotent.status_code == 200
    assert idempotent.json() == {"provider": "vk", "status": "confirmed", "idempotent": True}

    async def count_identities() -> int:
        async with client.app_state["sessionmaker"]() as db:
            identities = list(
                await db.scalars(
                    select(ExternalIdentity).where(
                        ExternalIdentity.user_id == UUID(login.json()["user_id"]),
                        ExternalIdentity.provider == "vk",
                    )
                )
            )
            return len(identities)

    assert asyncio.run(count_identities()) == 1

    lifecycle_events = [
        event
        for event in _load_auth_audit_events(client)
        if event.event_type
        in {
            "provider_link_started",
            "provider_link_callback_verified",
            "provider_link_confirmed",
        }
    ]
    assert {event.event_type for event in lifecycle_events} == {
        "provider_link_started",
        "provider_link_callback_verified",
        "provider_link_confirmed",
    }
    for event in lifecycle_events:
        assert len(event.metadata_json["link_state_sha256"]) == 64
        assert "link_state_id" not in event.metadata_json
        assert "candidate_identity_subject" not in event.metadata_json
        assert "candidate_email" not in event.metadata_json


def test_provider_link_callback_replay_scrubs_pending_candidate(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)
    started = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    login = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": started.json()["state_nonce"], "code": "TEST-YA-USER"},
    )
    assert login.status_code == 200
    session_id = UUID(login.json()["active_session_id"])
    csrf = issue_csrf_token(session_id=session_id, secret=client.app.state.web_csrf_secret)
    link_start = client.post(
        "/api/v1/auth/providers/vk/link/start",
        params={"workspace_id": login.json()["workspace_id"]},
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    link_id = UUID(link_start.json()["link_state_id"])
    provider_state = parse_qs(urlparse(link_start.json()["authorization_url"]).query)["state"][0]
    first = client.get(
        "/api/v1/auth/callback/vk",
        params={"state": provider_state, "code": "vk:replayed-user"},
        follow_redirects=False,
    )
    assert first.status_code == 303

    replay = client.get(
        "/api/v1/auth/callback/vk",
        params={"state": provider_state, "code": "vk:replayed-user"},
        follow_redirects=False,
    )
    assert replay.status_code == 400
    assert replay.json()["code"] == "callback_state_reused"

    async def load() -> tuple[WorkspaceProviderLinkState, ExternalIdentity | None]:
        async with client.app_state["sessionmaker"]() as db:
            link = await db.get(WorkspaceProviderLinkState, link_id)
            assert link is not None
            identity = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.provider == "vk",
                    ExternalIdentity.provider_subject == "vk:replayed-user",
                )
            )
            return link, identity

    import asyncio

    link, identity = asyncio.run(load())
    assert link.status == "rejected"
    assert link.candidate_identity_subject is None
    assert link.candidate_email is None
    assert link.candidate_phone is None
    assert identity is None


def test_provider_link_confirmation_expiry_scrubs_candidate(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)
    started = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    login = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": started.json()["state_nonce"], "code": "TEST-YA-USER"},
    )
    session_id = UUID(login.json()["active_session_id"])
    csrf = issue_csrf_token(session_id=session_id, secret=client.app.state.web_csrf_secret)
    link_start = client.post(
        "/api/v1/auth/providers/vk/link/start",
        params={"workspace_id": login.json()["workspace_id"]},
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    link_id = UUID(link_start.json()["link_state_id"])
    provider_state = parse_qs(urlparse(link_start.json()["authorization_url"]).query)["state"][0]
    verified = client.get(
        "/api/v1/auth/callback/vk",
        params={"state": provider_state, "code": "vk:expired-user"},
        follow_redirects=False,
    )
    assert verified.status_code == 303

    async def expire_link() -> None:
        async with client.app_state["sessionmaker"]() as db:
            link = await db.get(WorkspaceProviderLinkState, link_id)
            assert link is not None
            link.expires_at = datetime(2020, 1, 1, tzinfo=UTC)
            await db.commit()

    import asyncio

    asyncio.run(expire_link())
    confirmation = client.post(
        f"/api/v1/auth/provider-links/{link_id}/confirm",
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    assert confirmation.status_code == 400
    assert confirmation.json()["code"] == "provider_link_expired"

    async def load() -> tuple[WorkspaceProviderLinkState, ExternalIdentity | None]:
        async with client.app_state["sessionmaker"]() as db:
            link = await db.get(WorkspaceProviderLinkState, link_id)
            assert link is not None
            identity = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.provider == "vk",
                    ExternalIdentity.provider_subject == "vk:expired-user",
                )
            )
            return link, identity

    link, identity = asyncio.run(load())
    assert link.status == "expired"
    assert link.candidate_identity_subject is None
    assert identity is None

    expired_event = next(
        event for event in _load_auth_audit_events(client) if event.event_type == "provider_link_expired"
    )
    assert expired_event.metadata_json["error_code"] == "provider_link_expired"
    assert len(expired_event.metadata_json["link_state_sha256"]) == 64
    assert str(link_id) not in str(expired_event.metadata_json)


def test_provider_link_confirmation_rejects_foreign_identity_without_transfer(
    monkeypatch, client: TestClient
) -> None:
    _patch_fake_providers(monkeypatch, client)
    other_user_id = uuid4()
    started = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    login = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": started.json()["state_nonce"], "code": "TEST-YA-USER"},
    )
    assert login.status_code == 200
    login_workspace_id = UUID(login.json()["workspace_id"])
    session_id = UUID(login.json()["active_session_id"])
    csrf = issue_csrf_token(session_id=session_id, secret=client.app.state.web_csrf_secret)
    link_start = client.post(
        "/api/v1/auth/providers/vk/link/start",
        params={"workspace_id": str(login_workspace_id)},
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    link_id = UUID(link_start.json()["link_state_id"])
    provider_state = parse_qs(urlparse(link_start.json()["authorization_url"]).query)["state"][0]
    callback = client.get(
        "/api/v1/auth/callback/vk",
        params={"state": provider_state, "code": "vk:foreign-user"},
        follow_redirects=False,
    )
    assert callback.status_code == 303

    async def seed_foreign_identity() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                UserIdentity(
                    id=other_user_id,
                    organization_id=ORG_ID,
                    external_subject="foreign-provider-link-user",
                )
            )
            await db.flush()
            db.add(
                ExternalIdentity(
                    user_id=other_user_id,
                    provider="vk",
                    provider_subject="vk:foreign-user",
                    is_verified=True,
                )
            )
            await db.commit()

    import asyncio

    asyncio.run(seed_foreign_identity())
    confirmation = client.post(
        f"/api/v1/auth/provider-links/{link_id}/confirm",
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    assert confirmation.status_code == 409
    assert confirmation.json()["code"] == "provider_link_conflict"
    assert str(other_user_id) not in confirmation.text
    assert "foreign-user" not in confirmation.text

    async def load() -> tuple[WorkspaceProviderLinkState, ExternalIdentity]:
        async with client.app_state["sessionmaker"]() as db:
            link = await db.get(WorkspaceProviderLinkState, link_id)
            assert link is not None
            identity = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.provider == "vk",
                    ExternalIdentity.provider_subject == "vk:foreign-user",
                )
            )
            assert identity is not None
            return link, identity

    link, identity = asyncio.run(load())
    assert link.status == "rejected"
    assert link.candidate_identity_subject is None
    assert identity.user_id == other_user_id

    conflict_event = next(
        event for event in _load_auth_audit_events(client) if event.event_type == "provider_link_conflict"
    )
    assert conflict_event.metadata_json["error_code"] == "provider_link_conflict"
    assert len(conflict_event.metadata_json["link_state_sha256"]) == 64
    assert str(link_id) not in str(conflict_event.metadata_json)
    assert "foreign-user" not in str(conflict_event.metadata_json)


def test_provider_link_confirmation_requires_the_initiating_session(
    monkeypatch, client: TestClient
) -> None:
    _patch_fake_providers(monkeypatch, client)
    started = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    login = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": started.json()["state_nonce"], "code": "TEST-YA-USER"},
    )
    assert login.status_code == 200
    login_workspace_id = UUID(login.json()["workspace_id"])
    session_id = UUID(login.json()["active_session_id"])
    csrf = issue_csrf_token(session_id=session_id, secret=client.app.state.web_csrf_secret)
    link_start = client.post(
        "/api/v1/auth/providers/vk/link/start",
        params={"workspace_id": str(login_workspace_id)},
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    link_id = UUID(link_start.json()["link_state_id"])
    provider_state = parse_qs(urlparse(link_start.json()["authorization_url"]).query)["state"][0]
    callback = client.get(
        "/api/v1/auth/callback/vk",
        params={"state": provider_state, "code": "vk:session-bound-user"},
        follow_redirects=False,
    )
    assert callback.status_code == 303

    async def issue_second_session() -> tuple[str, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            issued = await issue_auth_session(
                db,
                user_id=UUID(login.json()["user_id"]),
                workspace_id=login_workspace_id,
                device_id=DEVICE_ID,
                provider="yandex",
            )
            await db.commit()
            return issued.token, issued.id

    import asyncio

    second_token, second_session_id = asyncio.run(issue_second_session())
    second_csrf = issue_csrf_token(
        session_id=second_session_id,
        secret=client.app.state.web_csrf_secret,
    )
    confirmation = client.post(
        f"/api/v1/auth/provider-links/{link_id}/confirm",
        headers={
            "Authorization": f"Bearer {second_token}",
            "X-CSRF-Token": second_csrf,
        },
    )
    assert confirmation.status_code == 403
    assert confirmation.json()["code"] == "workspace_scope_denied"

    other_user_id = uuid4()

    async def issue_foreign_session() -> tuple[str, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                UserIdentity(
                    id=other_user_id,
                    organization_id=ORG_ID,
                    external_subject="provider-link-foreign-session",
                )
            )
            await db.flush()
            db.add(
                WorkspaceMembership(
                    workspace_id=WORKSPACE_ID,
                    user_id=other_user_id,
                    role="member",
                    status="active",
                )
            )
            await db.flush()
            issued = await issue_auth_session(
                db,
                user_id=other_user_id,
                workspace_id=WORKSPACE_ID,
                device_id=None,
                provider="email",
            )
            await db.commit()
            return issued.token, issued.id

    foreign_token, foreign_session_id = asyncio.run(issue_foreign_session())
    foreign_confirmation = client.post(
        f"/api/v1/auth/provider-links/{link_id}/confirm",
        headers={
            "Authorization": f"Bearer {foreign_token}",
            "X-CSRF-Token": issue_csrf_token(
                session_id=foreign_session_id,
                secret=client.app.state.web_csrf_secret,
            ),
        },
    )
    assert foreign_confirmation.status_code == 403
    assert foreign_confirmation.json()["code"] == "workspace_scope_denied"

    other_workspace_id = uuid4()

    async def issue_other_workspace_session() -> tuple[str, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                Workspace(
                    id=other_workspace_id,
                    organization_id=ORG_ID,
                    slug="provider-link-other-workspace",
                    name="Provider link other workspace",
                )
            )
            db.add(
                WorkspaceMembership(
                    workspace_id=other_workspace_id,
                    user_id=UUID(login.json()["user_id"]),
                    role="member",
                    status="active",
                )
            )
            await db.flush()
            issued = await issue_auth_session(
                db,
                user_id=UUID(login.json()["user_id"]),
                workspace_id=other_workspace_id,
                device_id=None,
                provider="yandex",
            )
            await db.commit()
            return issued.token, issued.id

    other_workspace_token, other_workspace_session_id = asyncio.run(issue_other_workspace_session())
    other_workspace_confirmation = client.post(
        f"/api/v1/auth/provider-links/{link_id}/confirm",
        headers={
            "Authorization": f"Bearer {other_workspace_token}",
            "X-CSRF-Token": issue_csrf_token(
                session_id=other_workspace_session_id,
                secret=client.app.state.web_csrf_secret,
            ),
        },
    )
    assert other_workspace_confirmation.status_code == 403
    assert other_workspace_confirmation.json()["code"] == "workspace_scope_denied"

    async def load() -> WorkspaceProviderLinkState:
        async with client.app_state["sessionmaker"]() as db:
            link = await db.get(WorkspaceProviderLinkState, link_id)
            assert link is not None
            return link

    link = asyncio.run(load())
    assert link.status == "callback_verified"
    assert link.candidate_identity_subject == "vk:session-bound-user"

    confirmed = client.post(
        f"/api/v1/auth/provider-links/{link_id}/confirm",
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    replayed_confirmation = client.post(
        f"/api/v1/auth/provider-links/{link_id}/confirm",
        headers={
            "Authorization": f"Bearer {login.json()['session_token']}",
            "X-CSRF-Token": csrf,
        },
    )
    assert confirmed.status_code == 200
    assert replayed_confirmation.status_code == 400
    assert replayed_confirmation.json()["code"] == "provider_link_reused"


def test_owner_session_cookie_can_create_desktop_meeting_without_legacy_device_headers(
    client: TestClient,
) -> None:
    async def issue_bound_cookie() -> str:
        async with client.app_state["sessionmaker"]() as db:
            issued = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=WORKSPACE_ID,
                device_id=DEVICE_ID,
                provider="email",
                now=datetime.now(UTC),
            )
            db.add(
                AuthSessionDeviceBinding(
                    auth_session_id=issued.id,
                    registered_device_id=DEVICE_ID,
                    device_state="trusted",
                    last_heartbeat_at=datetime.now(UTC),
                )
            )
            await db.commit()
            return issued.token

    session_cookie = client.portal.call(issue_bound_cookie)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, session_cookie)

    created = client.post(
        "/api/v1/meetings",
        json={"local_recording_id": "cookie-auth-desktop-recording", "duration_seconds": 60},
    )

    assert created.status_code == 200, created.json()
    payload = created.json()
    assert payload["local_recording_id"] == "cookie-auth-desktop-recording"
    assert payload["status"] == "draft"


def test_builtin_provider_callback_fails_closed_without_verified_exchange(client: TestClient) -> None:
    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200
    state_nonce = start.json()["state_nonce"]

    response = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": state_nonce, "code": "FORGED-YANDEX-CODE"},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "provider_unavailable"
    events = _load_auth_audit_events(client)
    failures = [event for event in events if event.event_type == "provider_callback_failed"]
    assert len(failures) == 1
    assert failures[0].metadata_json == {
        "error_code": "provider_unavailable",
        "reason": "verification_unavailable",
    }


def test_yandex_callback_uses_verified_profile_not_raw_code(monkeypatch, tmp_path, client: TestClient) -> None:
    _set_provider_self_enrollment(client, True)
    _write_secret_file(client, tmp_path, "yandex", "yandex-secret")
    fake_http = FakeProviderHttpClient()
    monkeypatch.setattr("twobrain_rec_server.auth.callbacks.get_provider_http_client", lambda: fake_http)

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200

    response = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": start.json()["state_nonce"], "code": "VALID-YANDEX-CODE"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_subject"] == "yandex-user-42"
    assert payload["provider_subject"] != "valid-yandex-code"
    assert fake_http.calls[0] == (
        "POST",
        "https://oauth.yandex.ru/token",
        {
            "grant_type": "authorization_code",
            "code": "VALID-YANDEX-CODE",
            "client_id": "twobrain-yandex-client-id",
            "client_secret": "yandex-secret",
            "redirect_uri": "http://testserver/api/v1/auth/callback/yandex",
        },
    )
    assert fake_http.calls[1][0:2] == ("GET", "https://login.yandex.ru/info")


def test_provider_start_uses_public_auth_base_url_for_redirect_uri(client: TestClient) -> None:
    client.app.state.settings.auth_base_url = "https://rec.2brain.pro"

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "/meetings"},
    )

    assert start.status_code == 200
    query = parse_qs(urlparse(start.json()["authorization_url"]).query)
    assert query["redirect_uri"] == ["https://rec.2brain.pro/api/v1/auth/callback/yandex"]


def test_vk_provider_start_uses_public_auth_base_url_and_vk_client_id(client: TestClient) -> None:
    client.app.state.settings.auth_base_url = "https://rec.2brain.pro"

    start = client.post(
        "/api/v1/auth/providers/vk/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "/meetings"},
    )

    assert start.status_code == 200
    query = parse_qs(urlparse(start.json()["authorization_url"]).query)
    assert query["client_id"] == ["twobrain-vk-client-id"]
    assert query["redirect_uri"] == ["https://rec.2brain.pro/api/v1/auth/callback/vk"]
    assert query["scope"] == ["email phone"]
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["code_challenge"][0]) >= 43


def test_vk_callback_uses_verified_profile_not_raw_code(monkeypatch, tmp_path, client: TestClient) -> None:
    _set_provider_self_enrollment(client, True)
    _write_secret_file(client, tmp_path, "vk", "vk-secret")
    fake_http = FakeProviderHttpClient()
    monkeypatch.setattr("twobrain_rec_server.auth.callbacks.get_provider_http_client", lambda: fake_http)

    start = client.post(
        "/api/v1/auth/providers/vk/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200

    response = client.get(
        "/api/v1/auth/callback/vk",
        params={"state": start.json()["state_nonce"], "code": "VALID-VK-CODE", "device_id": "VK-DEVICE"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_subject"] == "vk-user-42"
    assert payload["provider_subject"] != "valid-vk-code"
    assert fake_http.calls[0] == (
        "POST",
        "https://id.vk.ru/oauth2/auth",
        {
            "grant_type": "authorization_code",
            "client_id": "twobrain-vk-client-id",
            "code_verifier": fake_http.calls[0][2]["code_verifier"],
            "device_id": "VK-DEVICE",
            "redirect_uri": "http://testserver/api/v1/auth/callback/vk",
            "code": "VALID-VK-CODE",
            "state": start.json()["state_nonce"],
        },
    )
    assert fake_http.calls[1] == (
        "POST",
        "https://id.vk.ru/oauth2/user_info",
        {"client_id": "twobrain-vk-client-id", "access_token": "verified-vk-token"},
    )


def test_telegram_callback_rejects_forged_signature(tmp_path, client: TestClient) -> None:
    _set_provider_self_enrollment(client, True)
    bot_token = "telegram-bot-token"
    _write_secret_file(client, tmp_path, "telegram", bot_token)

    start = client.post(
        "/api/v1/auth/providers/telegram/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200
    state_nonce = start.json()["state_nonce"]
    telegram_payload = {
        "id": "424242",
        "first_name": "Telegram",
        "last_name": "User",
        "username": "telegram_user",
        "auth_date": str(int(datetime.now(UTC).timestamp())),
    }

    forged = client.get(
        "/api/v1/auth/callback/telegram",
        params={"state": state_nonce, **telegram_payload, "hash": "0" * 64},
    )
    assert forged.status_code == 503
    assert forged.json()["code"] == "provider_unavailable"

    retry = client.post(
        "/api/v1/auth/providers/telegram/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert retry.status_code == 200
    valid = client.get(
        "/api/v1/auth/callback/telegram",
        params={
            "state": retry.json()["state_nonce"],
            **telegram_payload,
            "hash": _telegram_hash(telegram_payload, bot_token),
        },
    )
    assert valid.status_code == 200
    assert valid.json()["provider_subject"] == "424242"


def test_provider_callback_creates_personal_space_when_corporate_enrollment_is_disabled(
    monkeypatch, client: TestClient
) -> None:
    _patch_fake_providers(monkeypatch, client, allow_self_enrollment=False)

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200
    state_nonce = start.json()["state_nonce"]

    response = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": state_nonce, "code": "NEW-UNINVITED-USER"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] != str(WORKSPACE_ID)

    async def load() -> tuple[Workspace, list[WorkspaceMembership], list[WorkspaceJoinOffer]]:
        async with client.app_state["sessionmaker"]() as db:
            user_id = UUID(payload["user_id"])
            personal = await db.scalar(
                select(Workspace).where(
                    Workspace.id == UUID(payload["workspace_id"]),
                    Workspace.kind == "personal",
                    Workspace.owner_user_id == user_id,
                )
            )
            assert personal is not None
            corporate_memberships = list(
                await db.scalars(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.workspace_id == WORKSPACE_ID,
                        WorkspaceMembership.user_id == user_id,
                    )
                )
            )
            offers = list(
                await db.scalars(
                    select(WorkspaceJoinOffer).where(
                        WorkspaceJoinOffer.user_id == user_id,
                    )
                )
            )
            return personal, corporate_memberships, offers

    import asyncio

    personal, corporate_memberships, offers = asyncio.run(load())
    assert personal.kind == "personal"
    assert corporate_memberships == []
    assert offers == []


def test_provider_domain_claim_never_auto_joins_or_discloses_corporate_space(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client, allow_self_enrollment=True)
    corporate_workspace_id = uuid4()
    corporate_name = "Закрытая команда Acme"

    async def seed_corporate_space() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                Workspace(
                    id=corporate_workspace_id,
                    organization_id=ORG_ID,
                    slug="acme-corporate",
                    name=corporate_name,
                    kind="corporate",
                )
            )
            await db.commit()

    import asyncio

    asyncio.run(seed_corporate_space())
    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    callback = client.get(
        "/api/v1/auth/callback/yandex",
        params={
            "state": start.json()["state_nonce"],
            "code": "DOMAIN-ONLY-USER",
            "email": "new.user@acme.example",
        },
    )

    assert callback.status_code == 200
    assert corporate_name not in callback.text
    payload = callback.json()
    assert payload["workspace_id"] != str(corporate_workspace_id)
    assert requires_explicit_corporate_enrollment() is True

    async def load() -> tuple[list[WorkspaceMembership], list[WorkspaceJoinOffer]]:
        async with client.app_state["sessionmaker"]() as db:
            memberships = list(
                await db.scalars(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.workspace_id == corporate_workspace_id,
                        WorkspaceMembership.user_id == UUID(payload["user_id"]),
                    )
                )
            )
            offers = list(
                await db.scalars(
                    select(WorkspaceJoinOffer).where(WorkspaceJoinOffer.user_id == UUID(payload["user_id"]))
                )
            )
            return memberships, offers

    memberships, offers = asyncio.run(load())
    assert memberships == []
    assert offers == []


def test_email_signup_reuses_new_and_legacy_identities_without_bootstrap_enrollment(
    client: TestClient,
) -> None:
    new_email = "new-personal@example.test"
    legacy_email = "legacy-personal@example.test"
    legacy_user_id = uuid4()

    async def seed_legacy_user() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                UserIdentity(
                    id=legacy_user_id,
                    organization_id=ORG_ID,
                    external_subject=f"email:{legacy_email}",
                    display_name="Legacy person",
                )
            )
            await db.flush()
            db.add_all(
                (
                    ExternalIdentity(
                        user_id=legacy_user_id,
                        provider="email",
                        provider_subject=legacy_email,
                        email=legacy_email,
                        is_verified=True,
                    ),
                    WorkspaceMembership(
                        workspace_id=WORKSPACE_ID,
                        user_id=legacy_user_id,
                        role="member",
                        status="active",
                    ),
                )
            )
            await db.commit()

    import asyncio

    asyncio.run(seed_legacy_user())

    def complete_signup(email: str) -> str:
        started = client.post("/sign-up/email/start", data={"email": email, "next": "/meetings"})
        assert started.status_code == 200
        assert 'name="workspace_id"' not in started.text
        state_match = re.search(r'name="state" value="([^"]+)"', started.text)
        code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", started.text)
        assert state_match is not None
        assert code_match is not None
        completed = client.post(
            "/sign-up/email/verify",
            data={
                "email": email,
                "code": code_match.group(1),
                "state": state_match.group(1),
                "next": "/meetings",
            },
            follow_redirects=False,
        )
        assert completed.status_code == 303
        token = completed.cookies.get(AUTH_SESSION_COOKIE_NAME)
        assert token is not None
        return token

    first_new_token = complete_signup(new_email)
    second_new_token = complete_signup(new_email)
    first_legacy_token = complete_signup(legacy_email)
    second_legacy_token = complete_signup(legacy_email)

    async def load_result() -> tuple[int, int, int, int, set[UUID]]:
        async with client.app_state["sessionmaker"]() as db:
            new_identity = await db.scalar(
                select(ExternalIdentity).where(ExternalIdentity.email == new_email)
            )
            assert new_identity is not None
            legacy_identity = await db.scalar(
                select(ExternalIdentity).where(ExternalIdentity.email == legacy_email)
            )
            assert legacy_identity is not None
            assert legacy_identity.user_id == legacy_user_id
            new_personal_spaces = list(
                await db.scalars(
                    select(Workspace).where(
                        Workspace.owner_user_id == new_identity.user_id,
                        Workspace.kind == "personal",
                    )
                )
            )
            legacy_personal_spaces = list(
                await db.scalars(
                    select(Workspace).where(
                        Workspace.owner_user_id == legacy_user_id,
                        Workspace.kind == "personal",
                    )
                )
            )
            bootstrap_memberships = list(
                await db.scalars(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.workspace_id == WORKSPACE_ID,
                        WorkspaceMembership.user_id.in_((new_identity.user_id, legacy_user_id)),
                    )
                )
            )
            sessions = list(
                await db.scalars(
                    select(AuthSession).where(
                        AuthSession.session_token_hash.in_(
                            tuple(
                                hashlib.sha256(token.encode()).hexdigest()
                                for token in (
                                    first_new_token,
                                    second_new_token,
                                    first_legacy_token,
                                    second_legacy_token,
                                )
                            )
                        )
                    )
                )
            )
            assert len(new_personal_spaces) == 1
            assert len(legacy_personal_spaces) == 1
            return (
                len(new_personal_spaces),
                len(legacy_personal_spaces),
                len(bootstrap_memberships),
                len(sessions),
                {session.workspace_id for session in sessions},
            )

    new_spaces, legacy_spaces, bootstrap_memberships, session_count, session_workspaces = asyncio.run(
        load_result()
    )
    assert new_spaces == 1
    assert legacy_spaces == 1
    assert bootstrap_memberships == 1
    assert session_count == 4
    assert WORKSPACE_ID not in session_workspaces


def test_provider_callback_creates_offer_and_personal_space_without_auto_join(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client, allow_self_enrollment=False)

    async def seed_invitation() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                WorkspaceInvitation(
                    workspace_id=WORKSPACE_ID,
                    target_contact="invited@example.test",
                    invited_role="member",
                    created_by_user_id=USER_ID,
                    expires_at=datetime.now(UTC) + timedelta(days=1),
                )
            )
            await db.commit()

    import asyncio

    asyncio.run(seed_invitation())

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    callback = client.get(
        "/api/v1/auth/callback/yandex",
        params={
            "state": start.json()["state_nonce"],
            "code": "NEW-INVITED-USER",
            "email": "invited@example.test",
        },
    )

    assert callback.status_code == 200
    callback_payload = callback.json()
    assert callback_payload["workspace_id"] != str(WORKSPACE_ID)

    async def load() -> tuple[Workspace, list[WorkspaceMembership], list[WorkspaceJoinOffer]]:
        async with client.app_state["sessionmaker"]() as db:
            user_id = UUID(callback_payload["user_id"])
            personal = await db.scalar(
                select(Workspace).where(
                    Workspace.id == UUID(callback_payload["workspace_id"]),
                    Workspace.kind == "personal",
                    Workspace.owner_user_id == user_id,
                )
            )
            assert personal is not None
            corporate_memberships = list(
                await db.scalars(
                    select(WorkspaceMembership).where(
                        WorkspaceMembership.workspace_id == WORKSPACE_ID,
                        WorkspaceMembership.user_id == user_id,
                    )
                )
            )
            offers = list(
                await db.scalars(
                    select(WorkspaceJoinOffer).where(
                        WorkspaceJoinOffer.workspace_id == WORKSPACE_ID,
                        WorkspaceJoinOffer.user_id == user_id,
                    )
                )
            )
            return personal, corporate_memberships, offers

    personal, corporate_memberships, offers = asyncio.run(load())
    assert personal.kind == "personal"
    assert corporate_memberships == []
    assert len(offers) == 1
    assert offers[0].status == "offered"


def test_auth_callback_provider_unavailable_returns_service_unavailable(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200
    state_nonce = start.json()["state_nonce"]

    response = client.get(
        "/api/v1/auth/callback/yandex",
        params={
            "state": state_nonce,
            "error": "server_error",
        },
    )
    assert response.status_code == 503
    assert response.json()["code"] == "provider_unavailable"


def test_auth_callback_user_denied_returns_forbidden(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200
    state_nonce = start.json()["state_nonce"]

    response = client.get(
        "/api/v1/auth/callback/yandex",
        params={
            "state": state_nonce,
            "error": "access_denied",
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "callback_denied"


def test_auth_callback_without_state_is_invalid(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200

    response = client.get(
        "/api/v1/auth/callback/yandex",
        params={"code": "TEST-YA-USER"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "callback_state_invalid"


def test_auth_callback_fails_for_identity_bound_to_other_organization(monkeypatch, client: TestClient) -> None:
    other_org_id = UUID("a0000000-0000-0000-0000-000000000001")
    other_workspace_id = UUID("a0000000-0000-0000-0000-000000000002")
    other_user_id = UUID("a0000000-0000-0000-0000-000000000003")

    def seed_conflicting_identity() -> None:
        async def seed() -> None:
            async with client.app_state["sessionmaker"]() as db:
                db.add(Organization(id=other_org_id, slug="other-org", name="Other Org"))
                await db.flush()
                db.add(
                    Workspace(
                        id=other_workspace_id,
                        organization_id=other_org_id,
                        slug="other-workspace",
                        name="Other Workspace",
                    )
                )
                await db.flush()
                db.add(
                    UserIdentity(
                        id=other_user_id,
                        organization_id=other_org_id,
                        external_subject="other-user-subject",
                        display_name="Other User",
                    )
                )
                await db.flush()
                db.add(
                    ExternalIdentity(
                        user_id=other_user_id,
                        provider="yandex",
                        provider_subject="test-ya-user",
                        is_verified=True,
                        subject_issued_at=None,
                        last_seen_at=None,
                    )
                )
                await db.commit()

        client.portal.call(seed)

    _patch_fake_providers(monkeypatch, client)
    seed_conflicting_identity()
    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200
    state_nonce = start.json()["state_nonce"]
    response = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": state_nonce, "code": "TEST-YA-USER"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "identity_subject_conflict"


def test_auth_callback_fails_for_inactive_identity_owner(monkeypatch, client: TestClient) -> None:
    inactive_user_id = UUID("b0000000-0000-0000-0000-000000000001")

    def seed_inactive_identity() -> None:
        async def seed() -> None:
            async with client.app_state["sessionmaker"]() as db:
                db.add(
                    UserIdentity(
                        id=inactive_user_id,
                        organization_id=ORG_ID,
                        external_subject="inactive-user-subject",
                        display_name="Inactive User",
                        status="inactive",
                    )
                )
                await db.flush()
                db.add(
                    ExternalIdentity(
                        user_id=inactive_user_id,
                        provider="yandex",
                        provider_subject="test-ya-user",
                        is_verified=True,
                        subject_issued_at=None,
                        last_seen_at=None,
                    )
                )
                await db.commit()

        client.portal.call(seed)

    _patch_fake_providers(monkeypatch, client)
    seed_inactive_identity()
    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    assert start.status_code == 200
    state_nonce = start.json()["state_nonce"]
    response = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": state_nonce, "code": "TEST-YA-USER"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "identity_user_inactive"


def test_auth_link_rejects_raw_candidate_subject(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    state_nonce = start.json()["state_nonce"]
    callback_payload = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": state_nonce, "code": "TEST-YA-USER", "email": "candidate@example.com", "phone": "+79990001111"},
    ).json()

    response = client.post(
        "/api/v1/auth/link",
        headers={
            "Authorization": f"Bearer {callback_payload['session_token']}",
            "X-Workspace-Id": callback_payload["workspace_id"],
        },
        json={
            "candidate_provider": "vk",
            "candidate_provider_subject": "VK-CANDIDATE",
            "candidate_phone": "+79990001111",
            "expected_workspace_id": callback_payload["workspace_id"],
        },
    )
    assert response.status_code == 409
    assert response.json()["code"] == "provider_link_requires_verified_callback"
    linked_user_id = callback_payload["user_id"]

    events = _load_auth_audit_events(client)
    link_events = [event for event in events if event.event_type == "provider_link_rejected"]
    assert len(link_events) == 1
    link_event = link_events[0]
    assert link_event.outcome == "failure"
    assert link_event.user_id is None
    assert str(link_event.actor_user_id) == linked_user_id
    assert link_event.metadata_json == {"error_code": "provider_link_requires_verified_callback"}

    async def no_raw_subject_link() -> None:
        async with client.app_state["sessionmaker"]() as db:
            identity = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.provider == "vk",
                    ExternalIdentity.provider_subject == "VK-CANDIDATE",
                )
            )
            assert identity is None

    import asyncio

    asyncio.run(no_raw_subject_link())


def test_auth_link_rejects_direct_subject_without_leaking_conflict(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)
    other_user_id = uuid4()

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    state_nonce = start.json()["state_nonce"]
    callback_payload = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": state_nonce, "code": "TEST-YA-USER"},
    ).json()

    async def seed_conflicting_link_identity() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(UserIdentity(id=other_user_id, organization_id=ORG_ID, external_subject=str(other_user_id)))
            await db.flush()
            db.add(WorkspaceMembership(workspace_id=WORKSPACE_ID, user_id=other_user_id, role="member", status="active"))
            db.add(
                ExternalIdentity(
                    user_id=other_user_id,
                    provider="vk",
                    provider_subject="vk-conflict-subject",
                    is_verified=True,
                )
            )
            await db.commit()

    import asyncio

    asyncio.run(seed_conflicting_link_identity())

    response = client.post(
        "/api/v1/auth/link",
        headers={
            "Authorization": f"Bearer {callback_payload['session_token']}",
            "X-Workspace-Id": callback_payload["workspace_id"],
        },
        json={
            "candidate_provider": "vk",
            "candidate_provider_subject": "vk-conflict-subject",
            "expected_workspace_id": callback_payload["workspace_id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "provider_link_requires_verified_callback"
    events = _load_auth_audit_events(client)
    conflict_events = [event for event in events if event.event_type == "provider_link_rejected"]
    assert len(conflict_events) == 1
    assert conflict_events[0].outcome == "failure"
    assert conflict_events[0].metadata_json == {"error_code": "provider_link_requires_verified_callback"}


def test_auth_device_register_revoke_blocks_session_bound_ingest(monkeypatch, client: TestClient) -> None:
    _patch_fake_providers(monkeypatch, client)

    start = client.post(
        "/api/v1/auth/providers/yandex/start",
        json={"workspace_id": str(WORKSPACE_ID), "workspace_return_url": "app://auth-callback"},
    )
    state_nonce = start.json()["state_nonce"]
    callback_payload = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": state_nonce, "code": "TEST-YA-DEVICE"},
    ).json()
    workspace_id = UUID(callback_payload["workspace_id"])
    unbound_device_id = uuid4()

    async def seed_unbound_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                RegisteredDevice(
                    id=unbound_device_id,
                    workspace_id=workspace_id,
                    user_id=UUID(callback_payload["user_id"]),
                    device_public_id="unbound-session-device",
                    status="active",
                    registration_state="approved",
                )
            )
            await db.commit()

    client.portal.call(seed_unbound_device)
    session_headers = {
        "Authorization": f"Bearer {callback_payload['session_token']}",
        "X-Workspace-Id": str(workspace_id),
    }

    untrusted = client.post(
        "/api/v1/meetings",
        headers=session_headers | {"X-Device-Id": str(unbound_device_id)},
        json={"local_recording_id": "untrusted-session-device", "duration_seconds": 60},
    )
    assert untrusted.status_code == 403
    assert untrusted.json()["code"] == "device_untrusted"

    register = client.post(
        "/api/v1/auth/devices/register",
        headers=session_headers,
        json={
            "device_public_id": "new-macos-device",
            "platform": "macos",
            "client_version": "0.13-test",
        },
    )
    assert register.status_code == 200
    device_payload = register.json()
    assert device_payload["status"] == "active"
    assert device_payload["registration_state"] == "approved"

    allowed = client.post(
        "/api/v1/meetings",
        headers=session_headers | {"X-Device-Id": device_payload["device_id"]},
        json={"local_recording_id": "trusted-session-device", "duration_seconds": 60},
    )
    assert allowed.status_code == 200

    revoke = client.post(
        f"/api/v1/auth/devices/{device_payload['device_id']}/revoke",
        headers=session_headers,
    )
    assert revoke.status_code == 200
    assert revoke.json()["status"] == "revoked"

    denied = client.post(
        "/api/v1/meetings",
        headers=session_headers | {"X-Device-Id": device_payload["device_id"]},
        json={"local_recording_id": "revoked-session-device", "duration_seconds": 60},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "device_revoked"

    events = _load_auth_audit_events(client)
    event_types = [event.event_type for event in events]
    assert "device_registered" in event_types
    assert "device_revoked" in event_types
    registered = next(event for event in events if event.event_type == "device_registered")
    assert "device_public_id" not in registered.metadata_json
    assert len(registered.metadata_json["device_public_id_sha256"]) == 64


def test_workspace_owner_can_revoke_another_user_device(client: TestClient) -> None:
    other_user_id = uuid4()
    other_device_id = uuid4()

    async def seed_other_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(UserIdentity(id=other_user_id, organization_id=ORG_ID, external_subject=str(other_user_id)))
            await db.flush()
            db.add(WorkspaceMembership(workspace_id=WORKSPACE_ID, user_id=other_user_id, role="member", status="active"))
            db.add(
                RegisteredDevice(
                    id=other_device_id,
                    workspace_id=WORKSPACE_ID,
                    user_id=other_user_id,
                    device_public_id="other-user-device",
                    status="active",
                    registration_state="approved",
                )
            )
            await db.commit()

    import asyncio

    asyncio.run(seed_other_device())

    response = client.post(
        f"/api/v1/auth/devices/{other_device_id}/revoke",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "revoked"


def test_workspace_member_cannot_revoke_another_user_device(client: TestClient) -> None:
    member_user_id = uuid4()
    owner_device_id = uuid4()

    async def seed_member_and_owner_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(UserIdentity(id=member_user_id, organization_id=ORG_ID, external_subject=str(member_user_id)))
            await db.flush()
            db.add(WorkspaceMembership(workspace_id=WORKSPACE_ID, user_id=member_user_id, role="member", status="active"))
            db.add(
                RegisteredDevice(
                    id=owner_device_id,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    device_public_id="owner-extra-device",
                    status="active",
                    registration_state="approved",
                )
            )
            await db.commit()

    import asyncio

    asyncio.run(seed_member_and_owner_device())

    response = client.post(
        f"/api/v1/auth/devices/{owner_device_id}/revoke",
        headers=auth_headers()
        | {
            "X-User-Id": str(member_user_id),
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "link_denied"


def test_active_space_list_and_switch_replace_the_scoped_session(client: TestClient) -> None:
    async def seed() -> tuple[str, UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            personal = await ensure_personal_workspace(
                db,
                organization_id=ORG_ID,
                user_id=USER_ID,
            )
            current = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=WORKSPACE_ID,
                device_id=DEVICE_ID,
                provider="space-switch-test",
            )
            db.add(
                AuthSessionDeviceBinding(
                    auth_session_id=current.id,
                    registered_device_id=DEVICE_ID,
                    device_state="trusted",
                    last_heartbeat_at=datetime.now(UTC),
                )
            )
            await db.commit()
            return current.token, current.id, personal.id

    import asyncio

    token, session_id, personal_workspace_id = asyncio.run(seed())
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, token)

    listed = client.get("/settings/spaces")
    assert listed.status_code == 200
    spaces = {space["id"]: space for space in listed.json()["spaces"]}
    assert spaces[str(WORKSPACE_ID)]["active"] is True
    assert spaces[str(personal_workspace_id)] == {
        "id": str(personal_workspace_id),
        "name": "Личное пространство",
        "kind": "personal",
        "role": "owner",
        "active": False,
    }

    csrf = issue_csrf_token(session_id=session_id, secret=client.app.state.web_csrf_secret)
    activated = client.post(
        f"/settings/spaces/{personal_workspace_id}/activate",
        headers={"X-CSRF-Token": csrf},
    )
    assert activated.status_code == 200
    assert activated.json()["active_space"] == {
        "id": str(personal_workspace_id),
        "name": "Личное пространство",
        "kind": "personal",
        "role": "owner",
        "active": True,
    }
    assert AUTH_SESSION_COOKIE_NAME in activated.headers["set-cookie"]
    assert "HttpOnly" in activated.headers["set-cookie"]
    assert "Secure" in activated.headers["set-cookie"]
    replacement_match = re.search(
        rf"{re.escape(AUTH_SESSION_COOKIE_NAME)}=([^;]+)", activated.headers["set-cookie"]
    )
    assert replacement_match is not None
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, replacement_match.group(1))

    current_settings = client.get("/settings")
    assert current_settings.status_code == 200
    assert "Активное пространство" in current_settings.text
    assert "Сейчас выбрано" in current_settings.text
    assert 'name="workspace_id"' not in current_settings.text

    client.cookies.clear()
    replaced = client.get("/settings/spaces", headers={"X-Auth-Session": token})
    assert replaced.status_code == 401
    assert replaced.json()["code"] == "auth_session_invalid"

    async def load_sessions() -> tuple[str, list[AuthSession], list[AuthSessionDeviceBinding]]:
        async with client.app_state["sessionmaker"]() as db:
            original = await db.get(AuthSession, session_id)
            assert original is not None
            replacements = list(
                await db.scalars(
                    select(AuthSession).where(
                        AuthSession.user_id == USER_ID,
                        AuthSession.workspace_id == personal_workspace_id,
                        AuthSession.status == "active",
                    )
                )
            )
            bindings = list(
                await db.scalars(
                    select(AuthSessionDeviceBinding).where(
                        AuthSessionDeviceBinding.auth_session_id.in_(tuple(session.id for session in replacements))
                    )
                )
            )
            return original.status, replacements, bindings

    original_status, replacements, bindings = asyncio.run(load_sessions())
    assert original_status == "replaced"
    assert len(replacements) == 1
    assert len(bindings) == 1
    assert bindings[0].device_state == "trusted"


def test_workspace_join_offers_require_explicit_csrf_protected_decisions(client: TestClient) -> None:
    async def seed() -> tuple[str, UUID, UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            accepted_workspace = Workspace(
                organization_id=ORG_ID,
                slug="offer-accepted-team",
                name="Команда для принятия",
                kind="corporate",
            )
            rejected_workspace = Workspace(
                organization_id=ORG_ID,
                slug="offer-rejected-team",
                name="Команда для отклонения",
                kind="corporate",
            )
            db.add_all((accepted_workspace, rejected_workspace))
            await db.flush()
            accepted_invitation = WorkspaceInvitation(
                workspace_id=accepted_workspace.id,
                target_contact="offer-owner@example.test",
                invited_role="member",
                created_by_user_id=USER_ID,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
            rejected_invitation = WorkspaceInvitation(
                workspace_id=rejected_workspace.id,
                target_contact="offer-owner@example.test",
                invited_role="admin",
                created_by_user_id=USER_ID,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
            db.add_all((accepted_invitation, rejected_invitation))
            await db.flush()
            accepted_offer = WorkspaceJoinOffer(
                workspace_id=accepted_workspace.id,
                user_id=USER_ID,
                invitation_id=accepted_invitation.id,
                workspace_name=accepted_workspace.name,
                invited_role=accepted_invitation.invited_role,
                expires_at=accepted_invitation.expires_at,
            )
            rejected_offer = WorkspaceJoinOffer(
                workspace_id=rejected_workspace.id,
                user_id=USER_ID,
                invitation_id=rejected_invitation.id,
                workspace_name=rejected_workspace.name,
                invited_role=rejected_invitation.invited_role,
                expires_at=rejected_invitation.expires_at,
            )
            db.add_all((accepted_offer, rejected_offer))
            session = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=WORKSPACE_ID,
                device_id=DEVICE_ID,
                provider="yandex",
            )
            db.add(
                AuthSessionDeviceBinding(
                    auth_session_id=session.id,
                    registered_device_id=DEVICE_ID,
                    device_state="trusted",
                    last_heartbeat_at=datetime.now(UTC),
                )
            )
            await db.commit()
            return session.token, session.id, accepted_offer.id, rejected_offer.id

    import asyncio

    token, session_id, accepted_offer_id, rejected_offer_id = asyncio.run(seed())
    csrf = issue_csrf_token(session_id=session_id, secret=client.app.state.web_csrf_secret)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, token)

    listed = client.get("/settings/join-offers")
    assert listed.status_code == 200
    assert {offer["workspace_name"] for offer in listed.json()["offers"]} == {
        "Команда для принятия",
        "Команда для отклонения",
    }
    assert "offer-owner@example.test" not in listed.text

    settings = client.get("/settings")
    assert settings.status_code == 200
    assert "Приглашения в команды" in settings.text
    assert "Команда для принятия" in settings.text
    assert "offer-owner@example.test" not in settings.text

    missing_csrf = client.post(f"/settings/join-offers/{accepted_offer_id}/accept")
    assert missing_csrf.status_code == 403

    accepted = client.post(
        f"/settings/join-offers/{accepted_offer_id}/accept",
        headers={"X-CSRF-Token": csrf},
    )
    assert accepted.status_code == 200
    assert accepted.json() == {"status": "accepted", "idempotent": False}
    replay = client.post(
        f"/settings/join-offers/{accepted_offer_id}/accept",
        headers={"X-CSRF-Token": csrf},
    )
    assert replay.status_code == 200
    assert replay.json() == {"status": "accepted", "idempotent": True}
    rejected = client.post(
        f"/settings/join-offers/{rejected_offer_id}/reject",
        headers={"X-CSRF-Token": csrf},
    )
    assert rejected.status_code == 200
    assert rejected.json() == {"status": "rejected", "idempotent": False}

    async def load() -> tuple[WorkspaceJoinOffer, WorkspaceJoinOffer, WorkspaceMembership | None]:
        async with client.app_state["sessionmaker"]() as db:
            accepted_offer = await db.get(WorkspaceJoinOffer, accepted_offer_id)
            rejected_offer = await db.get(WorkspaceJoinOffer, rejected_offer_id)
            assert accepted_offer is not None
            assert rejected_offer is not None
            membership = await db.get(
                WorkspaceMembership,
                {"workspace_id": accepted_offer.workspace_id, "user_id": USER_ID},
            )
            return accepted_offer, rejected_offer, membership

    accepted_offer, rejected_offer, membership = asyncio.run(load())
    assert accepted_offer.status == "accepted"
    assert rejected_offer.status == "rejected"
    assert membership is not None
    assert membership.status == "active"
