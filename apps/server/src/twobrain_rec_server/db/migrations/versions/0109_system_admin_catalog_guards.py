"""Close optimistic-concurrency and audit gaps in catalog mutations."""

from alembic import op

revision: str = "0109_system_admin_catalog_guards"
down_revision: str | None = "0108_system_admin_mutation_audit"
branch_labels: str | None = None
depends_on: str | None = None

AUTHORITY = "twobrain_rec_system_authority"
SYSTEM = "twobrain_rec_system"


def _replace(signature: str, old: str, new: str) -> None:
    qualified = signature if "." in signature else f"system_control.{signature}"
    replacement = "''" if new == "" else f"$replacement${new}$replacement$"
    op.execute(
        f"""
        do $$
        declare source text; updated text;
        begin
          select pg_get_functiondef('{qualified}'::regprocedure) into source;
          if source is null or position($needle${old}$needle$ in source)=0 then
            raise exception '0109 expected function text was not found: {qualified}';
          end if;
          updated := replace(source, $needle${old}$needle$, {replacement});
          execute updated;
        end $$;
        """
    )


def upgrade() -> None:
    op.execute(
        """
        create table if not exists system_control.catalog_mutation_idempotency(
          principal_id uuid not null references system_control.principals(id),
          command varchar(64) not null,
          idempotency_key uuid not null,
          request_hash varchar(64) not null,
          result jsonb,
          created_at timestamptz not null default clock_timestamp(),
          primary key(principal_id,command,idempotency_key)
        )
        """
    )
    op.execute("revoke all on system_control.catalog_mutation_idempotency from public")
    op.execute(
        "grant select,insert,update on system_control.catalog_mutation_idempotency "
        f"to {AUTHORITY}"
    )
    op.execute("alter table public.promotion_code_batches add column if not exists request_hash varchar(64)")
    op.execute(
        """
        create or replace function system_control.issue_promotion_codes(
          p_campaign uuid, p_key text, p_hashes jsonb, p_targets jsonb, p_request_hash text
        ) returns jsonb language plpgsql security definer
        set search_path=pg_catalog,public,pg_temp as $$
        declare c record; b record; result jsonb;
        begin
          if not system_control.permission_allowed('promotions.manage','campaign',p_campaign) then
            return jsonb_build_object('error','access_denied');
          end if;
          if p_request_hash is null or p_request_hash !~ '^[0-9a-f]{64}$' then
            return jsonb_build_object('error','invalid_batch');
          end if;
          select id into c from public.promotion_campaigns where id=p_campaign for update;
          select id,request_hash,code_count,code_ids into b
            from public.promotion_code_batches
           where campaign_id=p_campaign and idempotency_key=p_key
           for update;
          if b.id is not null then
            if b.request_hash is distinct from p_request_hash then
              return jsonb_build_object('error','idempotency_conflict');
            end if;
            return jsonb_build_object('duplicate',true,'batch_id',b.id,'code_count',b.code_count,'code_ids',b.code_ids);
          end if;
          result := system_control.issue_promotion_codes(p_campaign,p_key,p_hashes,p_targets);
          if result->>'error' is null then
            update public.promotion_code_batches set request_hash=p_request_hash
             where campaign_id=p_campaign and idempotency_key=p_key;
          elsif result->>'duplicate'='true' then
            select id,request_hash,code_count,code_ids into b
              from public.promotion_code_batches
             where campaign_id=p_campaign and idempotency_key=p_key
             for update;
            if b.request_hash is distinct from p_request_hash then
              return jsonb_build_object('error','idempotency_conflict');
            end if;
          end if;
          return result;
        end $$
        """
    )
    op.execute("revoke all on function system_control.issue_promotion_codes(uuid,text,jsonb,jsonb,text) from public")
    op.execute(f"alter function system_control.issue_promotion_codes(uuid,text,jsonb,jsonb,text) owner to {AUTHORITY}")
    op.execute(f"grant execute on function system_control.issue_promotion_codes(uuid,text,jsonb,jsonb,text) to {SYSTEM}")
    # The legacy overload is an implementation detail of the guarded wrapper;
    # callers must provide a payload hash through the five-argument command.
    op.execute(f"revoke execute on function system_control.issue_promotion_codes(uuid,text,jsonb,jsonb) from {SYSTEM}")
    # Access is mediated by the security-definer helpers below.  The runtime
    # role must not receive direct table privileges in the system schema.
    # Reconcile legacy counters before any writer can use the campaign cap.
    # Older reservation flows could reuse a released row without replaying the
    # insert trigger, leaving reserved_count below the ledger truth.
    op.execute(
        """
        update public.promotion_campaigns c
           set reserved_count = counts.reserved_count,
               redeemed_count = counts.redeemed_count
          from (
            select c0.id,
                   count(*) filter (where r.state='reserved')::integer as reserved_count,
                   count(*) filter (where r.state='redeemed')::integer as redeemed_count
              from public.promotion_campaigns c0
              left join public.promotion_redemptions r on r.campaign_id=c0.id
             group by c0.id
          ) counts
         where c.id=counts.id
        """
    )
    _replace(
        "system_control.list_catalog_plans(uuid)",
        "left join public.billing_plan_versions v on v.id=p.current_version_id",
        "left join public.billing_plan_versions v on v.id=coalesce(p.current_version_id,(select dv.id from public.billing_plan_versions dv where dv.plan_id=p.id and dv.status='draft' order by dv.version desc limit 1))",
    )
    _replace(
        "system_control.create_promotion_campaign(text,text,text,text,text,integer,integer,text,uuid,integer,bigint,timestamptz,timestamptz,text)",
        "or p_plan is null or p_kind not in ('discount','gift')",
        "or p_plan is null or not exists(select 1 from public.billing_plans bp join public.billing_plan_versions bpv on bpv.id=bp.current_version_id where bp.code=p_plan and bp.sales_state='open' and bpv.status='published') or p_kind not in ('discount','gift')",
    )
    _replace(
        "system_control.get_user_detail(uuid)",
        "'subscription',(select jsonb_build_object(",
        "'subscriptions',coalesce((select jsonb_agg(jsonb_build_object(\n                'workspace_id',s.workspace_id,'billing_owner_id',s.billing_owner_id,'state',s.state,\n                'plan_code',s.plan_code,'cycle',s.cycle,'paid_through',s.paid_through,\n                'trial_ends_at',s.trial_ends_at,'recurring_allowed',s.recurring_allowed,\n                'schedule_version',s.schedule_version,'application_version',s.application_version) order by s.workspace_id)\n              from public.workspace_subscriptions s where exists (select 1 from public.workspaces w where w.id=s.workspace_id and (w.owner_user_id=p_user or exists (select 1 from public.workspace_memberships m where m.workspace_id=w.id and m.user_id=p_user and m.status='active')))),'[]'::jsonb),\n            'subscription',(select jsonb_build_object(",
    )
    # Denials from catalog/promotion functions must survive the command
    # transaction and retain the requested action/reason.
    op.execute(
        """
        create or replace function system_control.begin_catalog_mutation(
          p_command text, p_key uuid, p_request_hash text
        ) returns jsonb language plpgsql security definer
        set search_path=pg_catalog,public,pg_temp as $$
        declare a record; existing record; inserted_hash text;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null or p_command is null or p_command !~ '^[a-z][a-z0-9._-]{0,63}$'
             or p_key is null or p_request_hash is null or p_request_hash !~ '^[0-9a-f]{64}$' then
            return jsonb_build_object('error','access_denied');
          end if;
          insert into system_control.catalog_mutation_idempotency(
            principal_id,command,idempotency_key,request_hash
          ) values(a.principal_id,p_command,p_key,p_request_hash)
          on conflict (principal_id,command,idempotency_key) do nothing
          returning request_hash into inserted_hash;
          if found then
            return jsonb_build_object('_new',true);
          end if;
          select request_hash,result into existing
            from system_control.catalog_mutation_idempotency
           where principal_id=a.principal_id and command=p_command and idempotency_key=p_key
           for update;
          if existing.request_hash<>p_request_hash then
            return jsonb_build_object('error','idempotency_conflict');
          end if;
          if existing.result is null then
            return jsonb_build_object('error','idempotency_in_progress');
          end if;
          return jsonb_build_object('_cached_result',existing.result);
        end $$
        """
    )
    op.execute(
        """
        create or replace function system_control.finish_catalog_mutation(
          p_command text, p_key uuid, p_result jsonb
        ) returns boolean language plpgsql security definer
        set search_path=pg_catalog,public,pg_temp as $$
        declare a record;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null or p_command is null or p_command !~ '^[a-z][a-z0-9._-]{0,63}$'
             or p_key is null then
            return false;
          end if;
          update system_control.catalog_mutation_idempotency
             set result=p_result
           where principal_id=a.principal_id and command=p_command and idempotency_key=p_key;
          return found;
        end $$
        """
    )
    for signature in (
        "begin_catalog_mutation(text,uuid,text)",
        "finish_catalog_mutation(text,uuid,jsonb)",
        "issue_promotion_codes(uuid,text,jsonb,jsonb,text)",
    ):
        op.execute(f"revoke all on function system_control.{signature} from public")
        op.execute(f"alter function system_control.{signature} owner to {AUTHORITY}")
        op.execute(f"grant execute on function system_control.{signature} to {SYSTEM}")

    op.execute(
        """
        create or replace function system_control.record_admin_denial(
          p_permission text, p_action text, p_target_type text, p_target_id uuid, p_reason text
        ) returns uuid language plpgsql security definer
        set search_path=pg_catalog,public,pg_temp as $$
        declare a record; event_id uuid;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null or p_reason is null or length(btrim(p_reason)) not between 10 and 500
             or p_action is null or p_action !~ '^[a-z][a-z0-9._-]{0,39}$'
             or (p_target_type is null) <> (p_target_id is null) then
            return null;
          end if;
          event_id := gen_random_uuid();
          insert into system_control.audit_events(
            id,principal_id,session_id,role,permission,action,target_type,target_id,result,reason,occurred_at
          ) values(event_id,a.principal_id,a.session_id,a.role,p_permission,p_action,p_target_type,p_target_id,
                   'denied',btrim(p_reason),statement_timestamp());
          return event_id;
        end $$
        """
    )
    op.execute("revoke all on function system_control.record_admin_denial(text,text,text,uuid,text) from public")
    op.execute(f"alter function system_control.record_admin_denial(text,text,text,uuid,text) owner to {AUTHORITY}")
    op.execute(f"grant execute on function system_control.record_admin_denial(text,text,text,uuid,text) to {SYSTEM}")

    # Add a compare-and-swap wrapper while preserving the old SQL signature
    # for existing internal callers during the migration window.
    op.execute(
        """
        create or replace function system_control.publish_catalog_plan(
          p_plan uuid, p_version uuid, p_expected_version integer
        ) returns jsonb language plpgsql security definer
        set search_path=pg_catalog,public,pg_temp as $$
        declare current_version integer;
        begin
          select version into current_version from public.billing_plans where id=p_plan for update;
          if current_version is null then return jsonb_build_object('error','not_found'); end if;
          if p_expected_version is null or current_version<>p_expected_version then
            return jsonb_build_object('error','version_conflict','version',current_version);
          end if;
          return system_control.publish_catalog_plan(p_plan,p_version);
        end $$
        """
    )
    op.execute(
        """
        create or replace function system_control.set_catalog_plan_state(
          p_plan uuid, p_state text, p_expected_version integer
        ) returns jsonb language plpgsql security definer
        set search_path=pg_catalog,public,pg_temp as $$
        declare current_version integer;
        begin
          select version into current_version from public.billing_plans where id=p_plan for update;
          if current_version is null then return jsonb_build_object('error','not_found'); end if;
          if p_expected_version is null or current_version<>p_expected_version then
            return jsonb_build_object('error','version_conflict','version',current_version);
          end if;
          return system_control.set_catalog_plan_state(p_plan,p_state);
        end $$
        """
    )
    op.execute(
        """
        create or replace function system_control.set_promotion_campaign_state(
          p_id uuid, p_state text, p_expected_version integer
        ) returns jsonb language plpgsql security definer
        set search_path=pg_catalog,public,pg_temp as $$
        declare current_version integer;
        begin
          select version into current_version from public.promotion_campaigns where id=p_id for update;
          if current_version is null then return jsonb_build_object('error','not_found'); end if;
          if p_expected_version is null or current_version<>p_expected_version then
            return jsonb_build_object('error','version_conflict','version',current_version);
          end if;
          return system_control.set_promotion_campaign_state(p_id,p_state);
        end $$
        """
    )
    for signature in (
        "publish_catalog_plan(uuid,uuid,integer)",
        "set_catalog_plan_state(uuid,text,integer)",
        "set_promotion_campaign_state(uuid,text,integer)",
    ):
        op.execute(f"revoke all on function system_control.{signature} from public")
        op.execute(f"alter function system_control.{signature} owner to {AUTHORITY}")
        op.execute(f"grant execute on function system_control.{signature} to {SYSTEM}")

    # Management reasons use the same minimum as every other sensitive action.
    for signature in (
        "invite_administrator(text,text,timestamptz,text,text)",
        "update_administrator(uuid,integer,text,text,timestamptz,text)",
        "resend_administrator_invitation(uuid,integer,text,text)",
        "create_administrator_grant(uuid,integer,text,text,uuid,timestamptz,text)",
        "revoke_administrator_grant(uuid,integer,text)",
    ):
        _replace(signature, "not between 1 and 1000", "not between 10 and 500")
    _replace(
        "system_control.auth_rate_limit(text,text,uuid)",
        "delete from system_control.rate_limits where bucket_hash=p_bucket and kind=p_kind\n            and window_start<=clock_timestamp()-interval '15 minutes';",
        "delete from system_control.rate_limits where window_start<=clock_timestamp()-interval '15 minutes';",
    )
    _replace(
        "system_control.claim_subscription_operation(uuid,uuid)",
        "and s.absolute_expires_at>clock_timestamp() and r.version=o.assignment_version",
        "and s.absolute_expires_at>clock_timestamp() and s.last_interaction_at>clock_timestamp()-interval '30 minutes'\n              and s.mfa_at>clock_timestamp()-interval '5 minutes' and r.version=o.assignment_version",
    )


