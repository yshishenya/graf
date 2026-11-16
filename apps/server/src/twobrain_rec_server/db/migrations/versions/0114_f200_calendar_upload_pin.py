"""Keep the accepted calendar attempt on the strict upload session."""

import sqlalchemy as sa
from alembic import op

revision: str = "0114_f200_calendar_upload_pin"
down_revision: str | None = "0113_fair_use_operator_history"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("upload_sessions", sa.Column("calendar_match_attempt_id", sa.Uuid(), nullable=True))


def downgrade():
    op.drop_column("upload_sessions", "calendar_match_attempt_id")
