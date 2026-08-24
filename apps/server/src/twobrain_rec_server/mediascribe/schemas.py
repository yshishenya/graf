from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from twobrain_rec_server.domain.speaker_turns import SpeakerTurnDiagnostics
from twobrain_rec_server.domain.statuses import (
    ProcessingAvailabilityStatus,
    SummaryStatus,
)

_SAFE_PROVIDER_VALUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class _ForwardCompatibleStrEnum(StrEnum):
    """A provider enum that keeps an unknown value instead of rejecting it."""

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str) or not value or len(value) > 128:
            return None
        # Keep an unknown provider enum forward-compatible without retaining
        # arbitrary response text in a durable DTO. The adapter separately
        # exposes the bounded raw token when it is safe to do so.
        if not _SAFE_PROVIDER_VALUE_RE.fullmatch(value):
            value = "unknown_provider_state"
        member = str.__new__(cls, value)
        member._name_ = "UNKNOWN"
        member._value_ = value
        return member

    @property
    def is_known(self) -> bool:
        return self.name != "UNKNOWN"

    @property
    def safe_value(self) -> str:
        return self.value if self.is_known else "unknown_provider_state"


class MediaScribeProviderStatus(_ForwardCompatibleStrEnum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    DIARIZING = "diarizing"
    SUMMARIZING = "summarizing"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
    BLOCKED = "blocked"


class MediaScribeProviderQueueState(_ForwardCompatibleStrEnum):
    WAITING_FOR_DISPATCH = "waiting_for_dispatch"
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETING = "deleting"


class MediaScribeSummaryState(_ForwardCompatibleStrEnum):
    NOT_REQUESTED = "not_requested"
    UNAVAILABLE = "unavailable"
    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


class MediaScribeDeletionState(_ForwardCompatibleStrEnum):
    CANCELLING = "cancelling"
    COMPLETED = "completed"


class MediaScribeModel(BaseModel):
    # These are server-side provider-boundary DTOs. Keep forward-compatible
    # fields in memory so a newer provider response can be reconciled/debugged,
    # while GRAF projections must continue to copy only their explicit fields.
    model_config = ConfigDict(extra="allow")


class MediaScribeResponseHeaders(MediaScribeModel):
    status_code: int | None = None
    location: str | None = None
    retry_after_seconds: int | None = None
    idempotency_replayed: bool | None = None
    request_id: str | None = None
    api_version: str | None = None
    job_status: str | None = None
    queue_state: str | None = None
    job_deleted: bool | None = None
    error_code: str | None = None
    error_origin: str | None = None
    error_retryable: bool | None = None
    raw_headers: dict[str, str] = Field(default_factory=dict)


class MediaScribeProblemDetails(MediaScribeModel):
    type: str | None = None
    title: str | None = None
    status: int | None = None
    detail: str | None = None
    instance: str | None = None
    code: str | None = None
    retryable: bool | None = None
    request_id: str | None = None
    job_id: str | None = None
    error_origin: str | None = None
    errors: list[dict[str, Any]] | None = None


class MediaScribeSubmitRequest(MediaScribeModel):
    mic_object_key: str
    incoming_object_key: str
    diarize: bool = True
    summarize: bool = False
    speaker_count_mode: str | None = None
    num_speakers: int | None = Field(default=None, ge=1)


class MediaScribeMediaSource(MediaScribeModel):
    role: str
    filename: str
    content_type: str | None = None


class MediaScribeInferenceRuntimeVersion(MediaScribeModel):
    status: str
    alignment_algorithm_version: str | None = None
    asr_model_version: str | None = None
    asr_profile: str | None = None
    backend: str | None = None
    build_sha: str | None = None
    diarization_model_version: str | None = None
    exclusive_gpu_model_residency: bool | None = None
    gpu_concurrency: int | None = None
    image_digest: str | None = None
    max_request_wall_seconds: int | None = None
    model_lock_sha256: str | None = None
    provenance_complete: bool = False
    service_version: str | None = None


class MediaScribeWorkerBuild(MediaScribeModel):
    service_version: str
    build_sha: str
    image_digest: str
    worker_count: int


class MediaScribeWorkerFleet(MediaScribeModel):
    status: str
    heartbeat_max_age_seconds: int
    active_workers: int = 0
    builds: list[MediaScribeWorkerBuild] = Field(default_factory=list)
    busy_workers: int = 0
    degraded_workers: int = 0
    homogeneous: bool = False
    matches_api_build: bool = False
    provenance_complete: bool = False
    stale_workers: int = 0


class MediaScribeCapabilitiesResponse(MediaScribeModel):
    api_contract_version: str = "v1"
    asynchronous_jobs: bool = True
    automatic_speaker_count_when_omitted: bool = True
    cancellation_grace_seconds: int
    default_poll_interval_seconds: int = 3
    delivery_without_idempotency_key: str = "at_least_once"
    dual_track_supported: bool = True
    idempotency_key_header: str = "Idempotency-Key"
    idempotency_key_max_length: int = 256
    idempotency_key_required: bool = False
    max_active_jobs_global: int
    max_active_jobs_per_user: int
    max_job_attempts: int
    max_speaker_count_hint: int
    max_upload_size_bytes_per_file: int
    queue_dispatch_max_attempts: int
    queue_dispatch_max_backoff_seconds: int
    speaker_count_modes: list[str] = Field(default_factory=list)
    summary_available: bool
    summary_requested_by_default: bool = True
    summary_supported: bool = True
    supported_media_extensions: list[str] = Field(default_factory=list)
    headers: MediaScribeResponseHeaders = Field(default_factory=MediaScribeResponseHeaders)
    http_status: int | None = None


class MediaScribeVersionResponse(MediaScribeModel):
    api_contract_version: str = "v1"
    service: str
    service_version: str
    build_sha: str
    image_digest: str
    queue_contract: str
    inference_backend: str
    inference_runtime: MediaScribeInferenceRuntimeVersion
    worker_fleet: MediaScribeWorkerFleet
    max_upload_size_bytes_per_file: int
    headers: MediaScribeResponseHeaders = Field(default_factory=MediaScribeResponseHeaders)
    http_status: int | None = None


class MediaScribeJobSnapshotResponse(MediaScribeModel):
    id: str = Field(min_length=1)
    source_filename: str = ""
    source_mode: str = "single"
    source_media: list[MediaScribeMediaSource] | None = None
    content_type: str | None = None
    diarization_enabled: bool = False
    summary_enabled: bool = False
    summary_state: MediaScribeSummaryState = MediaScribeSummaryState.QUEUED
    status: MediaScribeProviderStatus = MediaScribeProviderStatus.UPLOADED
    queue_state: MediaScribeProviderQueueState = MediaScribeProviderQueueState.WAITING_FOR_DISPATCH
    status_raw: str | None = None
    queue_state_raw: str | None = None
    status_projection: str | None = None
    queue_state_projection: str | None = None
    attempt: int = 0
    max_attempts: int = 3
    queue_position: int | None = None
    retry_after_seconds: int | None = None
    next_retry_at: str | None = None
    result_available: bool = False
    idempotency_replayed: bool = False
    num_speakers: int | None = Field(default=None, ge=1)
    error_message: str | None = None
    error_code: str | None = None
    error_origin: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MediaScribeJobResponse(MediaScribeJobSnapshotResponse):
    object: str = "transcription.job"
    retrieve_url: str | None = None
    result_url: str | None = None
    deletion_url: str | None = None
    headers: MediaScribeResponseHeaders = Field(default_factory=MediaScribeResponseHeaders)
    http_status: int | None = None


class MediaScribeSubmitResponse(MediaScribeModel):
    external_job_id: str = Field(min_length=1)
    status: MediaScribeProviderStatus = MediaScribeProviderStatus.UPLOADED
    queue_state: MediaScribeProviderQueueState | None = None
    status_raw: str | None = None
    queue_state_raw: str | None = None
    status_projection: str | None = None
    queue_state_projection: str | None = None
    attempt: int = 0
    max_attempts: int = 3
    retry_after_seconds: int | None = None
    next_retry_at: str | None = None
    result_available: bool = False
    idempotency_replayed: bool = False
    location: str | None = None
    result_url: str | None = None
    deletion_url: str | None = None
    request_id: str | None = None
    api_contract_version: str | None = None
    egress_state: str = "accepted"
    headers: MediaScribeResponseHeaders = Field(default_factory=MediaScribeResponseHeaders)
    http_status: int | None = None


class MediaScribePollResponse(MediaScribeModel):
    external_job_id: str = Field(min_length=1)
    status: MediaScribeProviderStatus
    queue_state: MediaScribeProviderQueueState | None = None
    status_raw: str | None = None
    queue_state_raw: str | None = None
    status_projection: str | None = None
    queue_state_projection: str | None = None
    reason_code: str | None = None
    error_code: str | None = None
    error_origin: str | None = None
    error_message: str | None = None
    attempt: int = 0
    max_attempts: int = 3
    retry_after_seconds: int | None = None
    next_retry_at: str | None = None
    result_available: bool = False
    request_id: str | None = None
    headers: MediaScribeResponseHeaders = Field(default_factory=MediaScribeResponseHeaders)
    http_status: int | None = None


class MediaScribeTranscriptSegment(MediaScribeModel):
    sequence: int = Field(default=0, ge=0)
    start_seconds: float = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("start_seconds", "start"),
    )
    end_seconds: float = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("end_seconds", "end"),
    )
    text: str
    source_role: str | None = None
    source_role_original: str | None = None


