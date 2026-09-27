from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from twobrain_rec_server.billing.purchases import (
    PurchaseError,
    StorageSegment,
    quote_storage_purchase,
)

GB = 1_000_000_000
START = datetime(2026, 9, 1, tzinfo=UTC)
END = datetime(2026, 10, 1, tzinfo=UTC)


def segment(*, start=START, end=END, capacity=2 * GB, old=0, new=29_000):
    return StorageSegment(
        base_grant_id=uuid4(),
        starts_at=start,
        ends_at=end,
        cycle="month",
        capacity_bytes=capacity,
        current_price_minor=old,
        target_price_minor=new,
        target_catalog_id=uuid4(),
    )


def test_current_prorata_plus_full_future_period_are_not_one_long_month():
    quote = quote_storage_purchase(
        segments=[segment(), segment(start=END, end=datetime(2026, 11, 1, tzinfo=UTC))],
        target_capacity_bytes=5 * GB,
        now=START + timedelta(days=15),
    )
    assert quote.list_amount_minor == 14_500 + 29_000
    assert quote.payable_amount_minor == 43_500
    assert len(quote.segments) == 2
    assert quote.segments[0].starts_at == START + timedelta(days=15)


def test_larger_prepaid_future_capacity_is_preserved_without_negative_charge():
    quote = quote_storage_purchase(
        segments=[
            segment(capacity=5 * GB, old=29_000, new=79_000),
            segment(
                start=END,
                end=datetime(2026, 11, 1, tzinfo=UTC),
                capacity=100 * GB,
                old=199_000,
                new=79_000,
            ),
        ],
        target_capacity_bytes=20 * GB,
        now=START + timedelta(days=15),
    )
    assert quote.list_amount_minor == 25_000
    assert len(quote.segments) == 1
    assert quote.next_capacity_bytes == 20 * GB
    assert quote.ends_at == datetime(2026, 11, 1, tzinfo=UTC)


def test_floor_is_applied_before_discount_and_invalid_discount_never_charges_full_price():
    quote = quote_storage_purchase(
        segments=[segment()],
        target_capacity_bytes=5 * GB,
        now=END - timedelta(seconds=1),
    )
    assert quote.deferred_to_renewal and quote.payable_amount_minor == 0
    with pytest.raises(PurchaseError, match="миним"):
        quote_storage_purchase(
            segments=[segment()],
            target_capacity_bytes=5 * GB,
            now=END - timedelta(days=1),
            discount_percent=99,
        )


def test_ninety_nine_percent_discount_is_one_real_nonzero_purchase():
    quote = quote_storage_purchase(
        segments=[segment()],
        target_capacity_bytes=5 * GB,
        now=START,
        discount_percent=99,
    )
    assert quote.list_amount_minor == 29_000
    assert quote.payable_amount_minor == 290


def test_bonus_horizon_defers_the_whole_change_without_claiming_immediate_capacity():
    quote = quote_storage_purchase(
        segments=[segment()],
        target_capacity_bytes=5 * GB,
        now=START,
        bonus_interval=True,
    )
    assert quote.deferred_to_renewal and not quote.segments
    assert quote.payable_amount_minor == 0


@pytest.mark.parametrize("capacity", [5, 20, 100, 500])
@pytest.mark.parametrize("cycle", ["month", "year"])
def test_supported_ladder_and_year_are_exact(capacity, cycle):
    prices = {5: 29_000, 20: 79_000, 100: 199_000, 500: 499_000}
    item = StorageSegment(
        uuid4(),
        START,
        datetime(2027, 9, 1, tzinfo=UTC) if cycle == "year" else END,
        cycle,
        2 * GB,
        0,
        prices[capacity] * (10 if cycle == "year" else 1),
        uuid4(),
    )
    quote = quote_storage_purchase(segments=[item], target_capacity_bytes=capacity * GB, now=START)
    assert quote.payable_amount_minor == item.target_price_minor


def test_integer_microsecond_rounding_and_exact_end():
    item = segment(start=START, end=START + timedelta(microseconds=3), new=1000)
    quote = quote_storage_purchase(
        segments=[item],
        target_capacity_bytes=5 * GB,
        now=START + timedelta(microseconds=1),
    )
    assert quote.payable_amount_minor == 666
    with pytest.raises(PurchaseError):
        quote_storage_purchase(segments=[item], target_capacity_bytes=5 * GB, now=item.ends_at)


@pytest.mark.parametrize("bad_percent", [-1, 100, True])
def test_invalid_percent_is_rejected(bad_percent):
    with pytest.raises(PurchaseError):
        quote_storage_purchase(
            segments=[segment()],
            target_capacity_bytes=5 * GB,
            now=START,
            discount_percent=bad_percent,
        )


def test_naive_time_and_overlapping_grants_are_not_silently_reinterpreted():
    with pytest.raises(PurchaseError):
        quote_storage_purchase(
            segments=[segment()], target_capacity_bytes=5 * GB, now=START.replace(tzinfo=None)
        )
    with pytest.raises(PurchaseError):
        quote_storage_purchase(
            segments=[segment(), segment()], target_capacity_bytes=5 * GB, now=START
        )


def test_renewal_window_skips_missed_attempts_without_catchup():
    from twobrain_rec_server.billing.renewal_charge import next_renewal_attempt

    end = datetime(2026, 10, 1, tzinfo=UTC)
    for hours in [72, 48, 24, 12]:
        now = end - timedelta(hours=hours)
        assert (
            next_renewal_attempt(
                paid_through=end, now=now, resolved_attempts=set(), unresolved=False
            )
            == now
        )
    assert (
        next_renewal_attempt(paid_through=end, now=end, resolved_attempts=set(), unresolved=False)
        is None
    )
    assert (
        next_renewal_attempt(
            paid_through=end, now=end - timedelta(hours=12), resolved_attempts={3}, unresolved=False
        )
        is None
    )
    assert (
        next_renewal_attempt(
            paid_through=end,
            now=end - timedelta(hours=12),
            resolved_attempts=set(),
            unresolved=True,
        )
        is None
    )
    assert next_renewal_attempt(
        paid_through=end, now=end - timedelta(hours=60), resolved_attempts={1}, unresolved=False
    ) == end - timedelta(hours=48)
