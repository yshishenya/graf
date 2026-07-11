import base64
from datetime import UTC, datetime

import pytest

from twobrain_rec_server.support.redaction import (
    REDACTED_METADATA,
    SupportIncidentRedactionError,
    blocking_unsafe_unknown_fields,
    build_server_redacted_report,
    canonical_report_json,
)


def safe_report_payload() -> dict[str, object]:
    return {
        "schema_version": "desktop-support-incident.v1",
        "app_name": "GRAF",
        "bundle_id": "pro.2brain.graf",
        "app_version": "2026.06.26",
        "build_version": "1234",
        "macos_version": "15.5",
        "architecture": "arm64",
        "locale": "ru-RU",
        "timezone": "Europe/Moscow",
        "environment_base_url_identity": "https://rec.2brain.pro/api/private?token=redacted",
        "workspace_fingerprint": "ws_fpr_7b2e",
        "user_fingerprint": "usr_fpr_01af",
        "device_fingerprint": "dev_fpr_41dd",
        "safe_device_identifier": "device:dev_fpr_41dd",
        "safe_recording_identity": "local:rec_fpr_18ce",
        "local_recording_id_fingerprint": "rec_fpr_18ce",
        "server_meeting_present": False,
        "server_meeting_fingerprint": "not_applicable",
        "server_media_revision_present": False,
        "server_media_revision_fingerprint": "not_applicable",
        "custody_lifecycle_state": "terminal_undelivered",
        "upload_queue_item_state": "failed",
        "retry_class": "terminal",
        "retry_mode": "not_retryable",
        "normal_user_action": "send_support_report",
        "failure_category": "retention_expired",
        "problem_code": "custody.retention_expired.local_retained",
        "sync_conflict_state": "retention_expired",
        "created_at": "2026-06-26T10:00:00Z",
        "updated_at": "2026-06-26T10:05:00Z",
        "retention_deadline": "2026-06-26T10:00:00Z",
        "server_identity_present": False,
        "local_media_retained": True,
        "data_loss_risk": "possible",
        "server_copy_known": False,
        "upload_attempt_count": 3,
        "last_attempt_at": "2026-06-26T09:58:00Z",
        "next_retry_at": "not_applicable",
        "last_safe_http_status": "unknown",
        "last_safe_problem_code": "retention_expired",
        "upload_session_present": False,
        "upload_session_fingerprint": "not_applicable",
        "expected_parts_count": 0,
        "uploaded_parts_count": 0,
        "range_mismatch_metadata": {"has_mismatch": False, "missing_range_count": 0},
        "local_file_completeness_profile": {
            "manifest_present": True,
            "manifest_schema_version": "local_recording_manifest.v1",
            "audio_files_present": True,
            "missing_file_count": 0,
            "corrupt_file_count": 0,
            "total_size_bucket": "100mb_1gb",
            "duration_bucket": "30m_2h",
            "exact_size_bytes": 123456789,
            "raw_path": "/Users/example/private.wav",
        },
        "local_purge_state": "none",
        "local_purge_tasks": [],
        "local_purge_ack_state": "not_applicable",
        "processing_status": "not_submitted",
        "app_queue_schema_version": "desktop-upload-queue.v1",
        "ledger_schema_version": "desktop-upload-ledger.v1",
        "redaction_state": "metadata_only",
        "affected_count": 1,
        "safe_affected_identities": ["affected_fpr_01"],
    }


def test_redacts_to_deterministic_metadata_only_report() -> None:
    report = build_server_redacted_report(
        safe_report_payload(),
        received_at=datetime(2026, 6, 26, 11, 0, tzinfo=UTC),
    )

    assert report["environment_base_url_identity"] == "rec.2brain.pro"
    assert report["local_file_completeness_profile"]["total_size_bucket"] == "100mb_1gb"
    assert "exact_size_bytes" not in report["local_file_completeness_profile"]
    assert "raw_path" not in report["local_file_completeness_profile"]
    assert report["redaction_state"] == "metadata_only"
    assert report["affected_count"] == 1
    assert report["safe_affected_identities"] == ["affected_fpr_01"]
    assert report["redaction_result"] == "accepted_with_redactions"
    assert report["safe_report_fingerprint"].startswith("report_fpr_")
    assert report["dedupe_key"].startswith("support_dedupe_")
    assert canonical_report_json(report) == canonical_report_json(dict(reversed(report.items())))


def test_safe_report_fingerprint_is_stable_across_received_at() -> None:
    first = build_server_redacted_report(
        safe_report_payload(),
        received_at=datetime(2026, 6, 26, 11, 0, tzinfo=UTC),
    )
    second = build_server_redacted_report(
        safe_report_payload(),
        received_at=datetime(2026, 6, 26, 11, 5, tzinfo=UTC),
    )

    assert first["received_at"] != second["received_at"]
    assert first["safe_report_fingerprint"] == second["safe_report_fingerprint"]


