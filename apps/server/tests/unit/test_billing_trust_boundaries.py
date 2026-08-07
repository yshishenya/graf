from twobrain_rec_server.api.billing import MAX_BILLING_WEBHOOK_BYTES
from twobrain_rec_server.billing.trial import require_trial_activation
from twobrain_rec_server.billing.yookassa import is_allowed_confirmation_url


def test_trial_requires_active_personal_workspace_owner_and_unused_identity() -> None:
    require_trial_activation(
        identity_status="active",
        membership_role="owner",
        workspace_kind="personal",
        already_used=False,
    )


def test_trial_rejects_non_owner_or_corporate_workspace() -> None:
    for role, kind in (("member", "personal"), ("owner", "corporate")):
        try:
            require_trial_activation(
                identity_status="active",
                membership_role=role,
                workspace_kind=kind,
                already_used=False,
            )
        except PermissionError:
            pass
        else:
            raise AssertionError("trial must fail closed for non-personal owner context")


def test_confirmation_url_is_yookassa_allowlisted_https_only() -> None:
    assert is_allowed_confirmation_url("https://yookassa.ru/checkout/abc")
    assert is_allowed_confirmation_url("https://api.yookassa.test/checkout/abc")
    assert not is_allowed_confirmation_url("http://yookassa.ru/checkout/abc")
    assert not is_allowed_confirmation_url("https://evil.example/checkout/abc")


def test_billing_webhook_has_bounded_body_budget() -> None:
    assert MAX_BILLING_WEBHOOK_BYTES == 256 * 1024
