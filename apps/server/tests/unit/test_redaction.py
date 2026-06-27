from twobrain_rec_server.observability.logging import template_path
from twobrain_rec_server.observability.redaction import (
    contains_forbidden_evidence_content,
    redact_mapping,
)


def test_redacts_secret_like_keys_recursively() -> None:
    payload = {
        "status": "failed",
        "authorization": "Bearer secret",
        "nested": {"minio_secret_key": "secret", "byte_count": 10},
    }
    redacted = redact_mapping(payload)
    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["nested"]["minio_secret_key"] == "[REDACTED]"
    assert redacted["nested"]["byte_count"] == 10


def test_templates_resource_identifiers_in_request_paths() -> None:
    path = "/api/v1/meetings/11111111-1111-1111-1111-111111111111/upload-sessions"

    assert template_path(path) == "/api/v1/meetings/{uuid}/upload-sessions"


def test_redacts_calendar_sensitive_keys_recursively() -> None:
    payload = {
        "calendar": {
            "attendee_email_dump": ["person@example.test"],
            "conference_url": "https://meet.example.test/private",
            "raw_event_payload": {"description": "private agenda"},
        },
        "safe_event_count": 2,
    }

    redacted = redact_mapping(payload)

    assert redacted["calendar"]["attendee_email_dump"] == "[REDACTED]"
    assert redacted["calendar"]["conference_url"] == "[REDACTED]"
    assert redacted["calendar"]["raw_event_payload"] == "[REDACTED]"
    assert redacted["safe_event_count"] == 2


def test_forbidden_evidence_scan_catches_calendar_secret_markers() -> None:
    assert contains_forbidden_evidence_content("app_password: synthetic")
    assert contains_forbidden_evidence_content("raw_event_payload: {...}")
    assert contains_forbidden_evidence_content("passcode: 123456")
