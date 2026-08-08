import inspect
from pathlib import Path

import pytest

from twobrain_rec_server.billing.history import mask_payment_method
from twobrain_rec_server.billing.refund_email import build_refund_mailto
from twobrain_rec_server.billing.yookassa import YooKassaClient

HISTORY_TEMPLATE = (
    Path(__file__).parents[2]
    / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_history_content.html"
)
INVOICE_TEMPLATE = (
    Path(__file__).parents[2]
    / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_invoice_content.html"
)


def test_payment_method_projection_accepts_only_explicitly_masked_labels() -> None:
    assert mask_payment_method("•••• 4242") == "•••• 4242"
    assert mask_payment_method("card_ending_4242") == "card_ending_4242"
    assert mask_payment_method("4111111111111111") is None
    assert mask_payment_method("card 4242 token=secret") is None


def test_refund_mailto_contains_only_safe_static_support_content() -> None:
    mailto = build_refund_mailto(
        support_email="billing@example.test",
        safe_invoice_number="INV-2026-0001",
    )

    assert mailto.startswith("mailto:billing@example.test?")
    assert "INV-2026-0001" in mailto
    assert "YooKassa" in mailto
    assert "amount" not in mailto.lower()
    assert "card" not in mailto.lower()
    assert "provider" not in mailto.lower()


@pytest.mark.parametrize(
    ("support_email", "safe_reference"),
    (
        ("billing@example.test\r\nBcc:evil@example.test", "INV-123"),
        ("not-an-email", "INV-123"),
        ("billing@example.test", "provider-payment-id"),
        ("billing@example.test", "INV-1%0d%0aBcc:evil@example.test"),
    ),
)
def test_refund_mailto_rejects_unsafe_addresses_and_references(
    support_email: str,
    safe_reference: str,
) -> None:
    with pytest.raises(ValueError):
        build_refund_mailto(
            support_email=support_email,
            safe_invoice_number=safe_reference,
        )


def test_history_ui_keeps_refund_as_email_only_and_warns_against_sensitive_data() -> None:
    template = HISTORY_TEMPLATE.read_text(encoding="utf-8")

    assert "Написать письмо" in template
    assert "Скопировать номер платежа" in template
    assert "Не отправляйте данные карты" in template
    assert "не создаёт заявку в продукте" in template
    assert not hasattr(YooKassaClient, "create_refund")
    assert '"POST", "/v3/refunds' not in inspect.getsource(YooKassaClient)


def test_invoice_detail_ui_exposes_only_safe_copy_and_mailto_actions() -> None:
    template = INVOICE_TEMPLATE.read_text(encoding="utf-8")

    assert "Скопировать номер платежа" in template
    assert "Скопировать email" in template
    assert "Написать письмо" in template
    assert "GRAF не создаёт заявку" in template
    assert "не отправляйте данные карты" in template.lower()
    assert "refund_mailto" in template
    assert "invoice.receipt_url" in template
