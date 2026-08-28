from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

CANONICAL_PROFILE_VERSION = "review_m4a_aac_lc_48k_mono_64k_v1"
VALIDATION_VERSION = "playback_validator_v1"
MAX_ATTEMPTS_PER_CYCLE = 4


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PUBLISHING = "publishing"
    RETRY_WAIT = "retry_wait"
    READY = "ready"
    TERMINAL = "terminal"
    CANCELLED = "cancelled"


class AttemptState(StrEnum):
    LOCAL_PREPARING = "local_preparing"
    UPLOADED = "uploaded"
    PUBLISHED = "published"
    CLEANUP_PENDING = "cleanup_pending"
    CLEANED = "cleaned"
    PURGED = "purged"


class BackfillState(StrEnum):
    INVENTORY_PENDING = "inventory_pending"
    INVENTORY_RUNNING = "inventory_running"
    INVENTORY_COMPLETE = "inventory_complete"
    DISPATCHING = "dispatching"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class TriggerKind(StrEnum):
    FINALIZE = "finalize"
    RECONCILE = "reconcile"
    LEGACY_BACKFILL = "legacy_backfill"


class PriorityClass(StrEnum):
    NEW_INGEST = "new_ingest"
    DUE_RETRY = "due_retry"
    LEGACY_BACKFILL = "legacy_backfill"


class PlannedAction(StrEnum):
    VALIDATE_CANDIDATE = "validate_candidate"
    PRESERVE_VALID = "preserve_valid"
    NORMALIZE_SOURCE = "normalize_source"
    UNAVAILABLE_SOURCE = "unavailable_source"


class DerivationKind(StrEnum):
    UPLOADED_CANDIDATE = "uploaded_candidate"
    SOURCE_BYTE_COPY = "source_byte_copy"
    LOSSLESS_FASTSTART_REMUX = "lossless_faststart_remux"
    SINGLE_SOURCE_TRANSCODE = "single_source_transcode"
    DUAL_SOURCE_MIX_TRANSCODE = "dual_source_mix_transcode"
    LEGACY_UNVALIDATED = "legacy_unvalidated"


class NormalizationReason(StrEnum):
    EMPTY_SOURCE = "empty_source"
    UNSUPPORTED_CONTAINER = "unsupported_container"
    UNSUPPORTED_CODEC = "unsupported_codec"
    ENCRYPTED_MEDIA = "encrypted_media"
    CORRUPT_SOURCE = "corrupt_source"
    NO_AUDIO = "no_audio"
    AMBIGUOUS_AUDIO_TRACKS = "ambiguous_audio_tracks"
    STREAM_LIMIT_EXCEEDED = "stream_limit_exceeded"
    DURATION_LIMIT_EXCEEDED = "duration_limit_exceeded"
    SOURCE_SIZE_LIMIT_EXCEEDED = "source_size_limit_exceeded"
    SOURCE_MISSING = "source_missing"
    SOURCE_MISMATCH = "source_mismatch"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    STORAGE_CAPACITY_EXCEEDED = "storage_capacity_exceeded"
    DATABASE_UNAVAILABLE = "database_unavailable"
    TEMPORAL_UNAVAILABLE = "temporal_unavailable"
    TEMPORARY_STORAGE_UNAVAILABLE = "temporary_storage_unavailable"
    WORKER_INTERRUPTED = "worker_interrupted"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    NORMALIZATION_TIMEOUT = "normalization_timeout"
    PUBLISH_INTERRUPTED = "publish_interrupted"
    GENERATED_OUTPUT_INVALID = "generated_output_invalid"
    MEETING_DELETING = "meeting_deleting"
    MEETING_DELETED = "meeting_deleted"
    AUDIO_PURGED = "audio_purged"
    REVISION_SUPERSEDED = "revision_superseded"


class ReasonClass(StrEnum):
    PERMANENT_SOURCE = "permanent_source"
    POLICY_BLOCK = "policy_block"
    AUTOMATIC_RETRY = "automatic_retry"
    LIFECYCLE = "lifecycle"


