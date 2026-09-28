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


def test_series_recordings_recheck_grant_revocation_and_deletion(client):
    import asyncio
    from datetime import UTC, datetime
    from uuid import UUID

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
    from tests.fixtures.admin import DEFAULT_MEMBER_USER_ID, seed_default_workspace_admin_roles
    from twobrain_rec_server.db.models import Meeting, MeetingShareGrant

    event, _, _ = seed_series(client)
    recordings = []
    for name in ("own", "shared", "denied"):
        response = client.post(
            "/api/v1/meetings",
            headers=auth_headers(),
            json={"local_recording_id": f"f279-access-{name}", "duration_seconds": 90},
        )
        assert response.status_code == 200, response.text
        meeting_id = response.json()["meeting_id"]
        recordings.append(meeting_id)
        linked = client.put(
            f"/api/v1/meetings/{meeting_id}/calendar-context",
            headers=auth_headers(),
            json={"event_id": event, "context_reason": "manual_selection"},
        )
        assert linked.status_code == 200, linked.text

    async def configure_access():
        async with client.app_state["sessionmaker"]() as db:
            await seed_default_workspace_admin_roles(db)
            # Retain reliable historical context links while exercising each meeting's ACL.
            for meeting_id in recordings[1:]:
                meeting = await db.get(Meeting, UUID(meeting_id))
                meeting.created_by_user_id = DEFAULT_MEMBER_USER_ID
                meeting.visibility = "owner_only"
            grant = MeetingShareGrant(
                workspace_id=WORKSPACE_ID,
                meeting_id=UUID(recordings[1]),
                grant_type="user",
                grantee_user_id=USER_ID,
                audience_type="user",
                audience_id=USER_ID,
                content_scope="full_meeting",
                created_by_user_id=DEFAULT_MEMBER_USER_ID,
                status="active",
            )
            db.add(grant)
            await db.commit()
            return grant.id

    grant_id = asyncio.run(configure_access())
    cards = client.get("/api/v1/calendar/overview", headers=auth_headers()).json()["cards"]
    url = f"/api/v1/calendar/series/{cards[0]['series_key']}/occurrences"

    def available_recordings():
        response = client.get(url, headers=auth_headers())
        assert response.status_code == 200, response.text
        assert recordings[2] not in response.text
        occurrence = next(row for row in response.json()["occurrences"] if row["event_id"] == event)
        assert "recording_count" not in occurrence
        return {row["meeting_id"] for row in occurrence["recordings"]}, response.text

    assert available_recordings()[0] == set(recordings[:2])

    async def revoke():
        async with client.app_state["sessionmaker"]() as db:
            grant = await db.get(MeetingShareGrant, grant_id)
            grant.status = "revoked"
            grant.revoked_at = datetime.now(UTC)
            await db.commit()

    asyncio.run(revoke())
    ids, payload = available_recordings()
    assert ids == {recordings[0]}
    assert recordings[1] not in payload

    async def delete_owned():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, UUID(recordings[0]))
            meeting.deletion_state = "deleted"
            meeting.deleted_at = datetime.now(UTC)
            await db.commit()

    asyncio.run(delete_owned())
    ids, payload = available_recordings()
    assert ids == set()
    assert all(meeting_id not in payload for meeting_id in recordings)


