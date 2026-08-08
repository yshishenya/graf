from twobrain_rec_server.billing.audit import metadata_only


def test_billing_audit_is_metadata_only_and_bounded() -> None:
    result = metadata_only(
        {
            "event": "refund_observed",
            "source": "registry",
            "provider_id": "pay-secret",
            "email_body": "private support text",
            "meeting_content": "transcript",
            "amount_minor": 79000,
            "promo_code_hash": "hash",
            "referral_reward": "week",
            "receipt_contact": "private@example.test",
            "count": 2,
        }
    )
    assert result == {"event": "refund_observed", "source": "registry", "count": "2"}
