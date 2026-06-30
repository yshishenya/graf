from tests.fixtures.calendar import (
    PROVIDER_CASES,
    attendee_heavy_event_fixture,
    private_free_busy_event_fixture,
    provider_fixture_matrix,
    recurrence_exception_fixture,
)


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


def test_provider_fixtures_preserve_identity_schedule_and_context_fields() -> None:
    for event in provider_fixture_matrix():
        assert event["provider_calendar_id"]
        assert event["provider_event_id"]
        assert event["ical_uid"]
        assert event["starts_at"] < event["ends_at"]
        assert event["title_state"] == "available"
        assert event["participants"]
        assert event["conference_links"]
