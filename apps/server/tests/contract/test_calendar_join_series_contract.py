from twobrain_rec_server.api.calendar import router


def test_join_target_and_series_contracts_exist_without_replacing_upcoming():
    routes = {route.path for route in router.routes}
    assert "/api/v1/calendar/events/{event_id}/join-target" in routes
    assert "/api/v1/calendar/events/{event_id}/open" in routes
    assert "/api/v1/calendar/events/upcoming" in routes
    assert "/api/v1/calendar/overview" in routes
    assert "/api/v1/calendar/series/{series_key}/occurrences" in routes


def seed_series(client):
    import asyncio
    from datetime import UTC, datetime, timedelta

    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
    from tests.fixtures.calendar_settings import (
        calendar_settings_calendar,
        calendar_settings_snapshot,
        calendar_settings_source,
    )
    from twobrain_rec_server.calendar.credentials import generate_credential_key, seal_credential

    key = generate_credential_key()
    client.app.state.credential_encryption_key = key

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            source = calendar_settings_source()
            source.workspace_id = WORKSPACE_ID
            source.owner_user_id = USER_ID
            calendar = calendar_settings_calendar(source, selected=True)
            db.add(source)
            await db.flush()
            db.add(calendar)
            await db.flush()
            rows = []
            for n in range(12):
                row = calendar_settings_snapshot(
                    source,
                    calendar,
                    starts_at=datetime.now(UTC) + timedelta(days=n + 1),
                    provider_event_id=f"f279-{n}",
                )
                row.recurring_series_id = "synthetic-weekly"
                row.provider_extras_json = {
                    "sealed_open_meeting_url": seal_credential(
                        "https://meet.google.com/abc-defg-hij?pwd=synthetic", key
                    ).decode()
                }
                rows.append(row)
                db.add(row)
            other = calendar_settings_snapshot(
                source,
                calendar,
                starts_at=datetime.now(UTC) + timedelta(days=2),
                provider_event_id="f279-other",
            )
            other.recurring_series_id = "different-series"
            db.add(other)
            await db.commit()
            return str(rows[0].id), str(calendar.id), str(source.id)

    return asyncio.run(seed())


def test_join_resolves_without_redirect_and_rechecks_cancelled(client):
    import asyncio
    from uuid import UUID

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from twobrain_rec_server.db.models import CalendarEventSnapshot

    event, _, _ = seed_series(client)
    response = client.get(f"/api/v1/calendar/events/{event}/join-target", headers=auth_headers())
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["https_url"].endswith("?pwd=synthetic")

    async def cancel():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(CalendarEventSnapshot, UUID(event))
            row.source_status = "cancelled"
            await db.commit()

    asyncio.run(cancel())
    assert (
        client.get(
            f"/api/v1/calendar/events/{event}/join-target", headers=auth_headers()
        ).status_code
        == 404
    )


def test_overview_groups_before_limit_and_history_paginates(client):
    from tests.contract.test_ingest_openapi_contract import auth_headers

    seed_series(client)
    overview = client.get("/api/v1/calendar/overview?limit=2", headers=auth_headers())
    assert overview.status_code == 200, overview.text
    cards = overview.json()["cards"]
    assert len(cards) == 2
    assert cards[0]["series_key"] != cards[1]["series_key"]
    url = f"/api/v1/calendar/series/{cards[0]['series_key']}/occurrences"
    page = client.get(url, params={"limit": 5}, headers=auth_headers())
    assert page.status_code == 200, page.text
    body = page.json()
    ids = [x["event_id"] for x in body["occurrences"]]
    assert len(ids) == 5
    while body["next_cursor"]:
        body = client.get(
            url,
            params={
                "limit": 5,
                "cursor": body["next_cursor"],
                "from": body["coverage_range"]["from"],
                "to": body["coverage_range"]["to"],
            },
            headers=auth_headers(),
        ).json()
        ids += [x["event_id"] for x in body["occurrences"]]
    assert len(ids) == len(set(ids)) == 12
    bad = client.get(
        url,
        params={"from": "2026-01-01T00:00:00Z", "to": "2028-01-01T00:00:00Z"},
        headers=auth_headers(),
    )
    assert bad.status_code == 422
    html = client.get("/desktop/meetings", headers=auth_headers())
    assert html.status_code == 200, html.text[:100]
    assert html.text.count('data-calendar-series="') == 2
    assert "data-calendar-join=" in html.text


