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


def test_referral_binding_uses_a_token_scoped_context() -> None:
    migration = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0050_referral_token_lookup_context.py"
    source = migration.read_text(encoding="utf-8")
    assert "auth_referral_lookup" in source
    assert "app.referral_token_hash" in source
    assert "invitee_user_id = rec_current_user_id()" in source
    owner_policy = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0055_referral_owner_lookup.py"
    owner_source = owner_policy.read_text(encoding="utf-8")
    assert "inviter_user_id = rec_current_user_id()" in owner_source
