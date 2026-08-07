from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.billing.catalog import ADDON_CAPACITY_BYTES
from twobrain_rec_server.billing.storage_addons import (
    choose_storage_addon,
    effective_storage_capacity,
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
