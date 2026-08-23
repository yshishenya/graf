"""Bind callback identities and split account-linking RLS by operation."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0076_account_linking_rls"
down_revision: str | None = "0075_calendar_sync_maintenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


POLICY_TABLES = (
    "user_identities",
    "external_identities",
    "auth_callback_states",
    "workspace_provider_link_states",
    "account_merge_intents",
    "account_merge_journals",
)

MAINTENANCE_SCOPE = """
    rec_context_kind() = 'maintenance'
    and rec_maintenance_allowed()
"""

ACCOUNT_MERGE_SCOPE = """
    rec_context_kind() = 'account_merge'
    and rec_account_merge_context_valid()
"""

USER_ACCOUNT_MERGE_READ_SCOPE = f"""
    ({ACCOUNT_MERGE_SCOPE})
    and id in (
        rec_setting_uuid('app.account_merge_survivor_user_id'),
        rec_setting_uuid('app.account_merge_source_user_id')
    )
"""

USER_ACCOUNT_MERGE_WRITE_SCOPE = f"""
    ({ACCOUNT_MERGE_SCOPE})
    and id = rec_setting_uuid('app.account_merge_source_user_id')
"""

EXTERNAL_ACCOUNT_MERGE_READ_SCOPE = f"""
    ({ACCOUNT_MERGE_SCOPE})
    and user_id in (
        rec_setting_uuid('app.account_merge_survivor_user_id'),
        rec_setting_uuid('app.account_merge_source_user_id')
    )
"""

EXTERNAL_ACCOUNT_MERGE_SOURCE_SCOPE = f"""
    ({ACCOUNT_MERGE_SCOPE})
    and user_id = rec_setting_uuid('app.account_merge_source_user_id')
"""

EXTERNAL_ACCOUNT_MERGE_SURVIVOR_SCOPE = f"""
    ({ACCOUNT_MERGE_SCOPE})
    and user_id = rec_setting_uuid('app.account_merge_survivor_user_id')
"""

EXTERNAL_ACCOUNT_MERGE_SOURCE_PROOF_DEACTIVATION_SCOPE = f"""
    ({ACCOUNT_MERGE_SCOPE})
    and id = (
        select source_external_identity_id
        from account_merge_intents
        where account_merge_intents.id = rec_setting_uuid('app.account_merge_intent_id')
    )
    and user_id = rec_setting_uuid('app.account_merge_source_user_id')
    and is_active = false
    and is_verified = false
    and rec_account_merge_source_proof_deactivation_allowed(external_identities.id)
"""

CALLBACK_ACCOUNT_MERGE_SCOPE = f"""
    ({ACCOUNT_MERGE_SCOPE})
    and id = (
        select proof_callback_state_id
        from account_merge_intents
        where account_merge_intents.id = rec_setting_uuid('app.account_merge_intent_id')
    )
"""

PROVIDER_LINK_ACCOUNT_MERGE_SCOPE = f"""
    ({ACCOUNT_MERGE_SCOPE})
    and id = (
        select provider_link_state_id
        from account_merge_intents
        where account_merge_intents.id = rec_setting_uuid('app.account_merge_intent_id')
    )
"""

MERGE_INTENT_EXACT_SCOPE = f"""
    ({ACCOUNT_MERGE_SCOPE})
    and id = rec_setting_uuid('app.account_merge_intent_id')
"""

MERGE_JOURNAL_EXACT_SCOPE = f"""
    ({ACCOUNT_MERGE_SCOPE})
    and merge_intent_id = rec_setting_uuid('app.account_merge_intent_id')
    and workspace_id = rec_current_workspace_id()
    and survivor_user_id = rec_setting_uuid('app.account_merge_survivor_user_id')
    and source_user_id = rec_setting_uuid('app.account_merge_source_user_id')
    and status = 'completed'
    and (policy_version, preview_fingerprint) = (
        select policy_version, preview_fingerprint
        from account_merge_intents
        where account_merge_intents.id = rec_setting_uuid('app.account_merge_intent_id')
    )
