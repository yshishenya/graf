"""Allow one bounded provider unlink to revoke the user's sessions cross-workspace."""

from collections.abc import Sequence

from alembic import op

revision: str = "0077_provider_unlink_xworkspace"
down_revision: str | None = "0076_account_linking_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        """
        create or replace function rec_provider_unlink_workspace_access(candidate_workspace_id uuid)
        returns boolean
        language sql
        stable
        security definer
        set search_path = pg_catalog, public
        set row_security = off
        as $$
            select session_user = 'twobrain_rec_app'
            and rec_context_kind() = 'auth_provider_unlink'
            and candidate_workspace_id is not null
            and rec_current_user_id() is not null
            and rec_current_organization_id() is not null
            and exists (
                select 1
                from workspaces workspace_parent
                join workspace_memberships membership
                  on membership.workspace_id = workspace_parent.id
                where workspace_parent.id = candidate_workspace_id
                  and workspace_parent.organization_id = rec_current_organization_id()
                  and membership.user_id = rec_current_user_id()
                  and membership.status = 'active'
            )
        $$
        """
    )

    policies = {
        "registered_devices": """
            (
                rec_context_kind() = 'request'
                and workspace_id = rec_current_workspace_id()
                and user_id = rec_current_user_id()
            )
            or (
                rec_context_kind() = 'auth_provider_unlink'
                and user_id = rec_current_user_id()
                and rec_provider_unlink_workspace_access(workspace_id)
            )
            or rec_maintenance_allowed()
        """,
        "auth_sessions": """
            (
                rec_context_kind() in ('request', 'auth_bootstrap')
                and workspace_id = rec_current_workspace_id()
                and user_id = rec_current_user_id()
            )
            or (
                rec_context_kind() = 'auth_session_lookup'
                and session_token_hash = rec_auth_session_token_hash()
            )
            or (
                rec_context_kind() = 'auth_provider_unlink'
                and user_id = rec_current_user_id()
                and rec_provider_unlink_workspace_access(workspace_id)
            )
            or rec_maintenance_allowed()
        """,
        "auth_session_device_bindings": """
            (
                rec_context_kind() in ('request', 'auth_bootstrap')
                and exists (
                    select 1 from auth_sessions session_parent
                    where session_parent.id = auth_session_device_bindings.auth_session_id
                      and session_parent.workspace_id = rec_current_workspace_id()
                      and session_parent.user_id = rec_current_user_id()
                )
                and exists (
                    select 1 from registered_devices device_parent
                    where device_parent.id = auth_session_device_bindings.registered_device_id
                      and device_parent.workspace_id = rec_current_workspace_id()
                      and device_parent.user_id = rec_current_user_id()
                )
            )
            or (
                rec_context_kind() = 'auth_provider_unlink'
                and exists (
                    select 1 from auth_sessions session_parent
                    where session_parent.id = auth_session_device_bindings.auth_session_id
                      and session_parent.user_id = rec_current_user_id()
                      and rec_provider_unlink_workspace_access(session_parent.workspace_id)
                )
                and exists (
                    select 1 from registered_devices device_parent
                    where device_parent.id = auth_session_device_bindings.registered_device_id
                      and device_parent.user_id = rec_current_user_id()
                      and rec_provider_unlink_workspace_access(device_parent.workspace_id)
                )
            )
            or rec_maintenance_allowed()
        """,
    }
    _replace_policies(policies)


def _replace_policies(policies: dict[str, str]) -> None:
    for table_name, expression in policies.items():
        op.execute(f"drop policy if exists {table_name}_tenant_isolation on {table_name}")
        op.execute(
            f"create policy {table_name}_tenant_isolation on {table_name} "
            f"using ({expression}) with check ({expression})"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    _replace_policies(
        {
            "registered_devices": """
                rec_context_kind() = 'request'
                and workspace_id = rec_current_workspace_id()
                and user_id = rec_current_user_id()
                or rec_maintenance_allowed()
            """,
            "auth_sessions": """
                (
                    rec_context_kind() in ('request', 'auth_bootstrap')
                    and workspace_id = rec_current_workspace_id()
                    and user_id = rec_current_user_id()
                )
                or (
                    rec_context_kind() = 'auth_session_lookup'
                    and session_token_hash = rec_auth_session_token_hash()
                )
                or rec_maintenance_allowed()
            """,
            "auth_session_device_bindings": """
                rec_context_kind() in ('request', 'auth_bootstrap')
                and exists (
                    select 1 from auth_sessions session_parent
                    where session_parent.id = auth_session_device_bindings.auth_session_id
                      and session_parent.workspace_id = rec_current_workspace_id()
                      and session_parent.user_id = rec_current_user_id()
                )
                and exists (
                    select 1 from registered_devices device_parent
                    where device_parent.id = auth_session_device_bindings.registered_device_id
                      and device_parent.workspace_id = rec_current_workspace_id()
                      and device_parent.user_id = rec_current_user_id()
                )
                or rec_maintenance_allowed()
            """,
        }
    )
    op.execute("drop function if exists rec_provider_unlink_workspace_access(uuid)")
