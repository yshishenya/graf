from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing.recovery import (
    classify_provider_outcome,
    parse_retry_after,
    retry_timer_is_current,
    schedule_retry,
)


def test_retry_after_and_provider_classification_are_machine_first() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)

    assert parse_retry_after("30", now=now) == timedelta(seconds=30)
    assert parse_retry_after("not-a-delay", now=now) is None
    assert classify_provider_outcome(status_code=503, code="provider_unavailable").status == ProcessingStatus.WAITING_RETRY
    assert classify_provider_outcome(status_code=400, code="bad_input").status == ProcessingStatus.FAILED_TERMINAL


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
