from datetime import UTC, datetime
from uuid import UUID

import pytest

import twobrain_rec_server.billing.entitlements as entitlements
from twobrain_rec_server.db.models import (
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)

WORKSPACE_ID = UUID("22222222-2222-4222-8222-222222222222")
OWNER_ID = UUID("33333333-3333-4333-8333-333333333333")
OPERATION_ID = UUID("44444444-4444-4444-8444-444444444444")
INVOICE_ID = UUID("55555555-5555-4555-8555-555555555555")


class _FakeDb:
    def __init__(self, values: list[object]) -> None:
        self._values = iter(values)
        self.added: list[object] = []

    async def scalar(self, _query: object) -> object:
        return next(self._values)

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        return None


@pytest.mark.anyio
async def test_confirmed_payment_grants_once_and_records_receipt_state(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_promo(*_args: object, **_kwargs: object) -> str:
        return "none"

    async def no_credit(*_args: object, **_kwargs: object) -> str:
        return "ineligible"

    async def no_notification(*_args: object, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(entitlements, "redeem_invoice_promo", no_promo)
    monkeypatch.setattr(entitlements, "create_pending_credit", no_credit)
    monkeypatch.setattr(entitlements, "enqueue_billing_notification", no_notification)

    operation = BillingOperation(
        id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        kind="initial_checkout",
        idempotency_key="checkout-1",
        provider_id="payment-1",
        request_snapshot={
            "plan_code": "personal",
            "cycle": "month",
            "billing_actor_user_id": str(OWNER_ID),
            "recurring_consent": False,
            "catalog_snapshot": {"storage_bytes": 5_000_000_000},
        },
    )
    invoice = BillingInvoice(
        id=INVOICE_ID,
        workspace_id=WORKSPACE_ID,
        operation_id=OPERATION_ID,
        safe_number="INV-1",
        amount_minor=79_000,
        currency="RUB",
        plan_snapshot={"plan_code": "personal", "cycle": "month"},
    )
    owner = WorkspaceMembership(
        workspace_id=WORKSPACE_ID,
        user_id=OWNER_ID,
        role="owner",
        status="active",
    )
    workspace = Workspace(
        id=WORKSPACE_ID,
        organization_id=UUID("66666666-6666-4666-8666-666666666666"),
        slug="personal",
        name="Personal",
        kind="personal",
        owner_user_id=OWNER_ID,
    )
    db = _FakeDb([operation, invoice, None, workspace, owner, None])

    result = await entitlements.grant_confirmed_payment(
        db,
        workspace_id=WORKSPACE_ID,
        provider_payment_id="payment-1",
        amount_minor=79_000,
        currency="RUB",
        paid_at=datetime(2026, 8, 7, 12, tzinfo=UTC),
        receipt_registration="succeeded",
    )

    assert result == "granted"
    assert invoice.status == "succeeded"
    assert invoice.plan_snapshot["receipt_registration"] == "succeeded"
    assert operation.state == "succeeded"
    grant = next(row for row in db.added if isinstance(row, BillingEntitlementGrant))
    assert grant.provider_payment_id == "payment-1"
    assert grant.ends_at == datetime(2026, 9, 7, 12, tzinfo=UTC)
    subscription = next(row for row in db.added if isinstance(row, WorkspaceSubscription))
    assert subscription.plan_code == "personal"
    assert subscription.capacity_bytes == 5_000_000_000
    assert subscription.paid_through == grant.ends_at

    duplicate_db = _FakeDb([operation, invoice, grant])
    assert (
        await entitlements.grant_confirmed_payment(
            duplicate_db,
            workspace_id=WORKSPACE_ID,
            provider_payment_id="payment-1",
            amount_minor=79_000,
            currency="RUB",
            paid_at=datetime(2026, 8, 7, 12, tzinfo=UTC),
            receipt_registration="succeeded",
        )
        == "duplicate"
    )
    assert not [row for row in duplicate_db.added if isinstance(row, BillingEntitlementGrant)]

    # A duplicate payment GET must not downgrade receipt truth or move a
    # previously succeeded operation into reconciliation_gap.
    duplicate_pending_db = _FakeDb([operation, invoice, grant])
    assert (
        await entitlements.grant_confirmed_payment(
            duplicate_pending_db,
            workspace_id=WORKSPACE_ID,
            provider_payment_id="payment-1",
            amount_minor=79_000,
            currency="RUB",
            paid_at=datetime(2026, 8, 7, 12, tzinfo=UTC),
            receipt_registration="pending",
        )
        == "duplicate"
    )
    assert operation.state == "succeeded"
    assert invoice.plan_snapshot["receipt_registration"] == "succeeded"


@pytest.mark.anyio
async def test_confirmed_payment_does_not_grant_personal_entitlement_to_linked_workspace() -> None:
    operation = BillingOperation(
        id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        kind="initial_checkout",
        idempotency_key="linked-checkout",
        provider_id="linked-payment",
        request_snapshot={
            "plan_code": "personal",
            "cycle": "month",
            "billing_actor_user_id": str(OWNER_ID),
        },
    )
    invoice = BillingInvoice(
        id=INVOICE_ID,
        workspace_id=WORKSPACE_ID,
        operation_id=OPERATION_ID,
        safe_number="INV-LINKED",
        amount_minor=79_000,
        currency="RUB",
        plan_snapshot={"plan_code": "personal", "cycle": "month"},
    )
    linked = Workspace(
        id=WORKSPACE_ID,
        organization_id=UUID("66666666-6666-4666-8666-666666666666"),
        slug="linked",
        name="Linked",
        kind="linked",
        owner_user_id=OWNER_ID,
    )
    owner = WorkspaceMembership(
        workspace_id=WORKSPACE_ID,
        user_id=OWNER_ID,
        role="owner",
        status="active",
    )
    db = _FakeDb([operation, invoice, None, linked, owner])

    result = await entitlements.grant_confirmed_payment(
        db,
        workspace_id=WORKSPACE_ID,
        provider_payment_id="linked-payment",
        amount_minor=79_000,
        currency="RUB",
        paid_at=datetime(2026, 8, 7, 12, tzinfo=UTC),
    )

    assert result == "owner_missing"
    assert operation.state == "reconciliation_gap"
    assert not [row for row in db.added if isinstance(row, BillingEntitlementGrant)]
