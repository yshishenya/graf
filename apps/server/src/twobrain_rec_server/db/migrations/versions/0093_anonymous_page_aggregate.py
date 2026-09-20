"""Add the level 1 anonymous page aggregate bucket counter.

The table stores coarse dimensions and a visit counter only. Device address,
session or visit identifier, user-agent string, device fingerprint, cookie
value and any pseudonym are forbidden by contract (FR-010, data-model.md), so
no such column exists here. The aggregate is written by one synchronous
insert-on-conflict statement on the public page path and never depends on the
analytics stack (research.md §2, §3).
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0093_anonymous_page_aggregate"
down_revision: str | None = "0092_recording_origin_cancel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anonymous_page_aggregate_buckets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("bucket_date", sa.Date(), nullable=False),
        sa.Column("bucket_hour", sa.SmallInteger()),
        sa.Column("surface", sa.String(40), nullable=False),
        sa.Column("landing_path", sa.String(200), nullable=False),
        sa.Column("source", sa.String(96)),
        sa.Column("medium", sa.String(96)),
        sa.Column("campaign", sa.String(96)),
        sa.Column("content", sa.String(96)),
        sa.Column("term", sa.String(96)),
        sa.Column("device_class", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("referrer_category", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("traffic_class", sa.String(16), nullable=False, server_default="external"),
        sa.Column("visits", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        # Missing campaign labels are equal for the key: a repeated visit must
        # update its bucket instead of adding a parallel row with NULL labels.
        sa.UniqueConstraint(
            "bucket_date",
            "bucket_hour",
            "surface",
            "landing_path",
            "source",
            "medium",
            "campaign",
            "content",
            "term",
            "device_class",
            "referrer_category",
            "traffic_class",
            name="uq_anonymous_page_aggregate_bucket",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(
            "bucket_hour IS NULL OR (bucket_hour >= 0 AND bucket_hour <= 23)",
            name="aggregate_hour",
        ),
        sa.CheckConstraint(
            "device_class IN ('desktop', 'mobile', 'tablet', 'unknown')",
            name="aggregate_device_class",
        ),
        sa.CheckConstraint(
            "referrer_category IN ('direct', 'organic', 'paid', 'referral', 'unknown')",
            name="aggregate_referrer_category",
        ),
        sa.CheckConstraint(
            "traffic_class IN ('external', 'internal', 'support', 'test', 'automated')",
            name="aggregate_traffic_class",
        ),
        sa.CheckConstraint(
            "visits >= 1",
            name="aggregate_visits",
        ),
    )
    op.create_index(
        "ix_anonymous_aggregate_report",
        "anonymous_page_aggregate_buckets",
        ["bucket_date", "traffic_class"],
    )


def downgrade() -> None:
    op.drop_index("ix_anonymous_aggregate_report", table_name="anonymous_page_aggregate_buckets")
    op.drop_table("anonymous_page_aggregate_buckets")
