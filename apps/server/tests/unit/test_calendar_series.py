from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from tests.fixtures.calendar_settings import (
    calendar_settings_calendar,
    calendar_settings_snapshot,
    calendar_settings_source,
)
from twobrain_rec_server.calendar.series import (
    decode_cursor,
    decode_overview_cursor,
    encode_cursor,
    representative,
    series_key,
)

NOW = datetime(2026, 9, 28, 10, 45, tzinfo=UTC)


def events():
    source = calendar_settings_source()
    calendar = calendar_settings_calendar(source)
    rows = [
        calendar_settings_snapshot(source, calendar, starts_at=NOW + timedelta(days=n))
        for n in range(12)
    ]
    for row in rows:
        row.recurring_series_id = "synthetic-series"
    return source, calendar, rows


def test_series_identity_keeps_calendar_owner_and_source_boundaries():
    source, calendar, rows = events()
    assert len({series_key(row, source.owner_user_id) for row in rows}) == 1
    key = series_key(rows[0], source.owner_user_id)
    assert series_key(rows[0], uuid4()) != key
    rows[0].external_calendar_id = uuid4()
    assert series_key(rows[0], source.owner_user_id) != key
    rows[0].recurring_series_id = None
    assert series_key(rows[0], source.owner_user_id) is None


def test_representative_prefers_latest_current_then_uuid_then_future():
    _, _, rows = events()
    a, b, c = rows[:3]
    a.starts_at = NOW - timedelta(minutes=45)
    a.ends_at = NOW + timedelta(minutes=15)
    b.starts_at = NOW - timedelta(minutes=15)
    b.ends_at = NOW + timedelta(minutes=45)
    assert representative([a, b, c], NOW) is b
    assert representative([a, b, c], b.ends_at) is c
    a.starts_at = b.starts_at
    a.id = UUID(int=1)
    b.id = UUID(int=2)
    assert representative([b, a], NOW) is a
    a.source_status = "cancelled"
    assert representative([a, b], NOW) is b


def test_cursor_is_bound_expiring_and_tamper_resistant():
    context = {"owner": "o", "workspace": "w", "series": "s", "from": "f", "to": "t"}
    cursor = encode_cursor(context, (NOW.isoformat(), str(UUID(int=1))), "test-secret", now=100)
    assert decode_cursor(cursor, context, "test-secret", now=101) == (
        NOW.isoformat(),
        str(UUID(int=1)),
    )
    for token, ctx, t in [
        (cursor + "x", context, 101),
        (cursor, {**context, "owner": "other"}, 101),
        (cursor, context, 3701),
        ("x" * 2049, context, 101),
    ]:
        with pytest.raises(ValueError):
            decode_cursor(token, ctx, "test-secret", now=t)


def test_overview_cursor_keeps_signed_window_without_weakening_scope_or_expiry():
    scope = {"owner": "o", "session": "session", "workspace": "w", "series": "overview"}
    context = {
        **scope,
        "anchor": NOW.isoformat(),
        "from": NOW.date().isoformat(),
        "to": (NOW + timedelta(days=30)).date().isoformat(),
    }
    last = (NOW.isoformat(), str(UUID(int=1)))
    cursor = encode_cursor(context, last, "test-secret", now=100)
    anchor, decoded, saved = decode_overview_cursor(cursor, scope, "test-secret", now=101)
    assert anchor == NOW and decoded == last and saved == context
    for key in scope:
        with pytest.raises(ValueError):
            decode_overview_cursor(cursor, {**scope, key: "other"}, "test-secret", now=101)
    with pytest.raises(ValueError):
        decode_overview_cursor(cursor, scope, "test-secret", now=3701)
    invalid = encode_cursor({**context, "to": "2028-01-01"}, last, "test-secret", now=100)
    with pytest.raises(ValueError):
        decode_overview_cursor(invalid, scope, "test-secret", now=101)
    with pytest.raises(ValueError):
        decode_cursor(cursor, scope, "test-secret", now=101)
