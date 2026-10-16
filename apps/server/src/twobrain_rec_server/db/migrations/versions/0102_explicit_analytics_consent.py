"""Nullable explicit analytics consent and milestone metadata; no backfill."""

import sqlalchemy as sa
from alembic import op

revision: str = "0102_explicit_analytics_consent"
down_revision: str | None = "0101_storage_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_identities", sa.Column("product_analytics_state", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_identities", "product_analytics_state")
