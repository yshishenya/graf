"""operator-created promotion campaigns and invoice-bound reservations

Revision ID: 0046_billing_promotions
Revises: 0045_billing_entitlement_grants
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0046_billing_promotions"
down_revision: str | None = "0045_billing_entitlement_grants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tenant_policy(table_name: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"alter table {table_name} enable row level security")
    op.execute(f"alter table {table_name} force row level security")
    op.execute(
        f"create policy {table_name}_tenant_isolation on {table_name} "
        "using ((rec_context_kind() in ('request', 'worker') "
        "and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed()) "
        "with check ((rec_context_kind() in ('request', 'worker') "
        "and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
    )


def _global_policy(table_name: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"alter table {table_name} enable row level security")
    op.execute(f"alter table {table_name} force row level security")
    op.execute(
        f"create policy {table_name}_global_access on {table_name} "
        "using (rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed()) "
        "with check (rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed())"
    )


def upgrade() -> None:
    op.create_table(
        "promotion_campaigns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("campaign_version", sa.String(64), nullable=False),
        sa.Column("plan_code", sa.String(32), nullable=False),
        sa.Column("cycle", sa.String(16)),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("max_redemptions", sa.Integer(), nullable=False),
        sa.Column("redeemed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("policy_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code_hash", name="uq_promotion_campaigns_code_hash"),
    )
    op.create_table(
        "promotion_redemptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("campaign_id", sa.Uuid(), sa.ForeignKey("promotion_campaigns.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("billing_invoices.id"), nullable=False),
        sa.Column("reservation_key", sa.String(240), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("list_amount_minor", sa.Integer(), nullable=False),
        sa.Column("payable_amount_minor", sa.Integer(), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False, server_default="reserved"),
        sa.Column("reserved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("redeemed_at", sa.DateTime(timezone=True)),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "workspace_id",
            "reservation_key",
            name="uq_promotion_redemptions_workspace_reservation_key",
        ),
        sa.UniqueConstraint("workspace_id", "campaign_id", name="uq_promotion_redemptions_workspace_campaign"),
    )
    op.create_index("ix_promotion_redemptions_invoice", "promotion_redemptions", ["invoice_id"])
    _global_policy("promotion_campaigns")
    _tenant_policy("promotion_redemptions")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in ("promotion_redemptions", "promotion_campaigns"):
            op.execute(f"drop policy if exists {table}_tenant_isolation on {table}")
            op.execute(f"drop policy if exists {table}_global_access on {table}")
            op.execute(f"alter table {table} no force row level security")
            op.execute(f"alter table {table} disable row level security")
    op.drop_index("ix_promotion_redemptions_invoice", table_name="promotion_redemptions")
    op.drop_table("promotion_redemptions")
    op.drop_table("promotion_campaigns")