def downgrade() -> None:
    _replace(
        "system_control.get_user_detail(uuid)",
        "'subscriptions',coalesce((select jsonb_agg(jsonb_build_object(\n                'workspace_id',s.workspace_id,'billing_owner_id',s.billing_owner_id,'state',s.state,\n                'plan_code',s.plan_code,'cycle',s.cycle,'paid_through',s.paid_through,\n                'trial_ends_at',s.trial_ends_at,'recurring_allowed',s.recurring_allowed,\n                'schedule_version',s.schedule_version,'application_version',s.application_version) order by s.workspace_id)\n              from public.workspace_subscriptions s where exists (select 1 from public.workspaces w where w.id=s.workspace_id and (w.owner_user_id=p_user or exists (select 1 from public.workspace_memberships m where m.workspace_id=w.id and m.user_id=p_user and m.status='active')))),'[]'::jsonb),\n            'subscription',(select jsonb_build_object(",
        "'subscription',(select jsonb_build_object(",
    )
    _replace(
        "system_control.list_catalog_plans(uuid)",
        "left join public.billing_plan_versions v on v.id=coalesce(p.current_version_id,(select dv.id from public.billing_plan_versions dv where dv.plan_id=p.id and dv.status='draft' order by dv.version desc limit 1))",
        "left join public.billing_plan_versions v on v.id=p.current_version_id",
    )
    _replace(
        "system_control.create_promotion_campaign(text,text,text,text,text,integer,integer,text,uuid,integer,bigint,timestamptz,timestamptz,text)",
        "or p_plan is null or not exists(select 1 from public.billing_plans bp join public.billing_plan_versions bpv on bpv.id=bp.current_version_id where bp.code=p_plan and bp.sales_state='open' and bpv.status='published') or p_kind not in ('discount','gift')",
        "or p_plan is null or p_kind not in ('discount','gift')",
    )
    _replace(
        "system_control.auth_rate_limit(text,text,uuid)",
        "delete from system_control.rate_limits where window_start<=clock_timestamp()-interval '15 minutes';",
        "delete from system_control.rate_limits where bucket_hash=p_bucket and kind=p_kind\n            and window_start<=clock_timestamp()-interval '15 minutes';",
    )
    _replace(
        "system_control.claim_subscription_operation(uuid,uuid)",
        "and s.absolute_expires_at>clock_timestamp() and s.last_interaction_at>clock_timestamp()-interval '30 minutes'\n              and s.mfa_at>clock_timestamp()-interval '5 minutes' and r.version=o.assignment_version",
        "and s.absolute_expires_at>clock_timestamp() and r.version=o.assignment_version",
    )
    for signature in (
        "system_control.invite_administrator(text,text,timestamptz,text,text)",
        "system_control.update_administrator(uuid,integer,text,text,timestamptz,text)",
        "system_control.resend_administrator_invitation(uuid,integer,text,text)",
        "system_control.create_administrator_grant(uuid,integer,text,text,uuid,timestamptz,text)",
        "system_control.revoke_administrator_grant(uuid,integer,text)",
    ):
        _replace(signature, "not between 10 and 500", "not between 1 and 1000")
    for signature in (
        "begin_catalog_mutation(text,uuid,text)",
        "finish_catalog_mutation(text,uuid,jsonb)",
        "issue_promotion_codes(uuid,text,jsonb,jsonb,text)",
    ):
        op.execute(f"drop function if exists system_control.{signature}")
    op.execute(f"grant execute on function system_control.issue_promotion_codes(uuid,text,jsonb,jsonb) to {SYSTEM}")
    for signature in (
        "publish_catalog_plan(uuid,uuid,integer)",
        "set_catalog_plan_state(uuid,text,integer)",
        "set_promotion_campaign_state(uuid,text,integer)",
    ):
        op.execute(f"drop function if exists system_control.{signature}")
    op.execute("drop function if exists system_control.record_admin_denial(text,text,text,uuid,text)")
    op.execute("alter table public.promotion_code_batches drop column if exists request_hash")
    op.execute("drop table if exists system_control.catalog_mutation_idempotency")
