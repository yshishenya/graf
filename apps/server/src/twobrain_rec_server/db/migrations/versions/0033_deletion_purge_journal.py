"""add durable controlled-artifact deletion journal

Revision ID: 0033_deletion_purge
Revises: 0032_content_regen_lineage
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_deletion_purge"
down_revision: str | None = "0032_content_regen_lineage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTENT_WORKSPACE_POLICIES = {
    "meeting_purge_journal": (
        "((rec_context_kind() in ('request', 'worker') "
        "and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
    )
}


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table(
        "meeting_purge_journal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("deletion_request_id", sa.Uuid(), sa.ForeignKey("meeting_deletion_requests.id")),
        sa.Column("artifact_class", sa.String(length=64), nullable=False),
        sa.Column("object_key", sa.String(length=1000), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("safe_reason", sa.String(length=240)),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "workspace_id", "meeting_id", "artifact_class", "object_key",
            name="uq_meeting_purge_journal_object",
        ),
    )
    op.create_index("ix_meeting_purge_journal_due", "meeting_purge_journal", ["state", "next_retry_at"])
    if _is_postgresql():
        op.execute("alter table meeting_purge_journal enable row level security")
        op.execute("alter table meeting_purge_journal force row level security")
        op.execute("drop policy if exists meeting_purge_journal_isolation on meeting_purge_journal")
        op.execute(
            "create policy meeting_purge_journal_isolation on meeting_purge_journal "
            "using (((rec_context_kind() in ('request', 'worker') and "
            "workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())) "
            "with check (((rec_context_kind() in ('request', 'worker') and "
            "workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed()))"
        )


def downgrade() -> None:
    if _is_postgresql():
        op.execute("drop policy if exists meeting_purge_journal_isolation on meeting_purge_journal")
        op.execute("alter table meeting_purge_journal no force row level security")
        op.execute("alter table meeting_purge_journal disable row level security")
    op.drop_index("ix_meeting_purge_journal_due", table_name="meeting_purge_journal")
    op.drop_table("meeting_purge_journal")
