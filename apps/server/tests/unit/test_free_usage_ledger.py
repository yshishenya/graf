from datetime import UTC, datetime

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
