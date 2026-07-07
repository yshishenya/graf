"""single track media upload provenance

Revision ID: 0016_single_track_media_upload
Revises: 0015_external_calendar_selection
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_single_track_media_upload"
down_revision: str | None = "0015_external_calendar_selection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if _is_postgresql():
        op.add_column(
            "mediascribe_jobs",
            sa.Column("source_track_artifact_id", sa.Uuid(), sa.ForeignKey("track_artifacts.id"), nullable=True),
        )
        op.alter_column(
            "mediascribe_jobs",
            "mic_track_artifact_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
        op.alter_column(
            "mediascribe_jobs",
            "incoming_track_artifact_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
        return
    with op.batch_alter_table("mediascribe_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("source_track_artifact_id", sa.Uuid(), sa.ForeignKey("track_artifacts.id"), nullable=True)
        )
        batch_op.alter_column("mic_track_artifact_id", existing_type=sa.Uuid(), nullable=True)
        batch_op.alter_column("incoming_track_artifact_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.execute(
        "update mediascribe_jobs set mic_track_artifact_id = source_track_artifact_id "
        "where mic_track_artifact_id is null and source_track_artifact_id is not null"
    )
    op.execute(
        "update mediascribe_jobs set incoming_track_artifact_id = source_track_artifact_id "
        "where incoming_track_artifact_id is null and source_track_artifact_id is not null"
    )
    if _is_postgresql():
        op.alter_column(
            "mediascribe_jobs",
            "incoming_track_artifact_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
        op.alter_column(
            "mediascribe_jobs",
            "mic_track_artifact_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
        op.drop_column("mediascribe_jobs", "source_track_artifact_id")
        return
    with op.batch_alter_table("mediascribe_jobs") as batch_op:
        batch_op.alter_column("incoming_track_artifact_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.alter_column("mic_track_artifact_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.drop_column("source_track_artifact_id")
