from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.providers import (
    CalendarCatalogEntry,
    CalendarEventPage,
    CalendarProviderError,
)
from twobrain_rec_server.calendar.service import disconnect_calendar_source
from twobrain_rec_server.calendar.sync import run_calendar_provider_sync
from twobrain_rec_server.calendar.worker import (
    CALENDAR_SYNC_INTERVAL_SECONDS,
    calendar_maintenance_context,
    enqueue_due_yandex_calendar_syncs,
)
from twobrain_rec_server.db.models import (
    CalendarCredentialEnvelope,
    CalendarEventSnapshot,
    CalendarSource,
    ExternalCalendar,
)


class FixtureProvider:
    provider_family = "caldav_yandex"

    def __init__(
        self,
        pages: list[CalendarEventPage | Exception],
        catalog: tuple[CalendarCatalogEntry, ...] = (),
    ) -> None:
        self.pages = list(pages)
        self.catalog = catalog
        self.credentials: list[str] = []
        self.calls: list[dict[str, object]] = []

    async def validate(self, credential: str):  # pragma: no cover - protocol completeness
        raise NotImplementedError

    async def list_calendars(self, credential: str, *, page_token: str | None = None):
        self.credentials.append(credential)
        return self.catalog, None

    async def list_events(
        self,
        credential: str,
        *,
        calendar_id: str,
        time_min=None,
        time_max=None,
        page_token: str | None = None,
        sync_token: str | None = None,
    ) -> CalendarEventPage:
        self.credentials.append(credential)
        self.calls.append(
            {
                "calendar_id": calendar_id,
                "time_min": time_min,
                "time_max": time_max,
                "page_token": page_token,
                "sync_token": sync_token,
            }
        )
        result = self.pages.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _tenant_scope() -> TenantScope:
    from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID

    return TenantScope(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
    )


def _create_selected_source(client) -> UUID:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "synthetic-owner@example.test",
            "credential_input": "synthetic-calendar-secret",
        },
    )
    assert created.status_code == 201
    source_id = UUID(created.json()["source"]["source_id"])
    selected = client.patch(
        f"/api/v1/calendar/sources/{source_id}/selected-calendars",
        headers=auth_headers(),
        json={"selected_provider_calendar_ids": ["primary"]},
    )
    assert selected.status_code == 200
    return source_id


def test_yandex_due_source_is_queued_after_five_minutes(client) -> None:
    source_id = _create_selected_source(client)
    now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)

    async def age_source() -> None:
        async with client.app_state["sessionmaker"]() as session:
            source = await session.get(CalendarSource, source_id)
            source.sync_state = "synced"
            source.last_successful_sync_at = now - timedelta(seconds=CALENDAR_SYNC_INTERVAL_SECONDS)
            source.last_sync_finished_at = source.last_successful_sync_at
            await session.commit()

    asyncio.run(age_source())
    queued = asyncio.run(
        enqueue_due_yandex_calendar_syncs(
            client.app_state["sessionmaker"],
            calendar_maintenance_context(),
            now=now,
        )
    )

    async def read_source() -> CalendarSource:
        async with client.app_state["sessionmaker"]() as session:
            return await session.get(CalendarSource, source_id)

    source = asyncio.run(read_source())
    assert queued == 1
    assert source.sync_state == "queued"
    assert source.sync_horizon_end is not None


