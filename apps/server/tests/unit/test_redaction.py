from twobrain_rec_server.observability.logging import template_path
from twobrain_rec_server.observability.redaction import redact_mapping


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
