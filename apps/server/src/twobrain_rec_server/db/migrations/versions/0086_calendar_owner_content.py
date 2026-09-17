"""Preserve complete owner calendar text without narrowing on rollback."""

import sqlalchemy as sa
from alembic import op

revision: str = "0086_calendar_owner_content"
down_revision: str = "0085_merge_summary_mediascribe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, columns in {
        "calendar_sources": ("provider_label",),
        "external_calendars": ("display_label", "owner_display_name"),
        "calendar_event_snapshots": ("title", "description", "location"),
        "calendar_participants": ("display_name",),
    }.items():
        for column in columns:
            op.alter_column(table, column, type_=sa.Text())


def downgrade() -> None:
    # Text is backward-compatible with the previous ORM String fields. Keep
    # widened columns so rollback never truncates already imported owner data.
    pass