PERMANENT_SOURCE_REASONS = frozenset(
    {
        NormalizationReason.EMPTY_SOURCE,
        NormalizationReason.UNSUPPORTED_CONTAINER,
        NormalizationReason.UNSUPPORTED_CODEC,
        NormalizationReason.ENCRYPTED_MEDIA,
        NormalizationReason.CORRUPT_SOURCE,
        NormalizationReason.NO_AUDIO,
        NormalizationReason.AMBIGUOUS_AUDIO_TRACKS,
        NormalizationReason.STREAM_LIMIT_EXCEEDED,
        NormalizationReason.DURATION_LIMIT_EXCEEDED,
        NormalizationReason.SOURCE_SIZE_LIMIT_EXCEEDED,
        NormalizationReason.SOURCE_MISSING,
        NormalizationReason.SOURCE_MISMATCH,
    }
)
POLICY_BLOCK_REASONS = frozenset({NormalizationReason.STORAGE_CAPACITY_EXCEEDED})
AUTOMATIC_RETRY_REASONS = frozenset(
    {
        NormalizationReason.STORAGE_UNAVAILABLE,
        NormalizationReason.DATABASE_UNAVAILABLE,
        NormalizationReason.TEMPORAL_UNAVAILABLE,
        NormalizationReason.TEMPORARY_STORAGE_UNAVAILABLE,
        NormalizationReason.WORKER_INTERRUPTED,
        NormalizationReason.DEPENDENCY_UNAVAILABLE,
        NormalizationReason.NORMALIZATION_TIMEOUT,
        NormalizationReason.PUBLISH_INTERRUPTED,
        NormalizationReason.GENERATED_OUTPUT_INVALID,
    }
)
LIFECYCLE_REASONS = frozenset(
    {
        NormalizationReason.MEETING_DELETING,
        NormalizationReason.MEETING_DELETED,
        NormalizationReason.AUDIO_PURGED,
        NormalizationReason.REVISION_SUPERSEDED,
    }
)


class InvalidNormalizationTransition(ValueError):
    """A durable normalization state transition violates the contract."""


JOB_TRANSITIONS = frozenset(
    {
        (JobState.QUEUED, JobState.RUNNING),
        (JobState.RUNNING, JobState.PUBLISHING),
        (JobState.PUBLISHING, JobState.READY),
        (JobState.RUNNING, JobState.RETRY_WAIT),
        (JobState.PUBLISHING, JobState.RETRY_WAIT),
        (JobState.QUEUED, JobState.RETRY_WAIT),
        (JobState.READY, JobState.RETRY_WAIT),
        (JobState.RETRY_WAIT, JobState.QUEUED),
        (JobState.QUEUED, JobState.TERMINAL),
        (JobState.RUNNING, JobState.TERMINAL),
        (JobState.PUBLISHING, JobState.TERMINAL),
        (JobState.RETRY_WAIT, JobState.TERMINAL),
        (JobState.QUEUED, JobState.CANCELLED),
        (JobState.RUNNING, JobState.CANCELLED),
        (JobState.PUBLISHING, JobState.CANCELLED),
        (JobState.RETRY_WAIT, JobState.CANCELLED),
        (JobState.READY, JobState.CANCELLED),
    }
)

ATTEMPT_TRANSITIONS = frozenset(
    {
        (AttemptState.LOCAL_PREPARING, AttemptState.UPLOADED),
        (AttemptState.UPLOADED, AttemptState.PUBLISHED),
        (AttemptState.LOCAL_PREPARING, AttemptState.CLEANUP_PENDING),
        (AttemptState.UPLOADED, AttemptState.CLEANUP_PENDING),
        (AttemptState.CLEANUP_PENDING, AttemptState.CLEANED),
        (AttemptState.CLEANUP_PENDING, AttemptState.PURGED),
        (AttemptState.CLEANED, AttemptState.CLEANUP_PENDING),
        (AttemptState.CLEANED, AttemptState.PURGED),
        (AttemptState.PUBLISHED, AttemptState.PURGED),
    }
)

BACKFILL_TRANSITIONS = frozenset(
    {
        (BackfillState.INVENTORY_PENDING, BackfillState.INVENTORY_RUNNING),
        (BackfillState.INVENTORY_PENDING, BackfillState.BLOCKED),
        (BackfillState.INVENTORY_RUNNING, BackfillState.INVENTORY_COMPLETE),
        (BackfillState.INVENTORY_RUNNING, BackfillState.BLOCKED),
        (BackfillState.INVENTORY_COMPLETE, BackfillState.DISPATCHING),
        (BackfillState.INVENTORY_COMPLETE, BackfillState.BLOCKED),
        (BackfillState.DISPATCHING, BackfillState.COMPLETE),
        (BackfillState.DISPATCHING, BackfillState.BLOCKED),
        (BackfillState.BLOCKED, BackfillState.INVENTORY_PENDING),
    }
)


