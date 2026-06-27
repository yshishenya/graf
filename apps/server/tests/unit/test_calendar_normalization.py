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
    normalized = normalize_calendar_event(calendar_event_fixture("google_calendar"))

    assert normalized.provider_family == "google_calendar"
    assert normalized.title == "Synthetic Planning Sync"
    assert normalized.title_state == "available"
    assert normalized.participant_count == 2
    assert normalized.meeting_link_present is True


def test_private_free_busy_normalization_does_not_fabricate_content() -> None:
    normalized = normalize_calendar_event(private_free_busy_event_fixture())

    assert normalized.title is None
    assert normalized.title_state == "free_busy_only"
    assert normalized.participant_count == 0
    assert normalized.meeting_link_present is False
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
            "google_calendar",
            provider_extras={
                "source_kind": "synthetic_google_event",
                "raw_event_payload": {"summary": "private"},
                "access_token": "secret",
            },
        )
    )

    assert normalized.provider_extras == {
        "source_kind": "synthetic_google_event",
        "raw_payload_retained": False,
    }


def test_icalendar_normalization_extracts_schedule_recurrence_and_links() -> None:
    normalized = normalize_icalendar_event(
        """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:yandex-uid@example.test
DTSTART:20260701T090000Z
DTEND:20260701T100000Z
SUMMARY:CalDAV planning
DESCRIPTION:Join https://telemost.yandex.ru/j/00000000000000
RRULE:FREQ=WEEKLY;COUNT=2
SEQUENCE:4
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
    assert normalized.recurrence_rule == {"rrule": "FREQ=WEEKLY;COUNT=2"}
    assert normalized.conference_links[0]["provider_family"] == "yandex_telemost"


def test_normalization_preserves_cancelled_and_duplicate_identity_without_fabricating_match() -> None:
    cancelled = normalize_calendar_event(
        calendar_event_fixture("microsoft_graph", provider_event_id="cancelled-instance", source_status="cancelled")
    )
    duplicate_copy = normalize_calendar_event(
        calendar_event_fixture("google_calendar", provider_event_id="organizer-copy", ical_uid=cancelled.ical_uid)
    )

    assert cancelled.source_status == "cancelled"
    assert duplicate_copy.ical_uid == cancelled.ical_uid
    assert duplicate_copy.provider_event_id != cancelled.provider_event_id
