"""allow the maintenance worker to reconcile queued calendar syncs"""

from collections.abc import Sequence

from alembic import op

revision: str = "0075_calendar_sync_maintenance"
down_revision: str | None = "0074_linked_workspace_proofs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENT_OPERATIONS = (
    "migration_verification",
    "production_smoke_setup",
    "production_smoke_cleanup",
    "backup_restore_rehearsal",
    "operator_diagnostics",
    "provider_link_cleanup",
    "playback_normalization_inventory",
    "playback_normalization_dispatch",
    "prompt_optimization",
    "outcome_dispatch_reconciliation",
    "deletion_purge_reconciliation",
    "processing_legacy_lineage_reconciliation",
    "outcome_initial_baseline_reconciliation",
    "billing_reconciliation",
    "billing_notification_reconciliation",
    "account_merge",
    "calendar_sync_reconciliation",
)
PREVIOUS_OPERATIONS = CURRENT_OPERATIONS[:-1]


def _replace_maintenance_helper(operations: tuple[str, ...]) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    literals = ", ".join(f"'{operation}'" for operation in operations)
    op.execute(
        f"""
        create or replace function rec_maintenance_allowed()
        returns boolean
        language sql
        stable
        as $$
            select session_user = 'twobrain_rec_maintenance'
            and rec_setting('app.context_kind') = 'maintenance'
            and rec_setting('app.maintenance_operation') = any(array[{literals}])
            and rec_setting('app.maintenance_actor') is not null
            and rec_setting('app.maintenance_reason') is not null
            and rec_setting('app.maintenance_feature_area') is not null
            or (
                session_user = 'twobrain_rec_app'
                and rec_account_merge_context_valid()
            )
        $$;
        """
    )


def upgrade() -> None:
    _replace_maintenance_helper(CURRENT_OPERATIONS)


def downgrade() -> None:
    _replace_maintenance_helper(PREVIOUS_OPERATIONS)