def reason_class(reason: NormalizationReason) -> ReasonClass:
    if reason in PERMANENT_SOURCE_REASONS:
        return ReasonClass.PERMANENT_SOURCE
    if reason in POLICY_BLOCK_REASONS:
        return ReasonClass.POLICY_BLOCK
    if reason in AUTOMATIC_RETRY_REASONS:
        return ReasonClass.AUTOMATIC_RETRY
    if reason in LIFECYCLE_REASONS:
        return ReasonClass.LIFECYCLE
    raise ValueError("Unknown normalization reason")


def ensure_job_transition(
    current: JobState,
    target: JobState,
    *,
    reason_code: NormalizationReason | None = None,
) -> None:
    if current == target:
        return
    if (current, target) not in JOB_TRANSITIONS:
        raise InvalidNormalizationTransition(f"Unsupported job transition: {current} -> {target}")

    expected_reason_classes = {
        JobState.RETRY_WAIT: {ReasonClass.AUTOMATIC_RETRY},
        JobState.TERMINAL: {ReasonClass.PERMANENT_SOURCE, ReasonClass.POLICY_BLOCK},
        JobState.CANCELLED: {ReasonClass.LIFECYCLE},
    }.get(target)
    if expected_reason_classes is None:
        if reason_code is not None:
            raise InvalidNormalizationTransition("Non-failure state cannot retain a reason")
        return
    if reason_code is None or reason_class(reason_code) not in expected_reason_classes:
        raise InvalidNormalizationTransition(f"Reason class does not match target state: {target}")


def ensure_attempt_transition(current: AttemptState, target: AttemptState) -> None:
    if current == target:
        return
    if (current, target) not in ATTEMPT_TRANSITIONS:
        raise InvalidNormalizationTransition(f"Unsupported attempt transition: {current} -> {target}")


def ensure_backfill_transition(
    current: BackfillState,
    target: BackfillState,
    *,
    newer_watermark: bool = False,
) -> None:
    if current == target:
        return
    if current is BackfillState.COMPLETE and target is BackfillState.INVENTORY_RUNNING:
        if newer_watermark:
            return
        raise InvalidNormalizationTransition("Completed backfill requires a newer watermark")
    if (current, target) not in BACKFILL_TRANSITIONS:
        raise InvalidNormalizationTransition(f"Unsupported backfill transition: {current} -> {target}")


def retry_attempt_delay(failed_attempt_in_cycle: int) -> timedelta | None:
    if not 1 <= failed_attempt_in_cycle <= MAX_ATTEMPTS_PER_CYCLE:
        raise ValueError("failed_attempt_in_cycle must be between 1 and 4")
    if failed_attempt_in_cycle == MAX_ATTEMPTS_PER_CYCLE:
        return None
    return timedelta(seconds=30 * (2 ** (failed_attempt_in_cycle - 1)))


def retry_cycle_due_at(now: datetime, completed_cycle_count: int) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if completed_cycle_count < 1:
        raise ValueError("completed_cycle_count must be positive")
    delays = (
        timedelta(minutes=15),
        timedelta(hours=1),
        timedelta(hours=6),
        timedelta(hours=24),
    )
    return now + delays[min(completed_cycle_count, len(delays)) - 1]


@dataclass(frozen=True, slots=True)
class RetryFailureSchedule:
    next_attempt_at: datetime
    completed_cycle_count: int
    temporal_retry: bool
    cycle_exhausted: bool


def retry_failure_schedule(
    now: datetime,
    *,
    failed_attempt_in_cycle: int,
    completed_cycle_count: int,
) -> RetryFailureSchedule:
    """Return the durable due time for one failed retryable attempt."""

    if completed_cycle_count < 0:
        raise ValueError("completed_cycle_count must not be negative")
    delay = retry_attempt_delay(failed_attempt_in_cycle)
    if delay is not None:
        return RetryFailureSchedule(
            next_attempt_at=now + delay,
            completed_cycle_count=completed_cycle_count,
            temporal_retry=True,
            cycle_exhausted=False,
        )
    completed_cycle_count += 1
    return RetryFailureSchedule(
        next_attempt_at=retry_cycle_due_at(now, completed_cycle_count),
        completed_cycle_count=completed_cycle_count,
        temporal_retry=False,
        cycle_exhausted=True,
    )
