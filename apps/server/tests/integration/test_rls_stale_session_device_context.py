from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from tests.contract.test_auth_contracts import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, REVOKED_DEVICE_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.db.models import AuthSession


def test_expired_auth_session_is_rejected_before_tenant_rows_are_available(client) -> None:
    raw_token = "expired-rls-session-token"

    async def seed_expired_session() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                AuthSession(
                    id=uuid4(),
                    user_id=USER_ID,
                    workspace_id=WORKSPACE_ID,
                    device_id=DEVICE_ID,
                    provider="rls-test",
                    session_token_hash=hash_token(raw_token),
                    status="active",
                    issued_at=datetime.now(UTC) - timedelta(days=2),
                    expires_at=datetime.now(UTC) - timedelta(days=1),
                )
            )
            await db.commit()

    client.portal.call(seed_expired_session)

    response = client.post(
        "/api/v1/meetings",
        headers={
            "Authorization": f"Bearer {raw_token}",
            "X-Workspace-Id": str(WORKSPACE_ID),
            "X-Device-Id": str(DEVICE_ID),
        },
        json={"local_recording_id": "expired-session-denied", "duration_seconds": 60},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "auth_session_expired"


def test_revoked_device_context_still_denies_sessionless_headers(client) -> None:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers() | {"X-Device-Id": str(REVOKED_DEVICE_ID)},
        json={"local_recording_id": "revoked-header-denied", "duration_seconds": 60},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "device_revoked"
