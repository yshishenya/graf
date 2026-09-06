"""Remove the obsolete internal billing launch-gate registry."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0079_remove_billing_launch_gates"
down_revision: str | None = "0078_processing_recovery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("billing_launch_gates")


def downgrade() -> None:
    op.create_table(
        "billing_launch_gates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("environment", sa.String(16), nullable=False),
        sa.Column("shop_id_hash", sa.String(64), nullable=False),
        sa.Column("deployment_sha", sa.String(64), nullable=False),
        sa.Column("gate_key", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("evidence_ref", sa.String(160), nullable=False),
        sa.Column("owner_role", sa.String(64), nullable=False),
        sa.Column("approver_ref", sa.String(120), nullable=False),
        sa.Column("executor_ref", sa.String(120), nullable=False),
        sa.Column("values_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "environment",
            "shop_id_hash",
            "deployment_sha",
            "gate_key",
            "version",
            name="uq_billing_launch_gates_identity",
        ),
        sa.CheckConstraint("version > 0", name="ck_billing_launch_gates_version"),
        sa.CheckConstraint("status in ('approved', 'rejected')", name="ck_billing_launch_gates_status"),
        sa.CheckConstraint("approved_at < valid_until", name="ck_billing_launch_gates_validity"),
        sa.CheckConstraint("approver_ref <> executor_ref", name="ck_billing_launch_gates_four_eyes"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("alter table billing_launch_gates enable row level security")
        op.execute("alter table billing_launch_gates force row level security")
        op.execute(
            "create policy billing_launch_gates_read on billing_launch_gates for select "
            "using (rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed())"
        )
        op.execute(
            "create policy billing_launch_gates_write on billing_launch_gates for all "
            "using (rec_maintenance_allowed()) with check (rec_maintenance_allowed())"
        )
