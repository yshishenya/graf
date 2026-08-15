from __future__ import annotations

from contextlib import AbstractAsyncContextManager

from tests.contract.test_auth_contracts import auth_headers
from tests.fakes.auth_contexts import AUTH_BOOTSTRAP_WORKSPACE_ID, WORKSPACE_ID
from twobrain_rec_server.auth.audit import denied_auth_access_metadata


class TrackingSessionFactory:
    def __init__(self, sessionmaker) -> None:
        self._sessionmaker = sessionmaker
        self.contexts: list[dict[str, str]] = []

    def __call__(self) -> AbstractAsyncContextManager:
        return _TrackingSession(self._sessionmaker(), self.contexts)


class _TrackingSession:
    def __init__(self, context_manager, contexts: list[dict[str, str]]) -> None:
        self._context_manager = context_manager
        self._contexts = contexts
        self._session = None

    async def __aenter__(self):
        self._session = await self._context_manager.__aenter__()
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        assert self._session is not None
        self._contexts.append(dict(self._session.info.get("tenant_context", {})))
        return await self._context_manager.__aexit__(exc_type, exc, tb)


def test_public_auth_provider_list_sets_workspace_context(client) -> None:
    tracking = TrackingSessionFactory(client.app_state["sessionmaker"])
    client.app.state.db_sessionmaker = tracking

    response = client.get("/api/v1/auth/providers")

    assert response.status_code == 200
    assert tracking.contexts[-1]["app.context_kind"] == "auth_public"
    assert tracking.contexts[-1]["app.workspace_id"] == str(AUTH_BOOTSTRAP_WORKSPACE_ID)


def test_authenticated_auth_policy_update_sets_request_context(client) -> None:
    tracking = TrackingSessionFactory(client.app_state["sessionmaker"])
    client.app.state.db_sessionmaker = tracking

    response = client.patch(
        "/api/v1/auth/policy",
        params={"workspace_id": str(WORKSPACE_ID)},
        headers=auth_headers(),
        json={"allow_vk": False},
    )

    assert response.status_code == 200
    assert tracking.contexts[-1]["app.context_kind"] == "request"
    assert tracking.contexts[-1]["app.workspace_id"] == str(WORKSPACE_ID)


def test_denied_auth_access_metadata_is_content_safe() -> None:
    metadata = denied_auth_access_metadata(
        route_name="auth_me",
        outcome="cross_tenant_read_not_found_or_empty",
        reason_code="workspace_scope_denied",
        workspace_id=str(WORKSPACE_ID),
        provider_subject="foreign-subject",
        session_token="secret-token",
        transcript_text="not allowed",
    )

    assert metadata == {
        "route_name": "auth_me",
        "outcome": "cross_tenant_read_not_found_or_empty",
        "reason_code": "workspace_scope_denied",
        "workspace_id": str(WORKSPACE_ID),
    }
