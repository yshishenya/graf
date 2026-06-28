from tests.fixtures.calendar import (
    PROVIDER_CASES,
    attendee_heavy_event_fixture,
    private_free_busy_event_fixture,
    provider_fixture_matrix,
    recurrence_exception_fixture,
)
from twobrain_rec_server.calendar.adapters import adapter_for_provider


def test_provider_fixture_matrix_covers_required_calendar_families() -> None:
    events = provider_fixture_matrix()

    assert {event["provider_family"] for event in events} == set(PROVIDER_CASES)


def test_provider_fixtures_are_synthetic_and_bounded() -> None:
    for event in provider_fixture_matrix():
        assert event["provider_extras"]["raw_payload_retained"] is False
        assert all(participant["email"].endswith("@example.test") for participant in event["participants"])
        assert all(link["url_hash"].startswith("sha256:") for link in event["conference_links"])


def test_private_free_busy_fixture_does_not_fabricate_content() -> None:
    event = private_free_busy_event_fixture()

    assert event["title"] is None
    assert event["participants"] == []
    assert event["conference_links"] == []
    assert event["limitation_states"]["title"] == "free_busy_only"


def test_attendee_heavy_fixture_keeps_small_synthetic_sample_by_default() -> None:
    event = attendee_heavy_event_fixture()

    assert len(event["participants"]) == 25
    assert {participant["workspace_relation"] for participant in event["participants"]} == {"external"}


def test_recurrence_exception_fixture_preserves_original_start() -> None:
    event = recurrence_exception_fixture()

    assert event["recurring_series_id"] == "series-1"
    assert event["recurrence_instance_id"]
    assert event["recurrence_exceptions"][0]["state"] == "moved"


def test_provider_adapters_map_required_families_with_bounds() -> None:
    expected = {
        "caldav_yandex": "caldav",
        "caldav_mail_ru": "caldav",
        "custom_caldav": "caldav",
        "custom_caldav_vk_workspace": "caldav",
        "caldav_mailion_myoffice": "caldav",
        "caldav_r7_office": "caldav",
        "caldav_communigate_pro": "caldav",
        "caldav_rupost": "caldav",
        "caldav_nextcloud_sogo": "caldav",
        "exchange_ews": "exchange_ews",
        "bitrix24": "bitrix24",
    }

    for provider_family, adapter_family in expected.items():
        adapter = adapter_for_provider(provider_family)
        assert adapter.provider_family == provider_family
        assert adapter.adapter_family == adapter_family
        assert adapter.timeout_seconds > 0
        assert adapter.max_pages > 0


def test_provider_fixtures_preserve_identity_schedule_and_context_fields() -> None:
    for event in provider_fixture_matrix():
        assert event["provider_calendar_id"]
        assert event["provider_event_id"]
        assert event["ical_uid"]
        assert event["starts_at"] < event["ends_at"]
        assert event["title_state"] == "available"
        assert event["participants"]
        assert event["conference_links"]


def test_generic_caldav_adapter_maps_icalendar_event_without_fetching_attachments() -> None:
    adapter = adapter_for_provider("caldav_yandex")
    normalized = adapter.map_event(
        {
            "provider_calendar_id": "primary",
            "icalendar": """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:caldav-event@example.test
DTSTART:20260701T090000Z
DTEND:20260701T100000Z
SUMMARY:CalDAV Sync
ATTACH:https://files.example.test/private.pdf
END:VEVENT
END:VCALENDAR
""",
        }
    )

    assert normalized.provider_family == "caldav_yandex"
    assert normalized.provider_calendar_id == "primary"
    assert normalized.ical_uid == "caldav-event@example.test"
    assert "private.pdf" not in str(normalized.provider_extras)


def test_exchange_ews_adapter_maps_native_event_resource() -> None:
    normalized = adapter_for_provider("exchange_ews").map_event(
        {
            "ItemId": {"Id": "ews-event", "ChangeKey": "ews-change"},
            "UID": "ews@example.test",
            "Subject": "Exchange Planning",
            "Sensitivity": "Normal",
            "Start": "2026-07-01T09:00:00Z",
            "End": "2026-07-01T10:00:00Z",
            "Organizer": {"Mailbox": {"EmailAddress": "organizer@example.test", "Name": "Organizer"}},
            "RequiredAttendees": [
                {"Mailbox": {"EmailAddress": "person@example.test", "Name": "Person"}, "ResponseType": "Accept"}
            ],
            "Location": "https://telemost.yandex.ru/j/00000000000000",
        }
    )

    assert normalized.provider_event_id == "ews-event"
    assert normalized.source_version == "ews-change"
    assert normalized.title == "Exchange Planning"
    assert normalized.participants[1]["response_status"] == "accepted"
    assert normalized.conference_links[0]["provider_family"] == "yandex_telemost"


def test_bitrix24_adapter_maps_native_event_resource() -> None:
    normalized = adapter_for_provider("bitrix24").map_event(
        {
            "ID": "bitrix-event",
            "OWNER_ID": "calendar-1",
            "NAME": "Bitrix Planning",
            "DATE_FROM": "2026-07-01T09:00:00Z",
            "DATE_TO": "2026-07-01T10:00:00Z",
            "MEETING_HOST": "organizer@example.test",
            "ATTENDEE_LIST": [{"EMAIL": "person@example.test", "STATUS": "Y"}],
            "LOCATION": "https://telemost.yandex.ru/j/00000000000000",
            "VERSION": "3",
        }
    )

    assert normalized.provider_event_id == "bitrix-event"
    assert normalized.provider_calendar_id == "calendar-1"
    assert normalized.title == "Bitrix Planning"
    assert normalized.participants[0]["participant_kind"] == "organizer"
    assert normalized.conference_links[0]["provider_family"] == "yandex_telemost"
