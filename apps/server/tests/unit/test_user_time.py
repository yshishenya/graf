from datetime import UTC, date, datetime

import pytest

from twobrain_rec_server.cabinet.user_time import (
    _display_timezone,
    display_timezone_name,
    format_user_datetime,
    user_time_middleware,
    validated_timezone,
)


def test_display_time_normalizes_instants_and_preserves_dates():
    token = _display_timezone.set("Asia/Yekaterinburg")
    try:
        for value in ("2026-09-05T21:30:00Z", "2026-09-06T02:30:00+05:00",
                      "2026-09-05T17:30:00.123456-04:00"):
            assert format_user_datetime(value) == "06.09.2026, 02:30"
        assert format_user_datetime(datetime(2026, 9, 5, 21, 30)) == "06.09.2026, 02:30"
        assert format_user_datetime(date(2026, 9, 5)) == "05.09.2026"
        assert format_user_datetime("2026-09-05") == "05.09.2026"
        assert format_user_datetime(None) == "Без даты"
        assert format_user_datetime("bad") == "Без даты"
    finally:
        _display_timezone.reset(token)
    assert format_user_datetime(datetime(2026, 9, 5, tzinfo=UTC)).endswith("(UTC)")


def test_dst_uses_rules_at_event_not_fixed_recording_offset():
    token = _display_timezone.set("America/New_York")
    try:
        assert format_user_datetime("2026-03-08T06:30:00Z") == "08.03.2026, 01:30"
        assert format_user_datetime("2026-03-08T07:30:00Z") == "08.03.2026, 03:30"
        assert format_user_datetime("2026-11-01T05:30:00Z") == "01.11.2026, 01:30"
        assert format_user_datetime("2026-11-01T06:30:00Z") == "01.11.2026, 01:30"
        assert format_user_datetime("2026-11-01T05:30:00Z", show_zone=True).endswith("(UTC-04:00)")
        assert format_user_datetime("2026-11-01T06:30:00Z", show_zone=True).endswith("(UTC-05:00)")
    finally:
        _display_timezone.reset(token)


@pytest.mark.parametrize("value", [None, "", "../UTC", "/etc/passwd", "not/a-zone", "x" * 101])
def test_untrusted_zone_falls_back(value):
    assert validated_timezone(value) == "UTC"


async def test_request_context_is_isolated_and_reset_on_errors():
    import asyncio

    from starlette.requests import Request

    from twobrain_rec_server.cabinet.user_time import time_reload_allowed

    async def run(zone, method="GET", path="/meetings", fail=False):
        request = Request({"type": "http", "method": method, "path": path,
                           "headers": [(b"cookie", f"graf_timezone={zone}".encode())]})

        async def next_request(_):
            await asyncio.sleep(0)
            assert display_timezone_name() == zone
            if fail:
                raise RuntimeError("synthetic failure")
            return time_reload_allowed()

        return await user_time_middleware(request, next_request)

    assert await asyncio.gather(run("UTC"), run("Asia/Yekaterinburg")) == [True, True]
    assert not await run("UTC", "POST")
    assert not await run("UTC", path="/billing/checkout/return")
    assert await run("UTC", path="/billing/invoices/INV-1234")
    assert await run("UTC", path="/billing/checkout/status/INV-1234")
    assert not await run("UTC", path="/billing/checkout/status/INV-1234/refresh")
    assert not await run("UTC", path="/auth/callback")
    with pytest.raises(RuntimeError):
        await run("Asia/Yekaterinburg", fail=True)
    assert display_timezone_name() == "UTC"
    assert not time_reload_allowed()


