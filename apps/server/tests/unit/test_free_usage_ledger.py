from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.billing.catalog import FREE_PROCESSING_SECONDS, classify_free_processing
from twobrain_rec_server.billing.usage import (
    MOSCOW,
    FreeUsageLedger,
    QuotaExceeded,
    QuotaOverrun,
    SourceRange,
)


def test_free_ledger_reserves_exact_seconds_and_deduplicates_ranges() -> None:
    ledger = FreeUsageLedger.for_moment(datetime(2026, 8, 6, 12, tzinfo=UTC))
    reservation = ledger.reserve("r1", 100)
    assert reservation.window_start.astimezone(MOSCOW).month == 8
    assert ledger.commit("r1", [SourceRange("track", 0, 60), SourceRange("track", 0, 60)]) == 60
    assert ledger.remaining_seconds == FREE_PROCESSING_SECONDS - 60
    assert ledger.threshold == "normal"


def test_free_ledger_rejects_reservation_overrun_and_exhaustion() -> None:
    ledger = FreeUsageLedger.for_moment(datetime(2026, 8, 6, 12, tzinfo=UTC))
    ledger.reserve("r1", FREE_PROCESSING_SECONDS)
    with pytest.raises(QuotaOverrun):
        ledger.commit("r1", [SourceRange("track", 0, FREE_PROCESSING_SECONDS + 1)])
    with pytest.raises(QuotaExceeded):
        ledger.reserve("r2", 1)


def test_free_ledger_keeps_reservation_on_original_moscow_window_across_midnight() -> None:
    before_midnight = datetime(2026, 8, 31, 20, 59, tzinfo=UTC)
    ledger = FreeUsageLedger.for_moment(before_midnight)
    reservation = ledger.reserve("cross-midnight", 30)
    assert reservation.window_start == ledger.window_start
    assert ledger.window_end > ledger.window_start
    assert ledger.for_moment(before_midnight + timedelta(minutes=2)).window_start != ledger.window_start


def test_free_ledger_releases_failed_reservation_without_rollover() -> None:
    ledger = FreeUsageLedger.for_moment(datetime(2026, 8, 6, 12, tzinfo=UTC))
    ledger.reserve("failed", 60)
    ledger.release("failed")
    assert ledger.remaining_seconds == FREE_PROCESSING_SECONDS
    assert ledger.reserve("new", 60).state == "active"


def test_free_threshold_copy_is_distinct_at_80_and_100_percent() -> None:
    assert classify_free_processing(committed_seconds=14_399) == "normal"
    assert classify_free_processing(committed_seconds=14_400) == "approaching"
    assert classify_free_processing(committed_seconds=17_999) == "approaching"
    assert classify_free_processing(committed_seconds=18_000) == "exhausted"


def test_free_ledger_commits_partial_success_without_rounding_or_rollover() -> None:
    ledger = FreeUsageLedger.for_moment(datetime(2026, 8, 31, 20, 59, tzinfo=UTC))
    reservation = ledger.reserve("partial", 100)
    assert ledger.commit("partial", [SourceRange("track", 10, 55)]) == 45
    assert reservation.state == "active"
    assert reservation.remaining_seconds == 55
    assert ledger.commit("partial", [SourceRange("track", 10, 30)]) == 0
    assert ledger.committed_seconds == 45
