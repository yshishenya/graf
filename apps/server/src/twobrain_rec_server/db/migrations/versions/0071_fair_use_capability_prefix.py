"""Align the fair-use capability database boundary with application validation."""

from collections.abc import Sequence

from alembic import op

revision: str = "0071_fair_use_capability_prefix"
down_revision: str | None = "0070_fair_use_review_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_fair_use_review_capability", "fair_use_reviews", type_="check")
    op.create_check_constraint(
        "ck_fair_use_review_capability",
        "fair_use_reviews",
        "capability ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_fair_use_review_capability", "fair_use_reviews", type_="check")
    op.create_check_constraint(
        "ck_fair_use_review_capability",
        "fair_use_reviews",
        "capability ~ '^[A-Za-z0-9_.:-]{1,64}$'",
    )
