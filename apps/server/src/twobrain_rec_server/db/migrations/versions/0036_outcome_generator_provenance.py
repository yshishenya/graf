"""pin baseline generator configuration provenance

Revision ID: 0036_generator_provenance
Revises: 0035_lifecycle_reconcile
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_generator_provenance"
down_revision: str | None = "0035_lifecycle_reconcile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_meeting_outcome_sets_current_generator",
        "meeting_outcome_sets",
        type_="unique",
    )
    op.add_column(
        "meeting_outcome_sets",
        sa.Column("generator_config_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "meeting_outcome_generation_attempts",
        sa.Column("generator_config_hash", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_meeting_outcome_sets_current_generator_config",
        "meeting_outcome_sets",
        [
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            "processing_result_id",
            "generator_version",
            "generator_config_hash",
        ],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_meeting_outcome_sets_current_generator_config",
        "meeting_outcome_sets",
        type_="unique",
    )
    op.drop_column("meeting_outcome_generation_attempts", "generator_config_hash")
    op.drop_column("meeting_outcome_sets", "generator_config_hash")
    op.create_unique_constraint(
        "uq_meeting_outcome_sets_current_generator",
        "meeting_outcome_sets",
        [
            "workspace_id",
            "meeting_id",
            "media_revision_id",
            "processing_result_id",
            "generator_version",
        ],
    )
