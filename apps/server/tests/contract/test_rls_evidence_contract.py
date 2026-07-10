from __future__ import annotations

from pathlib import Path

from twobrain_rec_server.processing.audit import safe_audit_metadata

REPO_ROOT = Path(__file__).resolve().parents[4]
FEATURE_DIR = REPO_ROOT / "specs/031-rls-hardening"
FORBIDDEN_EVIDENCE_MARKERS = (
    "raw_transcript_text",
    "raw_audio_bytes",
    "signed_dependency_url",
    "live_secret_path",
    "mediascribe_api_key_value",
)


def test_rls_feature_evidence_uses_placeholder_forbidden_markers_only() -> None:
    checked_files = [
        FEATURE_DIR / "spec.md",
        FEATURE_DIR / "plan.md",
        FEATURE_DIR / "quickstart.md",
        FEATURE_DIR / "contracts/access-outcomes.md",
        FEATURE_DIR / "contracts/tenant-context.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked_files)

    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        assert marker not in combined


def test_processing_dispatch_audit_metadata_keeps_only_safe_fields() -> None:
    metadata = safe_audit_metadata(
        {
            "workflow_id": "processing/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "started_count": 1,
            "reused_count": 0,
            "blocked_count": 0,
            "reason_code": "duplicate_workflow_reused",
            "transcript_text": "private transcript",
            "provider_payload": {"text": "private transcript"},
            "signed_url": "https://example.invalid/presigned",
            "api_key": "secret",
            "storage_object_key": "workspace/private/audio.wav",
        }
    )

    assert metadata == {
        "workflow_id": "processing/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "started_count": 1,
        "reused_count": 0,
        "blocked_count": 0,
        "reason_code": "duplicate_workflow_reused",
    }


def test_processing_result_contract_audit_metadata_keeps_safe_classification_fields() -> None:
    metadata = safe_audit_metadata(
        {
            "mediascribe_job_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "transcript_status": "unavailable",
            "transcript_reason": "no_recognizable_speech",
            "error_code": "invalid_audio_payload",
            "error_origin": "input_audio",
            "failure_reason": "invalid_audio_payload",
            "failure_source": "input_audio",
            "diagnostic_class": "input_audio_problem",
            "transcript_text": "private transcript",
            "download_url": "https://example.invalid/download",
            "storage_object_key": "workspace/private/audio.wav",
            "api_key": "secret",
        }
    )

    assert metadata == {
        "mediascribe_job_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "transcript_status": "unavailable",
        "transcript_reason": "no_recognizable_speech",
        "error_code": "invalid_audio_payload",
        "error_origin": "input_audio",
        "failure_reason": "invalid_audio_payload",
        "failure_source": "input_audio",
        "diagnostic_class": "input_audio_problem",
    }


def test_processing_result_contract_audit_does_not_restore_unknown_transcript_reason() -> None:
    metadata = safe_audit_metadata(
        {
            "transcript_status": "available",
            "transcript_reason": "private meeting words",
        }
    )

    assert metadata == {
        "transcript_status": "available",
        "transcript_reason": "[REDACTED]",
    }