def test_default_history_includes_overview_thirtieth_day_and_excludes_day31(client, monkeypatch):
    import asyncio
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
    from twobrain_rec_server.api import calendar as calendar_api
    from twobrain_rec_server.db.models import CalendarEventSnapshot, CalendarSettingsPreference

    frozen = datetime(2026, 9, 28, 12, tzinfo=UTC)
    today = frozen.replace(hour=0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen

    monkeypatch.setattr(calendar_api, "datetime", FrozenDateTime)
    seed_series(client)

    async def place_boundary_events():
        async with client.app_state["sessionmaker"]() as db:
            rows = list(
                await db.scalars(
                    select(CalendarEventSnapshot).order_by(CalendarEventSnapshot.provider_event_id)
                )
            )
            for row in rows:
                row.source_status = "cancelled"
            chosen = rows[:3]
            for row, offset in zip(
                chosen,
                [timedelta(days=30), timedelta(days=30, hours=10), timedelta(days=31)],
                strict=True,
            ):
                row.source_status = "confirmed"
                row.recurring_series_id = "boundary-series"
                row.starts_at = today + offset
                row.ends_at = row.starts_at + timedelta(hours=1)
            chosen[0].all_day = True
            db.add(
                CalendarSettingsPreference(
                    workspace_id=WORKSPACE_ID, owner_user_id=USER_ID, include_all_day_events=True
                )
            )
            await db.commit()
            return [str(row.id) for row in chosen]

    ids = asyncio.run(place_boundary_events())
    overview = client.get("/api/v1/calendar/overview", headers=auth_headers())
    assert overview.status_code == 200, overview.text
    card = next(row for row in overview.json()["cards"] if row["event_id"] == ids[0])
    url = f"/api/v1/calendar/series/{card['series_key']}/occurrences"
    history = client.get(url, headers=auth_headers())
    assert history.status_code == 200, history.text
    assert [row["event_id"] for row in history.json()["occurrences"]] == ids[:2]
    assert datetime.fromisoformat(history.json()["coverage_range"]["to"]) == today + timedelta(
        days=31
    )
    explicit = client.get(
        url, params={"to": (today + timedelta(days=30)).isoformat()}, headers=auth_headers()
    )
    assert explicit.status_code == 200, explicit.text
    assert explicit.json()["occurrences"] == []


def test_overview_cursor_preserves_issued_window_and_representative_across_midnight(
    client, monkeypatch
):
    import asyncio
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from twobrain_rec_server.api import calendar as calendar_api
    from twobrain_rec_server.db.models import CalendarEventSnapshot

    issued = datetime(2026, 9, 28, 23, 59, 59, tzinfo=UTC)

    class FrozenDateTime(datetime):
        value = issued

        @classmethod
        def now(cls, tz=None):
            return cls.value

    monkeypatch.setattr(calendar_api, "datetime", FrozenDateTime)
    seed_series(client)

    async def move():
        async with client.app_state["sessionmaker"]() as db:
            rows = list(
                await db.scalars(
                    select(CalendarEventSnapshot).order_by(CalendarEventSnapshot.provider_event_id)
                )
            )
            for row in rows:
                row.source_status = "cancelled"
            a, b, other = rows[:3]
            for row in (a, b, other):
                row.source_status = "confirmed"
            a.recurring_series_id = b.recurring_series_id = "midnight-series"
            a.starts_at = issued - timedelta(minutes=1)
            a.ends_at = issued + timedelta(milliseconds=500)
            b.starts_at = issued + timedelta(seconds=1)
            b.ends_at = issued + timedelta(hours=1)
            other.recurring_series_id = "other-series"
            other.starts_at = issued + timedelta(seconds=2)
            other.ends_at = issued + timedelta(hours=1)
            await db.commit()
            return str(a.id), str(other.id)

    first_id, second_id = asyncio.run(move())
    first = client.get("/api/v1/calendar/overview?limit=1", headers=auth_headers())
    assert first.status_code == 200, first.text
    assert first.json()["cards"][0]["event_id"] == first_id
    cursor = first.json()["next_cursor"]
    assert cursor
    FrozenDateTime.value = issued + timedelta(seconds=3)
    second = client.get(
        "/api/v1/calendar/overview", params={"cursor": cursor}, headers=auth_headers()
    )
    assert second.status_code == 200, second.text
    assert [row["event_id"] for row in second.json()["cards"]] == [second_id]
    assert second.json()["coverage_range"] == first.json()["coverage_range"]
    assert second.json()["next_cursor"] is None


def test_history_applies_eligibility_to_active_dates_but_keeps_minimal_cancellations(client):
    import asyncio
    from datetime import UTC, datetime

    from sqlalchemy import select

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
    from twobrain_rec_server.db.models import CalendarEventSnapshot, CalendarSettingsPreference

    seed_series(client)
    cards = client.get("/api/v1/calendar/overview", headers=auth_headers()).json()["cards"]
    url = f"/api/v1/calendar/series/{cards[0]['series_key']}/occurrences"

    async def remove_metadata():
        async with client.app_state["sessionmaker"]() as db:
            rows = list(
                (
                    await db.scalars(
                        select(CalendarEventSnapshot)
                        .where(CalendarEventSnapshot.recurring_series_id == "synthetic-weekly")
                        .order_by(CalendarEventSnapshot.starts_at)
                    )
                ).all()
            )
            for row in rows[:3]:
                row.conference_summary_json = {
                    "participant_count": 0,
                    "meeting_link_present": False,
                }
                row.provider_extras_json = {}
                row.location = None
                row.open_meeting_available = False
            rows[1].source_status = "cancelled"
            rows[2].source_deleted_at = datetime.now(UTC)
            await db.commit()
            return [str(row.id) for row in rows]

    ids = asyncio.run(remove_metadata())
    response = client.get(url, headers=auth_headers())
    assert response.status_code == 200, response.text
    rows = response.json()["occurrences"]
    assert {row["event_id"] for row in rows} == set(ids[1:])
    assert all(row["cancelled"] for row in rows if row["event_id"] in ids[1:3])

    async def include_empty_events():
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                CalendarSettingsPreference(
                    workspace_id=WORKSPACE_ID,
                    owner_user_id=USER_ID,
                    include_events_without_participants=True,
                    include_events_without_link_or_location=True,
                )
            )
            await db.commit()

    asyncio.run(include_empty_events())
    response = client.get(url, headers=auth_headers())
    assert response.status_code == 200, response.text
    assert {row["event_id"] for row in response.json()["occurrences"]} == set(ids)


