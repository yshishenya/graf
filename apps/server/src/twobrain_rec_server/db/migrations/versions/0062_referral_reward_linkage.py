"""Link a referral reward ledger entry to its attribution lifecycle row."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0062_referral_reward_linkage"
down_revision: str | None = "0061_referral_landing_lookup_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "time_credit_ledger_entries",
        sa.Column(
            "referral_attribution_id",
            sa.Uuid(),
            sa.ForeignKey("referral_attributions.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_time_credit_referral_attribution",
        "time_credit_ledger_entries",
        ["referral_attribution_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_time_credit_referral_attribution", table_name="time_credit_ledger_entries")
    op.drop_column("time_credit_ledger_entries", "referral_attribution_id")
