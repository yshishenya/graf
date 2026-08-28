"""Pure recovery decisions shared by API, worker and UI projections.

Provider business retries live here; Temporal is responsible for durable
waiting and PostgreSQL remains the user-facing source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from math import isfinite
from random import Random
from typing import TYPE_CHECKING

from twobrain_rec_server.domain.statuses import ProcessingStatus

if TYPE_CHECKING:
    from twobrain_rec_server.config import Settings

MIN_RETRY_DELAY = timedelta(seconds=5)
DEFAULT_RETRY_DELAY = timedelta(seconds=30)
MAX_RETRY_DELAY = timedelta(minutes=15)
DEFAULT_DEADLINE = timedelta(hours=4)


@dataclass(frozen=True, slots=True)
class RetrySchedule:
    next_attempt_at: datetime | None
    source: str | None
    retry_count: int
    generation: int
    stop_reason: str | None = None


def parse_retry_after(value: str | None, *, now: datetime | None = None) -> timedelta | None:
    """Parse delta-seconds or an HTTP date without trusting invalid hints."""

    if not value:
        return None
    try:
        seconds = float(value.strip())
    except (AttributeError, ValueError):
        try:
            target = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if target.tzinfo is None:
            target = target.replace(tzinfo=UTC)
        current = now or datetime.now(UTC)
        seconds = (target.astimezone(UTC) - current.astimezone(UTC)).total_seconds()
    if not isfinite(seconds) or seconds < 0:
        return None
    return timedelta(seconds=min(seconds, MAX_RETRY_DELAY.total_seconds()))


def schedule_retry(
    *,
    now: datetime,
    retry_count: int,
    generation: int,
    retry_after: timedelta | None = None,
    provider_next_attempt_at: datetime | None = None,
    deadline_at: datetime | None = None,
    source: str | None = None,
    jitter_ratio: float = 0.1,
    random_source: Random | None = None,
    min_delay: timedelta = MIN_RETRY_DELAY,
    default_delay: timedelta = DEFAULT_RETRY_DELAY,
    max_delay: timedelta = MAX_RETRY_DELAY,
    default_deadline: timedelta = DEFAULT_DEADLINE,
    max_attempts: int | None = None,
) -> RetrySchedule:
    """Return a bounded absolute schedule; injectable RNG keeps tests stable."""

    now = now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
    if max_attempts is not None and retry_count >= max_attempts:
        return RetrySchedule(
            None, None, retry_count, generation + 1, "max_attempts_exceeded"
        )
    deadline = deadline_at or now + default_deadline
    hinted_delay = retry_after
    if provider_next_attempt_at is not None:
        candidate = provider_next_attempt_at.astimezone(UTC) if provider_next_attempt_at.tzinfo else provider_next_attempt_at.replace(tzinfo=UTC)
        hinted_delay = max(timedelta(0), candidate - now)
        source = source or "provider_next_retry_at"
    if hinted_delay is None:
        backoff_seconds = default_delay.total_seconds() * (2 ** min(max(retry_count, 0), 8))
        hinted_delay = timedelta(seconds=min(backoff_seconds, max_delay.total_seconds()))
        source = source or "server_fallback"
    base = max(min_delay, min(hinted_delay, max_delay))
    jitter = max(0.0, min(jitter_ratio, 0.25))
    if jitter:
        rng = random_source or Random()
        base += timedelta(seconds=base.total_seconds() * rng.uniform(0, jitter))
    target = min(now + base, deadline)
    if target <= now or target >= deadline:
        return RetrySchedule(None, None, retry_count, generation + 1, "deadline_exceeded")
    return RetrySchedule(target, source, retry_count + 1, generation + 1)


def retry_timer_is_current(*, expected_generation: int, actual_generation: int, state: str) -> bool:
    return expected_generation == actual_generation and state == ProcessingStatus.WAITING_RETRY.value


def schedule_retry_with_settings(
    settings: Settings,
    *,
    respect_max_attempts: bool = True,
    **kwargs: object,
) -> RetrySchedule:
    """Apply deployment bounds while keeping the pure scheduler testable."""

    return schedule_retry(
        **kwargs,
        min_delay=timedelta(seconds=settings.processing_recovery_min_delay_seconds),
        default_delay=timedelta(seconds=settings.processing_recovery_default_delay_seconds),
        max_delay=timedelta(seconds=settings.processing_recovery_max_delay_seconds),
        default_deadline=timedelta(seconds=settings.processing_recovery_deadline_seconds),
        max_attempts=(settings.processing_recovery_max_attempts if respect_max_attempts else None),
        jitter_ratio=settings.processing_recovery_jitter_ratio,
    )
