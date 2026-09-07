"""Merge notification inbox with calendar and account settings."""

revision: str = "0088_merge_notifications"
down_revision = ("0087_merge_calendar_timezone", "0086_notification_inbox")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
