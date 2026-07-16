"""allow maintenance cleanup of expired provider link intents

Revision ID: 0025_provider_link_cleanup_maintenance
Revises: 0024_provider_link_verified_callback
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0025_provider_link_cleanup_maintenance"
down_revision: str | None = "0024_provider_link_verified_callback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENT_OPERATIONS = (
    "migration_verification",
    "production_smoke_setup",
    "production_smoke_cleanup",
    "backup_restore_rehearsal",
    "operator_diagnostics",
    "playback_normalization_inventory",
    "playback_normalization_dispatch",
    "provider_link_cleanup",
)
PREVIOUS_OPERATIONS = CURRENT_OPERATIONS[:-1]


def _replace_maintenance_helper(operations: tuple[str, ...]) -> None:
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
    if op.get_bind().dialect.name == "postgresql":
        _replace_maintenance_helper(CURRENT_OPERATIONS)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        _replace_maintenance_helper(PREVIOUS_OPERATIONS)
