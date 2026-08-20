"""Allow linked workspaces and bind account merges to exact auth proofs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0074_linked_workspace_proofs"
down_revision: str | None = "0073_account_auth_linking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PROOF_FOREIGN_KEYS = (
    (
        "initiating_auth_session_id",
        "auth_sessions",
        "fk_account_merge_intents_initiating_auth_session",
    ),
    (
        "source_external_identity_id",
        "external_identities",
        "fk_account_merge_intents_source_external_identity",
    ),
    (
        "proof_callback_state_id",
        "auth_callback_states",
        "fk_account_merge_intents_proof_callback_state",
    ),
    (
        "provider_link_state_id",
        "workspace_provider_link_states",
        "fk_account_merge_intents_provider_link_state",
    ),
)


EXACT_PROOF_ACCOUNT_MERGE_CONTEXT = """
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
                  and proof_link.status in ('callback_verified', 'confirmed')
              )
          )
    )
$$
"""


CURRENT_USER_LINEAGE_HELPER = """
create or replace function rec_current_user_lineage_contains(candidate_user_id uuid)
returns boolean
language sql
stable
security definer
set search_path = pg_catalog, public
set row_security = off
as $$
    select session_user = 'twobrain_rec_app'
    and rec_context_kind() in ('request', 'worker', 'auth_referral_user_lookup')
    and rec_current_user_id() is not null
    and candidate_user_id is not null
    and exists (
        with recursive user_lineage(user_id) as (
            select rec_current_user_id()
            union
            select source_user.id
            from user_identities source_user
            join user_lineage on source_user.merged_into_user_id = user_lineage.user_id
        )
        select 1 from user_lineage where user_id = candidate_user_id
    )
$$
"""


CURRENT_USER_OWNS_LINEAGE_WORKSPACE_HELPER = """
create or replace function rec_current_user_owns_lineage_workspace(candidate_workspace_id uuid)
returns boolean
language sql
stable
security definer
set search_path = pg_catalog, public
set row_security = off
as $$
    select session_user = 'twobrain_rec_app'
    and rec_context_kind() in ('request', 'worker')
    and rec_current_user_id() is not null
    and candidate_workspace_id is not null
    and exists (
        select 1
        from workspaces lineage_workspace
        join workspace_memberships lineage_membership
          on lineage_membership.workspace_id = lineage_workspace.id
        where lineage_workspace.id = candidate_workspace_id
          and lineage_workspace.owner_user_id = rec_current_user_id()
          and lineage_workspace.kind in ('personal', 'linked')
          and lineage_membership.user_id = rec_current_user_id()
          and lineage_membership.status = 'active'
    )
$$
"""


REFERRAL_LINEAGE_POLICY = """
create policy referral_attributions_user_history on referral_attributions
for select using (
    rec_context_kind() = 'auth_referral_user_lookup'
    and rec_current_user_lineage_contains(invitee_user_id)
)
"""


LEGACY_REFERRAL_USER_HISTORY_POLICY = """
create policy referral_attributions_user_history on referral_attributions
for select using (
    rec_context_kind() = 'auth_referral_user_lookup'
    and invitee_user_id = rec_current_user_id()
)
"""


FAIR_USE_LINEAGE_POLICY = """
create policy fair_use_reviews_tenant_isolation on fair_use_reviews
for all using (
    (
        rec_context_kind() in ('request', 'worker')
        and (
            (
                workspace_id = rec_current_workspace_id()
                and (
                    subject_user_id = rec_current_user_id()
                    or exists (
                        select 1 from workspaces owner_scope
                        where owner_scope.id = fair_use_reviews.workspace_id
                          and owner_scope.owner_user_id = rec_current_user_id()
                    )
                )
            )
            or (
                rec_current_user_lineage_contains(subject_user_id)
                and rec_current_user_owns_lineage_workspace(workspace_id)
            )
        )
    )
    or rec_maintenance_allowed()
)
with check (
    (
        rec_context_kind() in ('request', 'worker')
        and (
            (workspace_id = rec_current_workspace_id() and subject_user_id = rec_current_user_id())
            or (
                rec_current_user_lineage_contains(subject_user_id)
                and rec_current_user_owns_lineage_workspace(workspace_id)
            )
        )
    )
    or rec_maintenance_allowed()
)
"""


LEGACY_FAIR_USE_POLICY = """
create policy fair_use_reviews_tenant_isolation on fair_use_reviews
for all using (
    (
        rec_context_kind() in ('request', 'worker')
        and workspace_id = rec_current_workspace_id()
        and (
            subject_user_id = rec_current_user_id()
            or exists (
                select 1 from workspaces owner_scope
                where owner_scope.id = fair_use_reviews.workspace_id
                  and owner_scope.owner_user_id = rec_current_user_id()
            )
        )
    )
    or rec_maintenance_allowed()
)
with check (
    (
        rec_context_kind() in ('request', 'worker')
        and workspace_id = rec_current_workspace_id()
        and subject_user_id = rec_current_user_id()
    )
    or rec_maintenance_allowed()
)
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
    select session_user in ('twobrain_rec_app', 'twobrain_rec_maintenance')
    and rec_setting('app.context_kind') = 'account_merge'
    and rec_setting_uuid('app.account_merge_intent_id') is not null
    and rec_setting_uuid('app.account_merge_survivor_user_id') is not null
    and rec_setting_uuid('app.account_merge_source_user_id') is not null
    and exists (
        select 1
        from account_merge_intents merge_intent
        where merge_intent.id = rec_setting_uuid('app.account_merge_intent_id')
          and merge_intent.workspace_id = rec_setting_uuid('app.workspace_id')
          and merge_intent.survivor_user_id =
              rec_setting_uuid('app.account_merge_survivor_user_id')
          and merge_intent.source_user_id =
              rec_setting_uuid('app.account_merge_source_user_id')
          and merge_intent.status in (
              'initiated', 'awaiting_proof', 'preview_ready',
              'confirmed', 'blocked', 'completed'
          )
          and merge_intent.email_proof_state = 'verified'
          and merge_intent.oauth_proof_state = 'verified'
    )