def test_browser_join_confirmation_rechecks_original_page_session_and_revocation(client):
    from functools import partial

    from tests.integration.test_web_owner_session_context import _seed_owner_review_session
    from twobrain_rec_server.auth.csrf import issue_csrf_token
    from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
    from twobrain_rec_server.db.models import AuthSession

    event, _, _ = seed_series(client)
    url = f"/api/v1/calendar/events/{event}/join-target"
    original = client.portal.call(
        partial(_seed_owner_review_session, client, token="f279-original-session")
    )
    replacement = client.portal.call(
        partial(_seed_owner_review_session, client, token="f279-new-session")
    )
    csrf = issue_csrf_token(session_id=original.id, secret=client.app.state.web_csrf_secret)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, "f279-original-session")
    assert client.get(url).status_code == 200
    assert client.post(url).status_code == 403
    confirmed = client.post(url, headers={"X-CSRF-Token": csrf})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.headers["cache-control"] == "no-store"
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, "f279-new-session")
    assert client.get(url).status_code == 200  # Same owner, different session still has access.
    stale = client.post(url, headers={"X-CSRF-Token": csrf})
    assert stale.status_code == 403
    assert "https_url" not in stale.text
    # Logout must rotate a marker even for an older session that never had one.
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, "f279-original-session")
    logged_out = client.post("/logout", headers={"X-CSRF-Token": csrf}, follow_redirects=False)
    assert logged_out.status_code == 303, logged_out.text
    assert len(logged_out.cookies["__Host-graf_session_epoch"]) == 32
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, "f279-new-session")

    async def revoke():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(AuthSession, replacement.id)
            row.status = "revoked"
            await db.commit()

    client.portal.call(revoke)
    current_csrf = issue_csrf_token(
        session_id=replacement.id, secret=client.app.state.web_csrf_secret
    )
    rejected = client.post(url, headers={"X-CSRF-Token": current_csrf})
    assert rejected.status_code == 401
    assert "https_url" not in rejected.text


def test_series_recording_preview_bounds_acl_work_without_revealing_hidden_counts(
    client, monkeypatch
):
    import asyncio
    from datetime import UTC, datetime, timedelta
    from uuid import UUID, uuid4

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
    from tests.fixtures.admin import DEFAULT_MEMBER_USER_ID, seed_default_workspace_admin_roles
    from twobrain_rec_server.api.calendar import SERIES_RECORDING_CANDIDATE_LIMIT
    from twobrain_rec_server.cabinet import access
    from twobrain_rec_server.db.models import Meeting, RecordingCalendarContextLink

    event_id, _, _ = seed_series(client)
    owned, hidden = [], []

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            await seed_default_workspace_admin_roles(db)
            now = datetime.now(UTC)
            for n in range(SERIES_RECORDING_CANDIDATE_LIMIT + 8):
                denied = n >= SERIES_RECORDING_CANDIDATE_LIMIT + 5
                meeting_id = uuid4()
                (hidden if denied else owned).append(str(meeting_id))
                db.add(
                    Meeting(
                        id=meeting_id,
                        workspace_id=WORKSPACE_ID,
                        created_by_user_id=DEFAULT_MEMBER_USER_ID if denied else USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id=f"f279-bounded-{n}",
                        duration_seconds=90,
                        visibility="owner_only",
                        started_at=now + timedelta(seconds=n),
                    )
                )
                await db.flush()
                db.add(
                    RecordingCalendarContextLink(
                        workspace_id=WORKSPACE_ID,
                        meeting_id=meeting_id,
                        calendar_event_snapshot_id=UUID(event_id),
                        context_state="matched_user",
                    )
                )
            await db.commit()

    asyncio.run(seed())
    original = access.decide_meeting_access
    checked = []

    async def counted(db, meeting, **kwargs):
        checked.append(meeting.id)
        return await original(db, meeting, **kwargs)

    monkeypatch.setattr(access, "decide_meeting_access", counted)
    key = client.get("/api/v1/calendar/overview", headers=auth_headers()).json()["cards"][0][
        "series_key"
    ]
    response = client.get(f"/api/v1/calendar/series/{key}/occurrences", headers=auth_headers())
    assert response.status_code == 200, response.text
    payload = response.json()
    rows = payload["occurrences"]
    records = [record["meeting_id"] for row in rows for record in row["recordings"]]
    assert len(checked) == SERIES_RECORDING_CANDIDATE_LIMIT
    assert len(records) == SERIES_RECORDING_CANDIDATE_LIMIT - len(hidden)
    assert set(records) <= set(owned)
    assert all(value not in response.text for value in hidden)
    assert payload["partial"] is True
    # The same fixed incomplete-preview contract applies to empty occurrences;
    # it must not disclose whether omitted or invisible candidates exist.
    assert all(row["recordings_partial"] is True for row in rows)
    assert any(not row["recordings"] for row in rows)
    assert all("recording_count" not in row for row in rows)
