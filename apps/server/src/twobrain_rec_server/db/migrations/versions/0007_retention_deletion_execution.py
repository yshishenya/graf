"""retention deletion execution

Revision ID: 0007_retention_deletion_exec
Revises: 0006_access_sharing_downloads
Create Date: 2026-06-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_retention_deletion_exec"
down_revision: str | None = "0006_access_sharing_downloads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTENT_CONTEXT = "rec_context_kind() in ('request', 'worker')"
CONTENT_WORKSPACE_POLICIES = {
    "meeting_deletion_requests": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "meeting_deletion_artifact_states": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "meeting_deletion_reports": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "retention_policy_snapshots": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "local_purge_tasks": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "meeting_lifecycle_audit_events": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
}


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _maintenance_expression() -> str:
    return "rec_maintenance_allowed()"


def _policy_expression(expression: str) -> str:
    return f"(({expression}) or {_maintenance_expression()})"


def _create_all_policy(table_name: str, expression: str) -> None:
    table = _q(table_name)
    policy = _q(f"{table_name}_tenant_isolation")
    predicate = _policy_expression(expression)
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(
        f"create policy {policy} on {table} "
        f"using ({predicate}) "
        f"with check ({predicate})"
    )


def _drop_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(f"{table_name}_tenant_isolation")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.add_column("meetings", sa.Column("deletion_state", sa.String(length=64), nullable=False, server_default="none"))
    op.add_column("meetings", sa.Column("deletion_requested_at", sa.DateTime(timezone=True)))
    op.add_column("meetings", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.add_column("meetings", sa.Column("retention_delete_after", sa.DateTime(timezone=True)))
    op.add_column(
        "meetings",
        sa.Column("retention_policy_state", sa.String(length=64), nullable=False, server_default="not_configured"),
    )
    op.create_table(
        "retention_policy_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("policy_source", sa.String(length=64), nullable=False),
        sa.Column("meeting_delete_after_days", sa.Integer()),
        sa.Column("backup_expiry_days", sa.Integer()),
        sa.Column("local_buffer_expiry_days", sa.Integer()),
        sa.Column("unsafe_reason", sa.String(length=240)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "meeting_deletion_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("requested_by_device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id")),
        sa.Column("request_source", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("confirmation_boundary", sa.String(length=240), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="requested"),
        sa.Column("policy_snapshot_id", sa.Uuid(), sa.ForeignKey("retention_policy_snapshots.id")),
        sa.Column("failure_reason", sa.String(length=240)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "meeting_deletion_artifact_states",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("deletion_request_id", sa.Uuid(), sa.ForeignKey("meeting_deletion_requests.id"), nullable=False),
        sa.Column("artifact_class", sa.String(length=64), nullable=False),
        sa.Column("control_scope", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="not_started"),
        sa.Column("safe_reason", sa.String(length=240)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "meeting_deletion_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("deletion_request_id", sa.Uuid(), sa.ForeignKey("meeting_deletion_requests.id"), nullable=False),
        sa.Column("overall_state", sa.String(length=64), nullable=False, server_default="requested"),
        sa.Column("summary_label", sa.String(length=160), nullable=False),
        sa.Column("bounded_copy", sa.String(length=500), nullable=False),
        sa.Column("artifact_summary_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("backup_state", sa.String(length=64), nullable=False, server_default="not_applicable"),
        sa.Column("local_purge_state", sa.String(length=64), nullable=False, server_default="not_applicable"),
        sa.Column("external_dependency_state", sa.String(length=64), nullable=False, server_default="not_applicable"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "local_purge_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("deletion_request_id", sa.Uuid(), sa.ForeignKey("meeting_deletion_requests.id"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id"), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="pending"),
        sa.Column("reason_code", sa.String(length=120)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "meeting_lifecycle_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id")),
        sa.Column("deletion_request_id", sa.Uuid(), sa.ForeignKey("meeting_deletion_requests.id")),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id")),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("safe_reason", sa.String(length=240)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    if _is_postgresql():
        for table_name, expression in CONTENT_WORKSPACE_POLICIES.items():
            _create_all_policy(table_name, expression)


def downgrade() -> None:
    if _is_postgresql():
        for table_name in CONTENT_WORKSPACE_POLICIES:
            _drop_policy(table_name)
    for table_name in [
        "meeting_lifecycle_audit_events",
        "local_purge_tasks",
        "meeting_deletion_reports",
        "meeting_deletion_artifact_states",
        "meeting_deletion_requests",
        "retention_policy_snapshots",
    ]:
        op.drop_table(table_name)
    for column_name in [
        "retention_policy_state",
        "retention_delete_after",
        "deleted_at",
        "deletion_requested_at",
        "deletion_state",
    ]:
        op.drop_column("meetings", column_name)
