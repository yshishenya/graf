from __future__ import annotations

import pytest

from twobrain_rec_server.normalization.audit import (
    ALLOWED_METADATA_KEYS,
    NORMALIZATION_AUDIT_EVENT_TYPES,
    NormalizationAuditError,
    build_audit_receipt,
)


def test_audit_receipt_accepts_only_safe_typed_metadata() -> None:
    receipt = build_audit_receipt(
        "playback_normalization_completed",
        {
            "profile_version": "review_m4a_aac_lc_48k_mono_64k_v1",
            "state": "ready",
            "attempt_count": 1,
            "retry_cycle_count": 0,
            "stream_count": 1,
            "audio_stream_count": 1,
            "duration_bucket": "under_5m",
            "byte_bucket": "under_16mib",
            "full_decode_passed": True,
            "moov_before_mdat": True,
            "cleanup_result": "not_required",
        },
    )

    assert receipt.event_type in NORMALIZATION_AUDIT_EVENT_TYPES
    assert set(receipt.metadata_json) <= ALLOWED_METADATA_KEYS
    assert receipt.metadata_json["state"] == "ready"


def test_audit_receipt_accepts_durable_missing_object_recheck_truth() -> None:
    receipt = build_audit_receipt(
        "playback_normalization_temp_cleaned",
        {"cleanup_result": "already_missing_pending_recheck"},
    )

    assert receipt.metadata_json == {
        "cleanup_result": "already_missing_pending_recheck"
    }


def test_tolerant_mode_is_policy_fact_and_does_not_claim_recovery() -> None:
    receipt = build_audit_receipt(
        "playback_normalization_started",
        {"normalization_mode": "tolerant"},
    )

    assert receipt.metadata_json == {"normalization_mode": "tolerant"}
    assert "recovered_source" not in receipt.metadata_json

    explicit_truth = build_audit_receipt(
        "playback_normalization_completed",
        {
            "profile_version": "review_m4a_aac_lc_48k_mono_64k_v1",
            "state": "ready",
            "attempt_count": 1,
            "full_decode_passed": True,
            "moov_before_mdat": True,
            "normalization_mode": "tolerant",
            "recovered_source": False,
        },
    )
    assert explicit_truth.metadata_json["recovered_source"] is False


def test_audit_receipt_rejects_unallowlisted_normalization_mode() -> None:
    with pytest.raises(NormalizationAuditError):
        build_audit_receipt(
            "playback_normalization_started",
            {"normalization_mode": "strict"},
        )


def test_manual_retry_audit_requires_bounded_state_and_reason() -> None:
    receipt = build_audit_receipt(
        "playback_normalization_manual_retry_requested",
        {"state": "retry_wait", "reason_code": "worker_interrupted"},
    )
    assert receipt.metadata_json == {
        "state": "retry_wait",
        "reason_code": "worker_interrupted",
    }

    with pytest.raises(NormalizationAuditError):
        build_audit_receipt(
            "playback_normalization_manual_retry_requested",
            {"state": "retry_wait"},
        )


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "filename",
        "title",
        "object_key",
        "local_path",
        "object_url",
        "ffmpeg_stderr",
        "tags",
        "chapters",
        "audio",
        "transcript",
        "summary",
        "signed_url",
        "provider_payload",
        "credential",
    ],
)
def test_audit_receipt_rejects_forbidden_keys_without_echoing_values(forbidden_key: str) -> None:
    secret = "private-value-that-must-not-escape"
    with pytest.raises(NormalizationAuditError) as exc_info:
        build_audit_receipt(
            "playback_normalization_failed",
            {"reason_code": "corrupt_source", forbidden_key: secret},
        )
    assert secret not in str(exc_info.value)


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "/private/tmp/meeting.m4a",
        "s3://private-bucket/object-key",
        "https://storage.example.invalid/signed?token=secret",
        "Bearer secret-token",
        "ffmpeg stderr: private source title",
        "meeting-review.wav",
    ],
)
def test_audit_receipt_rejects_sensitive_values_even_under_allowed_key(unsafe_value: str) -> None:
    with pytest.raises(NormalizationAuditError) as exc_info:
        build_audit_receipt(
            "playback_normalization_temp_cleaned",
            {"cleanup_result": unsafe_value},
        )
    assert unsafe_value not in str(exc_info.value)
