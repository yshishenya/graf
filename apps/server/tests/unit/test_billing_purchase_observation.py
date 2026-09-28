from copy import deepcopy
from uuid import uuid4

import pytest

from twobrain_rec_server.billing.reconciliation import (
    ProviderObservationError,
    ProviderScope,
    validate_purchase_payment,
)
from twobrain_rec_server.db.models import BillingInvoice, BillingOperation


def test_new_purchase_requires_exact_provider_scope_and_invoice():
    workspace = uuid4()
    operation = BillingOperation(
        id=uuid4(),
        workspace_id=workspace,
        kind="storage_upgrade",
        provider_id="synthetic-payment",
        request_snapshot={
            "purchase_schema": 2,
            "provider_environment": "production",
            "provider_shop_id": "123",
        },
    )
    invoice = BillingInvoice(
        id=uuid4(),
        operation_id=operation.id,
        workspace_id=workspace,
        safe_number="INV-SYNTHETIC",
        amount_minor=290,
        currency="RUB",
    )
    scope = ProviderScope(environment="production", shop_id="123")
    payment = {
        "id": operation.provider_id,
        "status": "succeeded",
        "test": False,
        "recipient": {"account_id": "123"},
        "amount": {"value": "2.90", "currency": "RUB"},
        "metadata": {
            "workspace_id": str(workspace),
            "operation_id": str(operation.id),
            "invoice_number": invoice.safe_number,
        },
    }
    assert (
        validate_purchase_payment(payment, operation=operation, invoice=invoice, scope=scope)
        == "succeeded"
    )
    for path, replacement in [
        (("test",), True),
        (("test",), None),
        (("recipient", "account_id"), "999"),
        (("id",), "another-payment"),
        (("amount", "currency"), "USD"),
        (("amount", "value"), "29.00"),
        (("metadata", "operation_id"), str(uuid4())),
        (("metadata", "workspace_id"), str(uuid4())),
        (("metadata", "invoice_number"), "another-invoice"),
    ]:
        changed = deepcopy(payment)
        cursor = changed
        for part in path[:-1]:
            cursor = cursor[part]
        cursor[path[-1]] = replacement
        with pytest.raises(ProviderObservationError):
            validate_purchase_payment(changed, operation=operation, invoice=invoice, scope=scope)


@pytest.mark.parametrize("kind", ["initial_checkout", "storage_upgrade", "early_renewal"])
def test_late_post_or_network_error_never_reverts_confirmed_success(kind):
    from twobrain_rec_server.cabinet.web_routes.billing import (
        _bind_initial_checkout_payment,
        _record_initial_checkout_failure,
    )

    operation = BillingOperation(
        kind=kind,
        provider_id="synthetic-payment",
        state="succeeded",
        request_snapshot={"purchase_schema": 2},
    )
    invoice = BillingInvoice(status="succeeded")
    assert _bind_initial_checkout_payment(operation, invoice, {"id": "synthetic-payment"}) is None
    _record_initial_checkout_failure(operation, invoice, TimeoutError())
    assert operation.state == invoice.status == "succeeded"


def test_expired_unknown_payment_is_not_declared_canceled():
    from datetime import UTC, datetime, timedelta

    from twobrain_rec_server.cabinet.web_routes.billing import _record_initial_checkout_failure

    operation = BillingOperation(
        state="processing",
        request_snapshot={"purchase_schema": 2},
        provider_key_expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    invoice = BillingInvoice(status="pending")
    _record_initial_checkout_failure(operation, invoice, TimeoutError())
    assert operation.state == invoice.status == "manual_resolution"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode", ["empty", "ambiguous", "wrong_shop", "cursor_loop", "too_many_pages"]
)
async def test_reference_recovery_never_guesses_or_releases_unresolved_money(mode):
    from datetime import UTC, datetime

    from twobrain_rec_server.billing.webhook_reconciliation import recover_purchase_reference

    workspace, op_id = uuid4(), uuid4()
    operation = BillingOperation(
        id=op_id,
        workspace_id=workspace,
        provider_id=None,
        created_at=datetime.now(UTC),
        request_snapshot={
            "purchase_schema": 2,
            "provider_shop_id": "123",
            "provider_environment": "production",
        },
    )
    invoice = BillingInvoice(
        id=uuid4(),
        operation_id=op_id,
        workspace_id=workspace,
        amount_minor=1000,
        currency="RUB",
        safe_number="INV-SYNTHETIC",
    )
    payment = {
        "id": "synthetic-payment",
        "status": "succeeded",
        "test": False,
        "recipient": {"account_id": "wrong" if mode == "wrong_shop" else "123"},
        "amount": {"value": "10.00", "currency": "RUB"},
        "metadata": {
            "operation_id": str(op_id),
            "workspace_id": str(workspace),
            "invoice_number": invoice.safe_number,
        },
    }

    class Db:
        async def scalar(self, _query):
            return invoice

    class Provider:
        calls = 0

        async def list_payments(self, **kwargs):
            self.calls += 1
            assert kwargs["created_from"] < kwargs["created_until"]
            if mode == "empty":
                return {"items": []}
            if mode == "ambiguous":
                return {"items": [payment, {**payment, "id": "synthetic-another"}]}
            if mode in {"cursor_loop", "too_many_pages"}:
                return {
                    "items": [payment],
                    "next_cursor": "same" if mode == "cursor_loop" else str(self.calls),
                }
            return {"items": [payment]}

    provider = Provider()
    if mode == "empty":
        assert not await recover_purchase_reference(
            Db(),
            provider,
            operation=operation,
            scope=ProviderScope(environment="production", shop_id="123"),
        )
    else:
        with pytest.raises(ProviderObservationError):
            await recover_purchase_reference(
                Db(),
                provider,
                operation=operation,
                scope=ProviderScope(environment="production", shop_id="123"),
            )
    assert operation.provider_id is None and provider.calls <= 3


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 405, 415, 429, 409, 500, None])
@pytest.mark.parametrize("provider_id", [None, "synthetic-payment"])
def test_creation_rejection_never_discards_known_payment_or_ambiguous_result(
    status_code, provider_id
):
    from twobrain_rec_server.billing.yookassa import YooKassaProviderError
    from twobrain_rec_server.cabinet.web_routes.billing import _record_initial_checkout_failure

    operation = BillingOperation(
        state="processing", provider_id=provider_id, request_snapshot={"purchase_schema": 2}
    )
    invoice = BillingInvoice(status="pending")
    _record_initial_checkout_failure(
        operation, invoice, YooKassaProviderError("synthetic", status_code=status_code)
    )
    expected = (
        "unknown"
        if provider_id
        else (
            "canceled"
            if status_code in {400, 401, 403, 404, 405, 415, 429}
            else "manual_resolution"
        )
    )
    assert operation.state == invoice.status == expected
