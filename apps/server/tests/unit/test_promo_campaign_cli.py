import json
from datetime import UTC, datetime

import pytest

from scripts.manage_promo_campaign import (
    campaign_values_for_create,
    safe_campaign_metadata,
)
from twobrain_rec_server.billing.promotions import PromoError


def test_campaign_values_hash_code_and_keep_only_metadata() -> None:
    values = campaign_values_for_create(
        code=" launch‐10 ",
        campaign_version="launch-2026-08",
        discount_percent=10,
        max_redemptions=100,
        cycle="month",
        starts_at=datetime(2026, 8, 24, tzinfo=UTC),
        ends_at=datetime(2026, 9, 30, tzinfo=UTC),
    )
    metadata = safe_campaign_metadata(values, mode="dry_run", action="create")
    serialized = json.dumps(metadata, ensure_ascii=False)
    assert "LAUNCH-10" not in serialized
    assert len(values["code_hash"]) == 64
    assert metadata["action"] == "create"
    assert metadata["mode"] == "dry_run"


def test_campaign_values_reject_invalid_window_and_parameters() -> None:
    with pytest.raises(PromoError):
        campaign_values_for_create(
            code="SAVE10",
            campaign_version="v1",
            discount_percent=100,
            max_redemptions=1,
            cycle=None,
            starts_at=None,
            ends_at=None,
        )
    with pytest.raises(PromoError):
        campaign_values_for_create(
            code="SAVE10",
            campaign_version="v1",
            discount_percent=10,
            max_redemptions=1,
            cycle="month",
            starts_at=datetime(2026, 9, 1, tzinfo=UTC),
            ends_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
    with pytest.raises(PromoError, match="даты начала и окончания"):
        campaign_values_for_create(
            code="SAVE10",
            campaign_version="v1",
            discount_percent=10,
            max_redemptions=1,
            cycle="month",
            starts_at=None,
            ends_at=None,
        )


def test_acceptance_campaign_requires_single_use_bound_workspace_budget_and_window():
    from datetime import timedelta
    from uuid import uuid4

    start = datetime(2026, 9, 26, tzinfo=UTC)
    values = dict(
        code="SYNTHETIC",
        campaign_version="acceptance-v1",
        discount_percent=99,
        max_redemptions=1,
        cycle="month",
        starts_at=start,
        ends_at=start + timedelta(hours=2),
        purpose="storage_upgrade",
        acceptance_workspace=uuid4(),
        acceptance_limit_minor=20000,
    )
    policy = campaign_values_for_create(**values)["policy_snapshot"]
    assert policy["purposes"] == ["storage_upgrade"]
    assert policy["workspace_id"] == str(values["acceptance_workspace"])
    for change in [
        {"acceptance_limit_minor": 20001},
        {"acceptance_workspace": None},
        {"max_redemptions": 2},
        {"ends_at": start + timedelta(hours=25)},
    ]:
        with pytest.raises(PromoError):
            campaign_values_for_create(**{**values, **change})
