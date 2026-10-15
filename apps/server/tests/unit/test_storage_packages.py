from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from twobrain_rec_server.billing.catalog import (
    storage_package_capacity,
    storage_package_count,
)
from twobrain_rec_server.billing.purchases import (
    StorageSegment,
    accept_storage_price,
    effective_paid_storage,
    quote_storage_purchase,
    storage_price_is_accepted,
    storage_price_snapshot,
)
from twobrain_rec_server.db.models import BillingStoragePriceVersion, WorkspaceSubscription


@pytest.mark.parametrize("count", [0, 1, 2, 3, 19, 99])
def test_package_capacity_is_total_and_reversible(count):
    capacity = storage_package_capacity(count)
    assert capacity == (1 + count) * 5_000_000_000
    assert storage_package_count(capacity) == count


@pytest.mark.parametrize("count", [-1, 100, 1.5, True, "2", None])
def test_invalid_package_count_is_rejected(count):
    with pytest.raises(ValueError):
        storage_package_capacity(count)


@pytest.mark.parametrize("capacity", [0, 2_000_000_000, 7_000_000_000, 505_000_000_000])
def test_invalid_total_capacity_is_rejected(capacity):
    with pytest.raises(ValueError):
        storage_package_count(capacity)


@pytest.mark.parametrize("cycle,price", [("month", 25000), ("year", 250000)])
def test_two_packages_mid_period_charge_only_unpaid_difference(cycle, price):
    start = datetime(2026, 10, 1, tzinfo=UTC)
    end = start + timedelta(days=30 if cycle == "month" else 365)
    quote = quote_storage_purchase(
        segments=[
            StorageSegment(uuid4(), start, end, cycle, 10_000_000_000, price, 2 * price, uuid4())
        ],
        target_capacity_bytes=15_000_000_000,
        now=start + (end - start) / 2,
    )
    assert quote.payable_amount_minor == price // 2
    assert quote.next_capacity_bytes == 15_000_000_000


