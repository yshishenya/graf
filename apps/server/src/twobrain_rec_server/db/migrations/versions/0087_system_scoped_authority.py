"""Bind object permissions to assignments and persist access audit before use."""

from collections.abc import Sequence

from alembic import op

revision: str = "0087_system_scoped_authority"
down_revision: str | None = "0086_system_admin_boundary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM = "twobrain_rec_system"
AUTHORITY = "twobrain_rec_system_authority"
SCHEMA = "system_control"
# Frozen migration input, independent of future application permission changes.
ROLE_PERMISSIONS_JSON = """{
  "superadmin": [
    "admins.manage",
    "analytics.read",
    "audio.download",
    "audio.listen",
    "audit.read",
    "billing.manage",
    "billing.read",
    "catalog.draft",
    "catalog.publish",
    "catalog.read",
    "content.export",
    "content.read",
    "deletion.manage",
    "devices.read",
    "diagnostics.content",
    "exports.table",
    "fair_use.manage",
    "integrations.manage",
    "integrations.read",
    "meetings.metadata",
    "notifications.retry",
    "operations.manage",
    "operations.read",
    "processing.read",
    "processing.reprocess",
    "promotions.draft",
    "promotions.manage",
    "promotions.publish",
    "promotions.read",
    "queue.manage",
    "sessions.manage",
    "settings.manage",
    "settings.read",
    "support.manage",
    "support.read",
    "users.read"
  ],
  "system_admin": [
    "devices.read",
    "exports.table",
    "integrations.manage",
    "integrations.read",
    "meetings.metadata",
    "notifications.retry",
    "operations.manage",
    "operations.read",
    "processing.read",
    "processing.reprocess",
    "settings.manage",
    "settings.read",
    "support.manage",
    "support.read",
    "users.read"
  ],
  "support": [
    "devices.read",
    "integrations.read",
    "meetings.metadata",
    "processing.read",
    "support.manage",
    "support.read",
    "users.read"
  ],
  "billing_manager": [
    "billing.read",
    "catalog.draft",
    "catalog.read",
    "exports.table",
    "promotions.draft",
    "promotions.read",
    "users.read"
  ],
  "analyst": [
    "analytics.read",
    "exports.table"
  ],
  "auditor": [
    "audit.read",
    "exports.table"
  ]
}"""


def _function(
    signature: str, returns: str, body: str, *, sql: bool = True, public_api: bool = True
) -> None:
    language = "sql stable" if sql else "plpgsql volatile"
    op.execute(
        f"create or replace function {SCHEMA}.{signature} returns {returns} "
        f"language {language} security definer set search_path = pg_catalog as $$ {body} $$"
    )
    # Argument declarations are named only in the CREATE statement. PostgreSQL
    # accepts names in ALTER/GRANT function signatures as well.
    op.execute(f"revoke all on function {SCHEMA}.{signature} from public")
    op.execute(f"alter function {SCHEMA}.{signature} owner to {AUTHORITY}")
    if public_api:
        op.execute(f"grant execute on function {SCHEMA}.{signature} to {SYSTEM}")


