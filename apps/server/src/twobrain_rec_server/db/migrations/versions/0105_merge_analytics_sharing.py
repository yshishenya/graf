"""Merge explicit analytics consent and summary-sharing migration heads."""

revision: str = "0105_merge_analytics_sharing"
down_revision: tuple[str, str] = (
    "0102_explicit_analytics_consent",
    "0104_summary_share_scope_cascade",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Alembic applies both sibling branches before recording the merge."""


def downgrade() -> None:
    """Split the merge revision without undoing either sibling branch."""
