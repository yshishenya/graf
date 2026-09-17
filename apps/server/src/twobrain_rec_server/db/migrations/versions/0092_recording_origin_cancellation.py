"""Retain owner-origin cancellations before meeting creation."""

import sqlalchemy as sa
from alembic import op

revision: str = "0092_recording_origin_cancel"
down_revision: str = "0091_comment_reader_projection"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade():
    duplicates = op.get_bind().scalar(sa.text("""
        SELECT 1 FROM local_purge_tasks
        GROUP BY deletion_request_id, device_id, task_type HAVING count(*) > 1 LIMIT 1
    """))
    if duplicates:
        raise RuntimeError("Duplicate local purge tasks require reviewed reconciliation before migration; no deletion evidence was removed")
    op.create_unique_constraint("uq_local_purge_request_device_type", "local_purge_tasks", ["deletion_request_id", "device_id", "task_type"])
    op.create_table(
        "recording_origin_cancellations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("local_recording_id", sa.String(240), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "created_by_user_id", "local_recording_id", name="uq_recording_origin_cancellation"),
    )
    op.execute("ALTER TABLE recording_origin_cancellations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE recording_origin_cancellations FORCE ROW LEVEL SECURITY")
    owner = """rec_context_kind()='request' AND workspace_id=rec_current_workspace_id()
      AND created_by_user_id=rec_current_user_id()
      AND EXISTS (SELECT 1 FROM workspace_memberships wm
        WHERE wm.workspace_id=recording_origin_cancellations.workspace_id
          AND wm.user_id=rec_current_user_id() AND wm.status='active')"""
    op.execute(f"CREATE POLICY origin_cancellation_read ON recording_origin_cancellations FOR SELECT USING ({owner})")
    op.execute(f"CREATE POLICY origin_cancellation_insert ON recording_origin_cancellations FOR INSERT WITH CHECK ({owner})")
    # No UPDATE/DELETE policy: application roles cannot erase an accepted cancellation.


def downgrade():
    raise RuntimeError("Origin cancellation markers must be retained; restore a compatible application instead of dropping deletion truth")