def test_provider_sync_unseals_server_secret_and_persists_pages(client) -> None:
    source_id = _create_selected_source(client)
    provider = FixtureProvider(
        [
            CalendarEventPage(
                events=(
                    normalize_calendar_event(
                        calendar_event_fixture(
                            provider_calendar_id="primary",
                            provider_event_id="synthetic-runtime-event",
                        )
                    ),
                ),
                next_sync_token="cursor-next",
            )
        ]
    )

    async def run() -> object:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
                now=datetime(2026, 8, 19, tzinfo=UTC),
            )
            await session.commit()
            return result

    result = asyncio.run(run())
    assert result.state == "synced"
    assert result.event_count == 1
    assert provider.credentials == [
        '{"username":"synthetic-owner@example.test","credential_input":"synthetic-calendar-secret"}'
    ]
    assert provider.calls[0]["sync_token"] is None
    assert provider.calls[0]["time_min"] == datetime(2026, 8, 12, tzinfo=UTC)
    assert provider.calls[0]["time_max"] == datetime(2027, 8, 19, tzinfo=UTC)

    async def read_back() -> tuple[CalendarSource, ExternalCalendar, int]:
        async with client.app_state["sessionmaker"]() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source_id)
            )
            count = await session.scalar(
                select(func.count())
                .select_from(CalendarEventSnapshot)
                .where(CalendarEventSnapshot.calendar_source_id == source_id)
            )
            return source, calendar, int(count or 0)

    source, calendar, count = asyncio.run(read_back())
    assert source.sync_state == "synced"
    assert calendar.sync_token == "cursor-next"
    assert count == 1


def test_provider_sync_seals_join_url_and_desktop_returns_only_validated_https(client) -> None:
    source_id = _create_selected_source(client)
    starts_at = datetime.now(UTC).replace(microsecond=0)
    event = normalize_calendar_event(
        calendar_event_fixture(
            provider_calendar_id="primary",
            provider_event_id="synthetic-join-event",
            starts_at=starts_at,
        )
    )
    provider = FixtureProvider([CalendarEventPage(events=(event,))])

    async def run() -> str:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
                now=starts_at,
            )
            assert result.state == "synced"
            await session.commit()
        async with client.app_state["sessionmaker"]() as session:
            snapshot = await session.scalar(
                select(CalendarEventSnapshot).where(
                    CalendarEventSnapshot.provider_event_id == "synthetic-join-event"
                )
            )
            return str(snapshot.provider_extras_json)

    stored = asyncio.run(run())
    response = client.get(
        "/api/v1/desktop/calendar/upcoming",
        params={"before_minutes": 15, "after_minutes": 60},
        headers=auth_headers(),
    )
    opened = client.get(
        f"/api/v1/calendar/events/{response.json()['events'][0]['event_id']}/open",
        headers=auth_headers(),
        follow_redirects=False,
    )

    assert "https://meet.example.test/synthetic-room" not in stored
    assert "sealed_open_meeting_url" in stored
    assert response.status_code == 200
    assert response.json()["events"][0]["open_meeting_url"] == (
        "https://meet.example.test/synthetic-room"
    )
    assert opened.status_code == 303
    assert opened.headers["location"] == "https://meet.example.test/synthetic-room"


def test_api_provider_validation_failure_does_not_persist_source(client) -> None:
    class FailingProvider:
        async def validate(self, credential: str):
            raise CalendarProviderError("provider_timeout", retryable=True)

    original_factory = client.app.state.calendar_provider_factory
    client.app.state.calendar_provider_factory = lambda _provider_family: FailingProvider()
    try:
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
    finally:
        client.app.state.calendar_provider_factory = original_factory

    assert response.status_code == 502
    assert response.json()["code"] == "provider_timeout"

    async def source_count() -> int:
        async with client.app_state["sessionmaker"]() as session:
            return int(await session.scalar(select(func.count()).select_from(CalendarSource)) or 0)

    assert asyncio.run(source_count()) == 0


def test_provider_sync_discovers_catalog_before_selection(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "synthetic-owner@example.test",
            "credential_input": "synthetic-calendar-secret",
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    provider = FixtureProvider(
        [],
        catalog=(
            CalendarCatalogEntry(
                provider_calendar_id="primary",
                display_label="Synthetic Calendar",
                primary=True,
            ),
        ),
    )

    async def run() -> object:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
                now=datetime(2026, 8, 19, tzinfo=UTC),
            )
            await session.commit()
            return result

    result = asyncio.run(run())
    assert result.state == "catalog_updated"
    assert result.calendar_count == 1

    async def read_back() -> ExternalCalendar:
        async with client.app_state["sessionmaker"]() as session:
            return await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source_id)
            )

    calendar = asyncio.run(read_back())
    assert calendar.display_label == "Synthetic Calendar"
    assert calendar.selected is False


