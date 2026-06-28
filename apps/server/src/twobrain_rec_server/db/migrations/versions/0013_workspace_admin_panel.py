"""workspace admin panel

Revision ID: 0013_workspace_admin_panel
Revises: 0012_support_incidents
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_workspace_admin_panel"
down_revision: str | None = "0012_support_incidents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADMIN_TABLES = (
    "workspace_invitations",
    "workspace_quota_policies",
    "workspace_usage_daily",
    "user_usage_daily",
    "admin_audit_events",
)
POLICY_NAMES = {table: f"{table}_tenant_isolation" for table in ADMIN_TABLES}
ADMIN_TENANT_PREDICATE = (
    "((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
    "or rec_maintenance_allowed())"
)
AUTH_BOOTSTRAP_TENANT_PREDICATE = (
    "((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
    "or (rec_context_kind() = 'auth_bootstrap' and workspace_id = rec_current_workspace_id() "
    "and rec_auth_bootstrap_workspace_in_organization()) "
    "or rec_maintenance_allowed())"
)


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _create_all_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(POLICY_NAMES[table_name])
    predicate = _policy_predicate(table_name)
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"create policy {policy} on {table} using ({predicate}) with check ({predicate})")


def _drop_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(POLICY_NAMES[table_name])
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def _policy_predicate(table_name: str) -> str:
    if table_name in {"workspace_invitations", "admin_audit_events"}:
        return AUTH_BOOTSTRAP_TENANT_PREDICATE
    return ADMIN_TENANT_PREDICATE


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table(
        "workspace_invitations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("target_contact", sa.String(length=240), nullable=False),
        sa.Column("target_provider", sa.String(length=64)),
        sa.Column("invited_role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="admin"),
        sa.Column(
            "created_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("completed_membership_id", sa.String(length=160)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revocation_reason", sa.String(length=240)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index(
        "uq_workspace_invitations_active_pending_target",
        "workspace_invitations",
        ["workspace_id", "target_contact"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_workspace_invitations_workspace_status",
        "workspace_invitations",
        ["workspace_id", "status"],
    )

    op.create_table(
        "workspace_quota_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False, unique=True
        ),
        sa.Column("recording_minutes_limit", sa.Integer()),
        sa.Column("storage_bytes_limit", sa.BigInteger()),
        sa.Column("processing_jobs_limit", sa.Integer()),
        sa.Column(
            "policy_source", sa.String(length=80), nullable=False, server_default="display_only"
        ),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="not_configured"),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "workspace_usage_daily",
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("usage_date", sa.Date(), primary_key=True),
        sa.Column("recording_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("processing_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recording_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "freshness_state", sa.String(length=32), nullable=False, server_default="unknown"
        ),
        sa.Column("source_cutoff_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "user_usage_daily",
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), primary_key=True),
        sa.Column("usage_date", sa.Date(), primary_key=True),
        sa.Column("recording_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("processing_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "freshness_state", sa.String(length=32), nullable=False, server_default="unknown"
        ),
        sa.Column("source_cutoff_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "admin_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("actor_role", sa.String(length=32)),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target_kind", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=160)),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=120)),
        sa.Column("source_table", sa.String(length=120)),
        sa.Column("source_event_id", sa.String(length=160)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_admin_audit_events_workspace_created",
        "admin_audit_events",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_admin_audit_events_workspace_action", "admin_audit_events", ["workspace_id", "action"]
    )
    op.create_index(
        "ix_admin_audit_events_workspace_target",
        "admin_audit_events",
        ["workspace_id", "target_kind", "target_id"],
    )

    if _is_postgresql():
        for table_name in ADMIN_TABLES:
            _create_all_policy(table_name)


def downgrade() -> None:
    if _is_postgresql():
        for table_name in ADMIN_TABLES:
            _drop_policy(table_name)
    op.drop_index("ix_admin_audit_events_workspace_target", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_workspace_action", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_workspace_created", table_name="admin_audit_events")
    op.drop_table("admin_audit_events")
    op.drop_table("user_usage_daily")
    op.drop_table("workspace_usage_daily")
    op.drop_table("workspace_quota_policies")
    op.drop_index("ix_workspace_invitations_workspace_status", table_name="workspace_invitations")
    op.drop_index(
        "uq_workspace_invitations_active_pending_target", table_name="workspace_invitations"
    )
    op.drop_table("workspace_invitations")
