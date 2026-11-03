"""Keep the coarse region in the complete anonymous aggregate bucket key."""

import sqlalchemy as sa
from alembic import op

revision: str = "0105_anonymous_aggregate_region"
down_revision: str | None = "0104_summary_share_scope_cascade"
branch_labels = None
depends_on = None

TABLE = "anonymous_page_aggregate_buckets"
CONSTRAINT = "uq_anonymous_page_aggregate_bucket"
PREVIOUS_KEY = [
    "bucket_date", "bucket_hour", "surface", "landing_path", "source", "medium",
    "campaign", "content", "term", "device_class", "referrer_category", "traffic_class",
]


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("region", sa.String(7), nullable=False, server_default="unknown"))
    op.create_check_constraint("aggregate_region", TABLE, "region IN ('ru', 'non_ru', 'unknown')")
    op.drop_constraint(CONSTRAINT, TABLE, type_="unique")
    op.create_unique_constraint(
        CONSTRAINT, TABLE, [*PREVIOUS_KEY, "region"], postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    # Hold the table lock through the guard and schema change: a concurrent
    # region insert must not slip in after the check and be silently merged.
    op.execute(sa.text(f"LOCK TABLE {TABLE} IN ACCESS EXCLUSIVE MODE"))
    op.execute(sa.text(f"""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM {TABLE} WHERE region <> 'unknown') THEN
                RAISE EXCEPTION '0105 downgrade blocked: nonunknown aggregate region';
            END IF;
        END $$;
    """))
    op.drop_constraint(CONSTRAINT, TABLE, type_="unique")
    op.create_unique_constraint(CONSTRAINT, TABLE, PREVIOUS_KEY, postgresql_nulls_not_distinct=True)
    op.drop_constraint("aggregate_region", TABLE, type_="check")
    op.drop_column(TABLE, "region")
