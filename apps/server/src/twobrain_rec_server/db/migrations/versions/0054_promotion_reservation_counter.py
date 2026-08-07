"""Persist campaign-level reservation counts for atomic promo caps."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0054_promotion_reservation_counter"
down_revision: str | None = "0053_account_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "promotion_campaigns",
        sa.Column("reserved_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("promotion_campaigns", "reserved_count")
