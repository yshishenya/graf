"""verified provider link callback

Revision ID: 0024_provider_link_callback
Revises: 0023_production_smoke_setup
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_provider_link_callback"
down_revision: str | None = "0023_production_smoke_setup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _link_state_policy() -> str:
    return """
        ((rec_context_kind() in ('request', 'auth_bootstrap')
          and workspace_id = rec_current_workspace_id()
          and initiating_user_id = rec_current_user_id())
         or (rec_context_kind() = 'auth_callback_lookup'
             and exists (
                 select 1 from auth_callback_states callback_state
                 where callback_state.id = workspace_provider_link_states.callback_state_id
                   and callback_state.state_nonce = rec_auth_callback_state_nonce()))
         or rec_maintenance_allowed())
    """


def upgrade() -> None:
    with op.batch_alter_table("workspace_provider_link_states") as batch_op:
        batch_op.add_column(sa.Column("initiating_auth_session_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("callback_state_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("candidate_provider", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("candidate_display_name", sa.String(length=240), nullable=True))
        batch_op.add_column(sa.Column("callback_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_workspace_provider_link_states_initiating_auth_session",
            "auth_sessions",
            ["initiating_auth_session_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_workspace_provider_link_states_callback_state",
            "auth_callback_states",
            ["callback_state_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_workspace_provider_link_states_callback_state", ["callback_state_id"]
        )
    op.create_index(
        "ix_workspace_provider_link_states_expiry",
        "workspace_provider_link_states",
        ["expires_at"],
    )
    if not _is_postgresql():
        return
    op.execute('drop policy if exists "workspace_provider_link_states_tenant_isolation" on "workspace_provider_link_states"')
    op.execute(
        'create policy "workspace_provider_link_states_tenant_isolation" '
        'on "workspace_provider_link_states" using (' + _link_state_policy() + ') '
        'with check (' + _link_state_policy() + ')'
    )


def downgrade() -> None:
    if _is_postgresql():
        legacy_policy = """
            ((rec_context_kind() in ('request', 'auth_bootstrap')
              and workspace_id = rec_current_workspace_id()
              and initiating_user_id = rec_current_user_id())
             or rec_maintenance_allowed())
        """
        op.execute('drop policy if exists "workspace_provider_link_states_tenant_isolation" on "workspace_provider_link_states"')
        op.execute(
            'create policy "workspace_provider_link_states_tenant_isolation" '
            'on "workspace_provider_link_states" using (' + legacy_policy + ') '
            'with check (' + legacy_policy + ')'
        )
    op.drop_index("ix_workspace_provider_link_states_expiry", table_name="workspace_provider_link_states")
    with op.batch_alter_table("workspace_provider_link_states") as batch_op:
        batch_op.drop_constraint("uq_workspace_provider_link_states_callback_state", type_="unique")
        batch_op.drop_constraint("fk_workspace_provider_link_states_callback_state", type_="foreignkey")
        batch_op.drop_constraint("fk_workspace_provider_link_states_initiating_auth_session", type_="foreignkey")
        batch_op.drop_column("confirmed_at")
        batch_op.drop_column("callback_verified_at")
        batch_op.drop_column("candidate_display_name")
        batch_op.drop_column("candidate_provider")
        batch_op.drop_column("callback_state_id")
        batch_op.drop_column("initiating_auth_session_id")
