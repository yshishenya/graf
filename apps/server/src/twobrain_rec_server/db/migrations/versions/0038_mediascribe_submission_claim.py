"""prevent duplicate provider POSTs after worker retry or crash

Revision ID: 0038_mediascribe_submission_claim
Revises: 0037_candidate_lineage
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_mediascribe_claim"
down_revision: str | None = "0037_candidate_lineage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mediascribe_jobs",
        sa.Column("submission_claim_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "mediascribe_jobs",
        sa.Column("submission_claimed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    connection = op.get_bind()
    active_claims = connection.execute(
        sa.text(
            "SELECT count(*) FROM mediascribe_jobs "
            "WHERE submission_claim_token IS NOT NULL"
        )
    ).scalar_one()
    if active_claims:
        raise RuntimeError(
            "0038 downgrade requires all MediaScribe submission claims to be resolved"
        )
    op.drop_column("mediascribe_jobs", "submission_claimed_at")
    op.drop_column("mediascribe_jobs", "submission_claim_token")
