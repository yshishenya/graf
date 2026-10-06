"""Freeze share publications and reserve email attempts durably; opt-in only."""

import sqlalchemy as sa
from alembic import op

revision: str = "0102_summary_sharing"
down_revision: str | None = "0101_storage_packages"
branch_labels = None
depends_on = None
TABLES = (
    "published_meeting_summaries",
    "summary_delivery_batches",
    "summary_recipient_deliveries",
    "summary_email_suppressions",
)


def uuid_col(name, target=None, nullable=False, primary_key=False):
    args = [sa.ForeignKey(target)] if target else []
    return sa.Column(name, sa.Uuid(), *args, nullable=nullable, primary_key=primary_key)


def time_col(name, nullable=True, default=None):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable, server_default=default)


def base_columns():
    return [uuid_col("id", primary_key=True), uuid_col("workspace_id", "workspaces.id")]


PREVIOUS_OPERATIONS = (
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
    "outcome_initial_baseline_reconciliation",
    "billing_reconciliation",
    "billing_notification_reconciliation",
    "account_merge",
    "calendar_sync_reconciliation",
)
PREVIOUS_OPERATIONS = (*PREVIOUS_OPERATIONS, "processing_recovery_reconciliation")
CURRENT_OPERATIONS = (*PREVIOUS_OPERATIONS, "summary_delivery_reconciliation")


def _replace_maintenance_helper(operations: tuple[str, ...]) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    literals = ", ".join(f"'{operation}'" for operation in operations)
    op.execute(
        f"""
        create or replace function rec_maintenance_allowed()
        returns boolean
        language sql
        stable
        as $$
            select session_user = 'twobrain_rec_maintenance'
            and rec_setting('app.context_kind') = 'maintenance'
            and rec_setting('app.maintenance_operation') = any(array[{literals}])
            and rec_setting('app.maintenance_actor') is not null
            and rec_setting('app.maintenance_reason') is not null
            and rec_setting('app.maintenance_feature_area') is not null
            or (
                session_user = 'twobrain_rec_app'
                and rec_account_merge_context_valid()
            )
        $$;
        """
    )


