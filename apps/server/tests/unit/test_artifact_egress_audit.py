from twobrain_rec_server.cabinet.egress import safe_audit_metadata


def test_safe_audit_metadata_keeps_only_allowed_redacted_scalars() -> None:
    metadata = safe_audit_metadata(
        {
            "artifact_class": "transcript",
            "byte_length": 123,
            "storage_object_key": "private/object/key",
            "share_token_hash": "private-token-hash",
            "nested": {"secret": "value"},
        }
    )

    assert metadata == {"artifact_class": "transcript", "byte_length": 123}
