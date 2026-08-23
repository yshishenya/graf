from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from twobrain_rec_server.domain.speaker_turns import SpeakerTurnDiagnostics
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    SummaryStatus,
)


class MediaScribeSubmitRequest(BaseModel):
    mic_object_key: str
    incoming_object_key: str
    diarize: bool = True
    summarize: bool = False
    speaker_count_mode: str | None = None
    num_speakers: int | None = Field(default=None, ge=1)


class MediaScribeSubmitResponse(BaseModel):
    external_job_id: str = Field(min_length=1)
    status: MediaScribeJobStatus = MediaScribeJobStatus.UPLOADED


class MediaScribePollResponse(BaseModel):
    external_job_id: str
    status: MediaScribeJobStatus
    reason_code: str | None = None
    error_code: str | None = None
    error_origin: str | None = None


class MediaScribeSegment(BaseModel):
    sequence: int = Field(ge=0)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    text: str
    source_role: str
    source_role_original: str | None = None


class MediaScribeDiarizationSegment(MediaScribeSegment):
    speaker_label: str


class MediaScribeResult(BaseModel):
    external_job_id: str
    language: str | None = None
    transcript_status: ProcessingAvailabilityStatus = ProcessingAvailabilityStatus.UNAVAILABLE
    transcript_reason: Literal["no_recognizable_speech"] | None = None
    failure_reason: str | None = None
    failure_source: str | None = None
    transcript: list[MediaScribeSegment] = Field(default_factory=list)
    diarization: list[MediaScribeDiarizationSegment] = Field(default_factory=list)
    summary_status: SummaryStatus = SummaryStatus.NOT_REQUESTED
    result_version: int = Field(default=1, ge=1)
    provider_result_version: str | int | None = None
    provider_build_version: str | int | None = None
    provider_model_version: str | int | None = None
    alignment_version: str | int | None = None
    attribution_diagnostics: SpeakerTurnDiagnostics | None = Field(default=None, exclude=True)

    @field_validator("transcript_status")
    @classmethod
    def require_result_contract_transcript_status(
        cls,
        value: ProcessingAvailabilityStatus,
    ) -> ProcessingAvailabilityStatus:
        if value not in {
            ProcessingAvailabilityStatus.AVAILABLE,
            ProcessingAvailabilityStatus.UNAVAILABLE,
        }:
            raise ValueError("unsupported_transcript_status")
        return value

    @model_validator(mode="before")
    @classmethod
    def infer_legacy_transcript_status(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if (
            data.get("transcript_status") is None
            and data.get("transcript_reason") is None
            and data.get("transcript")
        ):
            return {**data, "transcript_status": ProcessingAvailabilityStatus.AVAILABLE}
        return data