def test_incremental_page_does_not_delete_unmentioned_snapshot(client) -> None:
    source_id = _create_selected_source(client)
    first = normalize_calendar_event(
        calendar_event_fixture(provider_calendar_id="primary", provider_event_id="event-a")
    )
    second = normalize_calendar_event(
        calendar_event_fixture(provider_calendar_id="primary", provider_event_id="event-b")
    )

    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source_id)
            )
            from twobrain_rec_server.calendar.sync import apply_calendar_sync_result

            await apply_calendar_sync_result(
                session,
                tenant_scope=_tenant_scope(),
                source=source,
                calendar=calendar,
                events=[first, second],
                sync_token="cursor-old",
                synced_at=datetime(2026, 8, 19, tzinfo=UTC),
            )
            await session.commit()

    asyncio.run(seed())
    provider = FixtureProvider(
        [
            CalendarEventPage(
                events=(first,),
                next_sync_token="cursor-new",
            )
        ]
    )

    async def run() -> None:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
                now=datetime(2026, 8, 19, 1, tzinfo=UTC),
            )
            assert result.state == "synced"
            await session.commit()

    asyncio.run(run())

    async def read_back() -> list[CalendarEventSnapshot]:
        async with client.app_state["sessionmaker"]() as session:
            return list(
                await session.scalars(
                    select(CalendarEventSnapshot).where(
                        CalendarEventSnapshot.calendar_source_id == source_id
                    )
                )
            )

    snapshots = asyncio.run(read_back())
    assert {snapshot.provider_event_id for snapshot in snapshots} == {"event-a", "event-b"}
    assert all(snapshot.source_deleted_at is None for snapshot in snapshots)


def test_cursor_invalidation_retries_as_full_sync_and_replaces_stale_snapshot(client) -> None:
    source_id = _create_selected_source(client)
    stale = normalize_calendar_event(
        calendar_event_fixture(
            provider_calendar_id="primary",
            provider_event_id="event-before-cursor-reset",
            starts_at=datetime(2026, 8, 21, 9, tzinfo=UTC),
        )
    )
    current = normalize_calendar_event(
        calendar_event_fixture(
            provider_calendar_id="primary",
            provider_event_id="event-after-cursor-reset",
            starts_at=datetime(2026, 8, 22, 9, tzinfo=UTC),
        )
    )

    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source_id)
            )
            from twobrain_rec_server.calendar.sync import apply_calendar_sync_result

            await apply_calendar_sync_result(
                session,
                tenant_scope=_tenant_scope(),
                source=source,
                calendar=calendar,
                events=[stale],
                sync_token="cursor-old",
                synced_at=datetime(2026, 8, 19, tzinfo=UTC),
            )
            await session.commit()

    asyncio.run(seed())
    provider = FixtureProvider(
        [
            CalendarProviderError("cursor_invalid"),
            CalendarEventPage(events=(current,), next_sync_token="cursor-new"),
        ]
    )
    sync_started_at = datetime(2026, 8, 20, tzinfo=UTC)

    async def run() -> object:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
                now=sync_started_at,
            )
            await session.commit()
            return result

    result = asyncio.run(run())
    assert result.state == "synced"
    assert [call["sync_token"] for call in provider.calls] == ["cursor-old", None]
    assert provider.calls[0]["time_min"] is None
    assert provider.calls[0]["time_max"] is None
    assert provider.calls[1]["time_min"] == datetime(2026, 8, 13, tzinfo=UTC)
    assert provider.calls[1]["time_max"] == datetime(2027, 8, 20, tzinfo=UTC)

    async def read_back() -> tuple[ExternalCalendar, list[CalendarEventSnapshot]]:
        async with client.app_state["sessionmaker"]() as session:
            calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source_id)
            )
            snapshots = list(
                await session.scalars(
                    select(CalendarEventSnapshot).where(
                        CalendarEventSnapshot.calendar_source_id == source_id
                    )
                )
            )
            return calendar, snapshots

    calendar, snapshots = asyncio.run(read_back())
    by_provider_id = {snapshot.provider_event_id: snapshot for snapshot in snapshots}
    assert calendar.sync_token == "cursor-new"
    assert by_provider_id["event-before-cursor-reset"].source_deleted_at == sync_started_at
    assert by_provider_id["event-after-cursor-reset"].source_deleted_at is None


