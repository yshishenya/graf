"""Merge calendar owner content and account time-zone migrations."""

from collections.abc import Sequence

revision: str = "0087_merge_calendar_timezone"
down_revision: tuple[str, str] = (
    "0086_calendar_owner_content",
    "0086_user_timezone",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
