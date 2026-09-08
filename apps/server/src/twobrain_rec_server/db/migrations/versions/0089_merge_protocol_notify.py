"""Merge full meeting protocols and notification inbox without rewriting data."""

revision: str = "0089_merge_protocol_notify"
down_revision = ("0088_meeting_protocol", "0088_merge_notifications")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
