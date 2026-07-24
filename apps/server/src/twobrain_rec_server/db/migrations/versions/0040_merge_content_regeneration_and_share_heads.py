"""merge the content-regeneration and meeting-share migration heads

Revision ID: 0040_merge_content_regen_share
Revises: 0035_meeting_share_security, 0039_legacy_lineage_backfill
Create Date: 2026-07-24
"""

from collections.abc import Sequence

revision: str = "0040_merge_content_regen_share"
down_revision: tuple[str, str] = (
    "0035_meeting_share_security",
    "0039_legacy_lineage_backfill",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge the two already-applied migration branches."""


def downgrade() -> None:
    """Keep the merge revision reversible without undoing either branch."""
