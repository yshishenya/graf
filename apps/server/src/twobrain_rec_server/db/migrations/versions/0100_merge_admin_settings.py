"""Join the system console and released calendar/timezone migration histories."""

revision: str = "0100_merge_admin_settings"
down_revision: tuple[str, str] = (
    "0099_checkout_catalog_admission",
    "0087_merge_calendar_timezone",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
