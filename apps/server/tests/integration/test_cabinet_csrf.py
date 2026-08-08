from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from tests.contract.test_calendar_context_contract import _seed_calendar_event
from tests.contract.test_ingest_openapi_contract import auth_headers
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
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.get("/meetings")

    assert response.status_code == 200
    assert '<meta name="csrf-token"' in response.text
    assert str(client.app.state.web_csrf_secret) not in response.text


def test_cookie_authenticated_deletion_request_requires_csrf_token(client) -> None:
    seeds = seed_cabinet_meetings(client)
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_token_missing"


def test_cookie_authenticated_deletion_request_rejects_stale_csrf_token(client) -> None:
    seeds = seed_cabinet_meetings(client)
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
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
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers={"X-CSRF-Token": csrf_token},
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )

    assert response.status_code == 202
    assert response.json()["meeting_id"] == str(seeds.ready_id)
    assert response.json()["report_url"].endswith("/deletion-report")


def test_native_session_header_can_ack_local_purge_without_weakening_browser_csrf(client) -> None:
    seeds = seed_cabinet_meetings(client)
    deletion = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    assert deletion.status_code == 202
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    task = client.get("/api/v1/desktop/local-purge-tasks").json()["tasks"][0]
    payload = {
        "state": "acknowledged",
        "reason_code": "local_artifacts_deleted",
        "client_version": "native-session-regression",
    }

    cookie_only = client.post(task["ack_url"], json=payload)

    assert cookie_only.status_code == 403
    assert cookie_only.json()["code"] == "csrf_token_missing"

    client.cookies.clear()
    native = client.post(
        task["ack_url"],
        headers={"X-Auth-Session": OWNER_REVIEW_TEST_TOKEN},
        json=payload,
    )

    assert native.status_code == 200
    assert native.json()["state"] == "acknowledged"
    assert native.json()["task_id"] == task["task_id"]


@pytest.mark.parametrize("method", ["put", "delete"])
@pytest.mark.parametrize(
    ("csrf_headers", "expected_code"),
    [
        ({}, "csrf_token_missing"),
        ({"X-CSRF-Token": "stale"}, "csrf_token_invalid"),
    ],
)
def test_us3_cookie_calendar_context_mutations_require_session_bound_csrf(
    client,
    method: str,
    csrf_headers: dict[str, str],
    expected_code: str,
) -> None:
    # FR-038/FR-039, SC-011: owner PUT/DELETE retain the existing web CSRF boundary.
    meeting_id, event_id = _seed_calendar_context_mutation_target(client)
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    path = f"/api/v1/meetings/{meeting_id}/calendar-context"

    if method == "put":
        response = client.put(
            path,
            headers=csrf_headers,
            json={"event_id": event_id, "context_reason": "ambiguity_resolution"},
        )
    else:
        response = client.delete(path, headers=csrf_headers)

    assert response.status_code == 403
    assert response.json()["code"] == expected_code


def test_us3_cookie_owner_can_select_and_clear_with_session_bound_csrf(client) -> None:
    # FR-015/FR-038/FR-039/FR-051: valid CSRF allows distinct owner select/clear intent.
    meeting_id, event_id = _seed_calendar_context_mutation_target(client)
    session = client.portal.call(_seed_owner_review_session, client)
    csrf_token = issue_csrf_token(
        session_id=session.id,
        secret=str(client.app.state.web_csrf_secret),
    )
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    path = f"/api/v1/meetings/{meeting_id}/calendar-context"
    headers = {"X-CSRF-Token": csrf_token}

    selected = client.put(
        path,
        headers=headers,
        json={"event_id": event_id, "context_reason": "ambiguity_resolution"},
    )
    cleared = client.delete(path, headers=headers)

    assert selected.status_code == 200
    assert selected.json()["context_state"] == "matched_user"
    assert selected.json()["decision_source"] == "user"
    assert cleared.status_code == 200
    assert cleared.json()["context_state"] == "cleared_by_user"
    assert cleared.json()["reason_code"] == "user_cleared"


def _seed_calendar_context_mutation_target(client) -> tuple[str, str]:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": f"calendar-context-csrf-{uuid4()}",
            "duration_seconds": 1200,
            "started_at": "2026-07-01T09:00:00Z",
        },
    )
    assert meeting.status_code == 200
    return meeting.json()["meeting_id"], _seed_calendar_event(client)


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
