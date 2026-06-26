from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.db.models import AuthSession, AuthSessionDeviceBinding
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY

OWNER_REVIEW_TEST_TOKEN = "csrf-owner-review-session-cookie-token"


def test_owner_session_meetings_page_exposes_csrf_meta_without_secret(client) -> None:
    seed_cabinet_meetings(client)
    client.portal.call(_seed_owner_review_session, client)

    response = client.get(
        "/meetings",
        cookies={AUTH_SESSION_COOKIE_NAME: OWNER_REVIEW_TEST_TOKEN},
    )

    assert response.status_code == 200
    assert '<meta name="csrf-token"' in response.text
    assert str(client.app.state.web_csrf_secret) not in response.text


def test_cookie_authenticated_deletion_request_requires_csrf_token(client) -> None:
    seeds = seed_cabinet_meetings(client)
    client.portal.call(_seed_owner_review_session, client)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        cookies={AUTH_SESSION_COOKIE_NAME: OWNER_REVIEW_TEST_TOKEN},
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_token_missing"


def test_cookie_authenticated_deletion_request_rejects_stale_csrf_token(client) -> None:
    seeds = seed_cabinet_meetings(client)
    client.portal.call(_seed_owner_review_session, client)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        cookies={AUTH_SESSION_COOKIE_NAME: OWNER_REVIEW_TEST_TOKEN},
        headers={"X-CSRF-Token": "stale"},
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_token_invalid"


def test_cookie_authenticated_deletion_request_accepts_session_bound_csrf_token(client) -> None:
    seeds = seed_cabinet_meetings(client)
    session = client.portal.call(_seed_owner_review_session, client)
    csrf_token = issue_csrf_token(
        session_id=session.id,
        secret=str(client.app.state.web_csrf_secret),
    )

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        cookies={AUTH_SESSION_COOKIE_NAME: OWNER_REVIEW_TEST_TOKEN},
        headers={"X-CSRF-Token": csrf_token},
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )

    assert response.status_code == 202
    assert response.json()["meeting_id"] == str(seeds.ready_id)
    assert response.json()["report_url"].endswith("/deletion-report")


async def _seed_owner_review_session(client) -> AuthSession:
    async with client.app_state["sessionmaker"]() as db:
        session = AuthSession(
            id=uuid4(),
            user_id=USER_ID,
            workspace_id=WORKSPACE_ID,
            device_id=DEVICE_ID,
            provider="owner_review_csrf_test",
            session_token_hash=hash_token(OWNER_REVIEW_TEST_TOKEN),
            status="active",
            issued_at=datetime.now(UTC) - timedelta(minutes=1),
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
            claims_fingerprint="feature-058-csrf",
        )
        db.add(session)
        await db.flush()
        db.add(
            AuthSessionDeviceBinding(
                auth_session_id=session.id,
                registered_device_id=DEVICE_ID,
                device_state="trusted",
            )
        )
        await db.commit()
        return session
