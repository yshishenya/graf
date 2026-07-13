import pytest

from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.calendar.audit import (
    calendar_match_audit_metadata,
    metadata_only_calendar_audit,
    safe_calendar_match_audit_outcome,
    safe_calendar_match_audit_reason,
)
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


@pytest.mark.parametrize(
    "outcome",
    [
        "matched_auto",
        "matched_user",
        "no_context",
        "ambiguous",
        "skipped_private",
        "skipped_all_day",
        "skipped_manual_upload",
        "skipped_offline_or_unknown",
        "skipped_stale_calendar",
        "calendar_unavailable",
        "declined_by_user",
        "cleared_by_user",
    ],
)
def test_calendar_match_audit_accepts_only_bounded_product_outcomes(outcome: str) -> None:
    assert safe_calendar_match_audit_outcome(outcome) == outcome


@pytest.mark.parametrize(
    "reason",
    [
        "single_fresh_candidate",
        "multiple_time_candidates",
        "no_matching_event",
        "private_free_busy_skipped",
        "all_day_skipped",
        "manual_upload_skipped",
        "offline_or_unknown_skipped",
        "selected_source_stale",
        "calendar_unavailable",
        "user_selected",
        "user_declined",
        "user_cleared",
    ],
)
def test_calendar_match_audit_accepts_only_bounded_product_reasons(reason: str) -> None:
    assert safe_calendar_match_audit_reason(reason) == reason


def test_calendar_match_audit_metadata_keeps_only_bounded_safe_fields() -> None:
    metadata = calendar_match_audit_metadata(
        {
            "context_state": "matched_auto",
            "safe_reason_code": "single_fresh_candidate",
            "matcher_version": "calendar_auto_match_v1",
            "candidate_count": 1,
            "roster_count": 4,
            "freshness_class": "current",
            "decision_source": "automatic",
            "title_applied": True,
            "user_override_preserved": False,
        }
    )

    assert metadata == {
        "context_state": "matched_auto",
        "safe_reason_code": "single_fresh_candidate",
        "matcher_version": "calendar_auto_match_v1",
        "candidate_count": 1,
        "roster_count": 4,
        "freshness_class": "current",
        "decision_source": "automatic",
        "title_applied": True,
        "user_override_preserved": False,
    }


def test_calendar_match_audit_metadata_drops_raw_calendar_and_recording_content() -> None:
    metadata = calendar_match_audit_metadata(
        {
            "candidate_count": 1,
            "event_id": "00000000-0000-0000-0000-000000000098",
            "raw_event_id": "provider-event-098",
            "event_title": "Private planning title",
            "description": "Private agenda",
            "attendee_name": "Private Person",
            "attendee_email": "person@example.test",
            "meeting_url": "https://meet.example.test/private",
            "passcode": "123456",
            "provider_payload": {"raw_event_payload": "private"},
            "refresh_token": "provider-secret",
            "transcript": "private transcript text",
            "raw_audio": b"private audio",
        }
    )

    assert metadata == {"candidate_count": 1}
    serialized = repr(metadata)
    for forbidden in (
        "provider-event-098",
        "Private planning title",
        "Private agenda",
        "Private Person",
        "person@example.test",
        "meet.example.test",
        "123456",
        "provider-secret",
        "private transcript text",
        "private audio",
    ):
        assert forbidden not in serialized


def test_us2_private_response_audit_projection_keeps_zero_count_and_no_details() -> None:
    # FR-010/FR-029/FR-030, SC-011: audit mirrors only the zero-detail safe response.
    metadata = calendar_match_audit_metadata(
        {
            "context_state": "skipped_private",
            "safe_reason_code": "private_free_busy_skipped",
            "matcher_version": "calendar_auto_match_v1",
            "candidate_count": 0,
            "roster_count": 0,
            "freshness_class": "current",
            "decision_source": "system_skip",
            "title_applied": False,
            "event_id": "00000000-0000-0000-0000-000000000098",
            "event_title": "Synthetic Restricted Planning Title",
            "description": "Synthetic Restricted Agenda Text",
            "attendee_name": "Synthetic Restricted Person",
            "attendee_email": "synthetic-private-person@example.test",
            "meeting_url": "https://private.example.test/secret",
            "passcode": "synthetic-passcode",
            "provider_payload": {"private": "synthetic-private-payload"},
        }
    )

    assert metadata == {
        "context_state": "skipped_private",
        "safe_reason_code": "private_free_busy_skipped",
        "matcher_version": "calendar_auto_match_v1",
        "candidate_count": 0,
        "roster_count": 0,
        "freshness_class": "current",
        "decision_source": "system_skip",
        "title_applied": False,
    }
    serialized = repr(metadata)
    for forbidden in (
        "00000000-0000-0000-0000-000000000098",
        "Synthetic Restricted Planning Title",
        "Synthetic Restricted Agenda Text",
        "Synthetic Restricted Person",
        "synthetic-private-person@example.test",
        "private.example.test",
        "synthetic-passcode",
        "synthetic-private-payload",
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("context_state", "provider_error_text"),
        ("safe_reason_code", "provider_error_text"),
        ("matcher_version", "private_event_title"),
        ("matcher_version", "Calendar matcher v1 with spaces"),
        ("matcher_version", "v" * 65),
        ("candidate_count", -1),
        ("candidate_count", 51),
        ("candidate_count", True),
        ("roster_count", -1),
        ("roster_count", 2_147_483_648),
        ("freshness_class", "provider_stale_reason"),
        ("decision_source", "provider"),
        ("title_applied", 1),
        ("user_override_preserved", "true"),
    ],
)
def test_calendar_match_audit_metadata_rejects_invalid_allowed_values(
    field: str, value: object
) -> None:
    with pytest.raises(ValueError, match=r"calendar match audit .*rejected"):
        calendar_match_audit_metadata({field: value})


def test_calendar_match_audit_rejects_unknown_outcome_and_reason() -> None:
    with pytest.raises(ValueError, match="calendar match audit outcome rejected"):
        safe_calendar_match_audit_outcome("provider_error_text")
    with pytest.raises(ValueError, match="calendar match audit reason rejected"):
        safe_calendar_match_audit_reason("provider_error_text")


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

    assert {participant["recipient_candidate_class"] for participant in participants} == {
        "internal_attendee",
        "room",
    }
    for participant in participants:
        assert "send" not in participant
        assert "share" not in participant
        assert "access" not in participant
