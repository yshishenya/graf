"""external calendar selected flag

Revision ID: 0013_external_calendar_selection
Revises: 0012_calendar_settings_prefs
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_external_calendar_selection"
down_revision: str | None = "0012_calendar_settings_prefs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "external_calendars",
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "update external_calendars set selected = true, visibility = 'available' "
        "where visibility = 'selected'"
    )
    op.create_index(
        "ix_external_calendars_source_selected",
        "external_calendars",
        ["workspace_id", "calendar_source_id", "selected"],
    )


def downgrade() -> None:
    op.drop_index("ix_external_calendars_source_selected", table_name="external_calendars")
    op.drop_column("external_calendars", "selected")