def test_hidden_fields_and_recordings_stay_scoped_to_occurrence(client):
    import asyncio
    from uuid import UUID

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
    from twobrain_rec_server.db.models import CalendarEventSnapshot, CalendarSettingsPreference

    event, _, _ = seed_series(client)
    recording_ids = []
    for n in range(2):
        response = client.post(
            "/api/v1/meetings",
            headers=auth_headers(),
            json={"local_recording_id": f"f279-recording-{n}", "duration_seconds": 900},
        )
        assert response.status_code == 200, response.text
        meeting = response.json()["meeting_id"]
        recording_ids.append(meeting)
        linked = client.put(
            f"/api/v1/meetings/{meeting}/calendar-context",
            headers=auth_headers(),
            json={"event_id": event, "context_reason": "manual_selection"},
        )
        assert linked.status_code == 200, linked.text

    async def hide():
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                CalendarSettingsPreference(
                    workspace_id=WORKSPACE_ID,
                    owner_user_id=USER_ID,
                    show_upcoming_time=False,
                    show_upcoming_title=False,
                )
            )
            row = await db.get(CalendarEventSnapshot, UUID(event))
            row.source_status = "cancelled"
            # A minimal cancelled provider occurrence no longer contains invitation metadata.
            row.conference_summary_json = {"meeting_link_present": False, "participant_count": 0}
            row.provider_extras_json = {}
            row.location = None
            row.open_meeting_available = False
            await db.commit()

    asyncio.run(hide())
    cards = client.get("/api/v1/calendar/overview", headers=auth_headers()).json()["cards"]
    key = cards[0]["series_key"]
    response = client.get(f"/api/v1/calendar/series/{key}/occurrences", headers=auth_headers())
    assert response.status_code == 200, response.text
    rows = response.json()["occurrences"]
    first = next(x for x in rows if x["event_id"] == event)
    assert {r["meeting_id"] for r in first["recordings"]} == set(recording_ids)
    assert first["cancelled"] is True and first["open_meeting_available"] is False
    assert all(
        x["starts_at"] is None
        and x["ends_at"] is None
        and x["title"] == "Название скрыто настройкой"
        for x in rows
    )
    assert all(not x["recordings"] for x in rows if x["event_id"] != event)


def test_unselected_calendar_removes_join_overview_and_history(client):
    import asyncio
    from uuid import UUID

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from twobrain_rec_server.db.models import ExternalCalendar

    event, calendar, _ = seed_series(client)
    key = client.get("/api/v1/calendar/overview", headers=auth_headers()).json()["cards"][0][
        "series_key"
    ]

    async def unselect():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(ExternalCalendar, UUID(calendar))
            row.selected = False
            await db.commit()

    asyncio.run(unselect())
    assert (
        client.get(
            f"/api/v1/calendar/events/{event}/join-target", headers=auth_headers()
        ).status_code
        == 404
    )
    assert client.get("/api/v1/calendar/overview", headers=auth_headers()).json()["cards"] == []
    assert (
        client.get(f"/api/v1/calendar/series/{key}/occurrences", headers=auth_headers()).status_code
        == 404
    )


