"""Enforce bounded fair-use review metadata at the database boundary."""

from collections.abc import Sequence

from alembic import op

revision: str = "0069_fair_use_review_constraints"
down_revision: str | None = "0068_fair_use_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_fair_use_review_deadline",
        "fair_use_reviews",
        "review_by <= starts_at + interval '24 hours'",
    )
    op.create_check_constraint(
        "ck_fair_use_review_capability",
        "fair_use_reviews",
        "capability ~ '^[A-Za-z0-9_.:-]{1,64}$'",
    )
    op.create_check_constraint(
        "ck_fair_use_review_evidence_ref",
        "fair_use_reviews",
        "evidence_ref ~ '^[A-Za-z0-9_.:-]{1,160}$'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_fair_use_review_evidence_ref", "fair_use_reviews", type_="check")
    op.drop_constraint("ck_fair_use_review_capability", "fair_use_reviews", type_="check")
    op.drop_constraint("ck_fair_use_review_deadline", "fair_use_reviews", type_="check")
