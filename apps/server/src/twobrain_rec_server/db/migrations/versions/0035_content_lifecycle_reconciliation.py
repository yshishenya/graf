"""add dispatch reconciliation lease state

Revision ID: 0035_lifecycle_reconcile
Revises: 0034_candidate_expiry
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_lifecycle_reconcile"
down_revision: str | None = "0034_candidate_expiry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PREVIOUS_MAINTENANCE_OPERATIONS = (
    "migration_verification",
    "production_smoke_setup",
    "production_smoke_cleanup",
    "backup_restore_rehearsal",
    "operator_diagnostics",
    "provider_link_cleanup",
    "playback_normalization_inventory",
    "playback_normalization_dispatch",
    "prompt_optimization",
)
MAINTENANCE_OPERATIONS = (
    *PREVIOUS_MAINTENANCE_OPERATIONS,
    "outcome_dispatch_reconciliation",
    "deletion_purge_reconciliation",
)


def _replace_maintenance_helper(operations: tuple[str, ...]) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    operation_literals = ", ".join(f"'{operation}'" for operation in operations)
    op.execute(
        f"""
        create or replace function rec_maintenance_allowed()
        returns boolean
        language sql
        stable
        as $$
            select rec_setting('app.context_kind') = 'maintenance'
            and rec_setting('app.maintenance_operation') = any(array[{operation_literals}])
            and rec_setting('app.maintenance_actor') is not null
            and rec_setting('app.maintenance_reason') is not null
            and rec_setting('app.maintenance_feature_area') is not null
            and session_user = 'twobrain_rec_maintenance'
        $$;
        """
    )


def upgrade() -> None:
    op.add_column(
        "dispatch_intents",
        sa.Column("reconciliation_state", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.add_column("dispatch_intents", sa.Column("last_reconciled_at", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_dispatch_intents_reconciliation",
        "dispatch_intents",
        ["reconciliation_state", "next_attempt_at"],
    )
    _replace_maintenance_helper(MAINTENANCE_OPERATIONS)


def downgrade() -> None:
    _replace_maintenance_helper(PREVIOUS_MAINTENANCE_OPERATIONS)
    op.drop_index("ix_dispatch_intents_reconciliation", table_name="dispatch_intents")
    op.drop_column("dispatch_intents", "last_reconciled_at")
    op.drop_column("dispatch_intents", "reconciliation_state")
