from twobrain_rec_server.domain.statuses import ProcessingAvailabilityStatus
from twobrain_rec_server.mediascribe.import_results import (
    normalize_result,
    result_digest,
)
from twobrain_rec_server.mediascribe.schemas import (
    MediaScribeDiarizationSegment,
    MediaScribeResult,
    MediaScribeSegment,
)
from twobrain_rec_server.processing.audit import safe_audit_metadata


def test_result_normalization_maps_roles_and_digest_is_stable() -> None:
    result = MediaScribeResult(
        external_job_id="job_result",
        transcript=[
            MediaScribeSegment(
                sequence=0, start_seconds=0, end_seconds=1, text="hello", source_role="microphone"
            )
        ],
        diarization=[
            MediaScribeDiarizationSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=1,
                text="hello",
                source_role="system",
                speaker_label="REMOTE_00",
            )
        ],
    )
    normalized = normalize_result(result)
    assert normalized.transcript[0].source_role == "mic"
    assert normalized.diarization[0].source_role == "incoming"
    assert result_digest(normalized) == result_digest(normalized)


def test_result_normalization_degrades_non_positive_timing() -> None:
    result = MediaScribeResult(
        external_job_id="job_bad",
        transcript=[
            MediaScribeSegment(
                sequence=0, start_seconds=2, end_seconds=1, text="bad", source_role="mic"
            )
        ],
    )
    normalized = normalize_result(result)

    assert normalized.attribution_diagnostics is not None
    assert normalized.attribution_diagnostics.result_state == "degraded_provider_result"
    assert "invalid_transcript_timing" in normalized.attribution_diagnostics.reason_codes


def test_explicit_unavailable_transcript_status_is_authoritative() -> None:
    result = MediaScribeResult(
        external_job_id="job_unavailable_with_rows",
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE,
        transcript=[
            MediaScribeSegment(
                sequence=0, start_seconds=0, end_seconds=1, text="ignored", source_role="mic"
            )
        ],
    )

    normalized = normalize_result(result)

    assert result.transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE
    assert normalized.transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE
    assert normalized.transcript == []


def test_result_normalization_detects_tiny_unknown_and_duplicate_text() -> None:
    result = MediaScribeResult(
        external_job_id="job_synthetic",
        transcript=[
            MediaScribeSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=3,
                text="synthetic phrase",
                source_role="mixed",
            )
        ],
        diarization=[
            MediaScribeDiarizationSegment(
                sequence=index,
                start_seconds=index,
                end_seconds=index + (0.04 if index == 2 else 1),
                text="synthetic phrase",
                source_role="mixed",
                speaker_label="UNKNOWN" if index == 2 else f"raw-{index}",
            )
            for index in range(3)
        ],
        provider_result_version="speaker-v2",
        provider_build_version="build-42",
        provider_model_version="model-safe",
        alignment_version="align-3",
    )

    normalized = normalize_result(result)

    diagnostics = normalized.attribution_diagnostics
    assert diagnostics is not None
    assert diagnostics.duplicate_text_count == 3
    assert diagnostics.unknown_tiny_count == 1
    assert diagnostics.provider_job_id == "job_synthetic"
    assert diagnostics.provider_result_version == "speaker-v2"
    assert diagnostics.provider_build_version == "build-42"
    assert diagnostics.provider_model_version == "model-safe"
    assert diagnostics.alignment_version == "align-3"
    assert "synthetic phrase" not in str(diagnostics.as_audit_metadata())


def test_internal_diagnostics_do_not_change_source_result_hash() -> None:
    result = MediaScribeResult(
        external_job_id="job_hash",
        transcript=[
            MediaScribeSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=1,
                text="synthetic",
                source_role="mixed",
            )
        ],
        diarization=[
            MediaScribeDiarizationSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=1,
                text="synthetic",
                source_role="mixed",
                speaker_label="raw-a",
            )
        ],
    )

    before = result_digest(result)
    normalized = normalize_result(result)

    assert normalized.attribution_diagnostics is not None
    assert result_digest(normalized) == before


def test_attribution_audit_metadata_preserves_only_bounded_diagnostics() -> None:
    metadata = safe_audit_metadata(
        {
            "provider_job_id": "job_safe_42",
            "provider_build_version": "build-42",
            "provider_model_version": "model-v3",
            "alignment_version": "align-v2",
            "raw_turn_count": 3,
            "accepted_turn_count": 0,
            "multi_label_conflict_count": 1,
            "unknown_tiny_count": 1,
            "duplicate_text_count": 3,
            "text_conservation_status": "mismatched",
            "source_result_hash": "a" * 64,
            "attribution_result_state": "degraded_provider_result",
            "defect_origin": "provider",
            "reason_codes": ["duplicated_full_text"],
            "transcript_text": "must not persist",
            "signed_url": "https://example.test/private",
        }
    )

    assert metadata == {
        "provider_job_id": "job_safe_42",
        "provider_build_version": "build-42",
        "provider_model_version": "model-v3",
        "alignment_version": "align-v2",
        "raw_turn_count": 3,
        "accepted_turn_count": 0,
        "multi_label_conflict_count": 1,
        "unknown_tiny_count": 1,
        "duplicate_text_count": 3,
        "text_conservation_status": "mismatched",
        "source_result_hash": "a" * 64,
        "attribution_result_state": "degraded_provider_result",
        "defect_origin": "provider",
        "reason_codes": ["duplicated_full_text"],
    }
