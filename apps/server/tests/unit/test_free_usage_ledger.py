from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.billing.catalog import FREE_PROCESSING_SECONDS
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
