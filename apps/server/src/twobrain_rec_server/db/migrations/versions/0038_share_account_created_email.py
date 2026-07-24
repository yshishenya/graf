"""support invitation magic-link bootstrap notification"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_share_account_created_email"
down_revision: str | None = "0037_auth_rate_limit_buckets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "meeting_share_invitations",
        sa.Column("encrypted_recipient_address", sa.String(), nullable=True),
    )
    op.add_column(
        "meeting_share_invitations",
        sa.Column(
            "account_created_email_status",
            sa.String(length=32),
            nullable=False,
            server_default="not_applicable",
        ),
    )
    op.add_column(
        "meeting_share_invitations",
        sa.Column("account_created_email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "meeting_share_invitations",
        sa.Column("account_created_email_failure_code", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meeting_share_invitations", "account_created_email_failure_code")
    op.drop_column("meeting_share_invitations", "account_created_email_sent_at")
    op.drop_column("meeting_share_invitations", "account_created_email_status")
    op.drop_column("meeting_share_invitations", "encrypted_recipient_address")
