"""Add proof-bound account merge state and archival source linkage."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0073_account_auth_linking"
down_revision: str | None = "0072_billing_launch_gates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_identities", sa.Column("merged_into_user_id", sa.Uuid()))
    op.add_column("user_identities", sa.Column("merged_at", sa.DateTime(timezone=True)))
    op.create_foreign_key(
        "fk_user_identities_merged_into",
        "user_identities",
        "user_identities",
        ["merged_into_user_id"],
        ["id"],
    )
    op.create_table(
        "account_merge_intents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("survivor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("source_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("email_proof_state", sa.String(32), nullable=False, server_default="missing"),
        sa.Column("oauth_proof_state", sa.String(32), nullable=False, server_default="missing"),
        sa.Column("preview_fingerprint", sa.String(64)),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="initiated"),
        sa.Column("blocker_code", sa.String(120)),
        sa.Column("error_code", sa.String(120)),
        sa.Column("idempotency_key_hash", sa.String(64)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("survivor_user_id <> source_user_id", name="ck_account_merge_distinct_users"),
    )
    op.create_index(
        "ix_account_merge_intents_expiry",
        "account_merge_intents",
        ["status", "expires_at"],
    )
    op.create_index(
        "uq_account_merge_active_pair",
        "account_merge_intents",
        ["survivor_user_id", "source_user_id"],
        unique=True,
        postgresql_where=sa.text("status in ('initiated', 'awaiting_proof', 'preview_ready', 'confirmed')"),
    )
    op.create_table(
        "account_merge_journals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("merge_intent_id", sa.Uuid(), sa.ForeignKey("account_merge_intents.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("survivor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("source_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("preview_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("counts_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("blocker_codes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("error_code", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("merge_intent_id"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            create or replace function rec_account_merge_context_valid()
            returns boolean
            language sql
            stable
            security definer
            set search_path = pg_catalog, public
            set row_security = off
            as $$
                select session_user in ('twobrain_rec_app', 'twobrain_rec_maintenance')
                and rec_setting('app.context_kind') = 'account_merge'
                and rec_setting_uuid('app.account_merge_intent_id') is not null
                and rec_setting_uuid('app.account_merge_survivor_user_id') is not null
                and rec_setting_uuid('app.account_merge_source_user_id') is not null
                and exists (
                    select 1
                    from account_merge_intents merge_intent
                    where merge_intent.id = rec_setting_uuid('app.account_merge_intent_id')
                      and merge_intent.workspace_id = rec_setting_uuid('app.workspace_id')
                      and merge_intent.survivor_user_id = rec_setting_uuid('app.account_merge_survivor_user_id')
                      and merge_intent.source_user_id = rec_setting_uuid('app.account_merge_source_user_id')
                      and merge_intent.status in ('initiated', 'awaiting_proof', 'preview_ready', 'confirmed', 'blocked', 'completed')
                      and merge_intent.email_proof_state = 'verified'
                      and merge_intent.oauth_proof_state = 'verified'
                )
            $$;
            """
        )
        op.execute(
            """
            revoke all on function rec_account_merge_context_valid() from public
            """
        )
        op.execute(
            """
            do $$
            begin
                if exists (select 1 from pg_roles where rolname = 'twobrain_rec_app') then
                    grant execute on function rec_account_merge_context_valid() to twobrain_rec_app;
                end if;
                if exists (select 1 from pg_roles where rolname = 'twobrain_rec_maintenance') then
                    grant execute on function rec_account_merge_context_valid() to twobrain_rec_maintenance;
                end if;
            end
            $$
            """
        )
        op.execute(
            """
            create or replace function rec_maintenance_allowed()
            returns boolean
            language sql
            stable
            as $$
                select (
                    session_user = 'twobrain_rec_maintenance'
                    and rec_setting('app.context_kind') = 'maintenance'
                    and rec_setting('app.maintenance_operation') = any(array[
                        'migration_verification', 'production_smoke_setup',
                        'production_smoke_cleanup', 'backup_restore_rehearsal',
                        'operator_diagnostics', 'provider_link_cleanup',
                        'playback_normalization_inventory', 'playback_normalization_dispatch',
                        'prompt_optimization', 'outcome_dispatch_reconciliation',
                        'deletion_purge_reconciliation',
                        'processing_legacy_lineage_reconciliation',
                        'outcome_initial_baseline_reconciliation', 'billing_reconciliation',
                        'billing_notification_reconciliation', 'account_merge'
                    ])
                    and rec_setting('app.maintenance_actor') is not null
                    and rec_setting('app.maintenance_reason') is not null
                    and rec_setting('app.maintenance_feature_area') is not null
                ) or (
                    session_user = 'twobrain_rec_app'
                    and rec_account_merge_context_valid()
                )
            $$;
            """
        )
        for table in ("account_merge_intents", "account_merge_journals"):
            op.execute(f"alter table {table} enable row level security")
            op.execute(f"alter table {table} force row level security")
            op.execute(f"drop policy if exists {table}_tenant_isolation on {table}")
            op.execute(
                f"create policy {table}_tenant_isolation on {table} "
                "using ((rec_context_kind() in ('request', 'auth_bootstrap') "
                "and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed()) "
                "with check ((rec_context_kind() in ('request', 'auth_bootstrap') "
                "and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
            )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in ("account_merge_journals", "account_merge_intents"):
            op.execute(f"drop policy if exists {table}_tenant_isolation on {table}")
            op.execute(f"alter table {table} no force row level security")
            op.execute(f"alter table {table} disable row level security")
        op.execute(
            """
            create or replace function rec_maintenance_allowed()
            returns boolean language sql stable as $$
                select rec_setting('app.context_kind') = 'maintenance'
                and rec_setting('app.maintenance_operation') = any(array[
                    'migration_verification', 'production_smoke_setup',
                    'production_smoke_cleanup', 'backup_restore_rehearsal',
                    'operator_diagnostics', 'provider_link_cleanup',
                    'playback_normalization_inventory', 'playback_normalization_dispatch',
                    'prompt_optimization', 'outcome_dispatch_reconciliation',
                    'deletion_purge_reconciliation',
                    'processing_legacy_lineage_reconciliation',
                    'outcome_initial_baseline_reconciliation', 'billing_reconciliation'
                ])
                and rec_setting('app.maintenance_actor') is not null
                and rec_setting('app.maintenance_reason') is not null
                and rec_setting('app.maintenance_feature_area') is not null
                and session_user = 'twobrain_rec_maintenance'
            $$
            """
        )
        op.execute("drop function if exists rec_account_merge_context_valid()")
    op.drop_table("account_merge_journals")
    op.drop_index("uq_account_merge_active_pair", table_name="account_merge_intents")
    op.drop_index("ix_account_merge_intents_expiry", table_name="account_merge_intents")
    op.drop_table("account_merge_intents")
    op.drop_constraint("fk_user_identities_merged_into", "user_identities", type_="foreignkey")
    op.drop_column("user_identities", "merged_at")
    op.drop_column("user_identities", "merged_into_user_id")
