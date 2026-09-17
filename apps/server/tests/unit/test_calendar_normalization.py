from datetime import UTC, date, datetime, timedelta

from tests.fixtures.calendar import (
    calendar_event_fixture,
    private_free_busy_event_fixture,
    recurrence_exception_fixture,
)
from twobrain_rec_server.calendar.normalize import (
    normalize_calendar_event,
    normalize_icalendar_event,
)


def test_normalization_preserves_available_fields() -> None:
    normalized = normalize_calendar_event(calendar_event_fixture("caldav_yandex"))

    assert normalized.provider_family == "caldav_yandex"
    assert normalized.title == "Synthetic Planning Sync"
    assert normalized.description == "Synthetic agenda"
    assert normalized.location == "Synthetic Room"
    assert normalized.transparency == "busy"
    assert normalized.title_state == "available"
    assert normalized.participant_count == 2
    assert normalized.meeting_link_present is True
    assert normalized.attachments_metadata == [
        {
            "file_name": "synthetic-agenda.pdf",
            "mime_type": "application/pdf",
            "content_url": "https://files.example.test/private.pdf",
        }
    ]
    assert normalized.source_updated_at == datetime(2026, 7, 1, 8, 0, tzinfo=UTC)


def test_normalization_preserves_complete_content_for_protected_persistence() -> None:
    normalized = normalize_calendar_event(
        calendar_event_fixture(
            "google_calendar",
            description="d" * 8192,
            location="l" * 1200,
        )
    )

    assert len(normalized.description or "") == 8192
    assert len(normalized.location or "") == 1200


def test_private_free_busy_normalization_does_not_fabricate_content() -> None:
    event = private_free_busy_event_fixture()
    event["conference_links"] = [
        {"provider_family": "generic", "source_field": "location", "url_hash": "sha256:private"}
    ]
    event["attachments_metadata"] = [{"file_name": "private.pdf"}]
    normalized = normalize_calendar_event(event)

    assert normalized.title is None
    assert normalized.title_state == "free_busy_only"
    assert normalized.participant_count == 0
    assert normalized.meeting_link_present is True
    assert normalized.attachments_metadata == [{"file_name": "private.pdf"}]
    assert normalized.limitation_states["participants"] == "private_redacted"


def test_normalization_preserves_recurrence_and_moved_instance_identity() -> None:
    normalized = normalize_calendar_event(recurrence_exception_fixture())

    assert normalized.recurring_series_id == "series-1"
    assert normalized.recurrence_instance_id == "series-1-20260701T090000Z"
    assert normalized.original_start == datetime(2026, 6, 30, 9, 0, tzinfo=UTC)
    assert normalized.recurrence_rule == {"freq": "weekly", "count": 4}
    assert normalized.recurrence_exceptions[0]["state"] == "moved"


def test_normalization_handles_all_day_floating_and_missing_dtend() -> None:
    normalized = normalize_calendar_event(
        calendar_event_fixture(
            "caldav_yandex",
            starts_at=date(2026, 7, 2),
            ends_at=None,
            all_day=True,
            floating_time=True,
        )
    )

    assert normalized.all_day is True
    assert normalized.floating_time is True
    assert normalized.ends_at - normalized.starts_at == timedelta(days=1)


def test_normalization_rejects_raw_provider_payload_extras() -> None:
    normalized = normalize_calendar_event(
        calendar_event_fixture(
            "caldav_yandex",
            provider_extras={
                "source_kind": "synthetic_caldav_event",
                "raw_event_payload": {"summary": "private"},
                "access_token": "secret",
            },
        )
    )

    assert normalized.provider_extras == {
        "source_kind": "synthetic_caldav_event",
        "raw_payload_retained": False,
    }


def test_owner_normalization_preserves_title_and_roster_display_name() -> None:
    # F251: owner content is preserved; storage and output own access/escaping.
    event = calendar_event_fixture("caldav_yandex")
    event["title"] = "Join https://meet.example.test/private?passcode=123"
    event["participants"][0]["display_name"] = "alice@example.test"

    normalized = normalize_calendar_event(event)

    assert normalized.title == event["title"]
    assert normalized.title_state == "available"
    assert normalized.participants[0]["display_name"] == "alice@example.test"


def test_icalendar_normalization_extracts_schedule_recurrence_and_links() -> None:
    normalized = normalize_icalendar_event(
        """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:yandex-uid@example.test
DTSTART:20260701T090000Z
DTEND:20260701T100000Z
SUMMARY:CalDAV planning
LOCATION:CalDAV Room
DESCRIPTION:Join https://telemost.yandex.ru/j/00000000000000
RRULE:FREQ=WEEKLY;COUNT=2
SEQUENCE:4
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
""",
        provider_family="caldav_yandex",
        provider_calendar_id="primary",
    )

    assert normalized.provider_family == "caldav_yandex"
    assert normalized.provider_calendar_id == "primary"
    assert normalized.ical_uid == "yandex-uid@example.test"
    assert normalized.source_version == "4"
    assert normalized.description == "Join https://telemost.yandex.ru/j/00000000000000"
    assert normalized.location == "CalDAV Room"
    assert normalized.transparency == "OPAQUE"
    assert normalized.recurrence_rule == {"rrule": "FREQ=WEEKLY;COUNT=2"}
    assert normalized.conference_links[0]["provider_family"] == "yandex_telemost"


