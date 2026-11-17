"""add retention scan to the maintenance operation allowlist

Revision ID: 0114_retention_scan_maintenance
Revises: 0113_fair_use_operator_history
Create Date: 2026-11-17
"""

from __future__ import annotations

from importlib import import_module

from alembic import op

revision = "0114_retention_scan_maintenance"
down_revision = "0113_fair_use_operator_history"
branch_labels = None
depends_on = None

PREVIOUS_OPERATIONS = import_module(
    "twobrain_rec_server.db.migrations.versions.0102_summary_sharing"
).CURRENT_OPERATIONS
CURRENT_OPERATIONS = (*PREVIOUS_OPERATIONS, "retention_scan")


def maintenance_allowed_body(operations: tuple[str, ...] = CURRENT_OPERATIONS) -> str:
    """Exact SQL body shared by the migration and the runtime bootstrap check."""

    literals = ",".join(repr(operation) for operation in operations)
    return f"""
    SELECT session_user = 'twobrain_rec_maintenance'
        AND public.rec_setting('app.context_kind') = 'maintenance'
        AND public.rec_setting('app.maintenance_operation') = ANY(ARRAY[{literals}])
        AND public.rec_setting('app.maintenance_actor') IS NOT NULL
        AND public.rec_setting('app.maintenance_reason') IS NOT NULL
        AND public.rec_setting('app.maintenance_feature_area') IS NOT NULL
        OR (session_user = 'twobrain_rec_app' AND public.rec_account_merge_context_valid())
"""


def _replace_maintenance_helper(operations: tuple[str, ...]) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        f"""
        create or replace function public.rec_maintenance_allowed()
        returns boolean
        language sql
        stable
        as $${maintenance_allowed_body(operations)}$$
        """
    )


def upgrade() -> None:
    _replace_maintenance_helper(CURRENT_OPERATIONS)


def downgrade() -> None:
    _replace_maintenance_helper(PREVIOUS_OPERATIONS)
