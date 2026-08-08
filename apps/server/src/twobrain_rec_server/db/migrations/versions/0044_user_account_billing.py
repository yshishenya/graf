"""foundational personal-account billing tables and tenant isolation

Revision ID: 0044_user_account_billing
Revises: 0043_initial_outcome_reconcile
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0044_user_account_billing"
down_revision: str | None = "0043_initial_outcome_reconcile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BILLING_TABLES = (
    "workspace_subscriptions",
    "trial_activations",
    "billing_operations",
    "billing_invoices",
    "billing_payment_methods",
    "observed_provider_refunds",
    "free_usage_windows",
    "usage_reservations",
    "usage_ledger_entries",
    "storage_reservations",
    "time_credit_ledger_entries",
    "billing_audit_events",
    "billing_notification_deliveries",
    "billing_webhook_events",
    "referral_attributions",
)
GLOBAL_BILLING_TABLES = ("billing_plan_versions",)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _tenant_policy(table_name: str) -> None:
    if not _is_postgresql():
        return
    quoted = sa.sql.elements.quoted_name(table_name, quote=True)
    policy = sa.sql.elements.quoted_name(f"{table_name}_tenant_isolation", quote=True)
    if table_name in GLOBAL_BILLING_TABLES:
        predicate = "rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed()"
    elif table_name == "billing_webhook_events":
        predicate = "(rec_context_kind() = 'auth_public' and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed()"
    else:
        predicate = "(rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed()"
    op.execute(f"alter table {quoted} enable row level security")
    op.execute(f"alter table {quoted} force row level security")
    op.execute(f"drop policy if exists {policy} on {quoted}")
    op.execute(
        f"create policy {policy} on {quoted} using ({predicate}) with check ({predicate})"
    )


def _drop_tenant_policy(table_name: str) -> None:
    if not _is_postgresql():
        return
    quoted = sa.sql.elements.quoted_name(table_name, quote=True)
    policy = sa.sql.elements.quoted_name(f"{table_name}_tenant_isolation", quote=True)
    op.execute(f"drop policy if exists {policy} on {quoted}")
    op.execute(f"alter table {quoted} no force row level security")
    op.execute(f"alter table {quoted} disable row level security")


def _replace_maintenance_helper(*, include_billing: bool) -> None:
    if not _is_postgresql():
        return
    operations = (
        "migration_verification",
        "production_smoke_setup",
        "production_smoke_cleanup",
        "backup_restore_rehearsal",
        "operator_diagnostics",
        "provider_link_cleanup",
        "playback_normalization_inventory",
        "playback_normalization_dispatch",
        "prompt_optimization",
        "outcome_dispatch_reconciliation",
        "deletion_purge_reconciliation",
        "processing_legacy_lineage_reconciliation",
        "outcome_initial_baseline_reconciliation",
    )
    if include_billing:
        operations = (*operations, "billing_reconciliation")
    literals = ", ".join(f"'{value}'" for value in operations)
    op.execute(
        f"""
        create or replace function rec_maintenance_allowed()
        returns boolean language sql stable as $$
            select rec_setting('app.context_kind') = 'maintenance'
            and rec_setting('app.maintenance_operation') = any(array[{literals}])
            and rec_setting('app.maintenance_actor') is not null
            and rec_setting('app.maintenance_reason') is not null
            and rec_setting('app.maintenance_feature_area') is not null
            and session_user = 'twobrain_rec_maintenance'
        $$;
        """
    )


def upgrade() -> None:
    op.create_table(
        "billing_plan_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("plan_code", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("cycle", sa.String(16), nullable=False, server_default="none"),
        sa.Column("amount_minor", sa.Integer()),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("storage_bytes", sa.BigInteger(), nullable=False),
        sa.Column("processing_mode", sa.String(16), nullable=False),
        sa.Column("enabled_for_checkout", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("policy_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("plan_code", "version", name="uq_billing_plan_versions_code_version"),
    )
    op.create_table(
        "billing_webhook_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("provider_event_id", sa.String(160), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("object_id", sa.String(160), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="accepted"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "provider_event_id", name="uq_billing_webhook_provider_event"),
    )
    op.create_table(
        "referral_attributions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("inviter_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("invitee_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("campaign_version", sa.String(64), nullable=False, server_default="referral-v1"),
        sa.Column("first_touched_at", sa.DateTime(timezone=True)),
        sa.Column("bound_at", sa.DateTime(timezone=True)),
        sa.Column("state", sa.String(32), nullable=False, server_default="issued"),
        sa.Column("risk_signal", sa.String(120)),
    )
    op.create_index(
        "ix_referral_attributions_workspace_state",
        "referral_attributions",
        ["workspace_id", "state"],
    )
    op.create_table(
        "workspace_subscriptions",
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("billing_owner_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("state", sa.String(32), nullable=False, server_default="free"),
        sa.Column("plan_code", sa.String(32), nullable=False, server_default="free"),
        sa.Column("cycle", sa.String(16), nullable=False, server_default="none"),
        sa.Column("capacity_bytes", sa.BigInteger(), nullable=False, server_default="250000000"),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("paid_through", sa.DateTime(timezone=True)),
        sa.Column("billing_anchor", sa.DateTime(timezone=True)),
        sa.Column("recurring_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recurring_authority_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("renewal_resolution", sa.String(40)),
        sa.Column("application_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "trial_activations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_trial_activations_user"),
    )
    op.create_table(
        "billing_operations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(240), nullable=False),
        sa.Column("provider_id", sa.String(160)),
        sa.Column("state", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("provider_key_expires_at", sa.DateTime(timezone=True)),
        sa.Column("request_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_billing_operations_key"),
    )
    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("operation_id", sa.Uuid(), sa.ForeignKey("billing_operations.id"), nullable=False),
        sa.Column("safe_number", sa.String(80), nullable=False, unique=True),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("plan_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("receipt_contact_snapshot", sa.String(254)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "operation_id", name="uq_billing_invoices_operation"),
    )
    op.create_table(
        "billing_payment_methods",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("encrypted_provider_ref", sa.String(2048), nullable=False),
        sa.Column("key_version", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="bank_card"),
        sa.Column("masked_label", sa.String(64)),
        sa.Column("state", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "observed_provider_refunds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("billing_invoices.id"), nullable=False),
        sa.Column("shop_environment", sa.String(32), nullable=False),
        sa.Column("provider_refund_id", sa.String(160), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="succeeded"),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("shop_environment", "provider_refund_id", name="uq_observed_refunds_provider"),
    )
    op.create_table(
        "free_usage_windows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("included_seconds", sa.Integer(), nullable=False, server_default="18000"),
        sa.Column("committed_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("freshness_state", sa.String(32), nullable=False, server_default="fresh"),
        sa.UniqueConstraint("workspace_id", "window_start", name="uq_free_usage_windows_workspace_window"),
    )
    op.create_table(
        "usage_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("window_id", sa.Uuid(), sa.ForeignKey("free_usage_windows.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(240), nullable=False),
        sa.Column("declared_seconds", sa.Integer(), nullable=False),
        sa.Column("committed_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state", sa.String(32), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_usage_reservations_key"),
    )
    op.create_table(
        "usage_ledger_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), sa.ForeignKey("usage_reservations.id"), nullable=False),
        sa.Column("source_id", sa.String(240), nullable=False),
        sa.Column("start_second", sa.Integer(), nullable=False),
        sa.Column("end_second", sa.Integer(), nullable=False),
        sa.Column("committed_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "storage_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(240), nullable=False),
        sa.Column("declared_bytes", sa.BigInteger(), nullable=False),
        sa.Column("committed_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("artifact_id", sa.Uuid(), sa.ForeignKey("track_artifacts.id")),
        sa.Column("state", sa.String(32), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_storage_reservations_key"),
    )
    op.create_table(
        "time_credit_ledger_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("source_ref", sa.String(240), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("maturity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_start", sa.DateTime(timezone=True)),
        sa.Column("applied_end", sa.DateTime(timezone=True)),
        sa.Column("reversal_of_id", sa.Uuid(), sa.ForeignKey("time_credit_ledger_entries.id")),
        sa.UniqueConstraint("workspace_id", "source_ref", name="uq_time_credit_source"),
    )
    op.create_table(
        "billing_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("target_kind", sa.String(64), nullable=False),
        sa.Column("target_ref", sa.String(160)),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(120)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_billing_audit_events_workspace_created", "billing_audit_events", ["workspace_id", "created_at"])
    op.create_table(
        "billing_notification_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("event_id", sa.String(160), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("template_key", sa.String(64), nullable=False),
        sa.Column("state", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("safe_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id", "event_id", "recipient_id", "channel",
            name="uq_billing_notification_delivery",
        ),
    )
    op.create_index(
        "ix_billing_notification_delivery_pending",
        "billing_notification_deliveries",
        ["workspace_id", "state", "created_at"],
    )
    op.create_index("ix_usage_ledger_entries_source_range", "usage_ledger_entries", ["workspace_id", "source_id", "start_second", "end_second"], unique=True)
    _replace_maintenance_helper(include_billing=True)
    for table_name in (*GLOBAL_BILLING_TABLES, *BILLING_TABLES):
        _tenant_policy(table_name)


def downgrade() -> None:
    for table_name in reversed((*GLOBAL_BILLING_TABLES, *BILLING_TABLES)):
        _drop_tenant_policy(table_name)
    op.drop_index("ix_usage_ledger_entries_source_range", table_name="usage_ledger_entries")
    op.drop_index("ix_billing_audit_events_workspace_created", table_name="billing_audit_events")
    op.drop_index("ix_billing_notification_delivery_pending", table_name="billing_notification_deliveries")
    op.drop_index("ix_referral_attributions_workspace_state", table_name="referral_attributions")
    for table_name in reversed((*GLOBAL_BILLING_TABLES, *BILLING_TABLES)):
        op.drop_table(table_name)
    _replace_maintenance_helper(include_billing=False)
