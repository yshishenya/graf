import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fakes.auth_providers import fake_provider_map
from twobrain_rec_server.auth.audit import write_auth_audit_event
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.db.models import (
    AuthAuditEvent,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceAuthPolicy,
    WorkspaceConsentCopy,
    WorkspaceMembership,
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
            "X-Workspace-Id": str(WORKSPACE_ID),
            "Authorization": f"Bearer {callback_payload['session_token']}",
        },
    )
    assert me.status_code == 200
    me_payload = me.json()
    assert me_payload["active_session_id"] == callback_payload["active_session_id"]
    assert me_payload["policy"]["workspace_id"] == str(WORKSPACE_ID)
    providers = me_payload["linked_providers"]
    assert len(providers) == 1
    assert providers[0]["provider"] == "yandex"
    assert providers[0]["provider_subject"] == "test-ya-user"
    assert providers[0]["is_primary"] is True
    assert providers[0]["confirmed_at"] is not None

    reused = client.get(
        "/api/v1/auth/callback/yandex",
        params={
            "state": state_nonce,
            "code": "TEST-YA-USER",
        },
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


def test_provider_callback_requires_workspace_enrollment_policy(monkeypatch, client: TestClient) -> None:
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

    assert response.status_code == 403
    assert response.json()["code"] == "workspace_enrollment_required"
    events = _load_auth_audit_events(client)
    failures = [event for event in events if event.event_type == "provider_callback_failed"]
    assert len(failures) == 1
    assert failures[0].metadata_json["error_code"] == "workspace_enrollment_required"


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


def test_auth_link_accepts_candidate_phone(monkeypatch, client: TestClient) -> None:
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
        headers={"Authorization": f"Bearer {callback_payload['session_token']}", "X-Workspace-Id": str(WORKSPACE_ID)},
        json={
            "candidate_provider": "vk",
            "candidate_provider_subject": "VK-CANDIDATE",
            "candidate_phone": "+79990001111",
            "expected_workspace_id": str(WORKSPACE_ID),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "confirmed"
    assert payload["provider"] == "vk"
    linked_user_id = callback_payload["user_id"]

    events = _load_auth_audit_events(client)
    link_events = [event for event in events if event.event_type == "provider_link_confirmed"]
    assert len(link_events) == 1
    link_event = link_events[0]
    assert link_event.outcome == "success"
    assert str(link_event.user_id) == linked_user_id
    assert str(link_event.actor_user_id) == linked_user_id
    assert link_event.metadata_json["link_status"] == "confirmed"


def test_auth_link_conflict_persists_metadata_only_audit(monkeypatch, client: TestClient) -> None:
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
            await db.flush()
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
        headers={"Authorization": f"Bearer {callback_payload['session_token']}", "X-Workspace-Id": str(WORKSPACE_ID)},
        json={
            "candidate_provider": "vk",
            "candidate_provider_subject": "vk-conflict-subject",
            "expected_workspace_id": str(WORKSPACE_ID),
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "link_conflict"
    events = _load_auth_audit_events(client)
    conflict_events = [event for event in events if event.event_type == "provider_link_conflict"]
    assert len(conflict_events) == 1
    assert conflict_events[0].outcome == "failure"
    assert conflict_events[0].metadata_json == {"error_code": "link_conflict"}


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
    unbound_device_id = uuid4()

    async def seed_unbound_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                RegisteredDevice(
                    id=unbound_device_id,
                    workspace_id=WORKSPACE_ID,
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
        "X-Workspace-Id": str(WORKSPACE_ID),
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
            await db.flush()
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
