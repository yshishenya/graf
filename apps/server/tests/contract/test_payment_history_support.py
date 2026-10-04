import inspect
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from twobrain_rec_server.billing.history import mask_payment_method
from twobrain_rec_server.billing.refund_email import build_refund_mailto
from twobrain_rec_server.billing.yookassa import YooKassaClient
from twobrain_rec_server.cabinet.templates import render_template

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
    assert "ЮKassa" in unquote(mailto)
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

    assert 'href="mailto:{{ support_email }}"' in template
    assert 'data-copy-value="{{ support_email }}">Скопировать адрес' in template
    assert 'href="{{ invoice.detail_url }}"' in template
    assert "Номер платежа можно скопировать в его сведениях" in template
    assert "Не отправляйте данные карты, идентификаторы ЮKassa, ссылки или содержимое встреч" in template
    assert "Запрос на возврат отправьте письмом в поддержку" in template
    assert "<form" not in template.lower()
    assert not hasattr(YooKassaClient, "create_refund")
    assert '"POST", "/v3/refunds' not in inspect.getsource(YooKassaClient)


def test_invoice_detail_ui_exposes_only_safe_copy_and_mailto_actions() -> None:
    template = INVOICE_TEMPLATE.read_text(encoding="utf-8")

    assert "Скопировать номер платежа" in template
    assert 'data-copy-value="{{ invoice.safe_number }}"' in template
    assert "Вопрос об оплате" in template
    assert "Запросить возврат" in template
    assert "Открытие письма не отправляет запрос и не оформляет возврат" in template
    assert "Данные карты отправлять не нужно" in template
    assert "Результат возврата уточняйте у поддержки: GRAF не показывает его статус" in template
    assert "Возврат не отключает автопродление" in template
    assert 'href="/billing/subscription"' in template
    assert 'href="{{ invoice.refund_mailto }}"' in template
    assert 'href="{{ invoice.question_mailto }}"' in template
    assert 'href="mailto:{{ support_email }}"' not in template
    assert "invoice.receipt_url" in template
    assert "formaction" not in template.lower()
    help_section = template.split('<summary>Помощь и возврат</summary>', 1)[1]
    assert "<form" not in help_section.lower()
    assert "submit" not in help_section.lower()
    assert not hasattr(YooKassaClient, "create_refund")
    assert '"POST", "/v3/refunds' not in inspect.getsource(YooKassaClient)
    for allowed, unavailable in ((None, False), (False, False), (False, True), (True, False)):
        invoice = {"safe_number": "INV-SYNTHETIC", "amount_label": "1 000 ₽",
                   "receipt_url": None, "receipt_label": "Чек готовится", "refund_mailto": None,
                   "discount_label": None, "payment_method_label": None, "receipt_contact_label": None,
                   "receipt_refresh_failed": unavailable}
        if allowed is not None:
            invoice["can_refresh_receipt"] = allowed
        html = render_template("cabinet/pages/billing_invoice_content.html",
                               invoice=invoice, csrf_token="synthetic-csrf")
        forms = re.findall(r"<form\b[^>]*>.*?</form>", html, re.IGNORECASE | re.DOTALL)
        assert len(re.findall(r"<form\b", html, re.IGNORECASE)) == (1 if allowed else 0)
        assert len(forms) == (1 if allowed else 0)
        if forms:
            form = forms[0]
            assert form.startswith('<form action="/billing/checkout/status/INV-SYNTHETIC/refresh?return_to=invoice" method="post">')
            assert 'type="hidden" name="csrf_token" value="synthetic-csrf"' in form
            assert re.findall(r'<input\b[^>]*name="([^"]+)"', form) == ["csrf_token"]
            assert form.count('type="submit"') == 1
            assert 'type="submit">Проверить чек</button>' in form


def test_invoice_question_and_refund_have_distinct_safe_subjects() -> None:
    from urllib.parse import parse_qs, urlsplit

    from twobrain_rec_server.billing import refund_email

    values = {"support_email": "billing@example.test", "safe_invoice_number": "INV-2026-0001"}
    question = refund_email.build_question_mailto(**values)
    refund = build_refund_mailto(**values)
    assert parse_qs(urlsplit(question).query)["subject"] == ["Вопрос об оплате INV-2026-0001"]
    assert parse_qs(urlsplit(refund).query)["subject"] == ["Возврат по платежу INV-2026-0001"]
    assert parse_qs(urlsplit(question).query)["body"] == parse_qs(urlsplit(refund).query)["body"]


@pytest.mark.parametrize("address", ["billing%0d%0aBcc@example.test", "billing\r\nBcc:evil@example.test"])
def test_support_mailto_rejects_encoded_header_injection(address) -> None:
    from twobrain_rec_server.billing import refund_email

    for builder in (refund_email.build_question_mailto, build_refund_mailto):
        with pytest.raises(ValueError):
            builder(support_email=address, safe_invoice_number="INV-SYNTHETIC")


def test_support_address_cannot_inject_mailto_query() -> None:
    from urllib.parse import parse_qs, urlsplit
    mailto = build_refund_mailto(support_email="billing?cc=evil@example.test", safe_invoice_number="INV-SYNTHETIC")
    assert set(parse_qs(urlsplit(mailto).query)) == {"subject", "body"}
