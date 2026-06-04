"""access placeholders

Revision ID: 0002_access_placeholders
Revises: 0001_ingest_foundation
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_access_placeholders"
down_revision: str | None = "0001_ingest_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("visibility", sa.String(length=64), nullable=False, server_default="owner_only"))
    op.add_column("meetings", sa.Column("share_policy_state", sa.String(length=64), nullable=False, server_default="not_available"))
    op.add_column("meetings", sa.Column("download_policy_state", sa.String(length=64), nullable=False, server_default="not_available"))


def downgrade() -> None:
    op.drop_column("meetings", "download_policy_state")
    op.drop_column("meetings", "share_policy_state")
    op.drop_column("meetings", "visibility")
