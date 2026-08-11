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
    ReferralLink,
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
    migration_0058 = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0058_referral_links_many_invitees.py"
    for model in models:
        table_name = model.__tablename__
        source = migration_0058.read_text(encoding="utf-8") if model is ReferralLink else migration_source
        assert table_name in source
        if model is not ReferralLink:
            assert "_tenant_isolation" in source


def test_referral_binding_uses_a_token_scoped_context() -> None:
    migration = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0050_referral_token_lookup_context.py"
    source = migration.read_text(encoding="utf-8")
    assert "auth_referral_lookup" in source
    assert "app.referral_token_hash" in source
    assert "invitee_user_id = rec_current_user_id()" in source
    owner_policy = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0055_referral_owner_lookup.py"
    owner_source = owner_policy.read_text(encoding="utf-8")
    assert "inviter_user_id = rec_current_user_id()" in owner_source


def test_billing_catalog_is_readable_but_maintenance_only_writable() -> None:
    migration = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0056_billing_catalog_write_rls.py"
    source = migration.read_text(encoding="utf-8")
    assert "rec_context_kind() in ('request', 'worker')" in source
    assert "with check (rec_maintenance_allowed())" in source


def test_referral_owner_lookup_is_scoped_to_selected_workspace() -> None:
    migration = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0057_referral_workspace_scope.py"
    source = migration.read_text(encoding="utf-8")
    assert "workspace_id = rec_current_workspace_id()" in source
    assert "rec_context_kind() = 'auth_public'" in source


def test_many_invitee_referral_migration_separates_link_and_attribution() -> None:
    migration = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0058_referral_links_many_invitees.py"
    source = migration.read_text(encoding="utf-8")
    assert 'create_table(' in source
    assert '"referral_links"' in source
    assert "referral_link_id" in source
    assert "uq_referral_attributions_link_invitee" in source
    assert "inviter_user_id = rec_current_user_id()" in source
    migration_0059 = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0059_referral_expiry_owner_write.py"
    source_0059 = migration_0059.read_text(encoding="utf-8")
    assert "expires_at" in source_0059
    assert "uq_referral_attributions_invitee" in source_0059
