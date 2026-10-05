"""Explicit summary automation rules, pause fences and instance exceptions."""

import sqlalchemy as sa
from alembic import op

revision = "0103_summary_autosend"
down_revision = "0102_summary_sharing"
branch_labels = None
depends_on = None

TABLES = ("summary_sharing_preferences", "summary_auto_send_rules", "summary_auto_send_exceptions")


def _tenant_columns():
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
    ]


def upgrade():
    op.create_table(
        "summary_sharing_preferences",
        *_tenant_columns(),
        sa.Column("ask_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auto_epoch", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_resumed_at", sa.DateTime(timezone=True)),
        sa.Column("budget_window_started_at", sa.DateTime(timezone=True)),
        sa.Column("budget_batches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "workspace_id", "owner_user_id", name="uq_summary_sharing_preferences_owner"
        ),
    )
    op.create_table(
        "summary_auto_send_rules",
        *_tenant_columns(),
        sa.Column(
            "distributor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False
        ),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("target_key", sa.String(100), nullable=False),
        sa.Column("canonical_target_key", sa.String(100), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id")),
        sa.Column(
            "calendar_source_id", sa.Uuid(), sa.ForeignKey("calendar_sources.id"), nullable=False
        ),
        sa.Column(
            "external_calendar_id",
            sa.Uuid(),
            sa.ForeignKey("external_calendars.id"),
            nullable=False,
        ),
        sa.Column("calendar_series_id", sa.String(500)),
        sa.Column("template_key", sa.String(160), nullable=False),
        sa.Column("approved_roster_fingerprint", sa.String(64), nullable=False),
        sa.Column("approved_recipients_json", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled_at", sa.DateTime(timezone=True)),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "owner_user_id",
            "scope",
            "target_key",
            name="uq_summary_auto_send_rule_target",
        ),
        sa.CheckConstraint("scope in ('meeting', 'series')", name="summary_auto_send_rule_scope"),
    )
    op.create_index(
        "ix_summary_auto_send_rules_active",
        "summary_auto_send_rules",
        ["workspace_id", "owner_user_id", "enabled"],
    )
    op.create_index(
        "ix_summary_auto_send_rules_canonical",
        "summary_auto_send_rules",
        ["workspace_id", "canonical_target_key", "enabled"],
    )
    op.create_table(
        "summary_auto_send_exceptions",
        *_tenant_columns(),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("rule_id", sa.Uuid(), sa.ForeignKey("summary_auto_send_rules.id")),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "owner_user_id",
            "meeting_id",
            name="uq_summary_auto_send_exception_meeting",
        ),
    )
    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f"alter table {table} enable row level security")
            op.execute(f"alter table {table} force row level security")
            predicate = "((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
            op.execute(
                f"create policy {table}_isolation on {table} using ({predicate}) with check ({predicate})"
            )
            for role in ("twobrain_rec_app", "twobrain_rec_maintenance"):
                op.execute(f"""do $$ begin
                    if exists(select 1 from pg_roles where rolname = '{role}') then
                        grant select, insert, update, delete on {table} to {role};
                    end if;
                end $$""")


def downgrade():
    for table in reversed(TABLES):
        op.drop_table(table)