def test_provider_sync_retries_retryable_read_with_bounded_backoff(client, monkeypatch) -> None:
    source_id = _create_selected_source(client)
    event = normalize_calendar_event(
        calendar_event_fixture(
            provider_calendar_id="primary",
            provider_event_id="event-after-retry",
        )
    )
    provider = FixtureProvider(
        [
            CalendarProviderError("rate_limited", retryable=True),
            CalendarEventPage(events=(event,), next_sync_token="cursor-after-retry"),
        ]
    )
    delays: list[float] = []

    async def no_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("twobrain_rec_server.calendar.sync.asyncio.sleep", no_sleep)

    async def run() -> object:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            await session.commit()
            return result

    result = asyncio.run(run())

    assert result.state == "synced"
    assert len(provider.calls) == 2
    assert len(delays) == 1
    assert 0.375 <= delays[0] <= 0.625


def test_provider_sync_rejects_repeated_event_page_token_without_partial_write(client) -> None:
    source_id = _create_selected_source(client)
    provider = FixtureProvider(
        [
            CalendarEventPage(next_page_token="repeated"),
            CalendarEventPage(next_page_token="repeated"),
        ]
    )

    async def run() -> object:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            await session.commit()
            return result

    result = asyncio.run(run())

    assert result.state == "failed"
    assert result.safe_reason_code == "invalid_payload"
    assert len(provider.calls) == 2


def test_sync_fails_closed_after_disconnect_without_provider_call(client) -> None:
    source_id = _create_selected_source(client)
    disconnected = client.post(
        f"/api/v1/calendar/sources/{source_id}/disconnect",
        headers=auth_headers(),
    )
    assert disconnected.status_code == 200
    provider = FixtureProvider([CalendarEventPage()])

    async def run() -> object:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            await session.commit()
            return result

    result = asyncio.run(run())
    assert result.state == "failed_closed"
    assert provider.calls == []


def test_disconnect_can_commit_during_provider_read_and_blocks_late_sync_write(client) -> None:
    source_id = _create_selected_source(client)
    event = normalize_calendar_event(
        calendar_event_fixture(
            provider_calendar_id="primary",
            provider_event_id="must-not-persist-after-disconnect",
        )
    )

    class DisconnectingProvider(FixtureProvider):
        async def list_events(self, credential: str, **kwargs) -> CalendarEventPage:
            async with client.app_state["sessionmaker"]() as other_session:
                await disconnect_calendar_source(
                    other_session,
                    _tenant_scope(),
                    source_id,
                )
            return CalendarEventPage(events=(event,))

    async def run() -> object:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=DisconnectingProvider([]),
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            await session.commit()
            return result

    result = asyncio.run(run())

    assert result.state == "failed_closed"

    async def read_back() -> tuple[str, int]:
        async with client.app_state["sessionmaker"]() as session:
            source = await session.get(CalendarSource, source_id)
            count = await session.scalar(
                select(func.count())
                .select_from(CalendarEventSnapshot)
                .where(
                    CalendarEventSnapshot.provider_event_id == "must-not-persist-after-disconnect"
                )
            )
            return source.connection_state, int(count or 0)

    assert asyncio.run(read_back()) == ("disconnected", 0)


def test_sync_does_not_read_purged_or_corrupt_credentials(client) -> None:
    source_id = _create_selected_source(client)
    provider = FixtureProvider([CalendarEventPage()])

    async def corrupt() -> None:
        async with client.app_state["sessionmaker"]() as session:
            envelope = await session.scalar(
                select(CalendarCredentialEnvelope).where(
                    CalendarCredentialEnvelope.calendar_source_id == source_id
                )
            )
            envelope.sealed_payload = b""
            await session.commit()

    asyncio.run(corrupt())

    async def run() -> object:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            await session.commit()
            return result

    result = asyncio.run(run())
    assert result.state == "failed"
    assert result.safe_reason_code == "invalid_credentials"
    assert provider.calls == []