def upgrade():
    _replace_maintenance_helper(CURRENT_OPERATIONS)
    op.create_table(
        TABLES[0],
        *base_columns(),
        uuid_col("meeting_id", "meetings.id"),
        uuid_col("owner_user_id", "user_identities.id"),
        uuid_col("source_outcome_id"),
        sa.Column("template_key", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("projection_json", sa.JSON(), nullable=False),
        time_col("published_at", False, sa.func.now()),
    )
    op.create_index("ix_published_summary_meeting", TABLES[0], ["workspace_id", "meeting_id"])
    with op.batch_alter_table("meeting_share_grants") as batch:
        batch.add_column(sa.Column("share_token_ciphertext", sa.String()))
        batch.add_column(sa.Column("published_summary_id", sa.Uuid()))
        batch.add_column(
            sa.Column("publication_version", sa.Integer(), nullable=False, server_default="1")
        )
        batch.create_foreign_key(
            "fk_grant_published_summary", TABLES[0], ["published_summary_id"], ["id"]
        )
    with op.batch_alter_table("meeting_share_invitations") as batch:
        batch.add_column(sa.Column("published_summary_id", sa.Uuid()))
        batch.add_column(time_col("read_expires_at"))
        batch.create_foreign_key(
            "fk_invitation_published_summary", TABLES[0], ["published_summary_id"], ["id"]
        )
    op.drop_index(
        "uq_meeting_share_invitations_address_status", table_name="meeting_share_invitations"
    )
    op.create_index(
        "uq_meeting_share_invitations_address_status",
        "meeting_share_invitations",
        ["workspace_id", "meeting_id", "normalized_address_hash"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('pending', 'sending', 'sent') AND published_summary_id IS NULL"
        ),
    )
    op.create_table(
        TABLES[1],
        *base_columns(),
        uuid_col("meeting_id", "meetings.id"),
        uuid_col("owner_user_id", "user_identities.id"),
        uuid_col("published_summary_id", TABLES[0] + ".id"),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("automatic", sa.Boolean(), nullable=False, server_default=sa.false()),
        uuid_col("auto_rule_id", nullable=True),
        sa.Column("auto_rule_version", sa.Integer()),
        sa.Column("auto_occurrence_key", sa.String(128)),
        sa.Column("auto_authority_json", sa.JSON()),
        time_col("ready_at"),
        time_col("scheduled_at", False),
        time_col("deadline_at", False),
        time_col("created_at", False, sa.func.now()),
        time_col("cancelled_at"),
        sa.Column("failure_code", sa.String(120)),
        sa.UniqueConstraint(
            "workspace_id", "owner_user_id", "idempotency_key", name="uq_summary_batch_operation"
        ),
    )
    op.create_index("ix_summary_batch_meeting", TABLES[1], ["workspace_id", "meeting_id"])
    op.create_index("ix_summary_batch_due", TABLES[1], ["state", "scheduled_at"])
    op.create_index(
        "uq_summary_auto_occurrence",
        TABLES[1],
        ["workspace_id", "auto_occurrence_key"],
        unique=True,
        postgresql_where=sa.text("automatic = true AND auto_occurrence_key IS NOT NULL"),
    )
    op.create_table(
        TABLES[2],
        *base_columns(),
        uuid_col("batch_id", TABLES[1] + ".id"),
        sa.Column("normalized_address_hash", sa.String(128), nullable=False),
        sa.Column("encrypted_address", sa.String(), nullable=False),
        uuid_col("user_id", "user_identities.id", True),
        uuid_col("invitation_id", "meeting_share_invitations.id", True),
        uuid_col("grant_id", "meeting_share_grants.id", True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        time_col("reserved_at"),
        time_col("read_expires_at"),
        time_col("completed_at"),
        sa.Column("failure_code", sa.String(120)),
        sa.Column("provider_message_id", sa.String(240)),
        sa.UniqueConstraint(
            "batch_id", "normalized_address_hash", name="uq_summary_recipient_address"
        ),
    )
    op.create_index("ix_summary_recipient_batch", TABLES[2], ["workspace_id", "batch_id"])
    op.create_table(
        TABLES[3],
        *base_columns(),
        uuid_col("sender_user_id", "user_identities.id"),
        sa.Column("normalized_address_hash", sa.String(128), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("token_ciphertext", sa.String(), nullable=False),
        time_col("opted_out_at"),
        time_col("created_at", False, sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id",
            "sender_user_id",
            "normalized_address_hash",
            name="uq_summary_suppression_scope",
        ),
    )
    op.create_unique_constraint(
        "uq_published_summary_scope", TABLES[0], ["id", "workspace_id", "meeting_id"]
    )
    op.create_foreign_key(
        "fk_published_summary_meeting_scope",
        TABLES[0],
        "meetings",
        ["meeting_id", "workspace_id"],
        ["id", "workspace_id"],
    )
    op.create_unique_constraint("uq_summary_batch_scope", TABLES[1], ["id", "workspace_id"])
    op.create_foreign_key(
        "fk_summary_batch_publication_scope",
        TABLES[1],
        TABLES[0],
        ["published_summary_id", "workspace_id", "meeting_id"],
        ["id", "workspace_id", "meeting_id"],
    )
    op.create_foreign_key(
        "fk_summary_recipient_batch_scope",
        TABLES[2],
        TABLES[1],
        ["batch_id", "workspace_id"],
        ["id", "workspace_id"],
    )
    for table, constraint in (
        ("meeting_share_grants", "fk_grant_publication_scope"),
        ("meeting_share_invitations", "fk_invitation_publication_scope"),
    ):
        op.create_foreign_key(
            constraint,
            table,
            TABLES[0],
            ["published_summary_id", "workspace_id", "meeting_id"],
            ["id", "workspace_id", "meeting_id"],
        )
    if op.get_bind().dialect.name == "postgresql":
        predicate = "((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
        for table in TABLES:
            op.execute(f"alter table {table} enable row level security")
            op.execute(f"alter table {table} force row level security")
            op.execute(
                f"create policy {table}_tenant_isolation on {table} using ({predicate}) with check ({predicate})"
            )
            for role in ("twobrain_rec_app", "twobrain_rec_maintenance"):
                op.execute(
                    f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {role}; END IF; END $$"
                )


def downgrade():
    _replace_maintenance_helper(PREVIOUS_OPERATIONS)
    op.drop_constraint("fk_grant_publication_scope", "meeting_share_grants", type_="foreignkey")
    op.drop_constraint(
        "fk_invitation_publication_scope", "meeting_share_invitations", type_="foreignkey"
    )
    # Multiple independent published invitations cannot safely collapse into the old unique index.
    op.drop_index(
        "uq_meeting_share_invitations_address_status", table_name="meeting_share_invitations"
    )
    for table in TABLES[:0:-1]:
        op.drop_table(table)
    with op.batch_alter_table("meeting_share_invitations") as batch:
        batch.drop_constraint("fk_invitation_published_summary", type_="foreignkey")
        batch.drop_column("read_expires_at")
        batch.drop_column("published_summary_id")
    with op.batch_alter_table("meeting_share_grants") as batch:
        batch.drop_constraint("fk_grant_published_summary", type_="foreignkey")
        batch.drop_column("publication_version")
        batch.drop_column("published_summary_id")
        batch.drop_column("share_token_ciphertext")
    op.drop_table(TABLES[0])
    op.create_index(
        "uq_meeting_share_invitations_address_status",
        "meeting_share_invitations",
        ["workspace_id", "meeting_id", "normalized_address_hash"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'sending', 'sent')"),
    )
