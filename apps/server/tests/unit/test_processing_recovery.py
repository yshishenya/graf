from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing.recovery import (
    parse_retry_after,
    retry_timer_is_current,
    schedule_retry,
    schedule_retry_with_settings,
)


def test_retry_after_is_safe_for_invalid_provider_hints() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)

    assert parse_retry_after("30", now=now) == timedelta(seconds=30)
    assert parse_retry_after("not-a-delay", now=now) is None


def test_retry_schedule_is_bounded_and_advances_generation() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    schedule = schedule_retry(
        now=now,
        retry_count=0,
        generation=4,
        provider_next_attempt_at=now + timedelta(hours=2),
        deadline_at=now + timedelta(hours=3),
        random_source=Random(0),
    )

    assert schedule.next_attempt_at is not None
    assert now + timedelta(minutes=15) <= schedule.next_attempt_at <= now + timedelta(minutes=16, seconds=30)
    assert schedule.source == "provider_next_retry_at"
    assert schedule.retry_count == 1
    assert schedule.generation == 5
    assert retry_timer_is_current(
        expected_generation=5,
        actual_generation=schedule.generation,
        state=ProcessingStatus.WAITING_RETRY.value,
    )
    assert not retry_timer_is_current(
        expected_generation=4,
        actual_generation=schedule.generation,
        state=ProcessingStatus.WAITING_RETRY.value,
    )


def test_retry_schedule_stops_at_deadline() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)

    schedule = schedule_retry(
        now=now,
        retry_count=2,
        generation=7,
        retry_after=timedelta(seconds=30),
        deadline_at=now + timedelta(seconds=10),
        random_source=Random(0),
    )

    assert schedule.next_attempt_at is None
    assert schedule.source is None
    assert schedule.generation == 8
    assert schedule.stop_reason == "deadline_exceeded"


def test_retry_schedule_stops_at_configured_attempt_limit() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    schedule = schedule_retry(
        now=now,
        retry_count=3,
        generation=7,
        max_attempts=3,
        random_source=Random(0),
    )

    assert schedule.next_attempt_at is None
    assert schedule.source is None
    assert schedule.retry_count == 3
    assert schedule.generation == 8
    assert schedule.stop_reason == "max_attempts_exceeded"


def test_provider_polling_ignores_generic_attempt_limit_until_deadline() -> None:
    settings = Settings(
        processing_recovery_deadline_seconds=60,
        processing_recovery_min_delay_seconds=5,
        processing_recovery_default_delay_seconds=5,
        processing_recovery_max_delay_seconds=5,
        processing_recovery_jitter_ratio=0,
    )
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)

    schedule = schedule_retry_with_settings(
        settings,
        respect_max_attempts=False,
        now=now,
        retry_count=settings.processing_recovery_max_attempts,
        generation=1,
        retry_after=timedelta(seconds=5),
        deadline_at=now + timedelta(seconds=60),
    )

    assert schedule.next_attempt_at == now + timedelta(seconds=5)
    assert schedule.stop_reason is None


def test_retry_schedule_distinguishes_deadline_from_attempt_limit() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    schedule = schedule_retry(
        now=now,
        retry_count=0,
        generation=7,
        retry_after=timedelta(seconds=30),
        deadline_at=now + timedelta(seconds=10),
        random_source=Random(0),
    )

    assert schedule.stop_reason == "deadline_exceeded"
