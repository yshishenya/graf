from pathlib import Path

from twobrain_rec_server.db.models.billing import (
    BillingAuditEvent,
    BillingInvoice,
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


def test_all_billing_tables_are_in_tenant_policy_inventory() -> None:
    migration_source = next(Path(__file__).parents[2].glob("src/twobrain_rec_server/db/migrations/versions/0044_user_account_billing.py")).read_text(encoding="utf-8")
    models = (
        BillingPlanVersion,
        WorkspaceSubscription,
        TrialActivation,
        BillingOperation,
        BillingInvoice,
        BillingPaymentMethod,
        ObservedProviderRefund,
        FreeUsageWindow,
        UsageReservation,
        UsageLedgerEntry,
        StorageReservation,
        TimeCreditLedgerEntry,
        BillingAuditEvent,
        BillingWebhookEvent,
        ReferralAttribution,
    )
    for model in models:
        table_name = model.__tablename__
        assert table_name in migration_source
        assert "_tenant_isolation" in migration_source
