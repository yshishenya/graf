"""Store full meeting protocols without rewriting historical outcomes."""

import sqlalchemy as sa
from alembic import op

revision: str = "0088_meeting_protocol"
down_revision = "0087_merge_calendar_timezone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meeting_outcome_sets", sa.Column("protocol_json", sa.JSON(), nullable=True))
    op.alter_column("meeting_outcome_items", "owner_text", existing_type=sa.String(240), type_=sa.Text())
    op.alter_column("meeting_outcome_items", "due_date_text", existing_type=sa.String(120), type_=sa.Text())


def downgrade() -> None:
    # No explicit VARCHAR cast: PostgreSQL must reject overlong values, not truncate them.
    op.alter_column("meeting_outcome_items", "owner_text", existing_type=sa.Text(), type_=sa.String(240))
    op.alter_column("meeting_outcome_items", "due_date_text", existing_type=sa.Text(), type_=sa.String(120))
    op.drop_column("meeting_outcome_sets", "protocol_json")