def test_icalendar_normalization_preserves_recurrence_instance_identity() -> None:
    normalized = normalize_icalendar_event(
        """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:series@example.test
RECURRENCE-ID:20260708T090000Z
DTSTART:20260708T100000Z
DTEND:20260708T110000Z
SUMMARY:Moved occurrence
EXDATE:20260715T090000Z
END:VEVENT
END:VCALENDAR
""",
        provider_family="caldav_yandex",
    )

    assert normalized.provider_event_id == "series@example.test:20260708T090000Z"
    assert normalized.ical_uid == "series@example.test"
    assert normalized.recurrence_instance_id == "20260708T090000Z"
    assert normalized.original_start == datetime(2026, 7, 8, 9, 0, tzinfo=UTC)
    assert normalized.recurrence_exceptions == [{"exdate": "20260715T090000Z"}]


def test_normalization_preserves_cancelled_and_duplicate_identity_without_fabricating_match() -> (
    None
):
    cancelled = normalize_calendar_event(
        calendar_event_fixture(
            "exchange_ews", provider_event_id="cancelled-instance", source_status="cancelled"
        )
    )
    duplicate_copy = normalize_calendar_event(
        calendar_event_fixture(
            "caldav_yandex", provider_event_id="organizer-copy", ical_uid=cancelled.ical_uid
        )
    )

    assert cancelled.source_status == "cancelled"
    assert duplicate_copy.ical_uid == cancelled.ical_uid
    assert duplicate_copy.provider_event_id != cancelled.provider_event_id


def test_owner_content_is_preserved_independently_of_title_and_privacy() -> None:
    for privacy in ("private", "confidential", "free_busy_only"):
        event = normalize_calendar_event(
            calendar_event_fixture(
                "caldav_yandex",
                privacy_class=privacy,
                title="owner@example.test https://zoom.us/j/1?pwd=synthetic" * 40,
                description="d" * 10000,
                location="l" * 2000,
                attachments_metadata=[{"url": "https://files.example.test/a", "file_name": "A"}],
            )
        )
        assert event.title == "owner@example.test https://zoom.us/j/1?pwd=synthetic" * 40
        assert event.description == "d" * 10000
        assert event.location == "l" * 2000
        assert event.attachments_metadata[0]["url"] == "https://files.example.test/a"
        assert event.meeting_link_present
    unnamed = normalize_calendar_event(calendar_event_fixture("caldav_yandex", title=None))
    assert unnamed.description == "Synthetic agenda"


def test_ical_resource_expands_exclusions_moves_cancellations_and_multiple_events() -> None:
    from twobrain_rec_server.calendar.normalize import normalize_icalendar_events

    text = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:series-a
