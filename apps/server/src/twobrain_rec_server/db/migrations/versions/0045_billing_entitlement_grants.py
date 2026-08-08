"""append-only provider-confirmed billing entitlement grants

Revision ID: 0045_billing_entitlement_grants
Revises: 0044_user_account_billing
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045_billing_entitlement_grants"
down_revision: str | None = "0044_user_account_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "billing_entitlement_grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("billing_invoices.id"), nullable=False),
        sa.Column("provider_payment_id", sa.String(160), nullable=False),
        sa.Column("plan_code", sa.String(32), nullable=False),
        sa.Column("cycle", sa.String(16), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("source", sa.String(40), nullable=False, server_default="provider_confirmed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "invoice_id", name="uq_billing_entitlement_grant_invoice"),
    )
    op.create_index(
        "ix_billing_entitlement_grants_workspace_period",
        "billing_entitlement_grants",
        ["workspace_id", "starts_at", "ends_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("alter table billing_entitlement_grants enable row level security")
        op.execute("alter table billing_entitlement_grants force row level security")
        op.execute("create policy billing_entitlement_grants_tenant_isolation on billing_entitlement_grants using ((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed()) with check ((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("drop policy if exists billing_entitlement_grants_tenant_isolation on billing_entitlement_grants")
        op.execute("alter table billing_entitlement_grants no force row level security")
        op.execute("alter table billing_entitlement_grants disable row level security")
    op.drop_index("ix_billing_entitlement_grants_workspace_period", table_name="billing_entitlement_grants")
    op.drop_table("billing_entitlement_grants")
