"""Default new provider jobs to single-file submission; retain historical rows."""

import sqlalchemy as sa
from alembic import op

revision: str = "0098_single_source_job_default"
down_revision = "0097_public_attribution_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("mediascribe_jobs") as batch:
        batch.alter_column(
            "request_mode",
            existing_type=sa.String(64),
            existing_nullable=False,
            server_default="single_track",
        )


def downgrade() -> None:
    with op.batch_alter_table("mediascribe_jobs") as batch:
        batch.alter_column(
            "request_mode",
            existing_type=sa.String(64),
            existing_nullable=False,
            server_default="dual_track",
        )
