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


def test_safe_audit_metadata_for_playback_keeps_source_mode_without_private_audio_fields() -> None:
    metadata = safe_audit_metadata(
        {
            "artifact_class": "audio",
            "request_class": "playback",
            "source_mode": "combined_review_stream",
            "byte_length": 456,
            "storage_object_key": "private/object/key",
            "sha256": "private-hash",
            "raw_audio": "private samples",
            "transcript_text": "private transcript",
        }
    )

    assert metadata == {
        "artifact_class": "audio",
        "request_class": "playback",
        "source_mode": "combined_review_stream",
        "byte_length": 456,
    }
