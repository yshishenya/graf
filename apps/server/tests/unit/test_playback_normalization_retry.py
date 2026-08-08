from datetime import UTC, datetime, timedelta

from twobrain_rec_server.normalization.statuses import retry_failure_schedule
from twobrain_rec_server.workflows.playback_normalization_workflow import (
    playback_normalization_retry_policy,
)


def test_temporal_retry_cycle_is_four_bounded_exponential_attempts() -> None:
    policy = playback_normalization_retry_policy()

    assert policy.initial_interval == timedelta(seconds=30)
    assert policy.backoff_coefficient == 2.0
    assert policy.maximum_interval == timedelta(minutes=15)
    assert policy.maximum_attempts == 4


def test_retry_failure_schedule_uses_short_attempts_then_long_term_daily_cycles() -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    for attempt, expected_delay in (
        (1, timedelta(seconds=30)),
        (2, timedelta(seconds=60)),
        (3, timedelta(seconds=120)),
    ):
        schedule = retry_failure_schedule(
            now,
            failed_attempt_in_cycle=attempt,
            completed_cycle_count=0,
        )
        assert schedule.next_attempt_at - now == expected_delay
        assert schedule.temporal_retry is True
        assert schedule.cycle_exhausted is False
        assert schedule.completed_cycle_count == 0

    expected_cycle_delays = (
        timedelta(minutes=15),
        timedelta(hours=1),
        timedelta(hours=6),
        timedelta(hours=24),
        timedelta(hours=24),
        timedelta(hours=24),
    )
    for completed_cycles, expected_delay in enumerate(expected_cycle_delays):
        schedule = retry_failure_schedule(
            now,
            failed_attempt_in_cycle=4,
            completed_cycle_count=completed_cycles,
        )
        assert schedule.next_attempt_at - now == expected_delay
        assert schedule.temporal_retry is False
        assert schedule.cycle_exhausted is True
        assert schedule.completed_cycle_count == completed_cycles + 1