def test_redacts_forbidden_values_and_never_keeps_content() -> None:
    payload = safe_report_payload()
    payload["last_safe_problem_code"] = "token=abc123"
    report = build_server_redacted_report(payload)
    encoded = canonical_report_json(report)

    assert report["last_safe_problem_code"] == REDACTED_METADATA
    assert report["forbidden_field_count"] >= 1
    assert "abc123" not in encoded


def test_rejects_unknown_forbidden_content_before_redaction() -> None:
    payload = safe_report_payload()
    payload["unknown_transcript_text"] = "transcript text: private words"
    payload["user_email"] = "person@example.test"

    assert blocking_unsafe_unknown_fields(payload) == ("unknown_transcript_text", "user_email")
    with pytest.raises(SupportIncidentRedactionError, match="support_incident.unsafe_payload"):
        build_server_redacted_report(payload)


def test_missing_safe_values_stay_present_as_unknown() -> None:
    payload = safe_report_payload()
    del payload["architecture"]

    report = build_server_redacted_report(payload)

    assert report["architecture"] == "unknown"
    assert "architecture" in report


def test_redacts_aggregate_identities_to_bounded_safe_list() -> None:
    payload = safe_report_payload()
    payload["affected_count"] = 6
    payload["safe_affected_identities"] = [
        "affected_fpr_01",
        "affected_fpr_02",
        "affected_fpr_03",
        "affected_fpr_04",
        "affected_fpr_05",
        "affected_fpr_06",
    ]

    report = build_server_redacted_report(payload)

    assert report["affected_count"] == 6
    assert report["safe_affected_identities"] == [
        "affected_fpr_01",
        "affected_fpr_02",
        "affected_fpr_03",
        "affected_fpr_04",
        "affected_fpr_05",
    ]


def test_redacts_human_text_in_safe_identifier_fields() -> None:
    payload = safe_report_payload()
    payload["workspace_fingerprint"] = "Alice Smith"
    payload["safe_device_identifier"] = "device:Alice-MacBook"
    payload["safe_recording_identity"] = "local:Team Sync"
    payload["safe_affected_identities"] = ["Customer CEO"]

    report = build_server_redacted_report(payload)

    assert report["workspace_fingerprint"] == REDACTED_METADATA
    assert report["safe_device_identifier"] == REDACTED_METADATA
    assert report["safe_recording_identity"] == REDACTED_METADATA
    assert report["safe_affected_identities"] == [REDACTED_METADATA]


def test_redacts_encoded_chunks_from_support_incident_report() -> None:
    secret = b"meeting content: Alice roadmap and credential token"
    encoded = base64.urlsafe_b64encode(secret).decode("ascii").rstrip("=")
    payload = safe_report_payload()
    payload["local_purge_tasks"] = [encoded, "purge_local_buffers"]
    payload["app_name"] = encoded
    payload["last_safe_problem_code"] = encoded
    payload["local_file_completeness_profile"]["duration_bucket"] = encoded

    report = build_server_redacted_report(payload)
    report_json = canonical_report_json(report)

    assert report["local_purge_tasks"] == [REDACTED_METADATA, "purge_local_buffers"]
    assert report["app_name"] == REDACTED_METADATA
    assert report["last_safe_problem_code"] == REDACTED_METADATA
    assert report["local_file_completeness_profile"]["duration_bucket"] == REDACTED_METADATA
    assert encoded not in report_json
    assert report["redaction_result"] == "accepted_with_redactions"


def test_local_purge_tasks_are_bounded_to_metadata_enums() -> None:
    payload = safe_report_payload()
    payload["local_purge_tasks"] = [
        "purge_local_buffers",
        "acknowledged",
        "free form task",
    ] + ["pending"] * 12

    report = build_server_redacted_report(payload)

    assert report["local_purge_tasks"] == [
        "purge_local_buffers",
        "acknowledged",
        REDACTED_METADATA,
        "pending",
        "pending",
        "pending",
        "pending",
        "pending",
        "pending",
        "pending",
    ]


def test_rejects_non_metadata_only_or_unsupported_schema() -> None:
    payload = safe_report_payload()
    payload["redaction_state"] = "raw"
    with pytest.raises(SupportIncidentRedactionError, match="support_incident.unsafe_payload"):
        build_server_redacted_report(payload)

    payload = safe_report_payload()
    payload["schema_version"] = "desktop-support-incident.v0"
    with pytest.raises(SupportIncidentRedactionError, match="support_incident.unsupported_schema"):
        build_server_redacted_report(payload)
