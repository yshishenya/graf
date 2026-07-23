"""allow the isolated prompt-optimization operator path

Revision ID: 0033_prompt_opt_maintenance
Revises: 0032_outcome_pointer
Create Date: 2026-07-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0033_prompt_opt_maintenance"
down_revision: str | None = "0032_outcome_pointer"
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
)
PREVIOUS_OPERATIONS = CURRENT_OPERATIONS[:-1]


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
    _replace_maintenance_helper(CURRENT_OPERATIONS)


def downgrade() -> None:
    _replace_maintenance_helper(PREVIOUS_OPERATIONS)