def test_billing_account_sharing_and_audit_use_viewer_time():
    from uuid import UUID

    from twobrain_rec_server.cabinet.rendering import render_settings_page
    from twobrain_rec_server.cabinet.user_time import user_time_element
    from twobrain_rec_server.cabinet.view_models import (
        AccountProfileView,
        account_settings_surface,
    )
    from twobrain_rec_server.db.models import AuthSession
    from twobrain_rec_server.cabinet.web_routes.billing import _billing_datetime_label
    from twobrain_rec_server.cabinet.web_routes.fair_use import _date_label

    instant = datetime(2026, 9, 5, 21, 30, tzinfo=UTC)
    token = _display_timezone.set("Asia/Yekaterinburg")
    try:
        assert _billing_datetime_label(instant) == _date_label(instant) == (
            "06.09.2026, 02:30 (UTC+05:00)"
        )
        assert _billing_datetime_label(None) is None
        element = str(user_time_element(instant, show_zone=True))
        assert 'datetime="2026-09-05T21:30:00+00:00"' in element
        assert 'data-user-datetime' in element
        assert "06.09.2026, 02:30 (UTC+05:00)" in element
        profile = AccountProfileView(display_name="Synthetic", timezone=None)
        page = render_settings_page(category="account", profile=profile, account_surface=
            account_settings_surface(profile=profile, sessions=(AuthSession(
                id=UUID(int=1), user_id=UUID(int=2), workspace_id=UUID(int=3),
                provider="email", status="active", issued_at=instant,
                last_seen_at=instant, expires_at=datetime(2027, 1, 1, tzinfo=UTC),
            ),)))
        assert "06.09.2026, 02:30 (UTC+05:00)" in page
        assert 'name="timezone"' in page
        assert "Екатеринбург" in page
    finally:
        _display_timezone.reset(token)


def test_admin_calendar_day_filter_honors_dst_length():
    from sqlalchemy import column, select

    from twobrain_rec_server.admin.audit import _with_date_filters

    token = _display_timezone.set("America/New_York")
    try:
        day = date(2026, 3, 8)
        query = _with_date_filters(select(column("created_at")), column("created_at"),
                                   date_from=day, date_to=day)
        params = list(query.compile().params.values())
        assert params[0].astimezone(UTC) == datetime(2026, 3, 8, 5, tzinfo=UTC)
        assert params[1].astimezone(UTC) == datetime(2026, 3, 9, 4, tzinfo=UTC)
    finally:
        _display_timezone.reset(token)


def test_timezone_catalog_is_russian_and_uses_date_specific_offsets():
    from twobrain_rec_server.cabinet.user_time import (
        timezone_label,
        timezone_options,
        valid_timezone_choice,
    )

    assert timezone_label("Asia/Yekaterinburg") == "UTC+05:00 — Екатеринбург, Россия"
    assert timezone_label("Asia/Kathmandu") == "UTC+05:45 — Катманду, Непал"
    assert "UTC−05:00" in timezone_label("America/New_York", datetime(2026, 1, 1, tzinfo=UTC))
    assert "UTC−04:00" in timezone_label("America/New_York", datetime(2026, 7, 1, tzinfo=UTC))
    options = timezone_options("Asia/Katmandu")
    assert len(options) > 350
    assert any(item["value"] == "Asia/Katmandu" and "Катманду" in item["label"] for item in options)
    assert {"Europe/Moscow", "Asia/Yekaterinburg", "Asia/Kamchatka", "UTC"} <= {x["value"] for x in options}
    for zone in ("../UTC", "", "GMT+5", "Mars/Olympus", "x" * 65):
        assert not valid_timezone_choice(zone)


async def test_saved_account_zone_wins_over_device_and_is_request_scoped():
    import asyncio

    from starlette.requests import Request

    from twobrain_rec_server.cabinet.user_time import (
        apply_user_time_preference,
        viewer_time_context,
    )

    async def run(user, preferred, expected):
        request = Request({"type": "http", "method": "GET", "path": "/meetings",
                           "headers": [(b"cookie", b"graf_timezone=Asia/Yekaterinburg")]})
        async def next_request(_):
            apply_user_time_preference(user_id=user, session_id="synthetic", timezone=preferred)
            await asyncio.sleep(0)
            assert display_timezone_name() == expected
            assert viewer_time_context()["user"] == user
            assert viewer_time_context()["preferred"] == (preferred or "")
        await user_time_middleware(request, next_request)
    await asyncio.gather(run("a", "America/New_York", "America/New_York"),
                         run("b", None, "Asia/Yekaterinburg"))
    assert display_timezone_name() == "UTC"
    assert viewer_time_context()["user"] == ""


def test_all_day_calendar_date_does_not_shift_with_viewer_timezone():
    from twobrain_rec_server.cabinet.rendering import _home_upcoming_time_label

    token = _display_timezone.set("America/Los_Angeles")
    try:
        value = datetime(2026, 9, 6, tzinfo=UTC)
        assert _home_upcoming_time_label(value, "America/Los_Angeles", all_day=True) == "06.09.2026, весь день"
    finally:
        _display_timezone.reset(token)
