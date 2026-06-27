from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.calendar.audit import metadata_only_calendar_audit
from twobrain_rec_server.calendar.normalize import (
    normalize_calendar_event,
    normalize_calendar_participants,
)
from twobrain_rec_server.observability.redaction import redact_mapping


def test_calendar_audit_metadata_redacts_content_bearing_fields() -> None:
    metadata = metadata_only_calendar_audit(
        {
            "event_count": 3,
            "attendee_email": "person@example.test",
            "meeting_url": "https://meet.example.test/private",
            "description": "private agenda",
            "passcode_value": "123456",
        }
    )

    assert metadata["event_count"] == 3
    assert metadata["attendee_email"] == "[REDACTED]"
    assert metadata["meeting_url"] == "[REDACTED]"
    assert metadata["description"] == "[REDACTED]"
    assert metadata["passcode_value"] == "[REDACTED]"


def test_global_redaction_covers_calendar_sensitive_keys() -> None:
    redacted = redact_mapping(
        {
            "calendar_passcode": "123456",
            "attendee_email": "person@example.test",
            "provider_payload": {"raw_event_payload": "private"},
        }
    )

    assert redacted["calendar_passcode"] == "[REDACTED]"
    assert redacted["attendee_email"] == "[REDACTED]"
    assert redacted["provider_payload"] == "[REDACTED]"


def test_provider_extras_reject_raw_payload_and_secret_fields() -> None:
    normalized = normalize_calendar_event(
        calendar_event_fixture(
            provider_extras={
                "safe_provider_kind": "synthetic",
                "raw_event_payload": {"description": "private agenda"},
                "refresh_token": "secret",
            }
        )
    )

    assert normalized.provider_extras["safe_provider_kind"] == "synthetic"
    assert normalized.provider_extras["raw_payload_retained"] is False
    assert "private agenda" not in str(normalized.provider_extras)
    assert "secret" not in str(normalized.provider_extras)


def test_recipient_candidates_do_not_create_send_share_or_access_payloads() -> None:
    participants = normalize_calendar_participants(
        [
            {"participant_kind": "required_attendee", "email": "person@example.test"},
            {"participant_kind": "room", "email": "room@example.test"},
        ]
    )

    assert {participant["recipient_candidate_class"] for participant in participants} == {"internal_attendee", "room"}
    for participant in participants:
        assert "send" not in participant
        assert "share" not in participant
        assert "access" not in participant
