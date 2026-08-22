from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.csrf import issue_csrf_token, require_csrf_token
from twobrain_rec_server.cabinet.web_routes.calendar_helpers import calendar_disconnect_result
from twobrain_rec_server.db.models import CalendarCredentialEnvelope, CalendarSource


def _connect(client) -> UUID:
    response = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "synthetic-owner@example.test",
            "credential_input": "synthetic-calendar-secret",
        },
    )
    assert response.status_code == 201
    return UUID(response.json()["source"]["source_id"])


def test_calendar_mutations_keep_csrf_bound_to_the_authenticated_subject() -> None:
    subject = UUID("40000000-0000-0000-0000-000000000001")
    token = issue_csrf_token(session_id=subject, secret="synthetic-csrf-secret")
    require_csrf_token(token, session_id=subject, secret="synthetic-csrf-secret")

    try:
        require_csrf_token(token, session_id=UUID(int=0), secret="synthetic-csrf-secret")
    except ProblemDetail as error:
        assert error.code == "csrf_token_invalid"
    else:  # pragma: no cover - assertion guard
        raise AssertionError("calendar mutation CSRF must be subject-bound")


def test_calendar_connect_validates_before_persisting_and_never_echoes_secret(client) -> None:
    response = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "synthetic-owner@example.test",
            "credential_input": "synthetic-calendar-secret",
        },
    )

    assert response.status_code == 201
    assert "synthetic-calendar-secret" not in response.text
    assert response.json()["source"]["credential_state"] == "sealed"
    assert response.json()["calendars"]


def test_calendar_source_ownership_fails_closed_without_existence_leakage(client) -> None:
    source_id = _connect(client)
    foreign_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    missing = client.get(f"/api/v1/calendar/sources/{foreign_id}", headers=auth_headers())
    assert missing.status_code == 404
    assert missing.json()["code"] == "calendar_source_not_found"
    assert str(source_id) not in missing.text


def test_calendar_disconnect_is_idempotent_and_removes_source_from_active_list(client) -> None:
    source_id = _connect(client)
    first = client.post(f"/api/v1/calendar/sources/{source_id}/disconnect", headers=auth_headers())
    second = client.post(f"/api/v1/calendar/sources/{source_id}/disconnect", headers=auth_headers())
    active = client.get("/api/v1/calendar/sources", headers=auth_headers())

    assert first.status_code == second.status_code == 200
    assert first.json()["credentials_purged"] is True
    assert second.json()["credentials_purged"] is True
    assert all(row["source_id"] != str(source_id) for row in active.json()["sources"])


def test_google_disconnect_is_local_and_never_calls_provider(client, monkeypatch) -> None:
    source_id = _connect(client)
    sessionmaker = client.app_state["sessionmaker"]

    async def mark_google() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            source.provider_family = "google_calendar"
            source.auth_mode = "oauth"
            await session.commit()

    asyncio.run(mark_google())

    async def provider_call_must_not_happen(*args, **kwargs):
        raise AssertionError("disconnect must not call Google")

    monkeypatch.setattr(
        "twobrain_rec_server.calendar.google.UrlLibGoogleHttpClient.request",
        provider_call_must_not_happen,
    )

    disconnected = client.post(
        f"/api/v1/calendar/sources/{source_id}/disconnect", headers=auth_headers()
    )

    assert disconnected.status_code == 200
    assert disconnected.json()["external_revoke"] == "not_applicable"

    async def read_local_purge() -> tuple[str, str, bytes]:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            envelope = await session.scalar(
                select(CalendarCredentialEnvelope).where(
                    CalendarCredentialEnvelope.calendar_source_id == source_id
                )
            )
            return source.connection_state, source.credential_state, envelope.sealed_payload

    assert asyncio.run(read_local_purge()) == ("disconnected", "purged", b"")


def test_web_disconnect_result_depends_only_on_local_cleanup() -> None:
    assert (
        calendar_disconnect_result(
            {
                "connection_state": "disconnected",
                "credentials_purged": True,
                "unmatched_future_cache_purged": True,
                "external_revoke": "failed",
            }
        )
        == "success"
    )
