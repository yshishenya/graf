"""mediascribe result contract metadata

Revision ID: 0018_mediascribe_result
Revises: 0017_meeting_detection
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_mediascribe_result"
down_revision: str | None = "0017_meeting_detection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.add_column("processing_results", sa.Column("failure_reason", sa.String(length=240), nullable=True))
    op.add_column("processing_results", sa.Column("failure_source", sa.String(length=64), nullable=True))
    op.add_column("meeting_outcome_sets", sa.Column("failure_source", sa.String(length=64), nullable=True))
    op.add_column("meeting_outcome_generation_attempts", sa.Column("failure_source", sa.String(length=64), nullable=True))


def downgrade() -> None:
    if _is_postgresql():
        op.drop_column("meeting_outcome_generation_attempts", "failure_source")
        op.drop_column("meeting_outcome_sets", "failure_source")
        op.drop_column("processing_results", "failure_source")
        op.drop_column("processing_results", "failure_reason")
        return
    with op.batch_alter_table("meeting_outcome_generation_attempts") as batch_op:
        batch_op.drop_column("failure_source")
    with op.batch_alter_table("meeting_outcome_sets") as batch_op:
        batch_op.drop_column("failure_source")
    with op.batch_alter_table("processing_results") as batch_op:
        batch_op.drop_column("failure_source")
        batch_op.drop_column("failure_reason")
