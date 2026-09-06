"""Durable, target-scoped administrative operations and worker continuation."""

from collections.abc import Sequence

from alembic import op

revision: str = "0088_system_operations"
down_revision: str | None = "0087_system_scoped_authority"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTHORITY = "twobrain_rec_system_authority"
SYSTEM = "twobrain_rec_system"
WORKER = "twobrain_rec_maintenance"


def function(signature: str, returns: str, body: str, role: str | None = SYSTEM) -> None:
    op.execute(f"""create function system_control.{signature} returns {returns}
        language plpgsql volatile security definer set search_path = pg_catalog
        as $$ {body} $$""")
    op.execute(f"revoke all on function system_control.{signature} from public")
    op.execute(f"alter function system_control.{signature} owner to {AUTHORITY}")
    if role:
        op.execute(f"grant execute on function system_control.{signature} to {role}")


def upgrade() -> None:
    op.execute("""do $$ begin
        if not exists(select 1 from pg_roles where rolname='twobrain_rec_maintenance') then
          create role twobrain_rec_maintenance nologin nosuperuser nobypassrls noinherit;
        end if;
    end $$""")
    op.execute(f"grant create on schema system_control to {AUTHORITY}")
    op.execute("alter table public.meetings add column control_version bigint not null default 1")
    op.execute("""create function public.bump_meeting_control_version() returns trigger
        language plpgsql set search_path = pg_catalog as $$ begin
        new.control_version := old.control_version + 1; return new; end $$""")
    op.execute("revoke all on function public.bump_meeting_control_version() from public")
    op.execute("""create trigger bump_control_version before update on public.meetings
        for each row execute function public.bump_meeting_control_version()""")
    op.execute(f"grant select (control_version) on public.meetings to {SYSTEM}")
    op.execute(f"grant select (id,control_version,deletion_state), update(id) on public.meetings to {AUTHORITY}")
    op.execute(f"create policy system_command_authority_read on public.meetings for select to {AUTHORITY} using (true)")
    op.execute(f"create policy system_command_authority_lock on public.meetings for update to {AUTHORITY} using (true) with check (true)")
    op.execute(f"grant update(id) on system_control.principals to {AUTHORITY}")
    op.execute(f"create policy authority_lock on system_control.principals for update to {AUTHORITY} using (true) with check (true)")
    op.execute("""create table system_control.previews (
        id uuid primary key default gen_random_uuid(),
        principal_id uuid not null references system_control.principals(id),
        session_id uuid not null references system_control.sessions(id),
        command jsonb not null, permission varchar(40) not null,
        target_id uuid not null, expected_version bigint not null check (expected_version > 0),
        effect_hash varchar(64) not null,
        created_at timestamptz not null default now(),
        expires_at timestamptz not null default now() + interval '5 minutes',
        check (expires_at > created_at and expires_at <= created_at + interval '5 minutes')
    )""")
    op.execute("""create table system_control.operations (
        id uuid primary key default gen_random_uuid(),
        principal_id uuid not null references system_control.principals(id),
        session_id uuid not null references system_control.sessions(id),
        assignment_id uuid not null references system_control.role_assignments(id),
        assignment_version integer not null,
        preview_id uuid not null unique references system_control.previews(id),
        kind varchar(40) not null, command jsonb not null, permission varchar(40) not null,
        idempotency_key uuid not null, request_hash varchar(64) not null,
        state varchar(32) not null default 'queued'
            check (state in ('queued','running','awaiting_reconciliation','succeeded',
                             'partially_succeeded','failed','cancelled')),
        created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
        unique (principal_id,kind,idempotency_key)
    )""")
    op.execute("""create table system_control.operation_targets (
        operation_id uuid not null references system_control.operations(id),
        target_type varchar(24) not null, target_id uuid not null,
        expected_version bigint not null,
        state varchar(32) not null default 'queued'
            check (state in ('queued','running','awaiting_reconciliation','succeeded','failed','cancelled')),
        effect_started_at timestamptz, domain_ref uuid,
        attempt_fence bigint not null default 0,
        allowed_continuation_actions text[] not null default '{}',
        error_code varchar(40),
        primary key(operation_id,target_id)
    )""")
    op.execute("create index ix_system_operations_pending on system_control.operations(state,created_at)")
    op.execute("alter table system_control.audit_events add column operation_id uuid references system_control.operations(id)")
    for table in ("previews", "operations", "operation_targets"):
        op.execute(f"alter table system_control.{table} enable row level security")
        op.execute(f"alter table system_control.{table} force row level security")
        op.execute(f"revoke all on system_control.{table} from public")
        op.execute(f"grant select,insert,update on system_control.{table} to {AUTHORITY}")
        op.execute(f"create policy authority_only on system_control.{table} to {AUTHORITY} using (true) with check (true)")
    # Revocations and claims serialize on the same principal row, including
    # revocations executed by an operator rather than through the web process.
    function("lock_authority_principal()", "trigger", """
        begin
          perform id from system_control.principals
            where id = old.principal_id for update;
          if tg_op = 'DELETE' then return old; end if;
          if new.principal_id <> old.principal_id then
            raise exception 'system authority cannot change principal';
          end if;
          return new;
        end
    """, None)
    for table in ("sessions", "role_assignments", "permission_grants"):
        op.execute(f"""create trigger serialize_system_authority before update or delete
            on system_control.{table} for each row
            execute function system_control.lock_authority_principal()""")

    function("operation_audit(p_operation uuid, p_action text, p_result text)", "void", """
        begin
          insert into system_control.audit_events
            (id,principal_id,session_id,role,permission,action,target_type,target_id,
             result,reason,operation_id)
          select gen_random_uuid(),o.principal_id,o.session_id,r.role,o.permission,p_action,
            t.target_type,t.target_id,p_result,o.command->>'reason',o.id
          from system_control.operations o
          join system_control.role_assignments r on r.id=o.assignment_id
          join system_control.operation_targets t on t.operation_id=o.id
          where o.id=p_operation;
        end
    """, None)
    function("operation_error(p_code text, p_command jsonb)", "jsonb", """
        declare a record;
        begin
          select * into a from system_control.audit_identity();
          if a.principal_id is not null then
            insert into system_control.audit_events
              (id,principal_id,session_id,role,permission,action,result,reason)
            values(gen_random_uuid(),a.principal_id,a.session_id,a.role,'operations.manage',
              'command.denied','denied',left(p_command->>'reason',1000));
          end if;
          return jsonb_build_object('error',p_code);
        end
    """, None)
    function("preview_meeting_operation(p_command jsonb)", "jsonb", """
        declare a record; p system_control.previews; permission text; target uuid; version bigint;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null then return system_control.operation_error('access_denied',p_command); end if;
          if jsonb_typeof(p_command) <> 'object'
            or not p_command ?& array['kind','target_id','expected_version','reason']
            or (p_command - array['kind','target_id','expected_version','reason']) <> '{}'::jsonb
            or jsonb_typeof(p_command->'reason') <> 'string'
            or length(btrim(p_command->>'reason')) not between 1 and 1000
            or jsonb_typeof(p_command->'expected_version') <> 'number'
            or (p_command->>'expected_version') !~ '^[1-9][0-9]{0,17}$' then
            return system_control.operation_error('invalid_command',p_command);
          end if;
          permission := case p_command->>'kind'
            when 'meeting.reprocess' then 'processing.reprocess'
            when 'meeting.delete' then 'deletion.manage' else null end;
          begin target := (p_command->>'target_id')::uuid;
          exception when invalid_text_representation then
            return system_control.operation_error('invalid_target',p_command); end;
          if permission is null or target is null or not
            system_control.permission_allowed(permission,'meeting',target)
            then return system_control.operation_error('access_denied',p_command); end if;
          select control_version into version from public.meetings
            where id=target and deletion_state='none';
          if version is null then return system_control.operation_error('target_unavailable',p_command); end if;
          if version <> (p_command->>'expected_version')::bigint then
            return system_control.operation_error('version_conflict',p_command); end if;
          insert into system_control.previews
            (principal_id,session_id,command,permission,target_id,expected_version,effect_hash)
          values (a.principal_id,a.session_id,p_command,permission,target,version,
            encode(sha256(convert_to(p_command::text,'UTF8')),'hex')) returning * into p;
          return jsonb_build_object('preview_id',p.id,'effect_hash',p.effect_hash,
            'expires_at',p.expires_at,'expected_version',p.expected_version,'command',p.command);
        end
    """)
    function("commit_operation(p_preview uuid, p_hash text, p_key uuid)", "jsonb", """
        declare a record; p system_control.previews; o system_control.operations; version bigint;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null then return system_control.operation_error('access_denied',p.command); end if;
          perform id from system_control.principals where id=a.principal_id for update;
          select * into a from system_control.current_authority();
          if a.principal_id is null then return system_control.operation_error('access_denied',p.command); end if;
          select * into p from system_control.previews where id=p_preview
            and principal_id=a.principal_id and session_id=a.session_id;
          if p.id is null then return system_control.operation_error('preview_unavailable',p.command); end if;
          if not system_control.principal_permission(p.permission,'meeting',p.target_id)
            then return system_control.operation_error('access_denied',p.command); end if;
          select * into o from system_control.operations where principal_id=a.principal_id
            and kind=p.command->>'kind' and idempotency_key=p_key;
          if o.id is not null then
            if o.request_hash <> p_hash or p.effect_hash <> p_hash then
              return system_control.operation_error('idempotency_conflict',p.command); end if;
            return jsonb_build_object('operation_id',o.id,'state',o.state);
          end if;
          if p_key is null or p_hash is distinct from p.effect_hash then
            return system_control.operation_error('preview_conflict',p.command); end if;
          if p.expires_at <= clock_timestamp() then
            return system_control.operation_error('preview_expired',p.command); end if;
          if a.mfa_at < clock_timestamp() - interval '5 minutes' then
            return system_control.operation_error('step_up_required',p.command); end if;
          if exists (select 1 from system_control.operations where preview_id=p.id) then
            return system_control.operation_error('preview_consumed',p.command); end if;
          select control_version into version from public.meetings
            where id=p.target_id and deletion_state='none' for update;
          if version is distinct from p.expected_version then
            return system_control.operation_error('version_conflict',p.command); end if;
          insert into system_control.operations
            (principal_id,session_id,assignment_id,assignment_version,preview_id,
             kind,command,permission,idempotency_key,request_hash)
          values (a.principal_id,a.session_id,a.assignment_id,a.assignment_version,p.id,
            p.command->>'kind',p.command,p.permission,p_key,p_hash) returning * into o;
          insert into system_control.operation_targets(operation_id,target_type,target_id,expected_version)
            values(o.id,'meeting',p.target_id,p.expected_version);
          perform system_control.operation_audit(o.id,'command.commit','allowed');
          return jsonb_build_object('operation_id',o.id,'state',o.state);
        end
    """)
    function("read_operation(p_id uuid)", "jsonb", """
        declare a record; result jsonb;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null then return null; end if;
          select jsonb_build_object('operation_id',o.id,'kind',o.kind,'state',o.state,
            'actor_id',o.principal_id,'created_at',o.created_at,'updated_at',o.updated_at,
            'targets',(select jsonb_agg(jsonb_build_object('target_id',t.target_id,
              'state',t.state,'error_code',t.error_code,'effect_started_at',t.effect_started_at))
              from system_control.operation_targets t where t.operation_id=o.id))
          into result from system_control.operations o where o.id=p_id and
            (o.principal_id=a.principal_id or system_control.principal_permission('operations.read',null,null));
          return result;
        end
    """)
    # Workers receive only these checked functions, never SELECT on the schema.
    op.execute(f"grant usage on schema system_control to {WORKER}")
    function("pending_system_operations()", "table(operation_id uuid, target_id uuid)", """
        begin
          if session_user <> 'twobrain_rec_maintenance' then return; end if;
          return query select o.id,t.target_id from system_control.operations o
            join system_control.operation_targets t on t.operation_id=o.id
            where o.state in ('queued','running','awaiting_reconciliation')
              and t.state in ('queued','running','awaiting_reconciliation')
            order by o.created_at limit 100;
        end
    """, WORKER)
    function("claim_system_operation(p_id uuid, p_target uuid)", "jsonb", """
        declare o system_control.operations; t system_control.operation_targets; valid boolean; version bigint;
        begin
          if session_user <> 'twobrain_rec_maintenance' then return null; end if;
          select * into o from system_control.operations where id=p_id;
          if o.id is null then return null; end if;
          perform id from system_control.principals where id=o.principal_id for update;
          select * into t from system_control.operation_targets
            where operation_id=p_id and target_id=p_target for update;
          if t.operation_id is null or t.state <> 'queued' then return null; end if;
          select exists (select 1 from system_control.principals p
            join system_control.sessions s on s.id=o.session_id and s.principal_id=p.id
            join system_control.role_assignments r on r.id=o.assignment_id and r.principal_id=p.id
            where p.id=o.principal_id and p.status='active' and p.auth_version=s.auth_version
              and s.revoked_at is null and s.absolute_expires_at>clock_timestamp()
              and s.last_interaction_at>clock_timestamp()-interval '30 minutes'
              and r.version=o.assignment_version and r.revoked_at is null
              and r.starts_at<=clock_timestamp() and (r.expires_at is null or r.expires_at>clock_timestamp())
              and ((o.kind='meeting.delete' and r.role='superadmin')
                or (o.kind='meeting.reprocess' and r.role in ('superadmin','system_admin')))) into valid;
          if not valid then
            update system_control.operation_targets set state='cancelled',error_code='authority_revoked'
              where operation_id=p_id and target_id=p_target;
            update system_control.operations set state='cancelled',updated_at=clock_timestamp() where id=p_id;
            perform system_control.operation_audit(p_id,'command.cancel','denied');
            return null;
          end if;
          select control_version into version from public.meetings
            where id=p_target and deletion_state='none' for update;
          if version is distinct from t.expected_version then
            update system_control.operation_targets set state='failed',error_code='version_conflict'
              where operation_id=p_id and target_id=p_target;
            update system_control.operations set state='failed',updated_at=clock_timestamp() where id=p_id;
            perform system_control.operation_audit(p_id,'command.conflict','denied');
            return null;
          end if;
          update system_control.operation_targets set state='running',effect_started_at=clock_timestamp(),
            domain_ref=gen_random_uuid(),attempt_fence=attempt_fence+1,
            allowed_continuation_actions=case o.kind when 'meeting.delete'
              then array['observe','finalize','purge'] else array['observe','reconcile','finalize'] end
            where operation_id=p_id and target_id=p_target returning * into t;
          update system_control.operations set state='running',updated_at=clock_timestamp() where id=p_id;
          perform system_control.operation_audit(p_id,'command.start','allowed');
          return jsonb_build_object('operation_id',p_id,'command',o.command,'target_id',p_target,
            'domain_ref',t.domain_ref,'attempt_fence',t.attempt_fence,'mode','start');
        end
    """, WORKER)
    function("continue_system_operation(p_id uuid, p_target uuid, p_fence bigint, p_ref uuid, p_action text)", "jsonb", """
        declare o system_control.operations; t system_control.operation_targets;
        begin
          if session_user <> 'twobrain_rec_maintenance' then return null; end if;
          select * into t from system_control.operation_targets
            where operation_id=p_id and target_id=p_target for update;
          if t.effect_started_at is null or t.state not in ('running','awaiting_reconciliation')
            or t.attempt_fence is distinct from p_fence or t.domain_ref is distinct from p_ref
            or p_action is null or not p_action=any(t.allowed_continuation_actions) then return null; end if;
          select * into o from system_control.operations where id=p_id;
          return jsonb_build_object('operation_id',p_id,'command',o.command,'target_id',p_target,
            'domain_ref',t.domain_ref,'attempt_fence',t.attempt_fence,'mode',p_action);
        end
    """, WORKER)
    function("record_system_operation_result(p_id uuid, p_target uuid, p_fence bigint, p_ref uuid, p_state text)", "boolean", """
        declare t system_control.operation_targets;
        begin
          if session_user <> 'twobrain_rec_maintenance' or p_state is null
            or p_state not in ('succeeded','failed','awaiting_reconciliation') then return false; end if;
          select * into t from system_control.operation_targets
            where operation_id=p_id and target_id=p_target for update;
          if t.effect_started_at is null or t.attempt_fence is distinct from p_fence
            or t.domain_ref is distinct from p_ref then return false; end if;
          if t.state=p_state then return true; end if;
          if t.state not in ('running','awaiting_reconciliation') then return false; end if;
          update system_control.operation_targets set state=p_state where operation_id=p_id and target_id=p_target;
          update system_control.operations set state=p_state,updated_at=clock_timestamp() where id=p_id;
          perform system_control.operation_audit(p_id,'command.' || p_state,'allowed');
          return true;
        end
    """, WORKER)
    op.execute(f"revoke create on schema system_control from {AUTHORITY}")


