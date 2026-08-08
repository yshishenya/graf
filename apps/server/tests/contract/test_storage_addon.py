from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.billing.catalog import ADDON_CAPACITY_BYTES
from twobrain_rec_server.billing.storage_addons import (
    choose_storage_addon,
    effective_storage_capacity,
    quote_storage_addon_upgrade,
)


def test_storage_addon_is_one_total_capacity_and_co_termed() -> None:
    starts = datetime(2026, 8, 7, tzinfo=UTC)
    addon = choose_storage_addon(
        capacity_bytes=5_000_000_000,
        starts_at=starts,
        ends_at=starts + timedelta(days=31),
    )
    assert addon.capacity_bytes in ADDON_CAPACITY_BYTES
    assert effective_storage_capacity(plan_code="personal", addon=addon) == 5_000_000_000


def test_storage_addon_rejects_stacking_and_invalid_period() -> None:
    starts = datetime(2026, 8, 7, tzinfo=UTC)
    with pytest.raises(ValueError):
        choose_storage_addon(capacity_bytes=3_000_000_000, starts_at=starts, ends_at=starts + timedelta(days=1))
    with pytest.raises(ValueError):
        choose_storage_addon(capacity_bytes=5_000_000_000, starts_at=starts, ends_at=starts)
    addon = choose_storage_addon(
        capacity_bytes=5_000_000_000,
        starts_at=starts,
        ends_at=starts + timedelta(days=1),
    )
    with pytest.raises(ValueError):
        effective_storage_capacity(plan_code="free", addon=addon)


def test_mid_cycle_upgrade_is_floor_pro_rata_and_co_termed() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 9, 1, tzinfo=UTC)
    quote = quote_storage_addon_upgrade(
        current_capacity_bytes=2_000_000_000,
        target_capacity_bytes=5_000_000_000,
        current_period_price_minor=79_000,
        target_period_price_minor=99_000,
        paid_from=start,
        paid_through=end,
        now=datetime(2026, 8, 16, tzinfo=UTC),
        provider_floor_minor=100,
    )
    assert quote.amount_minor == 10_322
    assert quote.starts_at == datetime(2026, 8, 16, tzinfo=UTC)
    assert quote.ends_at == end
    assert quote.deferred_to_renewal is False


def test_addon_defers_during_bonus_or_below_provider_floor() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 9, 1, tzinfo=UTC)
    kwargs = dict(
        current_capacity_bytes=2_000_000_000,
        target_capacity_bytes=5_000_000_000,
        current_period_price_minor=79_000,
        target_period_price_minor=79_001,
        paid_from=start,
        paid_through=end,
        now=datetime(2026, 8, 31, tzinfo=UTC),
        provider_floor_minor=100,
    )
    assert quote_storage_addon_upgrade(**kwargs).deferred_to_renewal is True
    assert quote_storage_addon_upgrade(**kwargs, bonus_interval=True).ends_at == end
