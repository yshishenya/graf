"""Default new media revisions to canonical recordings without rewriting history."""

import sqlalchemy as sa
from alembic import op

revision: str = "0099_single_source_revision"
down_revision = "0098_single_source_job_default"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("media_revisions") as batch:
        batch.alter_column(
            "source_kind", existing_type=sa.String(64),
            existing_nullable=False, server_default="initial_mixed_recording",
        )


def downgrade() -> None:
    with op.batch_alter_table("media_revisions") as batch:
        batch.alter_column(
            "source_kind", existing_type=sa.String(64),
            existing_nullable=False, server_default="initial_recording",
        )