def downgrade() -> None:
    op.execute("""do $$ begin if exists(select 1 from system_control.operations)
        then raise exception 'system operations exist; destructive downgrade refused'; end if; end $$""")
    for signature in (
        "record_system_operation_result(uuid,uuid,bigint,uuid,text)",
        "continue_system_operation(uuid,uuid,bigint,uuid,text)",
        "claim_system_operation(uuid,uuid)", "pending_system_operations()", "read_operation(uuid)",
        "commit_operation(uuid,text,uuid)", "preview_meeting_operation(jsonb)",
        "operation_audit(uuid,text,text)", "operation_error(text,jsonb)",
    ):
        op.execute(f"drop function system_control.{signature}")
    for table in ("sessions", "role_assignments", "permission_grants"):
        op.execute(f"drop trigger serialize_system_authority on system_control.{table}")
    op.execute("drop function system_control.lock_authority_principal()")
    op.execute(f"revoke usage on schema system_control from {WORKER}")
    op.execute("alter table system_control.audit_events drop column operation_id")
    for table in ("operation_targets", "operations", "previews"):
        op.drop_table(table, schema="system_control")
    op.execute("drop policy authority_lock on system_control.principals")
    op.execute(f"revoke update(id) on system_control.principals from {AUTHORITY}")
    op.execute("drop policy system_command_authority_lock on public.meetings")
    op.execute("drop policy system_command_authority_read on public.meetings")
    op.execute(f"revoke select(id,control_version,deletion_state),update(id) on public.meetings from {AUTHORITY}")
    op.execute("drop trigger bump_control_version on public.meetings")
    op.execute("drop function public.bump_meeting_control_version()")
    op.execute("alter table public.meetings drop column control_version")
