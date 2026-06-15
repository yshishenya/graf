"""rls hardening

Revision ID: 0005_rls_hardening
Revises: 0004_mediascribe_processing
Create Date: 2026-06-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_rls_hardening"
down_revision: str | None = "0004_mediascribe_processing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALLOWED_MAINTENANCE_OPERATIONS = (
    "migration_verification",
    "production_smoke_cleanup",
    "backup_restore_rehearsal",
    "operator_diagnostics",
)

AUTH_REQUEST_CONTEXT = "rec_context_kind() in ('request', 'auth_bootstrap')"
AUTH_PUBLIC_CONTEXT = "rec_context_kind() in ('auth_public', 'auth_bootstrap')"
CONTENT_CONTEXT = "rec_context_kind() in ('request', 'worker')"
ORGANIZATION_REQUEST_SCOPE = (
    "rec_context_kind() = 'request' "
    "and rec_current_user_has_active_workspace_membership()"
)
ORGANIZATION_AUTH_BOOTSTRAP_SCOPE = (
    "rec_context_kind() = 'auth_bootstrap' "
    "and rec_auth_bootstrap_workspace_in_organization()"
)

AUTH_PUBLIC_WORKSPACE_POLICIES = {
    "workspaces": "rec_context_kind() in ('request', 'auth_public', 'auth_bootstrap') and id = rec_current_workspace_id()",
    "workspace_auth_policies": (
        f"(rec_context_kind() in ('request') or {AUTH_PUBLIC_CONTEXT}) "
        "and workspace_id = rec_current_workspace_id()"
    ),
    "workspace_consent_copy": (
        f"(rec_context_kind() in ('request') or {AUTH_PUBLIC_CONTEXT}) "
        "and workspace_id = rec_current_workspace_id()"
    ),
    "auth_audit_events": (
        f"(rec_context_kind() in ('request') or {AUTH_PUBLIC_CONTEXT}) "
        "and workspace_id = rec_current_workspace_id()"
    ),
}

AUTH_REQUEST_WORKSPACE_POLICIES = {
    "workspace_memberships": (
        f"{AUTH_REQUEST_CONTEXT} and workspace_id = rec_current_workspace_id() "
        "and user_id = rec_current_user_id()"
    ),
    "registered_devices": (
        "rec_context_kind() = 'request' and workspace_id = rec_current_workspace_id() "
        "and user_id = rec_current_user_id()"
    ),
    "auth_sessions": (
        f"({AUTH_REQUEST_CONTEXT} and workspace_id = rec_current_workspace_id() "
        "and user_id = rec_current_user_id()) "
        "or (rec_context_kind() = 'auth_session_lookup' and session_token_hash = rec_auth_session_token_hash())"
    ),
    "auth_session_device_bindings": (
        f"{AUTH_REQUEST_CONTEXT} and exists (select 1 from auth_sessions session_parent "
        "where session_parent.id = auth_session_device_bindings.auth_session_id "
        "and session_parent.workspace_id = rec_current_workspace_id() "
        "and session_parent.user_id = rec_current_user_id()) "
        "and exists (select 1 from registered_devices device_parent "
        "where device_parent.id = auth_session_device_bindings.registered_device_id "
        "and device_parent.workspace_id = rec_current_workspace_id() "
        "and device_parent.user_id = rec_current_user_id())"
    ),
    "workspace_provider_link_states": (
        f"{AUTH_REQUEST_CONTEXT} and workspace_id = rec_current_workspace_id() "
        "and initiating_user_id = rec_current_user_id()"
    ),
    "auth_callback_states": (
        f"({AUTH_PUBLIC_CONTEXT} and workspace_id = rec_current_workspace_id()) "
        "or (rec_context_kind() = 'auth_callback_lookup' "
        "and state_nonce = rec_auth_callback_state_nonce())"
    ),
}

CONTENT_WORKSPACE_POLICIES = {
    "meetings": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "upload_sessions": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "temporary_upload_objects": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "track_artifacts": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "manifest_snapshots": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "ingest_audit_events": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "processing_placeholders": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "processing_workflows": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "mediascribe_jobs": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "processing_results": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "transcript_segments": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "diarization_segments": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "processing_audit_events": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
    "processing_dependency_states": f"{CONTENT_CONTEXT} and workspace_id = rec_current_workspace_id()",
}

ORGANIZATION_POLICIES = {
    "organizations": (
        "((rec_context_kind() = 'request' and id = rec_current_organization_id() "
        "and rec_current_user_has_active_workspace_membership()) "
        "or (rec_context_kind() = 'auth_bootstrap' and id = rec_current_organization_id() "
        "and rec_auth_bootstrap_workspace_in_organization()))"
    ),
    "user_identities": (
        "((rec_context_kind() = 'request' "
        "and organization_id = rec_current_organization_id() "
        "and rec_current_user_has_active_workspace_membership()) "
        "or (rec_context_kind() = 'auth_bootstrap' "
        "and organization_id = rec_current_organization_id() "
        "and rec_auth_bootstrap_workspace_in_organization())) "
        "or (rec_context_kind() = 'auth_session_lookup' "
        "and exists (select 1 from auth_sessions session_parent "
        "where session_parent.user_id = user_identities.id "
        "and session_parent.session_token_hash = rec_auth_session_token_hash()))"
    ),
}

INHERITED_POLICIES = {
    "upload_parts": (
        f"{CONTENT_CONTEXT} and exists (select 1 from upload_sessions parent "
        "where parent.id = upload_parts.upload_session_id "
        "and parent.workspace_id = rec_current_workspace_id())"
    ),
    "external_identities": (
        f"(({ORGANIZATION_REQUEST_SCOPE}) or ({ORGANIZATION_AUTH_BOOTSTRAP_SCOPE})) "
        "and exists (select 1 from user_identities parent "
        "where parent.id = external_identities.user_id "
        "and parent.organization_id = rec_current_organization_id())"
    ),
}


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _maintenance_expression() -> str:
    return "rec_maintenance_allowed()"


def _policy_expression(expression: str) -> str:
    return f"(({expression}) or {_maintenance_expression()})"


def _create_all_policy(table_name: str, expression: str) -> None:
    table = _q(table_name)
    policy = _q(f"{table_name}_tenant_isolation")
    predicate = _policy_expression(expression)
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(
        f"create policy {policy} on {table} "
        f"using ({predicate}) "
        f"with check ({predicate})"
    )


def _drop_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(f"{table_name}_tenant_isolation")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgresql():
        return
    op.execute(
        """
        create or replace function rec_setting(name text)
        returns text
        language sql
        stable
        as $$
            select nullif(current_setting(name, true), '')
        $$;
        """
    )
    op.execute(
        """
        create or replace function rec_setting_uuid(name text)
        returns uuid
        language sql
        stable
        as $$
            with value(raw_value) as (
                select rec_setting(name)
            )
            select case
                when raw_value ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                then raw_value::uuid
                else null
            end
            from value
        $$;
        """
    )
    op.execute(
        """
        create or replace function rec_context_kind()
        returns text language sql stable
        as $$ select rec_setting('app.context_kind') $$;
        """
    )
    op.execute(
        """
        create or replace function rec_current_organization_id()
        returns uuid language sql stable
        as $$ select rec_setting_uuid('app.organization_id') $$;
        """
    )
    op.execute(
        """
        create or replace function rec_current_workspace_id()
        returns uuid language sql stable
        as $$ select rec_setting_uuid('app.workspace_id') $$;
        """
    )
    op.execute(
        """
        create or replace function rec_current_user_id()
        returns uuid language sql stable
        as $$ select rec_setting_uuid('app.user_id') $$;
        """
    )
    op.execute(
        """
        create or replace function rec_current_device_id()
        returns uuid language sql stable
        as $$ select rec_setting_uuid('app.device_id') $$;
        """
    )
    op.execute(
        """
        create or replace function rec_auth_session_token_hash()
        returns text language sql stable
        as $$ select rec_setting('app.auth_session_token_hash') $$;
        """
    )
    op.execute(
        """
        create or replace function rec_auth_callback_state_nonce()
        returns text language sql stable
        as $$ select rec_setting('app.auth_callback_state_nonce') $$;
        """
    )
    op.execute(
        """
        create or replace function rec_current_user_has_active_workspace_membership()
        returns boolean
        language sql
        stable
        as $$
            select exists (
                select 1
                from workspace_memberships membership
                join workspaces workspace_parent
                    on workspace_parent.id = membership.workspace_id
                where membership.workspace_id = rec_current_workspace_id()
                    and membership.user_id = rec_current_user_id()
                    and membership.status = 'active'
                    and workspace_parent.organization_id = rec_current_organization_id()
            )
        $$;
        """
    )
    op.execute(
        """
        create or replace function rec_auth_bootstrap_workspace_in_organization()
        returns boolean
        language sql
        stable
        as $$
            select rec_context_kind() = 'auth_bootstrap'
            and exists (
                select 1
                from workspaces workspace_parent
                where workspace_parent.id = rec_current_workspace_id()
                    and workspace_parent.organization_id = rec_current_organization_id()
            )
        $$;
        """
    )
    operations = ", ".join(f"'{operation}'" for operation in ALLOWED_MAINTENANCE_OPERATIONS)
    op.execute(
        f"""
        create or replace function rec_maintenance_allowed()
        returns boolean
        language sql
        stable
        as $$
            select rec_setting('app.context_kind') = 'maintenance'
            and rec_setting('app.maintenance_operation') = any(array[{operations}])
            and rec_setting('app.maintenance_actor') is not null
            and rec_setting('app.maintenance_reason') is not null
            and rec_setting('app.maintenance_feature_area') is not null
        $$;
        """
    )

    for table_name, expression in ORGANIZATION_POLICIES.items():
        _create_all_policy(table_name, expression)
    for table_name, expression in AUTH_PUBLIC_WORKSPACE_POLICIES.items():
        _create_all_policy(table_name, expression)
    for table_name, expression in AUTH_REQUEST_WORKSPACE_POLICIES.items():
        _create_all_policy(table_name, expression)
    for table_name, expression in CONTENT_WORKSPACE_POLICIES.items():
        _create_all_policy(table_name, expression)
    for table_name, expression in INHERITED_POLICIES.items():
        _create_all_policy(table_name, expression)


def downgrade() -> None:
    if not _is_postgresql():
        return
    for table_name in [
        *INHERITED_POLICIES,
        *CONTENT_WORKSPACE_POLICIES,
        *AUTH_REQUEST_WORKSPACE_POLICIES,
        *AUTH_PUBLIC_WORKSPACE_POLICIES,
        *ORGANIZATION_POLICIES,
    ]:
        _drop_policy(table_name)
    for function_name in [
        "rec_maintenance_allowed()",
        "rec_auth_bootstrap_workspace_in_organization()",
        "rec_current_user_has_active_workspace_membership()",
        "rec_auth_callback_state_nonce()",
        "rec_auth_session_token_hash()",
        "rec_current_device_id()",
        "rec_current_user_id()",
        "rec_current_workspace_id()",
        "rec_current_organization_id()",
        "rec_context_kind()",
        "rec_setting_uuid(text)",
        "rec_setting(text)",
    ]:
        op.execute(f"drop function if exists {function_name}")
