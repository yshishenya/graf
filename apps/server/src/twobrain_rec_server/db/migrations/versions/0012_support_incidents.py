"""support incidents

Revision ID: 0012_support_incidents
Revises: 0011_recording_display_timezone
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_support_incidents"
down_revision: str | None = "0011_recording_display_timezone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SUPPORT_TABLES = ("support_incidents", "support_incident_rate_limit_buckets")
POLICY_NAMES = {table: f"{table}_tenant_isolation" for table in SUPPORT_TABLES}


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _create_all_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(POLICY_NAMES[table_name])
    predicate = "((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
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


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table(
        "support_incidents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id"), nullable=False),
        sa.Column("incident_number", sa.String(length=32)),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False),
        sa.Column("problem_code", sa.String(length=160), nullable=False),
        sa.Column("failure_category", sa.String(length=120), nullable=False),
        sa.Column("retry_class", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="pending_github"),
        sa.Column("affected_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("safe_affected_identities", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("latest_safe_report_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("latest_safe_report_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("last_idempotency_key_fingerprint", sa.String(length=128)),
        sa.Column("first_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_duplicate_received_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("redaction_result", sa.String(length=64), nullable=False),
        sa.Column("github_repo", sa.String(length=240), nullable=False, server_default="yshishenya/crisp"),
        sa.Column("github_issue_number", sa.Integer()),
        sa.Column("github_issue_url", sa.String(length=500)),
        sa.Column("github_issue_state", sa.String(length=32)),
        sa.Column("github_last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("github_failure_code", sa.String(length=120)),
        sa.UniqueConstraint("workspace_id", "dedupe_key", name="uq_support_incidents_workspace_dedupe"),
    )
    op.create_index("ix_support_incidents_workspace_status", "support_incidents", ["workspace_id", "status"])
    op.create_index("ix_support_incidents_github_issue", "support_incidents", ["github_repo", "github_issue_number"])

    op.create_table(
        "support_incident_rate_limit_buckets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id"), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("blocked_until", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "workspace_id",
            "reporter_user_id",
            "device_id",
            "dedupe_key",
            name="uq_support_incident_rate_limit_scope",
        ),
    )
    op.create_index(
        "ix_support_incident_rate_limit_blocked_until",
        "support_incident_rate_limit_buckets",
        ["blocked_until"],
    )

    if _is_postgresql():
        for table_name in SUPPORT_TABLES:
            _create_all_policy(table_name)


def downgrade() -> None:
    if _is_postgresql():
        for table_name in SUPPORT_TABLES:
            _drop_policy(table_name)
    op.drop_index("ix_support_incident_rate_limit_blocked_until", table_name="support_incident_rate_limit_buckets")
    op.drop_table("support_incident_rate_limit_buckets")
    op.drop_index("ix_support_incidents_github_issue", table_name="support_incidents")
    op.drop_index("ix_support_incidents_workspace_status", table_name="support_incidents")
    op.drop_table("support_incidents")
