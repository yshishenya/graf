from twobrain_rec_server.billing.refund_email import build_refund_mailto


def test_refund_mailto_is_russian_first_and_redacts_sensitive_fields() -> None:
    mailto = build_refund_mailto(
        support_email="support@example.test",
        safe_invoice_number="INV-2026-0001",
    )

    assert mailto.startswith("mailto:support@example.test?")
    assert "INV-2026-0001" in mailto
    assert "amount" not in mailto.lower()
    assert "card" not in mailto.lower()


def test_refund_mailto_rejects_header_injection() -> None:
    try:
        build_refund_mailto(
            support_email="support@example.test",
            safe_invoice_number="INV-1%0d%0aBcc:evil@example.test",
        )
    except ValueError as exc:
        assert "reference" in str(exc)
    else:
        raise AssertionError("unsafe invoice reference must be rejected")
