"""recording sync transcription loop

Revision ID: 0008_recording_sync_loop
Revises: 0007_retention_deletion_exec
Create Date: 2026-06-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_recording_sync_loop"
down_revision: str | None = "0007_retention_deletion_exec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTENT_WORKSPACE_POLICIES = {
    "media_revisions": "((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
}

REVISION_LINKED_TABLES = [
    "upload_sessions",
    "temporary_upload_objects",
    "track_artifacts",
    "manifest_snapshots",
    "ingest_audit_events",
    "processing_workflows",
    "mediascribe_jobs",
    "processing_results",
    "processing_dependency_states",
]


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _create_media_revision_policy() -> None:
    table = _q("media_revisions")
    policy = _q("media_revisions_tenant_isolation")
    predicate = CONTENT_WORKSPACE_POLICIES["media_revisions"]
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(
        f"create policy {policy} on {table} "
        f"using ({predicate}) "
        f"with check ({predicate})"
    )


def _drop_media_revision_policy() -> None:
    table = _q("media_revisions")
    policy = _q("media_revisions_tenant_isolation")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def _media_revision_id_column() -> sa.Column:
    return sa.Column("media_revision_id", sa.Uuid(), sa.ForeignKey("media_revisions.id"))


def _add_media_revision_id_column(table_name: str) -> None:
    if _is_postgresql():
        op.add_column(table_name, _media_revision_id_column())
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(_media_revision_id_column())


def _drop_media_revision_id_column(table_name: str) -> None:
    if _is_postgresql():
        op.drop_column(table_name, "media_revision_id")
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_column("media_revision_id")


def upgrade() -> None:
    op.create_table(
        "media_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("local_media_revision_id", sa.String(length=300), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_kind", sa.String(length=64), nullable=False, server_default="initial_recording"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="pending_upload"),
        sa.Column("manifest_sha256", sa.String(length=64)),
        sa.Column("track_sha256_by_role", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("immutable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "meeting_id", "revision_number", name="uq_media_revisions_workspace_meeting_revision"),
        sa.UniqueConstraint("workspace_id", "local_media_revision_id", name="uq_media_revisions_workspace_local_revision"),
    )
    for table_name in REVISION_LINKED_TABLES:
        _add_media_revision_id_column(table_name)
    if _is_postgresql():
        _create_media_revision_policy()


def downgrade() -> None:
    if _is_postgresql():
        _drop_media_revision_policy()
    for table_name in reversed(REVISION_LINKED_TABLES):
        _drop_media_revision_id_column(table_name)
    op.drop_table("media_revisions")
