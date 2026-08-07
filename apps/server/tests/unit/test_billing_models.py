from sqlalchemy import UniqueConstraint

from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingNotificationDelivery,
    BillingOperation,
    BillingPaymentMethod,
    BillingPlanVersion,
    BillingWebhookEvent,
    FreeUsageWindow,
    ObservedProviderRefund,
    ReferralAttribution,
    StorageReservation,
    TimeCreditLedgerEntry,
    TrialActivation,
    UsageLedgerEntry,
    UsageReservation,
    WorkspaceSubscription,
)


def test_billing_models_are_workspace_bound_or_account_bound() -> None:
    workspace_models = (
        WorkspaceSubscription,
        BillingInvoice,
        BillingOperation,
        BillingNotificationDelivery,
        BillingPaymentMethod,
        ObservedProviderRefund,
        FreeUsageWindow,
        UsageReservation,
        UsageLedgerEntry,
        StorageReservation,
        TimeCreditLedgerEntry,
        BillingWebhookEvent,
        ReferralAttribution,
    )
    for model in workspace_models:
        assert "workspace_id" in model.__table__.c

    assert "user_id" in TrialActivation.__table__.c
    assert "workspace_id" in TrialActivation.__table__.c
    assert "policy_snapshot" in BillingPlanVersion.__table__.c


def test_billing_models_use_unique_idempotency_and_append_only_sources() -> None:
    operation_constraints = [c for c in BillingOperation.__table__.constraints if isinstance(c, UniqueConstraint)]
    assert any({column.name for column in c.columns} == {"workspace_id", "idempotency_key"} for c in operation_constraints)
    refund_constraints = [c for c in ObservedProviderRefund.__table__.constraints if isinstance(c, UniqueConstraint)]
    assert any({column.name for column in c.columns} == {"shop_environment", "provider_refund_id"} for c in refund_constraints)
    assert "request_snapshot" in BillingOperation.__table__.c
    assert "encrypted_provider_ref" in BillingPaymentMethod.__table__.c
    assert "raw_provider_payload" not in BillingOperation.__table__.c