"""

USER_ORGANIZATION_READ_SCOPE = """
    (
        rec_context_kind() = 'request'
        and organization_id = rec_current_organization_id()
        and rec_current_user_has_active_workspace_membership()
    )
    or (
        rec_context_kind() = 'auth_bootstrap'
        and organization_id = rec_current_organization_id()
        and rec_auth_bootstrap_workspace_in_organization()
    )
    or (
        rec_context_kind() = 'auth_session_lookup'
        and exists (
            select 1 from auth_sessions session_parent
            where session_parent.user_id = user_identities.id
              and session_parent.session_token_hash = rec_auth_session_token_hash()
        )
    )
"""

USER_AUTH_BOOTSTRAP_INSERT_SCOPE = """
    rec_context_kind() = 'auth_bootstrap'
    and organization_id = rec_current_organization_id()
    and rec_auth_bootstrap_workspace_in_organization()
"""

USER_SELF_WRITE_SCOPE = """
    (
        rec_context_kind() = 'request'
        and id = rec_current_user_id()
        and organization_id = rec_current_organization_id()
        and rec_current_user_has_active_workspace_membership()
    )
    or (
        rec_context_kind() = 'auth_bootstrap'
        and id = rec_current_user_id()
        and organization_id = rec_current_organization_id()
        and rec_auth_bootstrap_workspace_in_organization()
    )
"""

EXTERNAL_IDENTITY_ORGANIZATION_SCOPE = """
    (
        (
            rec_context_kind() = 'request'
            and rec_current_user_has_active_workspace_membership()
        )
        or (
            rec_context_kind() = 'auth_bootstrap'
            and rec_auth_bootstrap_workspace_in_organization()
        )
    )
    and exists (
        select 1 from user_identities parent
        where parent.id = external_identities.user_id
          and parent.organization_id = rec_current_organization_id()
    )
"""

EXTERNAL_IDENTITY_SELF_WRITE_SCOPE = """
    user_id = rec_current_user_id()
    and (
        (
            rec_context_kind() = 'request'
            and rec_current_user_has_active_workspace_membership()
        )
        or (
            rec_context_kind() = 'auth_bootstrap'
            and rec_auth_bootstrap_workspace_in_organization()
        )
    )
    and exists (
        select 1 from user_identities parent
        where parent.id = external_identities.user_id
          and parent.organization_id = rec_current_organization_id()
    )
"""

AUTH_CALLBACK_WORKSPACE_SCOPE = """
    rec_context_kind() in ('auth_public', 'auth_bootstrap')
    and workspace_id = rec_current_workspace_id()
"""

AUTH_CALLBACK_LOOKUP_SCOPE = """
    rec_context_kind() = 'auth_callback_lookup'
    and state_nonce = rec_auth_callback_state_nonce()
"""

PROVIDER_LINK_OWNER_SCOPE = """
    rec_context_kind() in ('request', 'auth_bootstrap')
    and workspace_id = rec_current_workspace_id()
    and initiating_user_id = rec_current_user_id()
"""

PROVIDER_LINK_CALLBACK_SCOPE = """
    rec_context_kind() = 'auth_callback_lookup'
    and exists (
        select 1 from auth_callback_states callback_state
        where callback_state.id = workspace_provider_link_states.callback_state_id
          and callback_state.state_nonce = rec_auth_callback_state_nonce()
    )
"""

MERGE_INTENT_OWNER_SCOPE = """
    rec_context_kind() in ('request', 'auth_bootstrap')
    and workspace_id = rec_current_workspace_id()
    and survivor_user_id = rec_current_user_id()
"""

MERGE_JOURNAL_OWNER_SCOPE = """
    rec_context_kind() in ('request', 'auth_bootstrap')
    and workspace_id = rec_current_workspace_id()
    and survivor_user_id = rec_current_user_id()
