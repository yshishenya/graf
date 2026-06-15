import pytest

from twobrain_rec_server.mediascribe.import_results import (
    MediaScribeResultValidationError,
    normalize_result,
    result_digest,
)
from twobrain_rec_server.mediascribe.schemas import (
    MediaScribeDiarizationSegment,
    MediaScribeResult,
    MediaScribeSegment,
)


def test_result_normalization_maps_roles_and_digest_is_stable() -> None:
    result = MediaScribeResult(
        external_job_id="job_result",
        transcript=[MediaScribeSegment(sequence=0, start_seconds=0, end_seconds=1, text="hello", source_role="microphone")],
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


def test_result_normalization_rejects_negative_timing() -> None:
    result = MediaScribeResult(
        external_job_id="job_bad",
        transcript=[MediaScribeSegment(sequence=0, start_seconds=2, end_seconds=1, text="bad", source_role="mic")],
    )
    with pytest.raises(MediaScribeResultValidationError):
        normalize_result(result)
