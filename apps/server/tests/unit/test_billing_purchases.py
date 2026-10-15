from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
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


@pytest.mark.parametrize("current_capacity", [20 * GB, 100 * GB])
def test_equal_current_target_still_prices_lower_prepaid_future_capacity(current_capacity):
    future = segment(start=END, end=datetime(2026, 11, 1, tzinfo=UTC),
                     capacity=5 * GB, old=0, new=75000)
    quote = quote_storage_purchase(
        segments=[segment(capacity=current_capacity, old=75000, new=75000), future],
        target_capacity_bytes=20 * GB, now=START + timedelta(days=15),
    )
    assert not quote.deferred_to_renewal
    assert quote.payable_amount_minor == 75000
    assert len(quote.segments) == 1
    assert quote.segments[0].base_grant_id == future.base_grant_id
    assert quote.segments[0].starts_at == END


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["missing", "disabled", "expired", "malformed", "foreign"])
async def test_acceptance_campaign_rejection_names_unavailable_promo_and_preserves_fence(failure):
    from twobrain_rec_server.billing.purchases import validate_acceptance_campaign

    workspace = uuid4()
    budget = SimpleNamespace(id=uuid4(), enabled=failure != "disabled", expires_at=START + timedelta(hours=1))
    if failure == "expired":
        budget.expires_at = START
    policy = {"workspace_id": str(workspace), "acceptance_budget_id": str(budget.id)}
    if failure == "malformed":
        policy["acceptance_budget_id"] = "synthetic-invalid-id"
    if failure == "foreign":
        policy["workspace_id"] = str(uuid4())
    before = dict(vars(budget)), dict(policy)
    db = SimpleNamespace(scalar=AsyncMock(return_value=None if failure == "missing" else budget), add=Mock(), flush=AsyncMock())
    with pytest.raises(PurchaseError) as rejected:
        await validate_acceptance_campaign(db, policy=policy, workspace_id=workspace, now=START)
    message = str(rejected.value).lower()
    assert "промокод" in message
    assert any(action in message for action in ("проверьте", "другой", "уберите", "поддерж"))
    assert "провероч" not in message and "бюджет" not in message
    assert (dict(vars(budget)), policy) == before
    db.add.assert_not_called()
    db.flush.assert_not_awaited()
    if failure == "malformed":
        db.scalar.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["disabled", "expired", "exhausted"])
async def test_acceptance_account_rejection_requires_support_without_promo_bypass(failure):
    from twobrain_rec_server.billing.purchases import reserve_acceptance_budget

    workspace, operation = uuid4(), uuid4()
    budget = SimpleNamespace(id=uuid4(), enabled=failure != "disabled", expires_at=START + timedelta(hours=1),
                             reserved_minor=100, spent_minor=100, limit_minor=200 if failure == "exhausted" else 1000)
    if failure == "expired":
        budget.expires_at = START
    before = dict(vars(budget))
    db = SimpleNamespace(scalar=AsyncMock(side_effect=[budget, SimpleNamespace(id=operation), None]), add=Mock(), flush=AsyncMock())
    with pytest.raises(PurchaseError) as rejected:
        await reserve_acceptance_budget(db, workspace_id=workspace, operation_id=operation, amount_minor=100, now=START)
    message = str(rejected.value).lower()
    assert "оплат" in message and "аккаунт" in message and "поддерж" in message
    assert "провероч" not in message and "бюджет" not in message and "промокод" not in message
    assert vars(budget) == before
    db.add.assert_not_called()
    db.flush.assert_not_awaited()
