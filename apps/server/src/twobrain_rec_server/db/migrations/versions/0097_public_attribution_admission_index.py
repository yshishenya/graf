"""Index durable public attribution creation time for admission control.

The public page path has a PostgreSQL-serialized admission guard that counts
new durable attribution rows in a short rolling window. The index keeps that
bounded count independent of the full 90-day retention table (security review
P1, FR-014, FR-058).
"""

from alembic import op

revision: str = "0097_public_attribution_index"
down_revision: str | None = "0096_client_attribution_bridge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_public_visit_attribution_created_at",
        "public_visit_attributions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_public_visit_attribution_created_at",
        table_name="public_visit_attributions",
    )