"""


EXACT_SEMANTIC_ACCOUNT_MERGE_CONTEXT = """
create or replace function rec_account_merge_context_valid()
returns boolean
language sql
stable
security definer
set search_path = pg_catalog, public
set row_security = off
as $$
    select session_user = 'twobrain_rec_app'
    and rec_setting('app.context_kind') = 'account_merge'
    and rec_setting_uuid('app.account_merge_intent_id') is not null
    and rec_setting_uuid('app.account_merge_survivor_user_id') is not null
    and rec_setting_uuid('app.account_merge_source_user_id') is not null
    and exists (
        select 1
        from account_merge_intents merge_intent
        join auth_sessions proof_session
          on proof_session.id = merge_intent.initiating_auth_session_id
        join external_identities proof_identity
          on proof_identity.id = merge_intent.source_external_identity_id
        join auth_callback_states proof_callback
          on proof_callback.id = merge_intent.proof_callback_state_id
        left join workspace_provider_link_states proof_link
          on proof_link.id = merge_intent.provider_link_state_id
        where merge_intent.id = rec_setting_uuid('app.account_merge_intent_id')
          and merge_intent.workspace_id = rec_setting_uuid('app.workspace_id')
          and merge_intent.survivor_user_id =
              rec_setting_uuid('app.account_merge_survivor_user_id')
          and merge_intent.source_user_id =
              rec_setting_uuid('app.account_merge_source_user_id')
          and merge_intent.initiating_auth_session_id is not null
          and merge_intent.source_external_identity_id is not null
          and merge_intent.proof_callback_state_id is not null
          and merge_intent.status in ('preview_ready', 'blocked')
          and merge_intent.expires_at > now()
          and merge_intent.email_proof_state = 'verified'
          and merge_intent.oauth_proof_state = 'verified'
          and proof_session.user_id = merge_intent.survivor_user_id
          and proof_session.workspace_id = merge_intent.workspace_id
          and proof_session.status = 'active'
          and proof_session.expires_at > now()
          and proof_identity.user_id = merge_intent.source_user_id
          and proof_identity.is_active
          and proof_callback.workspace_id = merge_intent.workspace_id
          and proof_callback.result = 'completed'
          and proof_callback.used_at is not null
          and proof_callback.verified_external_identity_id = proof_identity.id
          and (
              (
                  merge_intent.provider_link_state_id is null
                  and proof_callback.provider in ('email_link', 'email')
                  and proof_identity.provider = 'email'
                  and proof_identity.email is not null
                  and proof_identity.is_verified
              )
              or (
                  merge_intent.provider_link_state_id is not null
                  and proof_link.workspace_id = merge_intent.workspace_id
                  and proof_link.initiating_user_id = merge_intent.survivor_user_id
                  and proof_link.initiating_auth_session_id = proof_session.id
                  and proof_link.callback_state_id = proof_callback.id
                  and proof_link.candidate_provider = proof_callback.provider
                  and proof_link.candidate_provider = proof_identity.provider
                  and proof_link.target_provider_identity_id = proof_identity.id
                  and proof_link.status = 'confirmed'
              )
          )
    )
$$
"""


EXACT_SOURCE_PROOF_DEACTIVATION_CONTEXT = """
create or replace function rec_account_merge_source_proof_deactivation_allowed(
    candidate_identity_id uuid
)
returns boolean
language sql
stable
security definer
set search_path = pg_catalog, public
set row_security = off
as $$
    select session_user = 'twobrain_rec_app'
    and rec_setting('app.context_kind') = 'account_merge'
    and candidate_identity_id = (
        select merge_intent.source_external_identity_id
        from account_merge_intents merge_intent
        where merge_intent.id = rec_setting_uuid('app.account_merge_intent_id')
          and merge_intent.source_user_id =
              rec_setting_uuid('app.account_merge_source_user_id')
          and merge_intent.status in ('preview_ready', 'blocked')
          and merge_intent.expires_at > now()
    )