class MediaScribeDiarizationSegment(MediaScribeTranscriptSegment):
    speaker_label: str = Field(
        validation_alias=AliasChoices("speaker_label", "speaker"),
    )


class MediaScribeAcousticSpeakerTurn(MediaScribeModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    speaker: str
    source_role: str | None = None

class MediaScribeOverlapInterval(MediaScribeModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    speaker_count: int = Field(ge=2)
    source_role: str | None = None
    attribution: str = "unresolved"

class MediaScribeProvenance(MediaScribeModel):
    asr_model_version: str | None = None
    diarization_model_version: str | None = None
    alignment_algorithm_version: str | None = None
    detected_speaker_count: int | None = None
    quality_state: str | None = None
    quality_reasons: list[str] = Field(default_factory=list)
    word_timestamps_present: bool | None = None
    word_timestamps_complete: bool | None = None
    effective_diarization_parameters: dict[str, Any] = Field(default_factory=dict)
    worker_build_sha: str | None = None
    worker_image_digest: str | None = None
    service_version: str | None = None
    build_sha: str | None = None
    image_digest: str | None = None
    provenance_complete: bool | None = None


class MediaScribeSummaryResponse(MediaScribeModel):
    status: MediaScribeSummaryState
    content: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    model: str | None = None
    updated_at: str | None = None
    headers: MediaScribeResponseHeaders = Field(default_factory=MediaScribeResponseHeaders)
    http_status: int | None = None


class MediaScribeResult(MediaScribeModel):
    external_job_id: str = Field(min_length=1)
    job: MediaScribeJobSnapshotResponse | None = None
    language: str | None = None
    transcript_status: ProcessingAvailabilityStatus = ProcessingAvailabilityStatus.UNAVAILABLE
    transcript_reason: str | None = None
    failure_reason: str | None = None
    failure_source: str | None = None
    transcript: list[MediaScribeTranscriptSegment] = Field(default_factory=list)
    diarization: list[MediaScribeDiarizationSegment] | None = Field(default_factory=list)
    acoustic_speaker_turns: list[MediaScribeAcousticSpeakerTurn] = Field(default_factory=list)
    overlaps: list[MediaScribeOverlapInterval] = Field(default_factory=list)
    provenance: MediaScribeProvenance | None = None
    summary: MediaScribeSummaryResponse | None = None
    downloads: dict[str, str] = Field(default_factory=dict)
    summary_status: SummaryStatus = SummaryStatus.NOT_REQUESTED
    result_version: int = Field(default=1, ge=1)
    provider_result_version: str | int | None = None
    provider_build_version: str | int | None = None
    provider_model_version: str | int | None = None
    alignment_version: str | int | None = None
    attribution_diagnostics: SpeakerTurnDiagnostics | None = Field(default=None, exclude=True)
    request_id: str | None = None
    headers: MediaScribeResponseHeaders = Field(default_factory=MediaScribeResponseHeaders)
    http_status: int | None = None

    @model_validator(mode="after")
    def require_result_contract_transcript_status(self) -> MediaScribeResult:
        if self.transcript_status not in {
            ProcessingAvailabilityStatus.AVAILABLE,
            ProcessingAvailabilityStatus.UNAVAILABLE,
        }:
            raise ValueError("unsupported_transcript_status")
        return self

    @model_validator(mode="before")
    @classmethod
    def infer_legacy_transcript_status(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("transcript_status") is None and data.get("transcript_reason") is None and data.get("transcript"):
            return {**data, "transcript_status": ProcessingAvailabilityStatus.AVAILABLE}
        return data

    @model_validator(mode="after")
    def infer_legacy_summary_status(self) -> MediaScribeResult:
        if self.summary is None or self.summary_status != SummaryStatus.NOT_REQUESTED:
            return self
        mapped = {
            MediaScribeSummaryState.READY: SummaryStatus.AVAILABLE,
            MediaScribeSummaryState.FAILED: SummaryStatus.FAILED,
            MediaScribeSummaryState.RUNNING: SummaryStatus.UNAVAILABLE,
            MediaScribeSummaryState.QUEUED: SummaryStatus.UNAVAILABLE,
        }
        return self.model_copy(update={"summary_status": mapped.get(self.summary.status, SummaryStatus.UNAVAILABLE)})


class MediaScribeJobListResponse(MediaScribeModel):
    object: str = "list"
    data: list[MediaScribeJobResponse] = Field(default_factory=list)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=1)
    has_more: bool = False
    next_cursor: str | None = None
    headers: MediaScribeResponseHeaders = Field(default_factory=MediaScribeResponseHeaders)
    http_status: int | None = None


class MediaScribeDeletionResponse(MediaScribeModel):
    object: str = "transcription.deletion"
    id: str = Field(min_length=1)
    state: MediaScribeDeletionState
    deleted: bool
    requested_at: str
    deleted_at: str | None = None
    retry_after_seconds: int | None = None
    status_url: str
    headers: MediaScribeResponseHeaders = Field(default_factory=MediaScribeResponseHeaders)
    http_status: int | None = None


class MediaScribeDownloadResponse(MediaScribeModel):
    content: bytes
    content_type: str | None = None
    content_disposition: str | None = None
    request_id: str | None = None
    headers: MediaScribeResponseHeaders = Field(default_factory=MediaScribeResponseHeaders)
    http_status: int | None = None


# Short aliases keep the adapter API readable while the Response suffixes make
# the provider DTO boundary explicit for callers and tests.
MediaScribeCapabilities = MediaScribeCapabilitiesResponse
MediaScribeVersion = MediaScribeVersionResponse
MediaScribeJob = MediaScribeJobResponse
MediaScribeJobList = MediaScribeJobListResponse
MediaScribeSummary = MediaScribeSummaryResponse
MediaScribeDeletion = MediaScribeDeletionResponse
MediaScribeDownload = MediaScribeDownloadResponse

# Existing processing code imports this name. Keep it as an alias while
# allowing the v1 provider status to carry an unknown future value.
MediaScribeSegment = MediaScribeTranscriptSegment
