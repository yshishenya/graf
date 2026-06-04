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
