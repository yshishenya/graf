"""Merge the summary-slot and provider-unlink migration heads."""

from collections.abc import Sequence

revision: str = "0078_merge_summary_slots_provider_unlink"
down_revision: tuple[str, str] = (
    "0076_meeting_summary_slots",
    "0077_provider_unlink_xworkspace",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