$$
"""


LEGACY_ACCOUNT_MERGE_CONTEXT = """
create or replace function rec_account_merge_context_valid()
returns boolean
language sql
stable
security definer
set search_path = pg_catalog, public
set row_security = off
as $$
    select session_user = 'twobrain_rec_app'
    and rec_setting('app.context_kind') = 'account_merge'
    and rec_setting_uuid('app.account_merge_intent_id') is not null
    and rec_setting_uuid('app.account_merge_survivor_user_id') is not null
    and rec_setting_uuid('app.account_merge_source_user_id') is not null
    and exists (
        select 1
        from account_merge_intents merge_intent
        join auth_sessions proof_session
          on proof_session.id = merge_intent.initiating_auth_session_id
        join external_identities proof_identity
          on proof_identity.id = merge_intent.source_external_identity_id
        join auth_callback_states proof_callback
          on proof_callback.id = merge_intent.proof_callback_state_id
        left join workspace_provider_link_states proof_link
          on proof_link.id = merge_intent.provider_link_state_id
        where merge_intent.id = rec_setting_uuid('app.account_merge_intent_id')
          and merge_intent.workspace_id = rec_setting_uuid('app.workspace_id')
          and merge_intent.survivor_user_id =
              rec_setting_uuid('app.account_merge_survivor_user_id')
          and merge_intent.source_user_id =
              rec_setting_uuid('app.account_merge_source_user_id')
          and merge_intent.initiating_auth_session_id is not null
          and merge_intent.source_external_identity_id is not null
          and merge_intent.proof_callback_state_id is not null
          and merge_intent.status in ('preview_ready', 'blocked')
          and merge_intent.expires_at > now()
          and merge_intent.email_proof_state = 'verified'
          and merge_intent.oauth_proof_state = 'verified'
          and proof_session.user_id = merge_intent.survivor_user_id
          and proof_session.workspace_id = merge_intent.workspace_id
          and proof_session.status = 'active'
          and proof_session.expires_at > now()
          and proof_identity.user_id = merge_intent.source_user_id
          and proof_identity.is_active
          and proof_identity.is_verified
          and proof_callback.workspace_id = merge_intent.workspace_id
          and proof_callback.result = 'completed'
          and proof_callback.used_at is not null
          and (
              merge_intent.provider_link_state_id is null
              or (
                  proof_link.workspace_id = merge_intent.workspace_id
                  and proof_link.initiating_user_id = merge_intent.survivor_user_id
                  and proof_link.initiating_auth_session_id = proof_session.id
                  and proof_link.callback_state_id = proof_callback.id
                  and proof_link.target_provider_identity_id = proof_identity.id
                  and proof_link.status = 'confirmed'
              )
          )
    )
