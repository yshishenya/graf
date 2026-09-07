"""F251: scheduling, catalog and publication race regressions."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from tests.fixtures.calendar import calendar_event_fixture
from tests.integration.test_calendar_provider_runtime import (
    FixtureProvider,
    _create_selected_source,
    _tenant_scope,
)
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.providers import CalendarCatalogEntry, CalendarEventPage
from twobrain_rec_server.calendar.service import replace_selected_calendars, request_source_sync
from twobrain_rec_server.calendar.sync import run_calendar_provider_sync
from twobrain_rec_server.calendar.worker import (
    calendar_maintenance_context,
    enqueue_due_calendar_syncs,
)
from twobrain_rec_server.db.models import CalendarEventSnapshot, CalendarSource, ExternalCalendar


@pytest.mark.parametrize("family", ["google_calendar", "caldav_yandex"])
def test_both_calendar_providers_are_due_after_one_minute(client, family):
    source_id = _create_selected_source(client)
    now = datetime.now(UTC)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(CalendarSource, source_id)
            source.provider_family = family
            source.sync_state = "synced"
            source.last_sync_finished_at = now - timedelta(seconds=61)
            await db.commit()
        count = await enqueue_due_calendar_syncs(
            client.app_state["sessionmaker"], calendar_maintenance_context(), now=now
        )
        async with client.app_state["sessionmaker"]() as db:
            assert (await db.get(CalendarSource, source_id)).sync_state == "queued"
        assert count == 1

    asyncio.run(run())


def test_manual_retry_recovers_expired_claim_but_not_live_claim(client):
    source_id = _create_selected_source(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(CalendarSource, source_id)
            source.sync_state = "syncing"
            source.last_sync_started_at = datetime.now(UTC)
            await db.commit()
            assert (
                await request_source_sync(db, _tenant_scope(), source_id)
            ).sync_state == "syncing"
            source.last_sync_started_at = datetime.now(UTC) - timedelta(minutes=6)
            await db.commit()
            assert (
                await request_source_sync(db, _tenant_scope(), source_id)
            ).sync_state == "queued"

    asyncio.run(run())


def test_catalog_is_refreshed_while_existing_calendar_remains_selected(client):
    source_id = _create_selected_source(client)
    provider = FixtureProvider(
        [CalendarEventPage()],
        catalog=(
            CalendarCatalogEntry("primary", "Renamed"),
            CalendarCatalogEntry("new", "New calendar"),
        ),
    )

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            result = await run_calendar_provider_sync(
                db,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            assert result.state == "synced"
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            rows = list(
                await db.scalars(
                    select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source_id)
                )
            )
            assert {
                (r.provider_calendar_id, r.display_label, r.selected)
                for r in rows
                if r.visibility != "removed"
            } == {
                ("primary", "Renamed", True),
                ("new", "New calendar", False),
            }

    asyncio.run(run())


@pytest.mark.parametrize("change_during", ["catalog", "events"])
@pytest.mark.parametrize("provider_fails", [False, True])
def test_selection_change_fences_old_catalog_and_event_result(
    client, change_during, provider_fails
):
    source_id = _create_selected_source(client)
    event = normalize_calendar_event(
        calendar_event_fixture(provider_calendar_id="primary", provider_event_id="late-event")
    )

    async def change_selection():
        async with client.app_state["sessionmaker"]() as other:
            source = await other.get(CalendarSource, source_id)
            await replace_selected_calendars(other, _tenant_scope(), source, [])
            await other.commit()

    class ChangingProvider(FixtureProvider):
        async def list_calendars(self, credential, *, page_token=None):
            if change_during == "catalog":
                await change_selection()
                if provider_fails:
                    raise RuntimeError("synthetic late error")
            return (CalendarCatalogEntry("primary", "STALE CATALOG"),), None

        async def list_events(self, credential, **kwargs):
            if change_during == "events":
                await change_selection()
                if provider_fails:
                    raise RuntimeError("synthetic late error")
            return CalendarEventPage(events=(event,))

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            result = await run_calendar_provider_sync(
                db,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=ChangingProvider([]),
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            assert result.state != "synced"
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(CalendarSource, source_id)
            assert source.selected_calendar_count == 0
            assert source.sync_state == "never_synced"
            assert source.last_safe_error_code is None
            cal = await db.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source_id)
            )
            assert cal.display_label != "STALE CATALOG"
            assert not list(
                await db.scalars(
                    select(CalendarEventSnapshot).where(
                        CalendarEventSnapshot.calendar_source_id == source_id
                    )
                )
            )

    asyncio.run(run())


@pytest.mark.parametrize("family", ["google_calendar", "caldav_yandex"])
def test_expired_worker_is_requeued_automatically(client, family):
    source_id = _create_selected_source(client)
    now = datetime.now(UTC)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(CalendarSource, source_id)
            source.provider_family = family
            source.sync_state = "syncing"
            source.last_sync_started_at = now - timedelta(minutes=6)
            await db.commit()
        assert (
            await enqueue_due_calendar_syncs(
                client.app_state["sessionmaker"], calendar_maintenance_context(), now=now
            )
            == 1
        )
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(CalendarSource, source_id)
            assert source.sync_state == "queued"
            assert source.last_sync_started_at == now

    asyncio.run(run())


@pytest.mark.parametrize("by_uid", [False, True])
def test_undated_tombstone_cancels_persisted_event(client, by_uid):
    source_id = _create_selected_source(client)
    event = normalize_calendar_event(
        calendar_event_fixture(
            provider_calendar_id="primary",
            provider_event_id="deleted-event",
            ical_uid="deleted-uid",
        )
    )
    provider = FixtureProvider([CalendarEventPage(events=(event,), next_sync_token="cursor")])

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            assert (
                await run_calendar_provider_sync(
                    db,
                    tenant_scope=_tenant_scope(),
                    source_id=source_id,
                    provider=provider,
                    credential_encryption_key=client.app.state.credential_encryption_key,
                )
            ).state == "synced"
            await db.commit()
        tombstone = CalendarEventPage(
            deleted_ical_uids=("deleted-uid",) if by_uid else (),
            deleted_event_ids=() if by_uid else ("deleted-event",),
        )
        async with client.app_state["sessionmaker"]() as db:
            assert (
                await run_calendar_provider_sync(
                    db,
                    tenant_scope=_tenant_scope(),
                    source_id=source_id,
                    provider=FixtureProvider([tombstone]),
                    credential_encryption_key=client.app.state.credential_encryption_key,
                )
            ).state == "synced"
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            snapshot = await db.scalar(
                select(CalendarEventSnapshot).where(
                    CalendarEventSnapshot.calendar_source_id == source_id
                )
            )
            assert snapshot.source_status == "cancelled"
            assert snapshot.source_deleted_at is not None

    asyncio.run(run())


def test_google_owner_upgrade_uses_full_import_once_then_cursor(client):
    source_id = _create_selected_source(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(CalendarSource, source_id)
            source.provider_family = "google_calendar"
            calendar = await db.scalar(
                select(ExternalCalendar).where(
                    ExternalCalendar.calendar_source_id == source_id,
                    ExternalCalendar.selected.is_(True),
                )
            )
            calendar.sync_token = "legacy"
            await db.commit()
        for expected, token in [(None, "new"), ("new", "newer")]:
            provider = FixtureProvider([CalendarEventPage(next_sync_token=token)])
            async with client.app_state["sessionmaker"]() as db:
                result = await run_calendar_provider_sync(
                    db,
                    tenant_scope=_tenant_scope(),
                    source_id=source_id,
                    provider=provider,
                    credential_encryption_key=client.app.state.credential_encryption_key,
                )
                assert result.state == "synced"
                assert provider.calls[0]["sync_token"] == expected
                await db.commit()

    asyncio.run(run())


def test_reused_conference_link_on_different_dates_is_not_deduplicated():
    from twobrain_rec_server.calendar.service import dedupe_calendar_events

    start = datetime(2026, 9, 10, 9, tzinfo=UTC)
    events = [
        CalendarEventSnapshot(
            starts_at=start + timedelta(days=day),
            ends_at=start + timedelta(days=day, hours=1),
            conference_summary_json={"url_hashes": ["same-call"]},
        )
        for day in (0, 1)
    ]
    assert len(dedupe_calendar_events(events)) == 2


@pytest.mark.parametrize("error", ["provider_unavailable", "credential_encryption_unavailable"])
def test_restored_configuration_retries_previously_failed_closed_source(client, error):
    source_id = _create_selected_source(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(CalendarSource, source_id)
            source.sync_state = "failed_closed"
            source.last_safe_error_code = error
            source.last_sync_finished_at = datetime.now(UTC) - timedelta(minutes=2)
            await db.commit()
        assert (
            await enqueue_due_calendar_syncs(
                client.app_state["sessionmaker"], calendar_maintenance_context()
            )
            == 1
        )

    asyncio.run(run())


def test_google_refreshes_full_window_daily(client):
    source_id = _create_selected_source(client)
    now = datetime.now(UTC)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(CalendarSource, source_id)
            source.provider_family = "google_calendar"
            source.capabilities_json = {
                "owner_content_version": 1,
                "last_full_sync_at": (now - timedelta(days=1, seconds=1)).isoformat(),
            }
            calendar = await db.scalar(
                select(ExternalCalendar).where(
                    ExternalCalendar.calendar_source_id == source_id,
                    ExternalCalendar.selected.is_(True),
                )
            )
            calendar.sync_token = "old-window"
            await db.commit()
        provider = FixtureProvider([CalendarEventPage(next_sync_token="new-window")])
        async with client.app_state["sessionmaker"]() as db:
            result = await run_calendar_provider_sync(
                db,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=provider,
                credential_encryption_key=client.app.state.credential_encryption_key,
                now=now,
            )
            assert result.state == "synced"
            assert provider.calls[0]["sync_token"] is None
            assert provider.calls[0]["time_max"] == now + timedelta(days=365)
            await db.commit()

    asyncio.run(run())


def test_sync_keeps_preferred_call_link_and_does_not_delete_outside_window(client):
    from twobrain_rec_server.api.calendar import _open_meeting_url
    from twobrain_rec_server.calendar.conference_links import conference_link_dicts
    from twobrain_rec_server.calendar.sync import apply_calendar_sync_result, upsert_event_snapshot

    source_id = _create_selected_source(client)
    now = datetime.now(UTC)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(CalendarSource, source_id)
            calendar = await db.scalar(
                select(ExternalCalendar).where(
                    ExternalCalendar.calendar_source_id == source_id,
                    ExternalCalendar.selected.is_(True),
                )
            )
            source.sync_horizon_start = now
            source.sync_horizon_end = now + timedelta(days=30)
            event = normalize_calendar_event(
                calendar_event_fixture(
                    provider_event_id="outside",
                    starts_at=(now + timedelta(days=60)),
                    ends_at=(now + timedelta(days=60, hours=1)),
                    conference_links=conference_link_dicts(
                        ("description", "https://agenda.example.test/0 https://zoom.us/j/123456789")
                    ),
                )
            )
            snapshot = await upsert_event_snapshot(
                db,
                _tenant_scope(),
                source,
                calendar,
                event,
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            assert (
                _open_meeting_url(snapshot, client.app.state.credential_encryption_key)
                == "https://zoom.us/j/123456789"
            )
            await apply_calendar_sync_result(
                db,
                tenant_scope=_tenant_scope(),
                source=source,
                calendar=calendar,
                events=[],
                sync_token=None,
                synced_at=now,
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            await db.flush()
            await db.refresh(snapshot)
            assert snapshot.source_deleted_at is None

    asyncio.run(run())


def test_policy_disable_during_read_blocks_late_publication(client):
    source_id = _create_selected_source(client)

    class DisablingProvider(FixtureProvider):
        async def list_events(self, credential, **kwargs):
            async with client.app_state["sessionmaker"]() as other:
                source = await other.get(CalendarSource, source_id)
                source.connection_state = "disabled_by_policy"
                await other.commit()
            return CalendarEventPage(events=(normalize_calendar_event(calendar_event_fixture()),))

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            result = await run_calendar_provider_sync(
                db,
                tenant_scope=_tenant_scope(),
                source_id=source_id,
                provider=DisablingProvider([]),
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            assert result.state == "failed_closed"
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            assert not list(
                await db.scalars(
                    select(CalendarEventSnapshot).where(
                        CalendarEventSnapshot.calendar_source_id == source_id
                    )
                )
            )
            assert (
                await db.get(CalendarSource, source_id)
            ).connection_state == "disabled_by_policy"

    asyncio.run(run())


@pytest.mark.parametrize("safe_code", ["invalid_payload", "provider_unavailable"])
def test_incomplete_provider_report_preserves_cached_events(client, safe_code):
    from twobrain_rec_server.calendar.providers import CalendarProviderError

    source_id = _create_selected_source(client)
    event = normalize_calendar_event(calendar_event_fixture(provider_calendar_id="primary"))
    now = event.starts_at - timedelta(hours=1)

    async def run():
        for page, expected in [
            (CalendarEventPage(events=(event,)), "synced"),
            (CalendarProviderError(safe_code), "failed"),
        ]:
            async with client.app_state["sessionmaker"]() as db:
                result = await run_calendar_provider_sync(
                    db, tenant_scope=_tenant_scope(), source_id=source_id,
                    provider=FixtureProvider([page]), now=now,
                    credential_encryption_key=client.app.state.credential_encryption_key,
                )
                assert result.state == expected
                await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            snapshots = list(await db.scalars(select(CalendarEventSnapshot).where(
                CalendarEventSnapshot.calendar_source_id == source_id
            )))
            assert len(snapshots) == 1
            assert snapshots[0].provider_event_id == event.provider_event_id
            assert snapshots[0].source_status != "cancelled"
            assert snapshots[0].source_deleted_at is None

    asyncio.run(run())
