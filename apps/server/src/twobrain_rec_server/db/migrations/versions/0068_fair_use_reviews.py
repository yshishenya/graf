"""Persist bounded fair-use review state and tenant isolation."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0068_fair_use_reviews"
down_revision: str | None = "0067_referral_bound_attributed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fair_use_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("subject_user_id", sa.Uuid(), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=32), nullable=False),
        sa.Column("evidence_ref", sa.String(length=160), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_by", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="notice"),
        sa.Column("appealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("appeal_ref", sa.String(length=64), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_code", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["subject_user_id"], ["user_identities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "evidence_ref", name="uq_fair_use_review_evidence"),
        sa.CheckConstraint(
            "reason_code in ('automated_bulk', 'resale', 'limit_circumvention', 'security_abuse')",
            name="ck_fair_use_review_reason",
        ),
        sa.CheckConstraint(
            "state in ('notice', 'restricted', 'appealed', 'cleared', 'confirmed')",
            name="ck_fair_use_review_state",
        ),
    )
    op.create_index(
        "ix_fair_use_reviews_workspace_state",
        "fair_use_reviews",
        ["workspace_id", "state", "review_by"],
    )
    op.create_index(
        "ix_fair_use_reviews_subject_state",
        "fair_use_reviews",
        ["subject_user_id", "state"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("alter table fair_use_reviews enable row level security")
        op.execute("alter table fair_use_reviews force row level security")
        op.execute(
            "create policy fair_use_reviews_tenant_isolation on fair_use_reviews "
            "for all using ("
            "(rec_context_kind() in ('request', 'worker') "
            "and workspace_id = rec_current_workspace_id() "
            "and (subject_user_id = rec_current_user_id() "
            "or exists (select 1 from workspaces owner_scope "
            "where owner_scope.id = fair_use_reviews.workspace_id "
            "and owner_scope.owner_user_id = rec_current_user_id()))) "
            "or rec_maintenance_allowed()"
            ") with check ("
            "(rec_context_kind() in ('request', 'worker') "
            "and workspace_id = rec_current_workspace_id() "
            "and subject_user_id = rec_current_user_id()) "
            "or rec_maintenance_allowed()"
            ")"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("drop policy if exists fair_use_reviews_tenant_isolation on fair_use_reviews")
    op.drop_index("ix_fair_use_reviews_subject_state", table_name="fair_use_reviews")
    op.drop_index("ix_fair_use_reviews_workspace_state", table_name="fair_use_reviews")
    op.drop_table("fair_use_reviews")
