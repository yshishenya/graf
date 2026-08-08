"""bound production smoke setup

Revision ID: 0023_production_smoke_setup
Revises: 0022_playback_normalization
Create Date: 2026-07-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0023_production_smoke_setup"
down_revision: str | None = "0022_playback_normalization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PREVIOUS_MAINTENANCE_OPERATIONS = (
    "migration_verification",
    "production_smoke_cleanup",
    "backup_restore_rehearsal",
    "operator_diagnostics",
)
MAINTENANCE_OPERATIONS = (
    *PREVIOUS_MAINTENANCE_OPERATIONS,
    "production_smoke_setup",
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
    _replace_maintenance_helper(MAINTENANCE_OPERATIONS)


def downgrade() -> None:
    _replace_maintenance_helper(PREVIOUS_MAINTENANCE_OPERATIONS)
