from twobrain_rec_server.cabinet.egress import ALLOWED_AUDIT_KEYS
from twobrain_rec_server.cabinet.exports import MEDIA_TYPES, SCHEMA_VERSION


def test_content_export_audit_allowlist_excludes_content_provider_and_storage_fields() -> None:
    forbidden = {
        "text",
        "transcript_text",
        "summary_text",
        "speaker_label",
        "source_references",
        "mediascribe_job_id",
        "provider_id",
        "api_key",
        "authorization",
        "storage_object_key",
        "signed_url",
        "private_path",
    }

    assert ALLOWED_AUDIT_KEYS.isdisjoint(forbidden)
    assert {
        "content_scope",
        "format",
        "processing_result_id",
        "outcome_set_id",
        "revision_token",
        "revision_fingerprint",
        "schema_version",
        "renderer_version",
        "turn_policy_version",
        "byte_length",
    } <= ALLOWED_AUDIT_KEYS


def test_content_export_public_contract_has_only_allowlisted_formats_and_version() -> None:
    assert set(MEDIA_TYPES) == {"txt", "md", "csv", "xlsx", "json", "srt", "vtt"}
    assert SCHEMA_VERSION == "graf.transcript-export.v2"
    assert all("zip" not in media_type for media_type in MEDIA_TYPES.values())
