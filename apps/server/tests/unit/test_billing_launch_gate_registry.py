from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.billing.launch_gates import (
    MANDATORY_BILLING_LAUNCH_GATES,
    BillingLaunchBlocked,
    require_current_billing_launch_gates,
    shop_id_hash,
)
from twobrain_rec_server.db.models import BillingLaunchGate


class FakeDb:
    def __init__(self, rows):
        self.rows = rows

    async def scalars(self, _query):
        return self.rows


def _rows(*, now: datetime, deployment_sha: str, missing: str | None = None):
    return [
        BillingLaunchGate(
            environment="production",
            shop_id_hash=shop_id_hash("shop-1"),
            deployment_sha=deployment_sha,
            gate_key=key,
            version=1,
            status="approved",
            evidence_ref=f"evidence:{key}",
            owner_role=key,
            approver_ref=f"approver:{key}",
            executor_ref="release:operator",
            values_json={
                "provider_correction": {
                    "threshold_minor": 0,
                    "approver_role": "finance",
                    "executor_role": "billing_operator",
                },
                "off_provider_correction": {
                    "threshold_minor": 0,
                    "approver_role": "finance",
                    "executor_role": "billing_operator",
                },
            },
            approved_at=now - timedelta(minutes=1),
            valid_until=now + timedelta(days=1),
        )
        for key in MANDATORY_BILLING_LAUNCH_GATES
        if key != missing
    ]


@pytest.mark.anyio
async def test_complete_current_registry_allows_provider_boundary() -> None:
    now = datetime(2026, 8, 13, tzinfo=UTC)
    sha = "a" * 40

    await require_current_billing_launch_gates(
        FakeDb(_rows(now=now, deployment_sha=sha)),
        environment="production",
        shop_id="shop-1",
        deployment_sha=sha,
        now=now,
    )


@pytest.mark.anyio
@pytest.mark.parametrize("missing", sorted(MANDATORY_BILLING_LAUNCH_GATES))
async def test_missing_gate_blocks_provider_boundary(missing: str) -> None:
    now = datetime(2026, 8, 13, tzinfo=UTC)
    with pytest.raises(BillingLaunchBlocked, match="incomplete"):
        await require_current_billing_launch_gates(
            FakeDb(_rows(now=now, deployment_sha="a" * 40, missing=missing)),
            environment="production",
            shop_id="shop-1",
            deployment_sha="a" * 40,
            now=now,
        )


@pytest.mark.anyio
async def test_missing_deployment_identity_blocks_before_database_lookup() -> None:
    with pytest.raises(BillingLaunchBlocked, match="deployment identity"):
        await require_current_billing_launch_gates(
            FakeDb([]),
            environment="production",
            shop_id="shop-1",
            deployment_sha=None,
        )


@pytest.mark.anyio
@pytest.mark.parametrize("field,value", [("status", "rejected"), ("revoked_at", datetime(2026, 8, 13, tzinfo=UTC))])
async def test_latest_invalid_gate_blocks_older_approval(field: str, value: object) -> None:
    now = datetime(2026, 8, 13, tzinfo=UTC)
    rows = _rows(now=now, deployment_sha="a" * 40)
    newest = rows[0]
    rows.append(
        BillingLaunchGate(
            environment=newest.environment,
            shop_id_hash=newest.shop_id_hash,
            deployment_sha=newest.deployment_sha,
            gate_key=newest.gate_key,
            version=1,
            status="approved",
            evidence_ref=newest.evidence_ref,
            owner_role=newest.owner_role,
            approver_ref=newest.approver_ref,
            executor_ref=newest.executor_ref,
            values_json=newest.values_json,
            approved_at=newest.approved_at,
            valid_until=newest.valid_until,
        )
    )
    newest.version = 2
    setattr(newest, field, value)

    with pytest.raises(BillingLaunchBlocked, match="invalid"):
        await require_current_billing_launch_gates(
            FakeDb(rows),
            environment="production",
            shop_id="shop-1",
            deployment_sha="a" * 40,
            now=now,
        )


@pytest.mark.anyio
async def test_missing_four_eyes_values_block_provider_boundary() -> None:
    now = datetime(2026, 8, 13, tzinfo=UTC)
    rows = _rows(now=now, deployment_sha="a" * 40)
    rows[0].values_json = {}

    with pytest.raises(BillingLaunchBlocked, match="invalid"):
        await require_current_billing_launch_gates(
            FakeDb(rows),
            environment="production",
            shop_id="shop-1",
            deployment_sha="a" * 40,
            now=now,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evidence_ref", " "),
        ("owner_role", " "),
        ("approver_ref", " RELEASE:OPERATOR "),
    ],
)
async def test_blank_or_equivalent_approval_identity_blocks_provider_boundary(
    field: str,
    value: str,
) -> None:
    now = datetime(2026, 8, 13, tzinfo=UTC)
    rows = _rows(now=now, deployment_sha="a" * 40)
    setattr(rows[0], field, value)

    with pytest.raises(BillingLaunchBlocked, match="invalid"):
        await require_current_billing_launch_gates(
            FakeDb(rows),
            environment="production",
            shop_id="shop-1",
            deployment_sha="a" * 40,
            now=now,
        )
