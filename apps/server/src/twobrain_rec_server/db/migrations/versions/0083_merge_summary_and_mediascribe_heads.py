"""Merge the summary lifecycle and current master migration heads."""

from collections.abc import Sequence

revision: str = "0083_merge_summary_mediascribe"
down_revision: tuple[str, str] | None = (
    "0080_merge_summary_state_processing_recovery",
    "0082_mediascribe_words",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
