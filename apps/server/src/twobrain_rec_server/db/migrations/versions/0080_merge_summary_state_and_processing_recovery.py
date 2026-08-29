"""Merge summary-state and processing-recovery migration heads."""

from collections.abc import Sequence

revision: str = "0080_merge_summary_state_processing_recovery"
down_revision: tuple[str, str] = (
    "0079_summary_state_versions",
    "0078_processing_recovery",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
