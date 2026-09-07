"""Durable, auditable subscription adjustments for the system console."""

from alembic import op

revision: str = "0104_system_admin_subscription_commands"
down_revision: str | None = "0103_system_admin_billing_console"
branch_labels: str | None = None
depends_on: str | None = None

AUTHORITY = "twobrain_rec_system_authority"
SYSTEM = "twobrain_rec_system"
WORKER = "twobrain_rec_maintenance"


def _function(signature: str, returns: str, body: str, *, role: str) -> None:
    op.execute(
        f"create or replace function system_control.{signature} returns {returns} "
        "language plpgsql security definer set search_path=pg_catalog,public,pg_temp as $$ "
        f"{body} $$"
    )
    op.execute(f"revoke all on function system_control.{signature} from public")
    op.execute(f"alter function system_control.{signature} owner to {AUTHORITY}")
    op.execute(f"grant execute on function system_control.{signature} to {role}")


def upgrade() -> None:
    # Keep the database-side maintenance allowlist in sync with the new worker
    # operation. RLS policies consult this function, so the application context
    # alone must never grant access.
    op.execute("""create or replace function rec_maintenance_allowed()
        returns boolean language sql stable as $$
        select session_user = 'twobrain_rec_maintenance'
          and rec_setting('app.context_kind') = 'maintenance'
          and rec_setting('app.maintenance_operation') = any(array[
            'migration_verification','production_smoke_setup','production_smoke_cleanup',
            'backup_restore_rehearsal','operator_diagnostics','provider_link_cleanup',
            'playback_normalization_inventory','playback_normalization_dispatch',
            'prompt_optimization','outcome_dispatch_reconciliation','summary_slots_reconciliation',
            'deletion_purge_reconciliation','outcome_initial_baseline_reconciliation',
            'billing_reconciliation','billing_notification_reconciliation','account_merge',
            'calendar_sync_reconciliation','processing_recovery_reconciliation',
            'system_billing_adjustment'])
          and rec_setting('app.maintenance_actor') is not null
          and rec_setting('app.maintenance_reason') is not null
          and rec_setting('app.maintenance_feature_area') is not null
          or (session_user = 'twobrain_rec_app' and rec_account_merge_context_valid())
        $$""")
    _function("list_subscription_adjustments(p_after uuid,p_workspace uuid)", "jsonb", """
        declare result jsonb;
        begin
          if not system_control.permission_allowed('billing.read',null,null) then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select a.id,a.workspace_id,a.subject_user_id,a.kind,a.feature_key,a.value,a.unit,
              a.plan_version_id,a.plan_mode,a.starts_at,a.ends_at,a.timezone,a.source_kind,
              a.source_ref,a.reason,a.created_at,
              (r.id is not null) revoked_at
            from public.billing_access_adjustments a
            left join public.billing_access_revocations r on r.adjustment_id=a.id
            where (p_after is null or a.id>p_after) and (p_workspace is null or a.workspace_id=p_workspace)
            order by a.id limit 101) rows;
          return result;
        end""", role=SYSTEM)

    _function("preview_subscription_operation(p_command jsonb)", "jsonb", """
        declare a record; p system_control.previews; target uuid; version bigint;
                kind text; params jsonb; reason text;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null or jsonb_typeof(p_command)<>'object'
             or not p_command ?& array['kind','target_id','expected_version','reason','parameters']
             or (p_command - array['kind','target_id','expected_version','reason','parameters']) <> '{}'::jsonb then
            return jsonb_build_object('error','invalid_command');
          end if;
          kind := p_command->>'kind'; params := p_command->'parameters'; reason := btrim(p_command->>'reason');
          if kind not in ('subscription.adjust','subscription.adjustment.revoke')
             or jsonb_typeof(params)<>'object' or length(reason) not between 10 and 500
             or (p_command->>'expected_version') !~ '^[1-9][0-9]{0,17}$' then
            return jsonb_build_object('error','invalid_command');
          end if;
          begin target := (p_command->>'target_id')::uuid; exception when others then return jsonb_build_object('error','invalid_target'); end;
          if not system_control.permission_allowed('billing.manage','subscription',target) then
            return jsonb_build_object('error','access_denied');
          end if;
          select greatest(1,coalesce(s.application_version,0)) into version
            from public.workspaces w left join public.workspace_subscriptions s on s.workspace_id=w.id
            where w.id=target;
          if version is null or version<>(p_command->>'expected_version')::bigint then
            return jsonb_build_object('error','version_conflict','current_version',version);
          end if;
          if kind='subscription.adjust' and (
             params->>'adjustment_kind' not in ('plan_interval','allow','deny','extra_quota','exact_limit')
             or params->>'source_ref' is null or params->>'starts_at' is null or params->>'ends_at' is null
             or params->>'timezone' is null) then
            return jsonb_build_object('error','invalid_command');
          end if;
          insert into system_control.previews(principal_id,session_id,command,permission,target_id,expected_version,effect_hash)
            values(a.principal_id,a.session_id,p_command,'billing.manage',target,version,
              encode(sha256(convert_to(p_command::text,'UTF8')),'hex')) returning * into p;
          return jsonb_build_object('preview_id',p.id,'expires_at',p.expires_at,'expected_version',version,
            'effect_hash',p.effect_hash,'command',p.command);
        end""", role=SYSTEM)

    _function("commit_subscription_operation(p_preview uuid,p_hash text,p_key uuid)", "jsonb", """
        declare a record; p system_control.previews; o system_control.operations;
                target uuid; version bigint;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null or p_hash is null or p_hash !~ '^[0-9a-f]{64}$' or p_key is null then
            return jsonb_build_object('error','access_denied');
          end if;
          select * into p from system_control.previews where id=p_preview for update;
          if p.id is null or p.principal_id<>a.principal_id or p.session_id<>a.session_id or p.permission<>'billing.manage' then
            return jsonb_build_object('error','preview_unavailable');
          end if;
          if p.effect_hash<>p_hash then return jsonb_build_object('error','preview_conflict'); end if;
          target := p.target_id;
          if not system_control.permission_allowed('billing.manage','subscription',target) then return jsonb_build_object('error','access_denied'); end if;
          select * into o from system_control.operations
            where principal_id=a.principal_id and kind=p.command->>'kind' and idempotency_key=p_key;
          if o.id is not null then
            if o.request_hash<>p_hash then return jsonb_build_object('error','idempotency_conflict'); end if;
            return jsonb_build_object('operation_id',o.id,'state',o.state,'kind',o.kind);
          end if;
          if p.expires_at<=clock_timestamp() then return jsonb_build_object('error','preview_expired'); end if;
          if a.mfa_at<=clock_timestamp()-interval '5 minutes' then return jsonb_build_object('error','step_up_required'); end if;
          if exists(select 1 from system_control.operations where preview_id=p.id) then
            return jsonb_build_object('error','preview_consumed'); end if;
          if not exists(select 1 from public.workspaces where id=target) then return jsonb_build_object('error','invalid_target'); end if;
          select greatest(1,coalesce(application_version,0)) into version
            from public.workspace_subscriptions where workspace_id=target;
          version := coalesce(version,1);
          if version is null or version<>p.expected_version then return jsonb_build_object('error','version_conflict','current_version',version); end if;
          insert into system_control.operations(principal_id,session_id,assignment_id,assignment_version,preview_id,kind,command,permission,idempotency_key,request_hash)
            values(a.principal_id,a.session_id,a.assignment_id,a.assignment_version,p.id,p.command->>'kind',p.command,'billing.manage',p_key,p_hash)
            on conflict (principal_id,kind,idempotency_key) do nothing;
          select * into o from system_control.operations
            where principal_id=a.principal_id and kind=p.command->>'kind' and idempotency_key=p_key;
          if o.request_hash<>p_hash then return jsonb_build_object('error','idempotency_conflict'); end if;
          insert into system_control.operation_targets(operation_id,target_type,target_id,expected_version)
            values(o.id,'subscription',target,p.expected_version) on conflict do nothing;
          perform system_control.operation_audit(o.id,'command.commit','allowed');
          return jsonb_build_object('operation_id',o.id,'state',o.state,'kind',o.kind);
        end""", role=SYSTEM)

    _function("pending_subscription_operations()", "table(operation_id uuid,target_id uuid)", """
        begin
          if session_user<>'twobrain_rec_maintenance' then return; end if;
          return query select o.id,t.target_id from system_control.operations o
            join system_control.operation_targets t on t.operation_id=o.id
            where o.kind in ('subscription.adjust','subscription.adjustment.revoke')
              and o.state in ('queued','running','awaiting_reconciliation')
              and t.state in ('queued','running','awaiting_reconciliation') order by o.created_at limit 100;
        end""", role=WORKER)

    _function("claim_subscription_operation(p_id uuid,p_target uuid)", "jsonb", """
        declare o system_control.operations; t system_control.operation_targets; valid boolean; version bigint;
        begin
          if session_user<>'twobrain_rec_maintenance' then return null; end if;
          select * into o from system_control.operations where id=p_id and kind in ('subscription.adjust','subscription.adjustment.revoke');
          if o.id is null then return null; end if;
          perform id from system_control.principals where id=o.principal_id for update;
          select * into t from system_control.operation_targets where operation_id=p_id and target_id=p_target for update;
          if t.operation_id is null or t.state<>'queued' then return null; end if;
          select exists(select 1 from system_control.principals p join system_control.sessions s on s.id=o.session_id and s.principal_id=p.id
            join system_control.role_assignments r on r.id=o.assignment_id and r.principal_id=p.id
            where p.id=o.principal_id and p.status='active' and p.auth_version=s.auth_version and s.revoked_at is null
              and s.absolute_expires_at>clock_timestamp() and r.version=o.assignment_version and r.revoked_at is null
              and r.starts_at<=clock_timestamp() and (r.expires_at is null or r.expires_at>clock_timestamp())
              and (r.role='superadmin' or exists(select 1 from system_control.permission_grants g
                where g.principal_id=p.id and g.assignment_id=r.id and g.assignment_version=r.version
                  and g.permission='billing.manage' and g.target_type='subscription' and g.target_id=p_target
                  and g.revoked_at is null and g.starts_at<=clock_timestamp() and g.expires_at>clock_timestamp()))) into valid;
          if not valid then update system_control.operation_targets set state='cancelled',error_code='authority_revoked' where operation_id=p_id and target_id=p_target;
            update system_control.operations set state='cancelled',updated_at=clock_timestamp() where id=p_id; perform system_control.operation_audit(p_id,'command.cancel','denied'); return null; end if;
          if not exists(select 1 from public.workspaces where id=p_target) then return null; end if;
          select greatest(1,coalesce(application_version,0)) into version from public.workspace_subscriptions where workspace_id=p_target;
          version := coalesce(version,1);
          if version is null or version is distinct from t.expected_version then
            update system_control.operation_targets set state='failed',error_code='version_conflict' where operation_id=p_id and target_id=p_target;
            update system_control.operations set state='failed',updated_at=clock_timestamp() where id=p_id; perform system_control.operation_audit(p_id,'command.conflict','denied'); return null; end if;
          update system_control.operation_targets set state='running',effect_started_at=clock_timestamp(),domain_ref=gen_random_uuid(),attempt_fence=attempt_fence+1,
            allowed_continuation_actions=array['observe','finalize'] where operation_id=p_id and target_id=p_target returning * into t;
          update system_control.operations set state='running',updated_at=clock_timestamp() where id=p_id;
          perform system_control.operation_audit(p_id,'command.start','allowed');
          return jsonb_build_object('operation_id',p_id,'command',o.command,'target_id',p_target,'domain_ref',t.domain_ref,'attempt_fence',t.attempt_fence,'mode','start');
        end""", role=WORKER)

    for table in ("billing_access_adjustments", "billing_access_revocations"):
        op.execute(f"grant select on public.{table} to {AUTHORITY}")
        op.execute(f"drop policy if exists system_admin_authority_read on public.{table}")
        op.execute(f"create policy system_admin_authority_read on public.{table} for select using (current_user='{AUTHORITY}')")
    op.execute("grant select on public.workspaces,public.workspace_subscriptions to " + AUTHORITY)


def downgrade() -> None:
    for signature in (
        "claim_subscription_operation(uuid,uuid)", "pending_subscription_operations()",
        "commit_subscription_operation(uuid,text,uuid)", "preview_subscription_operation(jsonb)",
        "list_subscription_adjustments(uuid,uuid)",
    ):
        op.execute(f"drop function if exists system_control.{signature}")
    for table in ("billing_access_adjustments", "billing_access_revocations"):
        op.execute(f"drop policy if exists system_admin_authority_read on public.{table}")
