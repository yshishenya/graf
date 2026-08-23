from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from twobrain_rec_server.domain.speaker_turns import canonical_speaker_model
from twobrain_rec_server.domain.statuses import ProcessingAvailabilityStatus
from twobrain_rec_server.mediascribe.schemas import MediaScribeResult

ROLE_ALIASES = {
    "microphone": "mic",
    "mic": "mic",
    "system": "incoming",
    "incoming": "incoming",
    "remote": "incoming",
    # A v5 result is one chronological ASR timeline, not a merged pair. Keep
    # its provenance explicit instead of falsely relabeling it as microphone or
    # incoming system audio.
    "mixed": "mixed",
    "media": "mixed",
}


class MediaScribeResultValidationError(ValueError):
    pass


def _persisted_seconds(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def normalize_source_role(role: str) -> str:
    normalized = ROLE_ALIASES.get(role.strip().lower())
    if normalized is None:
        raise MediaScribeResultValidationError("unsupported_source_role")
    return normalized


def normalize_result(result: MediaScribeResult) -> MediaScribeResult:
    if (
        result.transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE
        and not result.diarization
    ):
        return result.model_copy(update={"transcript": []})
    transcript = []
    source_transcript = (
        []
        if result.transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE
        else result.transcript
    )
    for segment in source_transcript:
        transcript.append(
            segment.model_copy(update={"source_role": normalize_source_role(segment.source_role)})
        )
    diarization = []
    for segment in result.diarization:
        diarization.append(
            segment.model_copy(update={"source_role": normalize_source_role(segment.source_role)})
        )
    diagnostics = canonical_speaker_model(
        [
            segment.model_copy(
                update={
                    "start_seconds": _persisted_seconds(segment.start_seconds),
                    "end_seconds": _persisted_seconds(segment.end_seconds),
                }
            )
            for segment in transcript
        ],
        [
            segment.model_copy(
                update={
                    "start_seconds": _persisted_seconds(segment.start_seconds),
                    "end_seconds": _persisted_seconds(segment.end_seconds),
                }
            )
            for segment in diarization
        ],
        processing_result_id=UUID(int=0),
        provider_job_id=result.external_job_id,
        provider_versions={
            "result_version": result.provider_result_version or result.result_version,
            "build_version": result.provider_build_version,
            "model_version": result.provider_model_version,
            "alignment_version": result.alignment_version,
        },
    ).diagnostics
    return result.model_copy(
        update={
            "transcript": transcript,
            "diarization": diarization,
            "attribution_diagnostics": diagnostics,
        }
    )


def result_digest(result: MediaScribeResult) -> str:
    payload = result.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
