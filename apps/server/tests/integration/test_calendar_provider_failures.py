import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from tests.contract.test_ingest_openapi_contract import auth_headers
from twobrain_rec_server.calendar.sync import record_source_sync_failure
from twobrain_rec_server.db.models import CalendarSource


def test_provider_timeout_marks_calendar_stale_without_blocking_meeting_creation(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    _mark_failure(client, source_id, "provider_timeout")

    listed = client.get("/api/v1/calendar/sources", headers=auth_headers())
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-provider-down", "duration_seconds": 600},
    )

    source = listed.json()["sources"][0]
    assert source["sync_state"] == "stale"
    assert source["safe_error_code"] == "provider_timeout"
    assert meeting.status_code == 200


def _mark_failure(client, source_id: UUID, reason: str) -> None:
    sessionmaker = client.app_state["sessionmaker"]

    async def mark() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            source.last_successful_sync_at = datetime.now(UTC) - timedelta(minutes=30)
            record_source_sync_failure(source, reason=reason, now=datetime.now(UTC))
            await session.commit()

    asyncio.run(mark())