$$
"""


LEGACY_ALL_POLICIES = {
    "user_identities": """
        (
            rec_context_kind() = 'request'
            and organization_id = rec_current_organization_id()
            and rec_current_user_has_active_workspace_membership()
        )
        or (
            rec_context_kind() = 'auth_bootstrap'
            and organization_id = rec_current_organization_id()
            and rec_auth_bootstrap_workspace_in_organization()
        )
        or (
            rec_context_kind() = 'auth_session_lookup'
            and exists (
                select 1 from auth_sessions session_parent
                where session_parent.user_id = user_identities.id
                  and session_parent.session_token_hash = rec_auth_session_token_hash()
            )
        )
        or rec_maintenance_allowed()
    """,
    "external_identities": f"""
        ({EXTERNAL_IDENTITY_ORGANIZATION_SCOPE})
        or rec_maintenance_allowed()
    """,
    "auth_callback_states": """
        (
            rec_context_kind() in ('auth_public', 'auth_bootstrap')
            and workspace_id = rec_current_workspace_id()
        )
        or (
            rec_context_kind() = 'auth_callback_lookup'
            and state_nonce = rec_auth_callback_state_nonce()
        )
        or rec_maintenance_allowed()
    """,
    "workspace_provider_link_states": """
        (
            rec_context_kind() in ('request', 'auth_bootstrap')
            and workspace_id = rec_current_workspace_id()
            and initiating_user_id = rec_current_user_id()
        )
        or (
            rec_context_kind() = 'auth_callback_lookup'
            and exists (
                select 1 from auth_callback_states callback_state
                where callback_state.id = workspace_provider_link_states.callback_state_id
                  and callback_state.state_nonce = rec_auth_callback_state_nonce()
            )
        )
        or rec_maintenance_allowed()
    """,
    "account_merge_intents": """
        (
            rec_context_kind() in ('request', 'auth_bootstrap')
            and workspace_id = rec_current_workspace_id()
        )
        or rec_maintenance_allowed()
    """,
    "account_merge_journals": """
        (
            rec_context_kind() in ('request', 'auth_bootstrap')
            and workspace_id = rec_current_workspace_id()
        )
        or rec_maintenance_allowed()
    """,
}


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _or(*expressions: str) -> str:
    return " or ".join(f"({expression})" for expression in expressions)


def _drop_account_linking_policies(table_name: str) -> None:
    op.execute(f"drop policy if exists {table_name}_tenant_isolation on {table_name}")
    for operation in ("select", "insert", "update", "delete"):
        op.execute(
            f"drop policy if exists {table_name}_{operation}_isolation on {table_name}"
        )


def _create_operation_policy(
    table_name: str,
    operation: str,
    *,
    using: str | None = None,
    check: str | None = None,
) -> None:
    clauses = []
    if using is not None:
        clauses.append(f"using ({using})")
    if check is not None:
        clauses.append(f"with check ({check})")
    op.execute(
        f"create policy {table_name}_{operation}_isolation on {table_name} "
        f"for {operation} {' '.join(clauses)}"
    )


def _create_operation_policies() -> None:
    user_select = _or(
        USER_ORGANIZATION_READ_SCOPE,
        USER_ACCOUNT_MERGE_READ_SCOPE,
        MAINTENANCE_SCOPE,
    )
    user_insert = _or(USER_AUTH_BOOTSTRAP_INSERT_SCOPE, MAINTENANCE_SCOPE)
    # FOR UPDATE needs the UPDATE USING predicate even when no mutation follows.
    # Same-organization rows may be locked during intent creation, while the
    # narrower WITH CHECK still prevents changing another profile.
    user_update_using = user_select
    user_update_check = _or(
        USER_SELF_WRITE_SCOPE,
        USER_ACCOUNT_MERGE_WRITE_SCOPE,
        MAINTENANCE_SCOPE,
    )
    _create_operation_policy("user_identities", "select", using=user_select)
    _create_operation_policy("user_identities", "insert", check=user_insert)
    _create_operation_policy(
        "user_identities",
        "update",
        using=user_update_using,
        check=user_update_check,
    )
    _create_operation_policy(
        "user_identities", "delete", using=MAINTENANCE_SCOPE
    )

    external_select = _or(
        EXTERNAL_IDENTITY_ORGANIZATION_SCOPE,
        EXTERNAL_ACCOUNT_MERGE_READ_SCOPE,
        MAINTENANCE_SCOPE,
    )
    external_insert = _or(
        EXTERNAL_IDENTITY_SELF_WRITE_SCOPE,
        MAINTENANCE_SCOPE,
    )
    external_update_using = _or(
        EXTERNAL_IDENTITY_SELF_WRITE_SCOPE,
        EXTERNAL_ACCOUNT_MERGE_SOURCE_SCOPE,
        MAINTENANCE_SCOPE,
    )
    external_update_check = _or(
        EXTERNAL_IDENTITY_SELF_WRITE_SCOPE,
        EXTERNAL_ACCOUNT_MERGE_SURVIVOR_SCOPE,
        EXTERNAL_ACCOUNT_MERGE_SOURCE_PROOF_DEACTIVATION_SCOPE,
        MAINTENANCE_SCOPE,
    )
    _create_operation_policy("external_identities", "select", using=external_select)
    _create_operation_policy("external_identities", "insert", check=external_insert)
    _create_operation_policy(
        "external_identities",
        "update",
        using=external_update_using,
        check=external_update_check,
    )
    _create_operation_policy(
        "external_identities", "delete", using=MAINTENANCE_SCOPE
    )

    callback_select = _or(
        AUTH_CALLBACK_WORKSPACE_SCOPE,
        AUTH_CALLBACK_LOOKUP_SCOPE,
        CALLBACK_ACCOUNT_MERGE_SCOPE,
        MAINTENANCE_SCOPE,
    )
    # PostgreSQL SELECT ... FOR UPDATE also evaluates the UPDATE policy.
    callback_write = _or(
        AUTH_CALLBACK_LOOKUP_SCOPE,
        CALLBACK_ACCOUNT_MERGE_SCOPE,
        MAINTENANCE_SCOPE,
    )
    callback_insert = _or(AUTH_CALLBACK_WORKSPACE_SCOPE, MAINTENANCE_SCOPE)
    _create_operation_policy("auth_callback_states", "select", using=callback_select)
    _create_operation_policy("auth_callback_states", "insert", check=callback_insert)
    _create_operation_policy(
        "auth_callback_states", "update", using=callback_write, check=callback_write
    )
    _create_operation_policy(
        "auth_callback_states", "delete", using=MAINTENANCE_SCOPE
    )

    provider_link_select = _or(
        PROVIDER_LINK_OWNER_SCOPE,
        PROVIDER_LINK_CALLBACK_SCOPE,
        PROVIDER_LINK_ACCOUNT_MERGE_SCOPE,
        MAINTENANCE_SCOPE,
    )
    provider_link_write = provider_link_select
    provider_link_insert = _or(PROVIDER_LINK_OWNER_SCOPE, MAINTENANCE_SCOPE)
    _create_operation_policy(
        "workspace_provider_link_states", "select", using=provider_link_select
    )
    _create_operation_policy(
        "workspace_provider_link_states", "insert", check=provider_link_insert
    )
    _create_operation_policy(
        "workspace_provider_link_states",
        "update",
        using=provider_link_write,
        check=provider_link_write,
    )
    _create_operation_policy(
        "workspace_provider_link_states", "delete", using=MAINTENANCE_SCOPE
    )

    merge_intent_scope = _or(
        MERGE_INTENT_OWNER_SCOPE,
        MERGE_INTENT_EXACT_SCOPE,
        MAINTENANCE_SCOPE,
    )
    merge_intent_insert = _or(MERGE_INTENT_OWNER_SCOPE, MAINTENANCE_SCOPE)
    _create_operation_policy(
        "account_merge_intents", "select", using=merge_intent_scope
    )
    _create_operation_policy(
        "account_merge_intents", "insert", check=merge_intent_insert
    )
    _create_operation_policy(
        "account_merge_intents",
        "update",
        using=merge_intent_scope,
        check=merge_intent_scope,
    )
    _create_operation_policy(
        "account_merge_intents", "delete", using=MAINTENANCE_SCOPE
    )

    merge_journal_select = _or(
        MERGE_JOURNAL_OWNER_SCOPE,
        MERGE_JOURNAL_EXACT_SCOPE,
        MAINTENANCE_SCOPE,
    )
    merge_journal_insert = _or(MERGE_JOURNAL_EXACT_SCOPE, MAINTENANCE_SCOPE)
    _create_operation_policy(
        "account_merge_journals", "select", using=merge_journal_select
    )
    _create_operation_policy(
        "account_merge_journals", "insert", check=merge_journal_insert
    )
    _create_operation_policy(
        "account_merge_journals", "update", using=MAINTENANCE_SCOPE, check=MAINTENANCE_SCOPE
    )
    _create_operation_policy(
        "account_merge_journals", "delete", using=MAINTENANCE_SCOPE
    )


def _restore_legacy_all_policies() -> None:
    for table_name, expression in LEGACY_ALL_POLICIES.items():
        op.execute(
            f"create policy {table_name}_tenant_isolation on {table_name} "
            f"using ({expression}) with check ({expression})"
        )


def upgrade() -> None:
    op.add_column(
        "auth_callback_states",
        sa.Column("verified_external_identity_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_auth_callback_states_verified_external_identity",
        "auth_callback_states",
        "external_identities",
        ["verified_external_identity_id"],
        ["id"],
    )
    op.create_index(
        "ix_auth_callback_states_verified_external_identity",
        "auth_callback_states",
        ["verified_external_identity_id"],
    )
    if not _is_postgresql():
        return

    op.execute(EXACT_SEMANTIC_ACCOUNT_MERGE_CONTEXT)
    op.execute(EXACT_SOURCE_PROOF_DEACTIVATION_CONTEXT)
    for table_name in POLICY_TABLES:
        _drop_account_linking_policies(table_name)
    _create_operation_policies()


def downgrade() -> None:
    if _is_postgresql():
        op.execute(LEGACY_ACCOUNT_MERGE_CONTEXT)
        for table_name in POLICY_TABLES:
            _drop_account_linking_policies(table_name)
        _restore_legacy_all_policies()
        op.execute(
            "drop function if exists "
            "rec_account_merge_source_proof_deactivation_allowed(uuid)"
        )

    op.drop_index(
        "ix_auth_callback_states_verified_external_identity",
        table_name="auth_callback_states",
    )
    op.drop_constraint(
        "fk_auth_callback_states_verified_external_identity",
        "auth_callback_states",
        type_="foreignkey",
    )
    op.drop_column("auth_callback_states", "verified_external_identity_id")