$$
"""


def _workspace_kind_constraint_names() -> list[str]:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return list(
            bind.scalars(
                sa.text(
                    """
                    select distinct constraint_row.conname
                    from pg_constraint constraint_row
                    join pg_attribute attribute_row
                      on attribute_row.attrelid = constraint_row.conrelid
                     and attribute_row.attnum = any(constraint_row.conkey)
                    where constraint_row.conrelid = 'workspaces'::regclass
                      and constraint_row.contype = 'c'
                      and attribute_row.attname = 'kind'
                    """
                )
            )
        )

    return [
        constraint["name"]
        for constraint in sa.inspect(bind).get_check_constraints("workspaces")
        if constraint.get("name") and "kind" in constraint.get("sqltext", "").lower()
    ]


def _replace_workspace_kind_check(*, allow_linked: bool) -> None:
    for constraint_name in _workspace_kind_constraint_names():
        op.drop_constraint(op.f(constraint_name), "workspaces", type_="check")

    allowed_kinds = (
        "'personal', 'corporate', 'linked'" if allow_linked else "'personal', 'corporate'"
    )
    op.create_check_constraint(
        op.f("ck_workspaces_kind"),
        "workspaces",
        f"kind in ({allowed_kinds})",
    )


def upgrade() -> None:
    _replace_workspace_kind_check(allow_linked=True)

    for column_name, target_table, constraint_name in PROOF_FOREIGN_KEYS:
        op.add_column("account_merge_intents", sa.Column(column_name, sa.Uuid(), nullable=True))
        op.create_foreign_key(
            constraint_name,
            "account_merge_intents",
            target_table,
            [column_name],
            ["id"],
        )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(CURRENT_USER_LINEAGE_HELPER)
        op.execute(CURRENT_USER_OWNS_LINEAGE_WORKSPACE_HELPER)
        op.execute("drop policy if exists referral_attributions_user_history on referral_attributions")
        op.execute(REFERRAL_LINEAGE_POLICY)
        op.execute(
            "create policy trial_activations_lineage_history on trial_activations "
            "for select using (rec_context_kind() in ('request', 'worker') "
            "and rec_current_user_lineage_contains(user_id))"
        )
        op.execute("drop policy if exists fair_use_reviews_tenant_isolation on fair_use_reviews")
        op.execute(FAIR_USE_LINEAGE_POLICY)
        op.execute(EXACT_PROOF_ACCOUNT_MERGE_CONTEXT)


def downgrade() -> None:
    linked_workspace_count = op.get_bind().execute(
        sa.text("select count(*) from workspaces where kind = 'linked'")
    ).scalar_one()
    if linked_workspace_count:
        raise RuntimeError(
            "cannot downgrade linked workspace migration while linked workspaces exist"
        )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(LEGACY_ACCOUNT_MERGE_CONTEXT)
        op.execute("drop policy if exists fair_use_reviews_tenant_isolation on fair_use_reviews")
        op.execute(LEGACY_FAIR_USE_POLICY)
        op.execute("drop policy if exists trial_activations_lineage_history on trial_activations")
        op.execute("drop policy if exists referral_attributions_user_history on referral_attributions")
        op.execute(LEGACY_REFERRAL_USER_HISTORY_POLICY)
        op.execute("drop function if exists rec_current_user_owns_lineage_workspace(uuid)")
        op.execute("drop function if exists rec_current_user_lineage_contains(uuid)")

    for column_name, _target_table, constraint_name in reversed(PROOF_FOREIGN_KEYS):
        op.drop_constraint(constraint_name, "account_merge_intents", type_="foreignkey")
        op.drop_column("account_merge_intents", column_name)

    _replace_workspace_kind_check(allow_linked=False)