def upgrade() -> None:
    op.execute(f"grant create on schema {SCHEMA} to {AUTHORITY}")
    op.execute("""
        create table system_control.permission_grants (
            id uuid primary key,
            principal_id uuid not null references system_control.principals(id),
            assignment_id uuid not null references system_control.role_assignments(id),
            assignment_version integer not null,
            version integer not null default 1,
            permission varchar(40) not null,
            target_type varchar(24) not null,
            target_id uuid not null,
            starts_at timestamptz not null, expires_at timestamptz not null,
            revoked_at timestamptz,
            granted_by uuid not null references system_control.principals(id),
            reason varchar(1000) not null,
            constraint ck_permission_grants_permission check (permission in (
                'content.read','audio.listen','audio.download','content.export','diagnostics.content',
                'billing.manage','catalog.publish','promotions.manage','promotions.publish')),
            constraint ck_permission_grants_lifetime check (
                expires_at > starts_at and expires_at <= starts_at + interval '24 hours'),
            constraint ck_permission_grants_versions check (version > 0 and assignment_version > 0)
        )
    """)
    op.execute("""
        create index ix_system_grants_scope on system_control.permission_grants
            (principal_id, permission, target_type, target_id)
    """)
    op.execute("""
        create table system_control.case_contexts (
            id uuid primary key,
            principal_id uuid not null references system_control.principals(id),
            session_id uuid not null references system_control.sessions(id),
            target_type varchar(24) not null, target_id uuid not null,
            reason varchar(1000) not null, created_at timestamptz not null default now(),
            expires_at timestamptz not null,
            constraint ck_case_contexts_lifetime check (
                expires_at > created_at and expires_at <= created_at + interval '12 hours'),
            constraint ck_case_contexts_reason check (length(btrim(reason)) between 1 and 1000)
        )
    """)
    op.execute("""
        create table system_control.audit_events (
            id uuid primary key,
            principal_id uuid not null references system_control.principals(id),
            session_id uuid not null references system_control.sessions(id),
            role varchar(24) not null, permission varchar(40) not null,
            action varchar(40) not null, target_type varchar(24), target_id uuid,
            case_context_id uuid references system_control.case_contexts(id),
            result varchar(16) not null, reason varchar(1000), occurred_at timestamptz not null default now(),
            writer_transaction bigint not null default txid_current(),
            constraint ck_audit_events_result check (result in ('allowed','denied'))
        )
    """)
    op.execute(
        "create index ix_system_audit_actor_time on system_control.audit_events (principal_id, occurred_at)"
    )
    op.execute(
        "create index ix_system_audit_target_time on system_control.audit_events (target_type, target_id, occurred_at)"
    )
    for table in ("permission_grants", "case_contexts", "audit_events"):
        op.execute(f"alter table {SCHEMA}.{table} enable row level security")
        op.execute(f"alter table {SCHEMA}.{table} force row level security")
        op.execute(f"revoke all on {SCHEMA}.{table} from public")
        op.execute(f"grant select on {SCHEMA}.{table} to {AUTHORITY}")
        op.execute(
            f"create policy authority_read on {SCHEMA}.{table} for select to {AUTHORITY} using (true)"
        )
    for table in ("case_contexts", "audit_events"):
        op.execute(f"grant insert on {SCHEMA}.{table} to {AUTHORITY}")
        op.execute(
            f"create policy authority_insert on {SCHEMA}.{table} for insert to {AUTHORITY} with check (true)"
        )

    _function(
        "current_authority()",
        """table (
        principal_id uuid, session_id uuid, role varchar, assignment_id uuid,
        assignment_version integer, mfa_at timestamptz, expires_at timestamptz)""",
        """
        select p.id, s.id, r.role, r.id, r.version, s.mfa_at, s.absolute_expires_at
        from system_control.sessions s
        join system_control.principals p on p.id = s.principal_id
        join system_control.role_assignments r on r.principal_id = p.id
        where session_user = 'twobrain_rec_system'
          and current_setting('app.context_kind', true) = 'system'
          and s.id::text = current_setting('app.system_session_id', true)
          and p.id::text = current_setting('app.system_actor_id', true)
          and s.token_hash = current_setting('app.system_session_token_hash', true)
          and p.status = 'active' and p.auth_version = s.auth_version
          and s.revoked_at is null and s.issued_at <= statement_timestamp()
          and s.absolute_expires_at > statement_timestamp()
          and s.last_interaction_at > statement_timestamp() - interval '30 minutes'
          and s.last_interaction_at <= statement_timestamp() and s.mfa_at <= statement_timestamp()
          and r.revoked_at is null and r.starts_at <= statement_timestamp()
          and (r.expires_at is null or r.expires_at > statement_timestamp())
    """,
    )
    _function(
        "audit_identity()",
        "table (principal_id uuid, session_id uuid, role varchar, expires_at timestamptz)",
        """
        select p.id, s.id, coalesce(r.role, 'unassigned')::varchar, s.absolute_expires_at
        from system_control.sessions s
        join system_control.principals p on p.id = s.principal_id
        left join system_control.role_assignments r
          on r.principal_id = p.id and r.revoked_at is null
        where session_user = 'twobrain_rec_system'
          and current_setting('app.context_kind', true) = 'system'
          and s.id::text = current_setting('app.system_session_id', true)
          and p.id::text = current_setting('app.system_actor_id', true)
          and s.token_hash = current_setting('app.system_session_token_hash', true)
    """,
        public_api=False,
    )
    _function(
        "principal_permission(p_permission text, p_type text, p_id uuid)",
        "boolean",
        f"""
        select exists (
            select 1 from system_control.current_authority() a
            where ('{ROLE_PERMISSIONS_JSON}'::jsonb -> a.role) ? p_permission
              or exists (
                select 1 from system_control.permission_grants g
                where g.principal_id = a.principal_id and g.assignment_id = a.assignment_id
                  and g.assignment_version = a.assignment_version
                  and g.permission = p_permission and g.target_type = p_type and g.target_id = p_id
                  and g.revoked_at is null and g.starts_at <= statement_timestamp()
                  and g.expires_at > statement_timestamp()
                  and (
                    (a.role in ('system_admin','support') and p_type = 'meeting'
                     and p_permission in ('content.read','audio.listen','audio.download',
                                          'content.export','diagnostics.content'))
                    or (a.role = 'billing_manager' and (
                        (p_permission = 'billing.manage' and p_type in ('user','workspace','subscription','invoice'))
                        or (p_permission = 'catalog.publish' and p_type in ('plan','plan_version'))
                        or (p_permission in ('promotions.manage','promotions.publish') and p_type = 'campaign')
                    ))
                  )
              )
        )
    """,
        public_api=False,
    )
    _function(
        "permission_allowed(p_permission text, p_type text, p_id uuid)",
        "boolean",
        """
        select coalesce(
            current_setting('app.system_permission', true) = p_permission
            and ((p_type is null and p_id is null) or
                 (p_type in ('meeting','user','workspace','subscription','invoice','plan','plan_version',
                             'campaign','device','incident','system') and p_id is not null))
            and (coalesce(current_setting('app.system_target_type', true), '') = '' or
                (current_setting('app.system_target_type', true) = p_type and
                 current_setting('app.system_target_id', true) = p_id::text))
            and system_control.principal_permission(p_permission, p_type, p_id), false)
    """,
    )
    _function(
        "case_allowed(p_type text, p_id uuid)",
        "boolean",
        """
        select exists (
            select 1 from system_control.case_contexts c
            join system_control.current_authority() a
              on c.principal_id = a.principal_id and c.session_id = a.session_id
            where c.id::text = current_setting('app.system_case_context_id', true)
              and c.target_type = p_type and c.target_id = p_id
              and c.expires_at > statement_timestamp()
        )
    """,
        public_api=False,
    )
    _function(
        "content_allowed(p_permission text, p_type text, p_id uuid)",
        "boolean",
        """
        select coalesce(
            p_permission in ('content.read','audio.listen','audio.download','content.export','diagnostics.content')
            and system_control.permission_allowed(p_permission, p_type, p_id)
            and system_control.case_allowed(p_type, p_id)
            and exists (
                select 1 from system_control.audit_events e
                join system_control.current_authority() a
                  on e.principal_id = a.principal_id and e.session_id = a.session_id
                where e.id::text = current_setting('app.system_audit_event_id', true)
                  and e.case_context_id::text = current_setting('app.system_case_context_id', true)
                  and e.permission = p_permission and e.target_type = p_type and e.target_id = p_id
                  and e.action = 'access' and e.result = 'allowed'
                  and e.writer_transaction is distinct from txid_current_if_assigned()
                  and e.occurred_at > statement_timestamp() - interval '60 seconds'
            ), false)
    """,
    )
    _function(
        "open_case_context(p_reason text)",
        "uuid",
        """
        declare a record; v_id uuid; v_type text; v_target uuid; v_allowed boolean;
        begin
            select * into a from system_control.audit_identity();
            if not found then raise insufficient_privilege using message = 'system session required'; end if;
            if p_reason is null or length(btrim(p_reason)) not between 1 and 1000 then
                raise invalid_parameter_value using message = 'case reason is required';
            end if;
            v_type := nullif(current_setting('app.system_target_type', true), '');
            v_target := nullif(current_setting('app.system_target_id', true), '')::uuid;
            if v_type is null or v_target is null then
                raise invalid_parameter_value using message = 'case target is required';
            end if;
            select exists (
                select 1 from (values
                    ('meeting','meetings.metadata'), ('meeting','content.read'),
                    ('meeting','audio.listen'), ('meeting','audio.download'),
                    ('meeting','content.export'), ('meeting','diagnostics.content'),
                    ('user','users.read'), ('workspace','users.read'), ('device','devices.read'),
                    ('subscription','billing.read'), ('invoice','billing.read'),
                    ('plan','catalog.read'), ('plan_version','catalog.read'),
                    ('campaign','promotions.read'), ('incident','support.read')
                ) as permitted(target_type, permission)
                where permitted.target_type = v_type
                  and system_control.principal_permission(permitted.permission, v_type, v_target)
            ) into v_allowed;
            if v_allowed then
                v_id := gen_random_uuid();
                insert into system_control.case_contexts
                    (id, principal_id, session_id, target_type, target_id, reason, created_at, expires_at)
                values (v_id, a.principal_id, a.session_id, v_type, v_target, btrim(p_reason),
                        statement_timestamp(), a.expires_at);
            end if;
            insert into system_control.audit_events
                (id, principal_id, session_id, role, permission, action, target_type, target_id,
                 case_context_id, result, reason, occurred_at)
            values (gen_random_uuid(), a.principal_id, a.session_id, a.role,
                    current_setting('app.system_permission', true), 'case.open', v_type, v_target,
                    v_id, case when v_allowed then 'allowed' else 'denied' end, btrim(p_reason), statement_timestamp());
            return v_id;
        end
    """,
        sql=False,
    )
    _function(
        "record_access()",
        "table (audit_event_id uuid, allowed boolean)",
        """
        declare a record; v_permission text; v_type text; v_target uuid;
                v_case uuid; v_allowed boolean; v_event uuid; v_reason text;
        begin
            select * into a from system_control.audit_identity();
            if not found then raise insufficient_privilege using message = 'system session required'; end if;
            v_permission := current_setting('app.system_permission', true);
            v_type := nullif(current_setting('app.system_target_type', true), '');
            v_target := nullif(current_setting('app.system_target_id', true), '')::uuid;
            v_allowed := system_control.permission_allowed(v_permission, v_type, v_target);
            if v_permission in ('content.read','audio.listen','audio.download','content.export','diagnostics.content') then
                v_allowed := v_allowed and system_control.case_allowed(v_type, v_target);
            end if;
            select c.id, c.reason into v_case, v_reason from system_control.case_contexts c
            where c.id::text = current_setting('app.system_case_context_id', true)
              and c.principal_id = a.principal_id and c.session_id = a.session_id
              and c.target_type = v_type and c.target_id = v_target;
            v_event := gen_random_uuid();
            insert into system_control.audit_events
                (id, principal_id, session_id, role, permission, action, target_type, target_id,
                 case_context_id, result, reason, occurred_at)
            values (v_event, a.principal_id, a.session_id, a.role, v_permission, 'access', v_type,
                    v_target, v_case, case when v_allowed then 'allowed' else 'denied' end, v_reason,
                    statement_timestamp());
            return query select v_event, v_allowed;
        end
    """,
        sql=False,
    )
    # Read-only audit projection is itself permission-scoped. No runtime gets
    # INSERT/UPDATE/DELETE directly, so actor/result fields cannot be forged.
    op.execute(f"grant select on {SCHEMA}.audit_events to {SYSTEM}")
    op.execute(f"""create policy system_audit_read on {SCHEMA}.audit_events for select to {SYSTEM}
                  using ((select {SCHEMA}.permission_allowed('audit.read', null, null)))""")
    op.execute(f"""create policy system_audit_gate on {SCHEMA}.audit_events as restrictive
                  for select to {SYSTEM}
                  using ((select {SCHEMA}.permission_allowed('audit.read', null, null)))""")
    op.execute(f"""alter policy system_metadata_gate on public.meetings using (
        (select {SCHEMA}.meeting_metadata_allowed()) and
        (coalesce(current_setting('app.system_target_id', true), '') = '' or
         (current_setting('app.system_target_type', true) = 'meeting' and
          current_setting('app.system_target_id', true) = id::text)))""")
    op.execute(f"revoke create on schema {SCHEMA} from {AUTHORITY}")


def downgrade() -> None:
    op.execute("""do $$ begin
        if exists (select 1 from system_control.audit_events)
           or exists (select 1 from system_control.permission_grants) then
            raise exception 'system authorization history exists; destructive downgrade refused';
        end if;
    end $$""")
    op.execute(
        f"alter policy system_metadata_gate on public.meetings "
        f"using ((select {SCHEMA}.meeting_metadata_allowed()))"
    )
    op.execute("drop policy system_audit_gate on system_control.audit_events")
    op.execute("drop policy system_audit_read on system_control.audit_events")
    for signature in (
        "record_access()",
        "open_case_context(text)",
        "content_allowed(text,text,uuid)",
        "case_allowed(text,uuid)",
        "permission_allowed(text,text,uuid)",
        "principal_permission(text,text,uuid)",
        "audit_identity()",
        "current_authority()",
    ):
        op.execute(f"drop function {SCHEMA}.{signature}")
    for table in ("audit_events", "case_contexts", "permission_grants"):
        op.drop_table(table, schema=SCHEMA)
