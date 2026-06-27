from twobrain_rec_server.calendar.conference_links import (
    classify_conference_link,
    extract_conference_link_candidates,
    safe_link_preview,
)
from twobrain_rec_server.calendar.normalize import normalize_icalendar_event


def test_classifies_common_conference_links_without_full_url_preview() -> None:
    classified = classify_conference_link("https://telemost.yandex.ru/j/00000000000000")

    assert classified.provider_family == "yandex_telemost"
    assert classified.url_hash.startswith("sha256:")
    assert classified.redacted_url_preview == "telemost.yandex.ru/..."


def test_safe_link_preview_drops_query_and_path_secret_material() -> None:
    assert safe_link_preview("https://meet.google.com/abc-defg-hij?pwd=secret") == "meet.google.com/..."


def test_extracts_multiple_links_and_keeps_redacted_diagnostics() -> None:
    links = extract_conference_link_candidates(
        "Join https://meet.google.com/abc-defg-hij?pwd=secret",
        "Backup https://telemost.yandex.ru/j/00000000000000?passcode=123",
        "Duplicate https://meet.google.com/abc-defg-hij?pwd=secret",
    )

    assert [link.provider_family for link in links] == ["google_meet", "yandex_telemost"]
    assert all(link.redacted_url_preview.endswith("/...") for link in links)
    assert all("secret" not in link.redacted_url_preview for link in links)
    assert any(link.contains_passcode for link in links)


def test_icalendar_attachment_urls_are_not_treated_as_conference_links() -> None:
    normalized = normalize_icalendar_event(
        """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:attachment-only@example.test
DTSTART:20260701T090000Z
DTEND:20260701T100000Z
SUMMARY:Attachment only
ATTACH:https://files.example.test/private.pdf
END:VEVENT
END:VCALENDAR
""",
        provider_family="caldav_yandex",
    )

    assert normalized.conference_links == []
    assert "private.pdf" not in str(normalized.provider_extras)


def test_cancelled_icalendar_event_does_not_expose_stale_conference_link() -> None:
    normalized = normalize_icalendar_event(
        """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:cancelled-link@example.test
DTSTART:20260701T090000Z
DTEND:20260701T100000Z
SUMMARY:Cancelled meeting
STATUS:CANCELLED
DESCRIPTION:Old link https://meet.google.com/abc-defg-hij?pwd=secret
END:VEVENT
END:VCALENDAR
""",
        provider_family="caldav_yandex",
    )

    assert normalized.source_status == "cancelled"
    assert normalized.conference_links == []
