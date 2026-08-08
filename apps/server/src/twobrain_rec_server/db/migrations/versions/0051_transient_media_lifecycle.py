"""Persist explicit no-archive admission and bounded transient-media lifetime."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0051_transient_media_lifecycle"
down_revision: str | None = "0050_referral_token_lookup_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "upload_sessions",
        sa.Column("archive_audio", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "processing_workflows",
        sa.Column("archive_audio", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "processing_workflows",
        sa.Column(
            "transient_state",
            sa.String(length=32),
            nullable=False,
            server_default="not_applicable",
        ),
    )
    for name in (
        "transient_admitted_at",
        "transient_terminal_at",
        "transient_purge_due_at",
        "transient_hard_deadline",
        "transient_purged_at",
    ):
        op.add_column(
            "processing_workflows",
            sa.Column(name, sa.DateTime(timezone=True), nullable=True),
        )
    op.create_check_constraint(
        "processing_workflows_transient_state_allowed",
        "processing_workflows",
        "transient_state in ('not_applicable', 'admitted', 'processing', 'terminal', 'purge_due', 'purged')",
    )
    op.create_check_constraint(
        "processing_workflows_transient_mode_facts",
        "processing_workflows",
        "(archive_audio = true and transient_state = 'not_applicable') or "
        "(archive_audio = false and transient_state <> 'not_applicable')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "processing_workflows_transient_mode_facts", "processing_workflows", type_="check"
    )
    op.drop_constraint(
        "processing_workflows_transient_state_allowed", "processing_workflows", type_="check"
    )
    for name in (
        "transient_purged_at",
        "transient_hard_deadline",
        "transient_purge_due_at",
        "transient_terminal_at",
        "transient_admitted_at",
        "transient_state",
        "archive_audio",
    ):
        op.drop_column("processing_workflows", name)
    op.drop_column("upload_sessions", "archive_audio")