def test_series_does_not_grant_another_workspace_member_access(client):
    from tests.contract.test_ingest_openapi_contract import auth_headers
    from tests.fixtures.admin import (
        DEFAULT_MEMBER_DEVICE_ID,
        DEFAULT_MEMBER_USER_ID,
        auth_headers_for,
    )
    from tests.integration.test_calendar_access_policy import _seed_default_workspace_roles

    event, _, source = seed_series(client)
    _seed_default_workspace_roles(client)
    key = client.get("/api/v1/calendar/overview", headers=auth_headers()).json()["cards"][0][
        "series_key"
    ]
    foreign = auth_headers_for(user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID)
    assert client.get("/api/v1/calendar/overview", headers=foreign).json()["cards"] == []
    assert (
        client.get(f"/api/v1/calendar/events/{event}/join-target", headers=foreign).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/calendar/series/{key}/occurrences", headers=foreign).status_code == 404
    )
    result = client.post(f"/api/v1/calendar/sources/{source}/disconnect", headers=auth_headers())
    assert result.status_code == 200
    assert (
        client.get(
            f"/api/v1/calendar/events/{event}/join-target", headers=auth_headers()
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/calendar/series/{key}/occurrences", headers=auth_headers()).status_code
        == 404
    )


def test_cursor_cannot_be_reused_for_other_series_and_never_echoes_input(client):
    from tests.contract.test_ingest_openapi_contract import auth_headers

    seed_series(client)
    cards = client.get("/api/v1/calendar/overview", headers=auth_headers()).json()["cards"]
    first, second = [c["series_key"] for c in cards]
    page = client.get(
        f"/api/v1/calendar/series/{first}/occurrences?limit=1", headers=auth_headers()
    ).json()
    for token in [page["next_cursor"], "x" * 2049]:
        result = client.get(
            f"/api/v1/calendar/series/{second}/occurrences",
            params={"cursor": token},
            headers=auth_headers(),
        )
        assert result.status_code == 422
        assert token not in result.text


def test_sql_overview_current_selection_move_and_calendar_collision(client):
    import asyncio
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from sqlalchemy import select

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from tests.fixtures.calendar_settings import (
        calendar_settings_calendar,
        calendar_settings_snapshot,
    )
    from twobrain_rec_server.db.models import CalendarEventSnapshot, CalendarSource

    first_id, _, source_id = seed_series(client)

    async def arrange():
        async with client.app_state["sessionmaker"]() as db:
            now = datetime.now(UTC)
            first = await db.get(CalendarEventSnapshot, UUID(first_id))
            first.starts_at, first.ends_at = (
                now - timedelta(minutes=45),
                now + timedelta(minutes=15),
            )
            second = await db.scalar(
                select(CalendarEventSnapshot).where(
                    CalendarEventSnapshot.provider_event_id == "f279-1"
                )
            )
            second.starts_at, second.ends_at = (
                now - timedelta(minutes=15),
                now + timedelta(minutes=45),
            )
            source = await db.get(CalendarSource, UUID(source_id))
            another = calendar_settings_calendar(source, selected=True)
            another.provider_calendar_id = "another-calendar"
            db.add(another)
            await db.flush()
            collision = calendar_settings_snapshot(
                source,
                another,
                provider_event_id="same-series-other-calendar",
                starts_at=now + timedelta(days=1),
            )
            collision.recurring_series_id = "synthetic-weekly"
            db.add(collision)
            await db.commit()
            return str(second.id), str(collision.id)

    second_id, collision_id = asyncio.run(arrange())
    cards = client.get("/api/v1/calendar/overview?limit=4", headers=auth_headers()).json()["cards"]
    assert cards[0]["event_id"] == second_id
    assert len(cards) == 3
    original_key = cards[0]["series_key"]
    assert next(x for x in cards if x["event_id"] == collision_id)["series_key"] != original_key

    async def move_and_cancel():
        async with client.app_state["sessionmaker"]() as db:
            second = await db.get(CalendarEventSnapshot, UUID(second_id))
            second.source_status = "cancelled"
            first = await db.get(CalendarEventSnapshot, UUID(first_id))
            first.starts_at += timedelta(days=7)
            first.ends_at += timedelta(days=7)
            await db.commit()

    asyncio.run(move_and_cancel())
    rows = client.get(
        f"/api/v1/calendar/series/{original_key}/occurrences", headers=auth_headers()
    ).json()["occurrences"]
    assert len(rows) == 12
    assert sum(x["event_id"] == first_id for x in rows) == 1
    assert next(x for x in rows if x["event_id"] == second_id)["cancelled"]
    assert all(x["series_key"] == original_key for x in rows)