@pytest.mark.parametrize(
    ("safe_code", "expected_credential_state"),
    [
        ("invalid_credentials", "invalid"),
        ("revoked_access", "invalid"),
        ("provider_timeout", "sealed"),
        ("rate_limited", "sealed"),
        ("invalid_payload", "sealed"),
    ],
)
def test_provider_failures_leave_safe_state_without_provider_detail(
    client, safe_code: str, expected_credential_state: str
) -> None:
    source_id = _create_selected_source(client)
    provider = FixtureProvider([CalendarProviderError(safe_code)])

    async def run() -> object:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
                now=datetime(2026, 8, 19, tzinfo=UTC),
            )
            await session.commit()
            return result

    result = asyncio.run(run())
    assert result.state == "failed"
    assert result.safe_reason_code == safe_code
    assert provider.calls

    async def read_back() -> CalendarSource:
        async with client.app_state["sessionmaker"]() as session:
            return await session.get(CalendarSource, source_id)

    source = asyncio.run(read_back())
    assert source.credential_state == expected_credential_state
    assert source.last_safe_error_code == safe_code
    assert "private" not in source.last_safe_error_code


def test_unexpected_provider_failure_cannot_leave_source_syncing(client) -> None:
    source_id = _create_selected_source(client)
    provider = FixtureProvider([RuntimeError("synthetic private provider failure")])

    async def run() -> object:
        async with client.app_state["sessionmaker"]() as session:
            result = await run_calendar_provider_sync(
                session,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            await session.commit()
            return result

    result = asyncio.run(run())

    assert result.state == "failed"
    assert result.safe_reason_code == "provider_unavailable"

    async def read_back() -> CalendarSource:
        async with client.app_state["sessionmaker"]() as session:
            return await session.get(CalendarSource, source_id)

    source = asyncio.run(read_back())
    assert source.sync_state == "failed"
    assert source.last_safe_error_code == "provider_unavailable"
    assert "synthetic private provider failure" not in str(source.__dict__)


def test_worker_unexpected_persistence_failure_cannot_leave_source_syncing(
    client, monkeypatch
) -> None:
    import twobrain_rec_server.calendar.worker as calendar_worker
    from twobrain_rec_server.config import Settings
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext

    source_id = _create_selected_source(client)
    sessionmaker = client.app_state["sessionmaker"]

    async def queue_source() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            source.sync_state = "queued"
            source.last_successful_sync_at = datetime(2026, 8, 19, tzinfo=UTC)
            await session.commit()

    async def fail_after_provider_read(*args, **kwargs) -> None:
        raise RuntimeError("synthetic private persistence failure")

    asyncio.run(queue_source())
    monkeypatch.setattr(calendar_worker, "provider_for_source", lambda source, settings: object())
    monkeypatch.setattr(calendar_worker, "_credential_key", lambda settings: b"synthetic-key")
    monkeypatch.setattr(calendar_worker, "run_calendar_provider_sync", fail_after_provider_read)

    context = MaintenanceTenantContext(
        operation_name=calendar_worker.CALENDAR_SYNC_OPERATION,
        actor_id="graf-maintenance",
        reason_category="calendar_provider_sync",
        feature_area="calendar",
    )
    with pytest.raises(RuntimeError):
        asyncio.run(calendar_worker.run_one_calendar_sync(sessionmaker, Settings(), context))

    async def read_back() -> CalendarSource:
        async with sessionmaker() as session:
            return await session.get(CalendarSource, source_id)

    source = asyncio.run(read_back())
    assert source.sync_state == "stale"
    assert source.last_sync_finished_at is not None
    assert source.last_safe_error_code == "provider_unavailable"
    assert "synthetic private persistence failure" not in str(source.__dict__)
