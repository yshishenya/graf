import pytest
from pydantic import ValidationError

from twobrain_rec_server.domain.statuses import ProcessingAvailabilityStatus
from twobrain_rec_server.mediascribe.import_results import (
    normalize_result,
    result_digest,
)
from twobrain_rec_server.mediascribe.schemas import (
    MediaScribeDiarizationSegment,
    MediaScribeResult,
    MediaScribeSegment,
    MediaScribeWordItem,
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


def test_result_digest_changes_when_provider_words_change() -> None:
    base = MediaScribeResult(
        external_job_id="job_words_hash",
        diarization=[
            MediaScribeDiarizationSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=1,
                text="hello",
                speaker_label="SPEAKER_00",
                words=[MediaScribeWordItem(word="hello")],
            )
        ],
    )
    changed = base.model_copy(
        deep=True,
        update={
            "diarization": [
                base.diarization[0].model_copy(
                    update={"words": [MediaScribeWordItem(word="changed")]}
                )
            ]
        },
    )

    assert result_digest(base) != result_digest(changed)


def test_word_item_requires_word_and_ignores_provider_extensions() -> None:
    with pytest.raises(ValidationError):
        MediaScribeWordItem.model_validate({"start": 0, "end": 1})

    word = MediaScribeWordItem.model_validate({"word": "hello", "future": "ignored"})
    assert word.word == "hello"
    assert "future" not in word.model_dump()


def test_missing_single_track_roles_normalize_to_mixed() -> None:
    result = MediaScribeResult(
        external_job_id="job_single_role",
        transcript=[MediaScribeSegment(sequence=0, start_seconds=0, end_seconds=1, text="hello")],
        diarization=[
            MediaScribeDiarizationSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=1,
                text="hello",
                speaker_label="SPEAKER_00",
            )
        ],
    )

    normalized = normalize_result(result)

    assert normalized.transcript[0].source_role == "mixed"
    assert normalized.diarization[0].source_role == "mixed"


def test_result_schema_rejects_unbounded_attribution_reason_code() -> None:
    with pytest.raises(ValidationError):
        MediaScribeResult.model_validate(
            {
                "external_job_id": "job_invalid_reason",
                "attribution_diagnostics": {
                    "result_state": "degraded_provider_result",
                    "defect_origin": "provider",
                    "reason_codes": ["private meeting content"],
                    "raw_turn_count": 1,
                    "accepted_turn_count": 0,
                    "multi_label_conflict_count": 0,
                    "unknown_tiny_count": 0,
                    "duplicate_text_count": 0,
                    "text_conservation_status": "mismatched",
                },
            }
        )


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


def test_result_normalization_degrades_impossible_provider_chronology() -> None:
    result = MediaScribeResult(
        external_job_id="job_chronology",
        transcript=[
            MediaScribeSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=2,
                text="first second",
                source_role="mixed",
            )
        ],
        diarization=[
            MediaScribeDiarizationSegment(
                sequence=0,
                start_seconds=1,
                end_seconds=2,
                text="second",
                source_role="mixed",
                speaker_label="voice-b",
            ),
            MediaScribeDiarizationSegment(
                sequence=1,
                start_seconds=0,
                end_seconds=1,
                text="first",
                source_role="mixed",
                speaker_label="voice-a",
            ),
        ],
    )

    diagnostics = normalize_result(result).attribution_diagnostics

    assert diagnostics is not None
    assert diagnostics.result_state == "degraded_provider_result"
    assert diagnostics.accepted_turn_count == 0
    assert diagnostics.reason_codes == ("impossible_provider_chronology",)


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


def test_provider_turns_survive_when_raw_transcript_is_unavailable() -> None:
    result = MediaScribeResult(
        external_job_id="job_provider_only",
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE,
        diarization=[
            MediaScribeDiarizationSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=1,
                text="synthetic",
                source_role="system",
                speaker_label="voice-a",
            )
        ],
    )

    normalized = normalize_result(result)

    assert normalized.transcript == []
    assert normalized.diarization[0].source_role == "incoming"
    assert normalized.diarization[0].speaker_label == "voice-a"
    assert normalized.attribution_diagnostics is not None
    assert normalized.attribution_diagnostics.reason_codes == ("transcript_evidence_unavailable",)
    assert normalized.attribution_diagnostics.accepted_turn_count == 1


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


def test_import_diagnostics_use_persisted_millisecond_precision_at_unknown_threshold() -> None:
    result = MediaScribeResult(
        external_job_id="job_rounding_boundary",
        transcript_status=ProcessingAvailabilityStatus.AVAILABLE,
        transcript=[
            MediaScribeSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=0.0504,
                text="synthetic",
                source_role="mixed",
            )
        ],
        diarization=[
            MediaScribeDiarizationSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=0.0504,
                text="synthetic",
                source_role="mixed",
                speaker_label="UNKNOWN",
            )
        ],
    )

    normalized = normalize_result(result)

    assert normalized.attribution_diagnostics is not None
    assert normalized.attribution_diagnostics.result_state == "degraded_provider_result"
    assert normalized.attribution_diagnostics.unknown_tiny_count == 1
    assert normalized.diarization[0].end_seconds == 0.0504


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


def test_attribution_audit_metadata_rejects_url_and_local_path_values() -> None:
    metadata = safe_audit_metadata(
        {
            "provider_job_id": "https://private.example/job",
            "provider_model_version": "file:///private/model",
            "provider_result_version": "/Users/private/result",
            "alignment_version": "C:/private/alignment",
            "provider_build_version": "private/build.wav",
        }
    )

    assert metadata["provider_job_id"] == "[REDACTED]"
    assert metadata["provider_model_version"] == "[REDACTED]"
    assert metadata["provider_result_version"] == "[REDACTED]"
    assert metadata["alignment_version"] == "[REDACTED]"
    assert metadata["provider_build_version"] == "[REDACTED]"


def test_result_import_projects_unknown_source_role_without_dropping_raw_role_or_extensions() -> None:
    result = MediaScribeResult(
        external_job_id="job_future_role",
        transcript=[
            MediaScribeSegment(
                sequence=0,
                start_seconds=0,
                end_seconds=1,
                text="hello",
                source_role="future_track",
                provider_segment_extension={"kept": True},
            )
        ],
        provider_result_extension={"kept": True},
    )

    normalized = normalize_result(result)

    assert normalized.transcript[0].source_role == "unknown_provider_state"
    assert normalized.transcript[0].source_role_original == "future_track"
    assert normalized.transcript[0].model_extra["provider_segment_extension"] == {"kept": True}
    assert normalized.model_extra["provider_result_extension"] == {"kept": True}


def test_result_import_treats_null_diarization_as_an_empty_internal_collection() -> None:
    result = MediaScribeResult(
        external_job_id="job_without_diarization",
        transcript=[MediaScribeSegment(sequence=0, start_seconds=0, end_seconds=1, text="hello")],
        diarization=None,
    )

    normalized = normalize_result(result)

    assert normalized.diarization == []
