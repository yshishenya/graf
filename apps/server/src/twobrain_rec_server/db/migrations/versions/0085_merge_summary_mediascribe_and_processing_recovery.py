"""Merge the summary and processing-recovery migration heads."""

from collections.abc import Sequence

revision: str = "0085_merge_summary_mediascribe"
down_revision: tuple[str, str] = (
    "0083_merge_summary_mediascribe",
    "0084_processing_recovery",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
