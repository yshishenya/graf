"""add personal workspaces and explicit join offers

Revision ID: 0027_workspace_onboarding
Revises: 0026_active_cleanup
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_workspace_onboarding"
down_revision: str | None = "0026_active_cleanup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_workspace_policy(*, allow_personal_creation: bool) -> None:
    personal_creation = (
        """
        or (
            rec_context_kind() = 'auth_bootstrap'
            and organization_id = rec_current_organization_id()
            and kind = 'personal'
            and owner_user_id = rec_current_user_id()
        )
        """
        if allow_personal_creation
        else ""
    )
    op.execute("drop policy if exists workspaces_tenant_isolation on workspaces")
    op.execute(
        f"""
        create policy workspaces_tenant_isolation on workspaces
        using (
            (
                rec_context_kind() in ('request', 'auth_public', 'auth_bootstrap')
                and id = rec_current_workspace_id()
            )
            {personal_creation}
            or rec_maintenance_allowed()
        )
        with check (
            (
                rec_context_kind() in ('request', 'auth_public', 'auth_bootstrap')
                and id = rec_current_workspace_id()
            )
            {personal_creation}
            or rec_maintenance_allowed()
        )
        """
    )


def _replace_membership_policy(*, allow_personal_creation: bool) -> None:
    personal_creation = (
        """
        or (
            rec_context_kind() = 'auth_bootstrap'
            and user_id = rec_current_user_id()
            and exists (
                select 1 from workspaces personal_workspace
                where personal_workspace.id = workspace_memberships.workspace_id
                  and personal_workspace.organization_id = rec_current_organization_id()
                  and personal_workspace.kind = 'personal'
                  and personal_workspace.owner_user_id = rec_current_user_id()
            )
        )
        """
        if allow_personal_creation
        else ""
    )
    op.execute("drop policy if exists workspace_memberships_tenant_isolation on workspace_memberships")
    op.execute(
        f"""
        create policy workspace_memberships_tenant_isolation on workspace_memberships
        using (
            (
                rec_context_kind() in ('request', 'auth_bootstrap')
                and workspace_id = rec_current_workspace_id()
                and user_id = rec_current_user_id()
            )
            {personal_creation}
            or rec_maintenance_allowed()
        )
        with check (
            (
                rec_context_kind() in ('request', 'auth_bootstrap')
                and workspace_id = rec_current_workspace_id()
                and user_id = rec_current_user_id()
            )
            {personal_creation}
            or rec_maintenance_allowed()
        )
        """
    )


def _create_join_offer_policy() -> None:
    predicate = """
        (
            rec_context_kind() = 'request'
            and user_id = rec_current_user_id()
            and rec_current_user_has_active_workspace_membership()
        )
        or rec_maintenance_allowed()
    """
    op.execute("alter table workspace_join_offers enable row level security")
    op.execute("alter table workspace_join_offers force row level security")
    op.execute("drop policy if exists workspace_join_offers_tenant_isolation on workspace_join_offers")
    op.execute(
        "create policy workspace_join_offers_tenant_isolation on workspace_join_offers "
        f"using ({predicate}) with check ({predicate})"
    )


def upgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.add_column(
            sa.Column("kind", sa.String(length=32), nullable=False, server_default="corporate")
        )
        batch_op.add_column(
            sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=True)
        )
    op.create_index(
        "uq_workspaces_personal_owner",
        "workspaces",
        ["organization_id", "owner_user_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'personal'"),
    )
    op.create_table(
        "workspace_join_offers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("invitation_id", sa.Uuid(), sa.ForeignKey("workspace_invitations.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="offered"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "invitation_id", name="uq_workspace_join_offers_user_invitation"),
    )
    op.create_index(
        "ix_workspace_join_offers_user_status",
        "workspace_join_offers",
        ["user_id", "status"],
    )
    _replace_workspace_policy(allow_personal_creation=True)
    _replace_membership_policy(allow_personal_creation=True)
    _create_join_offer_policy()


def downgrade() -> None:
    op.execute("drop policy if exists workspace_join_offers_tenant_isolation on workspace_join_offers")
    op.execute("alter table workspace_join_offers no force row level security")
    op.execute("alter table workspace_join_offers disable row level security")
    _replace_membership_policy(allow_personal_creation=False)
    _replace_workspace_policy(allow_personal_creation=False)
    op.drop_index("ix_workspace_join_offers_user_status", table_name="workspace_join_offers")
    op.drop_table("workspace_join_offers")
    op.drop_index("uq_workspaces_personal_owner", table_name="workspaces")
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.drop_column("owner_user_id")
        batch_op.drop_column("kind")
