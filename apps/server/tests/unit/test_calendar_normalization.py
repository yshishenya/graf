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
        {"file_name": "synthetic-agenda.pdf", "mime_type": "application/pdf"}
    ]
    assert normalized.source_updated_at == datetime(2026, 7, 1, 8, 0, tzinfo=UTC)


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
    assert normalized.meeting_link_present is False
    assert normalized.attachments_metadata == []
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


def test_098_normalization_hides_unsafe_title_and_roster_display_name() -> None:
    # FR-017/FR-030, SC-011: normalize once at the provider trust boundary.
    event = calendar_event_fixture("caldav_yandex")
    event["title"] = "Join https://meet.example.test/private?passcode=123"
    event["participants"][0]["display_name"] = "alice@example.test"

    normalized = normalize_calendar_event(event)

    assert normalized.title is None
    assert normalized.title_state == "policy_hidden"
    assert normalized.participants[0]["display_name"] is None


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

    assert normalized.provider_event_id == "20260708T090000Z"
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