DTSTART;TZID=Europe/Moscow:20260906T090000
DTEND;TZID=Europe/Moscow:20260906T100000
RRULE:FREQ=DAILY;COUNT=5
EXDATE;TZID=Europe/Moscow:20260907T090000
RDATE;TZID=Europe/Moscow:20260912T090000
CLASS:PRIVATE
SUMMARY:Private\\, name
ORGANIZER;CN=owner@example.test:mailto:owner@example.test
ATTENDEE;CN=Guest;ROLE=OPT-PARTICIPANT;PARTSTAT=ACCEPTED:mailto:guest@example.test
ATTACH;FMTTYPE=application/pdf:https://files.example.test/doc
END:VEVENT
BEGIN:VEVENT
UID:series-a
RECURRENCE-ID;TZID=Europe/Moscow:20260908T090000
DTSTART;TZID=Europe/Moscow:20260908T120000
DTEND;TZID=Europe/Moscow:20260908T130000
SUMMARY:Moved
END:VEVENT
BEGIN:VEVENT
UID:series-a
RECURRENCE-ID;TZID=Europe/Moscow:20260909T090000
STATUS:CANCELLED
END:VEVENT
BEGIN:VEVENT
UID:single-b
DTSTART;VALUE=DATE:20260910
SUMMARY:All day
END:VEVENT
BEGIN:VEVENT
UID:removed-series
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR"""
    events, deleted = normalize_icalendar_events(
        text,
        provider_family="caldav_yandex",
        time_min=datetime(2026, 9, 6, tzinfo=UTC),
        time_max=datetime(2026, 9, 13, tzinfo=UTC),
    )
    assert deleted == ("removed-series",)
    assert len(events) == 6
    base = next(e for e in events if e.title == "Private, name")
    assert base.starts_at.astimezone(UTC).hour == 6
    assert base.timezone == "Europe/Moscow"
    assert base.participants[0]["display_name"] == "owner@example.test"
    assert base.participants[1]["participant_kind"] == "optional_attendee"
    assert base.participants[1]["response_status"] == "accepted"
    assert base.attachments_metadata[0]["url"] == "https://files.example.test/doc"
    moved = next(e for e in events if e.title == "Moved")
    assert moved.starts_at.astimezone(UTC).hour == 9
    assert moved.original_start.astimezone(UTC).hour == 6
    assert moved.provider_event_id == "series-a:20260908T060000Z"
    cancelled = next(e for e in events if e.source_status == "cancelled")
    assert cancelled.original_start.astimezone(UTC) == datetime(2026, 9, 9, 6, tzinfo=UTC)
    single = next(e for e in events if e.ical_uid == "single-b")
    assert single.provider_event_id == "single-b"
    assert single.recurrence_instance_id is None
    assert single.ends_at - single.starts_at == timedelta(days=1)


def test_ical_dst_duration_and_floating_timezone_contract() -> None:
    import pytest

    from twobrain_rec_server.calendar.normalize import normalize_icalendar_events
    from twobrain_rec_server.calendar.providers import CalendarProviderError

    source = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:dst
DTSTART;TZID=Europe/Berlin:20261024T090000
DURATION:PT1H
RRULE:FREQ=DAILY;COUNT=3
SUMMARY:Test
END:VEVENT
END:VCALENDAR"""
    events, _ = normalize_icalendar_events(
        source,
        provider_family="caldav_yandex",
        time_min=datetime(2026, 10, 24, tzinfo=UTC),
        time_max=datetime(2026, 10, 28, tzinfo=UTC),
    )
    assert [e.starts_at.astimezone(UTC).hour for e in events] == [7, 8, 8]
    floating = source.replace(";TZID=Europe/Berlin", "")
    with pytest.raises(CalendarProviderError, match="invalid_payload"):
        normalize_icalendar_events(
            floating,
            provider_family="caldav_yandex",
            time_min=datetime(2026, 10, 24, tzinfo=UTC),
            time_max=datetime(2026, 10, 28, tzinfo=UTC),
        )
    declared = floating.replace("VERSION:2.0", "VERSION:2.0\nX-WR-TIMEZONE:Europe/Berlin")
    fixed, _ = normalize_icalendar_events(
        declared,
        provider_family="caldav_yandex",
        time_min=datetime(2026, 10, 24, tzinfo=UTC),
        time_max=datetime(2026, 10, 28, tzinfo=UTC),
    )
    assert [e.starts_at.astimezone(UTC).hour for e in fixed] == [7, 8, 8]


def test_ical_nonrecurring_move_keeps_identity_and_custom_vtimezone() -> None:
    from twobrain_rec_server.calendar.normalize import normalize_icalendar_events

    text = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VTIMEZONE
TZID:Custom/Synthetic
BEGIN:STANDARD
DTSTART:19700101T000000
TZOFFSETFROM:+0530
TZOFFSETTO:+0530
TZNAME:Synthetic
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
UID:single
DTSTART;TZID=Custom/Synthetic:20260906T090000
DURATION:PT1H
SUMMARY:Folded long
 line\\; comma\\, newline\\nend
END:VEVENT
END:VCALENDAR"""

    def parse(value):
        return normalize_icalendar_events(
            value,
            provider_family="caldav_yandex",
            time_min=datetime(2026, 9, 1, tzinfo=UTC),
            time_max=datetime(2026, 9, 12, tzinfo=UTC),
        )[0][0]

    before = parse(text)
    after = parse(text.replace("20260906T090000", "20260907T120000"))
    assert before.provider_event_id == after.provider_event_id == "single"
    assert before.recurrence_instance_id is after.recurrence_instance_id is None
    assert before.starts_at.astimezone(UTC) == datetime(2026, 9, 6, 3, 30, tzinfo=UTC)
    assert before.title == "Folded longline; comma, newline\nend"


def test_ical_this_and_future_moves_preserve_original_recurrence_ids() -> None:
    from twobrain_rec_server.calendar.normalize import normalize_icalendar_events

    text = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:range
DTSTART:20260906T090000Z
DTEND:20260906T100000Z
RRULE:FREQ=DAILY;COUNT=3
END:VEVENT
BEGIN:VEVENT
UID:range
RECURRENCE-ID;RANGE=THISANDFUTURE:20260907T090000Z
DTSTART:20260907T110000Z
DTEND:20260907T120000Z
END:VEVENT
END:VCALENDAR"""
    events, _ = normalize_icalendar_events(
        text,
        provider_family="caldav_yandex",
        time_min=datetime(2026, 9, 6, tzinfo=UTC),
        time_max=datetime(2026, 9, 10, tzinfo=UTC),
    )
    assert [event.starts_at.hour for event in events] == [9, 11, 11]
    assert [event.original_start.hour for event in events] == [9, 9, 9]


def test_duration_measures_elapsed_time_across_dst_transition() -> None:
    from zoneinfo import ZoneInfo

    zone = ZoneInfo("Europe/Berlin")
    event = normalize_calendar_event(
        calendar_event_fixture(
            "caldav_yandex",
            starts_at=datetime(2026, 10, 25, 1, 30, tzinfo=zone),
            ends_at=datetime(2026, 10, 25, 3, 30, tzinfo=zone),
        )
    )
    assert event.duration_seconds == 3 * 3600