def test_storage_price_consent_binds_all_terms_without_enabling_recurring():
    subscription = WorkspaceSubscription(workspace_id=uuid4(), recurring_allowed=False)
    price = BillingStoragePriceVersion(
        id=uuid4(),
        version=2,
        capacity_bytes=100_000_000_000,
        cycle="month",
        amount_minor=475000,
        currency="RUB",
        policy_snapshot={"offer_version": "personal-2026-09-27"},
    )
    assert storage_price_is_accepted(subscription, None)
    assert not storage_price_is_accepted(subscription, price)
    accept_storage_price(subscription, storage_price_snapshot(price))
    assert storage_price_is_accepted(subscription, price)

    assert subscription.recurring_allowed is False
    for field, new in [
        ("amount_minor", 475001),
        ("version", 3),
        ("cycle", "year"),
        ("capacity_bytes", 105_000_000_000),
        ("id", uuid4()),
        ("policy_snapshot", {"offer_version": "new-offer"}),
    ]:
        previous = getattr(price, field)
        setattr(price, field, new)
        assert not storage_price_is_accepted(subscription, price)
        setattr(price, field, previous)
    assert storage_price_is_accepted(subscription, price)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "snapshot,cached,expected",
    [
        (2_000_000_000, 2_000_000_000, 5_000_000_000),
        (20_000_000_000, 2_000_000_000, 20_000_000_000),
        (None, 2_000_000_000, 5_000_000_000),
        (None, 20_000_000_000, 20_000_000_000),
    ],
)
async def test_paid_bonus_gets_base_floor_without_overwriting_snapshot(snapshot, cached, expected):
    class DB:
        async def execute(self, _query):
            return SimpleNamespace(first=lambda: SimpleNamespace(capacity_snapshot_bytes=snapshot))

    now = datetime.now(UTC)
    sub = WorkspaceSubscription(
        workspace_id=uuid4(),
        plan_code="personal",
        state="personal",
        capacity_bytes=cached,
        paid_through=now + timedelta(days=1),
    )
    assert await effective_paid_storage(DB(), subscription=sub, now=now) == expected
    assert sub.capacity_bytes == cached


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["unaccepted", "catalog_changed"])
async def test_scheduled_renewal_rechecks_package_terms_before_any_provider_call(
    monkeypatch, tmp_path, change
):
    from dataclasses import replace

    from tests.unit.test_renewal_charge import (
        OPERATION_ID,
        WORKSPACE_ID,
        FakeDb,
        FakeProvider,
        _attempt_charge_moment,
        _planning_catalog,
        _rows,
        _settings,
    )
    from twobrain_rec_server.billing import renewal_charge as renewal
    from twobrain_rec_server.billing.catalog import validate_plan_version

    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=1)
    price = BillingStoragePriceVersion(
        id=uuid4(),
        version=2,
        capacity_bytes=10_000_000_000,
        cycle="month",
        amount_minor=25000,
        currency="RUB",
        policy_snapshot={"package_count": 1},
    )
    base_catalog = validate_plan_version(_planning_catalog())
    operation.request_snapshot = {
        **operation.request_snapshot,
        "catalog_snapshot": replace(
            base_catalog, amount_minor=104000, storage_bytes=10000000000
        ).as_dict(),
        "storage_price_snapshot": storage_price_snapshot(price),
    }
    if change == "catalog_changed":
        accept_storage_price(subscription, storage_price_snapshot(price))
        price.amount_minor = 30000

    async def base(*_args, **_kwargs):
        return base_catalog

    async def compose(*_args, **_kwargs):
        return replace(
            base_catalog,
            amount_minor=base_catalog.amount_minor + price.amount_minor,
            storage_bytes=price.capacity_bytes,
        ), price

    provider = FakeProvider({"id": "must-not-be-called"})
    monkeypatch.setattr(renewal, "_approved_catalog", base)
    monkeypatch.setattr(renewal, "compose_personal_catalog", compose)
    monkeypatch.setattr(renewal, "YooKassaClient", lambda _settings: provider)
    result = await renewal.charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=_attempt_charge_moment(1),
    )
    assert result.status == operation.state == invoice.status == "canceled"
    assert subscription.renewal_resolution == "price_changed"
    assert subscription.recurring_allowed is True
    assert provider.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_code", ["free", "personal"])
async def test_reactivation_quote_includes_previously_selected_storage(monkeypatch, plan_code):
    from twobrain_rec_server.billing import purchases
    from twobrain_rec_server.billing.catalog import validate_plan_version
    from twobrain_rec_server.db.models import BillingPlanVersion

    now = datetime(2026, 9, 28, tzinfo=UTC)
    sub = WorkspaceSubscription(workspace_id=uuid4(), plan_code=plan_code,
                                paid_through=now - timedelta(days=1),
                                next_capacity_bytes=10_000_000_000)
    base = validate_plan_version(BillingPlanVersion(
        plan_code="personal", version=1, cycle="month", amount_minor=100000,
        currency="RUB", storage_bytes=5_000_000_000, processing_mode="unlimited",
        enabled_for_checkout=True, policy_snapshot={"offer_version": "synthetic"}))
    price = BillingStoragePriceVersion(id=uuid4(), version=1, cycle="month",
                                      capacity_bytes=10_000_000_000, amount_minor=25000,
                                      currency="RUB", enabled_for_checkout=True, policy_snapshot={})

    async def catalog(*args, **kwargs):
        return {(10_000_000_000, "month"): price}

    monkeypatch.setattr(purchases, "storage_catalog", catalog)
    quoted, storage = await purchases.compose_personal_catalog(None, base=base,
                                                              subscription=sub, now=now)
    assert quoted.amount_minor == 125000
    assert quoted.storage_bytes == 10_000_000_000
    assert storage is price
