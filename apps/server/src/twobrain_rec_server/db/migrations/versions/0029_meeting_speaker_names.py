"""meeting-scoped speaker display names

Revision ID: 0029_speaker_names
Revises: 0028_active_space_read
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_speaker_names"
down_revision: str | None = "0028_active_space_read"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MEETING_SPEAKER_TABLES = ("meeting_speaker_names",)


def upgrade() -> None:
    op.create_table(
        "meeting_speaker_names",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("speaker_key", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column(
            "updated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("user_identities.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "meeting_id",
            "speaker_key",
            name="uq_meeting_speaker_names_workspace_meeting_key",
        ),
    )
    op.create_index(
        "ix_meeting_speaker_names_workspace_meeting",
        "meeting_speaker_names",
        ["workspace_id", "meeting_id"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("alter table meeting_speaker_names enable row level security")
        op.execute("alter table meeting_speaker_names force row level security")
        op.execute(
            "create policy meeting_speaker_names_tenant_isolation on meeting_speaker_names "
            "using ((rec_context_kind() = 'request' and workspace_id = rec_current_workspace_id()) "
            "or rec_maintenance_allowed()) "
            "with check ((rec_context_kind() = 'request' and workspace_id = rec_current_workspace_id()) "
            "or rec_maintenance_allowed())"
        )


def downgrade() -> None:
    op.drop_index(
        "ix_meeting_speaker_names_workspace_meeting",
        table_name="meeting_speaker_names",
    )
    op.drop_table("meeting_speaker_names")
