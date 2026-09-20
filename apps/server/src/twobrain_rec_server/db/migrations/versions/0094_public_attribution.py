"""Add level 2 visit attribution and the client acquisition attribute.

Visit attribution carries campaign labels from a paid click into registration
and stops being usable after 90 days. The client acquisition attribute is the
campaign recorded on the customer record at registration and is the basis of
campaign reporting for level 2 (FR-014, FR-015, FR-016, FR-017).
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0094_public_attribution"
down_revision: str | None = "0093_anonymous_page_aggregate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_visit_attributions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("attribution_ref", sa.String(120), nullable=False, unique=True),
        sa.Column("source", sa.String(96)),
        sa.Column("medium", sa.String(96)),
        sa.Column("campaign", sa.String(96)),
        sa.Column("content", sa.String(96)),
        sa.Column("term", sa.String(96)),
        sa.Column("yclid", sa.String(120)),
        sa.Column("landing_path", sa.String(200), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "expires_at > first_seen_at",
            name="attribution_window",
        ),
        # The 90-day window is a storage rule, not a convention of the writer.
        sa.CheckConstraint(
            "expires_at <= first_seen_at + interval '90 days'",
            name="attribution_max_window",
        ),
        sa.CheckConstraint(
            "yclid IS NULL OR (length(yclid) >= 8 AND length(yclid) <= 120)",
            name="attribution_yclid",
        ),
    )
    op.create_index(
        "ix_public_visit_attribution_expiry", "public_visit_attributions", ["expires_at"]
    )

    op.create_table(
        "client_acquisition_attributes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("source", sa.String(96)),
        sa.Column("medium", sa.String(96)),
        sa.Column("campaign", sa.String(96)),
        sa.Column("content", sa.String(96)),
        sa.Column("term", sa.String(96)),
        sa.Column("yclid", sa.String(120)),
        sa.Column("landing_path", sa.String(200), nullable=False),
        sa.Column(
            "attribution_rule", sa.String(40), nullable=False, server_default="last_non_direct_90d"
        ),
        sa.Column("attribution_confidence", sa.String(16), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "attribution_rule IN ('last_non_direct_90d')",
            name="acquisition_rule",
        ),
        sa.CheckConstraint(
            "attribution_confidence IN ('linked', 'weak', 'unknown')",
            name="acquisition_confidence",
        ),
        sa.UniqueConstraint(
            "account_id", name="uq_client_acquisition_account"
        ),
    )
    op.create_index(
        "ix_client_acquisition_captured", "client_acquisition_attributes", ["captured_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_client_acquisition_captured", table_name="client_acquisition_attributes")
    op.drop_table("client_acquisition_attributes")
    op.drop_index("ix_public_visit_attribution_expiry", table_name="public_visit_attributions")
    op.drop_table("public_visit_attributions")
