"""Close the fair-use review metadata boundary at the database layer."""

from collections.abc import Sequence

from alembic import op

revision: str = "0070_fair_use_review_metadata"
down_revision: str | None = "0069_fair_use_review_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_REVIEW_WINDOW = "review_by >= starts_at and review_by <= starts_at + interval '24 hours'"
_SAFE_EVIDENCE_REF = "evidence_ref !~* '(meeting|content|email|card|token|payload)'"


def upgrade() -> None:
    # Replace the deployed upper-bound-only check while preserving its stable
    # constraint name for ORM/schema consumers.
    op.drop_constraint("ck_fair_use_review_deadline", "fair_use_reviews", type_="check")
    op.create_check_constraint(
        "ck_fair_use_review_deadline",
        "fair_use_reviews",
        _REVIEW_WINDOW,
    )
    op.create_check_constraint(
        "ck_fair_use_review_evidence_safe",
        "fair_use_reviews",
        _SAFE_EVIDENCE_REF,
    )


def downgrade() -> None:
    op.drop_constraint("ck_fair_use_review_evidence_safe", "fair_use_reviews", type_="check")
    op.drop_constraint("ck_fair_use_review_deadline", "fair_use_reviews", type_="check")
    op.create_check_constraint(
        "ck_fair_use_review_deadline",
        "fair_use_reviews",
        "review_by <= starts_at + interval '24 hours'",
    )
