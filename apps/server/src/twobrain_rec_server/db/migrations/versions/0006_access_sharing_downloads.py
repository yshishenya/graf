"""access sharing downloads

Revision ID: 0006_access_sharing_downloads
Revises: 0005_rls_hardening
Create Date: 2026-06-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_access_sharing_downloads"
down_revision: str | None = "0005_rls_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTENT_CONTEXT = "rec_context_kind() in ('request', 'worker')"
CONTENT_WORKSPACE_POLICIES = {
    "meeting_share_grants": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "meeting_artifact_policies": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "meeting_egress_audit_events": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "export_packages": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
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
    op.create_table(
        "meeting_share_grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("grant_type", sa.String(length=32), nullable=False),
        sa.Column("grantee_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("share_token_hash", sa.String(length=128)),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("revoked_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "workspace_id",
            "meeting_id",
            "grantee_user_id",
            "status",
            name="uq_meeting_share_grants_active_user",
        ),
    )
    op.create_table(
        "meeting_artifact_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("audio_download", sa.String(length=32), nullable=False, server_default="disabled"),
        sa.Column("transcript_download", sa.String(length=32), nullable=False, server_default="disabled"),
        sa.Column("summary_download", sa.String(length=32), nullable=False, server_default="disabled"),
        sa.Column("package_export", sa.String(length=32), nullable=False, server_default="disabled"),
        sa.Column("policy_source", sa.String(length=64), nullable=False, server_default="meeting_default"),
        sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id",
            "meeting_id",
            name="uq_meeting_artifact_policies_workspace_meeting",
        ),
    )
    op.create_table(
        "meeting_egress_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id")),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id")),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("artifact_class", sa.String(length=32)),
        sa.Column("policy_reason", sa.String(length=240)),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "export_packages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="requested"),
        sa.Column("included_artifacts", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("excluded_artifacts", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("manifest_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("byte_length", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ready_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )
    if _is_postgresql():
        for table_name, expression in CONTENT_WORKSPACE_POLICIES.items():
            _create_all_policy(table_name, expression)


def downgrade() -> None:
    if _is_postgresql():
        for table_name in CONTENT_WORKSPACE_POLICIES:
            _drop_policy(table_name)
    for table_name in [
        "export_packages",
        "meeting_egress_audit_events",
        "meeting_artifact_policies",
        "meeting_share_grants",
    ]:
        op.drop_table(table_name)
