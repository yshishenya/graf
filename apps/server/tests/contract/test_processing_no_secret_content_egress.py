from twobrain_rec_server.observability.redaction import (
    contains_forbidden_evidence_content,
    redact_mapping,
)
from twobrain_rec_server.processing.audit import safe_audit_metadata


def test_processing_audit_metadata_drops_content_and_secret_fields() -> None:
    metadata = safe_audit_metadata(
        {
            "workflow_id": "processing/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "transcript_text": "hello secret meeting",
            "api_key": "secret",
            "signed_url": "https://example.invalid/audio?X-Amz-Signature=abc",
            "segment_count": 2,
        }
    )
    assert metadata == {
        "workflow_id": "processing/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "segment_count": 2,
    }


def test_processing_redaction_treats_mediascribe_payloads_as_sensitive() -> None:
    redacted = redact_mapping(
        {
            "mic_file": "raw bytes",
            "incoming_file": "raw bytes",
            "mediascribe_result": {"text": "meeting transcript"},
            "safe_count": 2,
        }
    )
    assert redacted["mic_file"] == "[REDACTED]"
    assert redacted["incoming_file"] == "[REDACTED]"
    assert redacted["mediascribe_result"] == "[REDACTED]"
    assert redacted["safe_count"] == 2
    assert contains_forbidden_evidence_content("x-api-key: value")
