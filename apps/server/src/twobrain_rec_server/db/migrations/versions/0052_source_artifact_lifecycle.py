"""Persist source retention gates and purge accounting evidence."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0052_source_artifact_lifecycle"
down_revision: str | None = "0051_transient_media_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "track_artifacts",
        sa.Column(
            "source_lifecycle_state",
            sa.String(length=32),
            nullable=False,
            server_default="not_source",
        ),
    )
    for name in (
        "source_transcript_imported_at",
        "source_playback_verified_at",
        "source_retention_purge_due_at",
        "source_purged_at",
    ):
        op.add_column(
            "track_artifacts",
            sa.Column(name, sa.DateTime(timezone=True), nullable=True),
        )
    op.add_column(
        "track_artifacts",
        sa.Column("source_retention_policy_version", sa.String(length=120), nullable=True),
    )
    op.create_check_constraint(
        "track_artifacts_source_lifecycle_state_allowed",
        "track_artifacts",
        "source_lifecycle_state in ('not_source', 'recoverable', 'purge_due', 'purge_pending', 'purged')",
    )
    op.add_column(
        "meeting_purge_journal",
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("meeting_purge_journal", "metadata_json")
    op.drop_constraint(
        "track_artifacts_source_lifecycle_state_allowed",
        "track_artifacts",
        type_="check",
    )
    op.drop_column("track_artifacts", "source_retention_policy_version")
    for name in (
        "source_purged_at",
        "source_retention_purge_due_at",
        "source_playback_verified_at",
        "source_transcript_imported_at",
        "source_lifecycle_state",
    ):
        op.drop_column("track_artifacts", name)
