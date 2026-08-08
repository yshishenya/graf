from uuid import uuid4

import pytest

from twobrain_rec_server.billing.checkout import build_checkout_intent, checkout_preview


def test_checkout_intent_has_safe_invoice_reference_and_bounded_key() -> None:
    intent = build_checkout_intent(
        workspace_id=uuid4(),
        idempotency_key="checkout-1",
        preview=checkout_preview(plan_code="personal", cycle="month"),
    )
    assert intent.invoice_number.startswith("INV-")
    assert len(intent.invoice_number) <= 80
    with pytest.raises(ValueError):
        build_checkout_intent(
            workspace_id=uuid4(),
            idempotency_key=" ",
            preview=intent.preview,
        )
