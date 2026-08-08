"""allow bounded active-space membership lookup

Revision ID: 0028_active_space_read
Revises: 0027_workspace_onboarding
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0028_active_space_read"
down_revision: str | None = "0027_workspace_onboarding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_membership_policy(*, allow_active_space_read: bool) -> None:
    active_space_read = (
        """
        or (
            rec_context_kind() = 'auth_bootstrap'
            and user_id = rec_current_user_id()
            and exists (
                select 1 from workspaces workspace_parent
                where workspace_parent.id = workspace_memberships.workspace_id
                  and workspace_parent.organization_id = rec_current_organization_id()
            )
        )
        """
        if allow_active_space_read
        else ""
    )
    personal_creation = """
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
    base = """
        (
            rec_context_kind() in ('request', 'auth_bootstrap')
            and workspace_id = rec_current_workspace_id()
            and user_id = rec_current_user_id()
        )
    """
    op.execute("drop policy if exists workspace_memberships_tenant_isolation on workspace_memberships")
    op.execute(
        "create policy workspace_memberships_tenant_isolation on workspace_memberships "
        f"using ({base} {personal_creation} {active_space_read} or rec_maintenance_allowed()) "
        f"with check ({base} {personal_creation} or rec_maintenance_allowed())"
    )


def upgrade() -> None:
    _replace_membership_policy(allow_active_space_read=True)


def downgrade() -> None:
    _replace_membership_policy(allow_active_space_read=False)
