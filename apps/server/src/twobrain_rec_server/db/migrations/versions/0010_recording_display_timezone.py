"""recording display timezone

Revision ID: 0010_recording_display_timezone
Revises: 0009_meeting_outcomes_mvp
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_recording_display_timezone"
down_revision: str | None = "0009_meeting_outcomes_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("recording_display_timezone_offset_minutes", sa.Integer()))


def downgrade() -> None:
    op.drop_column("meetings", "recording_display_timezone_offset_minutes")
