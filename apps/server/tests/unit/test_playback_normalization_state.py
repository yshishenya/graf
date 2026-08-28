from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
    AttemptState,
    BackfillState,
    InvalidNormalizationTransition,
    JobState,
    NormalizationReason,
    ReasonClass,
    ensure_attempt_transition,
    ensure_backfill_transition,
    ensure_job_transition,
    reason_class,
    retry_attempt_delay,
    retry_cycle_due_at,
)


def test_profile_and_validator_versions_are_stable() -> None:
    assert CANONICAL_PROFILE_VERSION == "review_m4a_aac_lc_48k_mono_64k_v1"
    assert VALIDATION_VERSION == "playback_validator_v1"


def test_job_state_machine_accepts_only_documented_transitions() -> None:
    for current, target in (
        (JobState.QUEUED, JobState.RUNNING),
        (JobState.RUNNING, JobState.PUBLISHING),
        (JobState.PUBLISHING, JobState.READY),
        (JobState.RETRY_WAIT, JobState.QUEUED),
    ):
        ensure_job_transition(current, target)
    for current in (JobState.RUNNING, JobState.PUBLISHING):
        ensure_job_transition(
            current,
            JobState.RETRY_WAIT,
            reason_code=NormalizationReason.WORKER_INTERRUPTED,
        )

    with pytest.raises(InvalidNormalizationTransition):
        ensure_job_transition(JobState.QUEUED, JobState.READY)
    with pytest.raises(InvalidNormalizationTransition):
        ensure_job_transition(JobState.READY, JobState.RUNNING)


def test_job_terminal_retry_and_deletion_reasons_are_class_safe() -> None:
    ensure_job_transition(
        JobState.RUNNING,
        JobState.RETRY_WAIT,
        reason_code=NormalizationReason.STORAGE_UNAVAILABLE,
    )
    ensure_job_transition(
        JobState.RUNNING,
        JobState.TERMINAL,
        reason_code=NormalizationReason.NO_AUDIO,
    )
    ensure_job_transition(
        JobState.PUBLISHING,
        JobState.TERMINAL,
        reason_code=NormalizationReason.STORAGE_CAPACITY_EXCEEDED,
    )
    ensure_job_transition(
        JobState.READY,
        JobState.CANCELLED,
        reason_code=NormalizationReason.MEETING_DELETED,
    )

    with pytest.raises(InvalidNormalizationTransition):
        ensure_job_transition(
            JobState.RUNNING,
            JobState.TERMINAL,
            reason_code=NormalizationReason.STORAGE_UNAVAILABLE,
        )
    with pytest.raises(InvalidNormalizationTransition):
        ensure_job_transition(
            JobState.RUNNING,
            JobState.RETRY_WAIT,
            reason_code=NormalizationReason.CORRUPT_SOURCE,
        )
    assert reason_class(NormalizationReason.NO_AUDIO) is ReasonClass.PERMANENT_SOURCE
    assert reason_class(NormalizationReason.STORAGE_CAPACITY_EXCEEDED) is ReasonClass.POLICY_BLOCK
    assert reason_class(NormalizationReason.NORMALIZATION_TIMEOUT) is ReasonClass.AUTOMATIC_RETRY
    assert reason_class(NormalizationReason.AUDIO_PURGED) is ReasonClass.LIFECYCLE


def test_retry_delays_are_bounded_and_long_term_recovery_never_stops() -> None:
    assert [retry_attempt_delay(number) for number in range(1, 4)] == [
        timedelta(seconds=30),
        timedelta(seconds=60),
        timedelta(seconds=120),
    ]
    assert retry_attempt_delay(4) is None

    now = datetime(2026, 7, 14, 8, 0, tzinfo=UTC)
    assert [retry_cycle_due_at(now, cycle) - now for cycle in range(1, 7)] == [
        timedelta(minutes=15),
        timedelta(hours=1),
        timedelta(hours=6),
        timedelta(hours=24),
        timedelta(hours=24),
        timedelta(hours=24),
    ]


def test_attempt_and_backfill_state_machines_are_explicit() -> None:
    for current, target in (
        (AttemptState.LOCAL_PREPARING, AttemptState.UPLOADED),
        (AttemptState.UPLOADED, AttemptState.PUBLISHED),
        (AttemptState.UPLOADED, AttemptState.CLEANUP_PENDING),
        (AttemptState.CLEANUP_PENDING, AttemptState.CLEANED),
        (AttemptState.CLEANED, AttemptState.CLEANUP_PENDING),
        (AttemptState.CLEANED, AttemptState.PURGED),
    ):
        ensure_attempt_transition(current, target)
    with pytest.raises(InvalidNormalizationTransition):
        ensure_attempt_transition(AttemptState.LOCAL_PREPARING, AttemptState.PUBLISHED)

    for current, target in (
        (BackfillState.INVENTORY_PENDING, BackfillState.INVENTORY_RUNNING),
        (BackfillState.INVENTORY_RUNNING, BackfillState.INVENTORY_COMPLETE),
        (BackfillState.INVENTORY_COMPLETE, BackfillState.DISPATCHING),
        (BackfillState.DISPATCHING, BackfillState.COMPLETE),
        (BackfillState.BLOCKED, BackfillState.INVENTORY_PENDING),
    ):
        ensure_backfill_transition(current, target)
    with pytest.raises(InvalidNormalizationTransition):
        ensure_backfill_transition(BackfillState.INVENTORY_PENDING, BackfillState.COMPLETE)
    with pytest.raises(InvalidNormalizationTransition):
        ensure_backfill_transition(BackfillState.COMPLETE, BackfillState.INVENTORY_RUNNING)
    ensure_backfill_transition(
        BackfillState.COMPLETE,
        BackfillState.INVENTORY_RUNNING,
        newer_watermark=True,
    )
