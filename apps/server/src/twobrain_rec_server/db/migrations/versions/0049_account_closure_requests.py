"""Persist account-close cooling and finalization state."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0049_account_closure_requests"
down_revision: str | None = "0048_billing_notification_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_closure_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column(
            "requested_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("user_identities.id"),
            nullable=False,
        ),
        sa.Column("request_key", sa.String(160), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column(
            "policy_version", sa.String(64), nullable=False, server_default="account-close-v1"
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finalize_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True)),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.String(240)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.UniqueConstraint(
            "workspace_id",
            "requested_by_user_id",
            "request_key",
            name="uq_account_closure_request_key",
        ),
    )
    op.create_index(
        "ix_account_closure_due",
        "account_closure_requests",
        ["state", "finalize_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("alter table account_closure_requests enable row level security")
        op.execute("alter table account_closure_requests force row level security")
        op.execute(
            "create policy account_closure_requests_owner on account_closure_requests "
            "using (requested_by_user_id = rec_current_user_id() or rec_maintenance_allowed()) "
            "with check (requested_by_user_id = rec_current_user_id() or rec_maintenance_allowed())"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "drop policy if exists account_closure_requests_owner "
            "on account_closure_requests"
        )
        op.execute("alter table account_closure_requests no force row level security")
        op.execute("alter table account_closure_requests disable row level security")
    op.drop_index("ix_account_closure_due", table_name="account_closure_requests")
    op.drop_table("account_closure_requests")
