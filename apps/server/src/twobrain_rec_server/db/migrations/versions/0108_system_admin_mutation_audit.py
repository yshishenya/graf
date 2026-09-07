"""Bind catalog and promotion commands to their target and audit reason."""

from alembic import op

revision: str = "0108_system_admin_mutation_audit"
down_revision: str | None = "0107_promotion_code_rls"
branch_labels: str | None = None
depends_on: str | None = None

AUTHORITY = "twobrain_rec_system_authority"
SYSTEM = "twobrain_rec_system"


def upgrade() -> None:
    # 0103 is already present in installations that upgrade this feature. Use
    # pg_get_functiondef so the compatibility migration changes only the
    # permission argument and keeps the existing command implementation.
    replacements = (
        ("system_control.publish_catalog_plan(uuid,uuid)", "'catalog.publish',null,null", "'catalog.publish','plan',p_plan"),
        ("system_control.set_catalog_plan_state(uuid,text)", "'catalog.publish',null,null", "'catalog.publish','plan',p_plan"),
        ("system_control.set_promotion_campaign_state(uuid,text)", "'promotions.publish',null,null", "'promotions.publish','campaign',p_id"),
        ("system_control.issue_promotion_codes(uuid,text,jsonb,jsonb)", "'promotions.manage',null,null", "'promotions.manage','campaign',p_campaign"),
    )
    for signature, old, new in replacements:
        op.execute(
            f"""
            do $$
            declare source text; updated text;
            begin
              select pg_get_functiondef('{signature}'::regprocedure) into source;
              updated := replace(source, $needle${old}$needle$, $replacement${new}$replacement$);
              if updated <> source then execute updated; end if;
            end $$;
            """
        )

    # Bind the subscription list to an explicit target when the console opens
    # one user's workspace from the user card. The empty target remains the
    # unfiltered global projection.
    op.execute(
        """
        do $$
        declare source text; updated text;
        begin
          select pg_get_functiondef(
            'system_control.list_billing_subscriptions(uuid,text,text)'::regprocedure
          ) into source;
          if source is not null and position('app.system_target_type' in source) = 0 then
            updated := replace(
              source,
              $needle$where (p_after is null or s.workspace_id>p_after)$needle$,
              $replacement$where (p_after is null or s.workspace_id>p_after)
              and (rec_setting('app.system_target_type') <> 'subscription'
                   or s.workspace_id = rec_setting_uuid('app.system_target_id'))$replacement$
            );
            if updated <> source then execute updated; end if;
          end if;
        end $$;
        """
    )

    op.execute(
        """
        do $$
        declare source text; updated text;
        begin
          select pg_get_functiondef(
            'system_control.list_billing_subscriptions(uuid,text,text)'::regprocedure
          ) into source;
          if source is not null and position('s.application_version' in source) = 0 then
            updated := replace(
              source,
              $needle$s.next_charge_at,s.schedule_version,$needle$,
              $replacement$s.next_charge_at,s.schedule_version,s.application_version,$replacement$
            );
            if updated <> source then execute updated; end if;
          end if;
        end $$;
        """
    )

    op.execute(
        """
        do $$
        declare source text; updated text;
        begin
          select pg_get_functiondef('system_control.set_catalog_plan_state(uuid,text)'::regprocedure) into source;
          updated := replace(source,
            $needle$if p_state<>'open' then update public.billing_plan_versions set enabled_for_checkout=false where id=p.current_version_id; end if;$needle$,
            $replacement$if p_state<>'open' then
              update public.billing_plan_versions set enabled_for_checkout=false where id=p.current_version_id;
            else
              update public.billing_plan_versions set enabled_for_checkout=true where id=p.current_version_id;
            end if;$replacement$);
          if updated <> source then execute updated; end if;
        end $$;
        """
    )

    # Installations that already ran 0105 need the bounded alert projection as
    # well; replacing the function keeps this compatibility migration
    # idempotent without recreating the observability objects.
    op.execute(
        """
        do $$
        declare source text; updated text;
        begin
          select pg_get_functiondef('system_control.list_system_alerts()'::regprocedure)
            into source;
          if source is not null and source !~ 'order by observed_at desc limit 200' then
            updated := replace(
              source,
              $needle$) events order by observed_at desc$needle$,
              $replacement$) events order by observed_at desc limit 200$replacement$
            );
            if updated <> source then execute updated; end if;
          end if;
        end $$;
        """
    )
    op.execute(
        """
        do $$
        declare source text; updated text;
        begin
          select pg_get_functiondef('system_control.list_system_metrics(timestamptz,timestamptz)'::regprocedure) into source;
          updated := replace(source,
            $needle$from public.storage_reservations where state in ('active','reserved'))$needle$,
            $replacement$from public.storage_reservations where state in ('active','reserved')
                and (expires_at is null or expires_at > started))$replacement$);
          if updated <> source then execute updated; end if;
        end $$;
        """
    )

    op.execute(
        """
        create or replace function system_control.record_admin_mutation(
          p_permission text,
          p_action text,
          p_target_type text,
          p_target_id uuid,
          p_reason text
        ) returns uuid
        language plpgsql security definer
        set search_path=pg_catalog,public,pg_temp
        as $$
        declare a record; event_id uuid;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null then
            raise insufficient_privilege using message = 'system session required';
          end if;
          if p_permission is null or p_action is null or p_action !~ '^[a-z][a-z0-9._-]{0,39}$'
             or (p_target_type is null) <> (p_target_id is null)
             or p_reason is null or length(btrim(p_reason)) not between 10 and 500
             or not system_control.permission_allowed(p_permission,p_target_type,p_target_id) then
            raise insufficient_privilege using message = 'administrative mutation is not allowed';
          end if;
          event_id := gen_random_uuid();
          insert into system_control.audit_events(
            id,principal_id,session_id,role,permission,action,target_type,target_id,
            result,reason,occurred_at
          ) values (
            event_id,a.principal_id,a.session_id,a.role,p_permission,p_action,
            p_target_type,p_target_id,'allowed',btrim(p_reason),statement_timestamp()
          );
          return event_id;
        end
        $$
        """
    )
    op.execute("revoke all on function system_control.record_admin_mutation(text,text,text,uuid,text) from public")
    op.execute(f"alter function system_control.record_admin_mutation(text,text,text,uuid,text) owner to {AUTHORITY}")
    op.execute(f"grant execute on function system_control.record_admin_mutation(text,text,text,uuid,text) to {SYSTEM}")
    op.execute(
        """
        create or replace function system_control.get_user_detail(p_user uuid)
        returns jsonb
        language plpgsql stable security definer
        set search_path=pg_catalog,public,pg_temp
        as $$
        declare u record; v_workspace_id uuid; money boolean;
        begin
          if p_user is null or not system_control.permission_allowed('users.read','user',p_user) then
            return null;
          end if;
          select id,display_name,status,created_at,merged_into_user_id into u
            from public.user_identities where id=p_user;
          if u.id is null then return null; end if;
          select w.id into v_workspace_id from public.workspaces w
            where w.owner_user_id=p_user and w.kind='personal' order by w.id limit 1;
          money := system_control.principal_permission('billing.read',null,null);
          return jsonb_build_object(
            'id',u.id,'display_name',u.display_name,'status',u.status,'created_at',u.created_at,
            'merged_into_user_id',u.merged_into_user_id,
            'emails',coalesce((select jsonb_agg(e.email order by e.id) from public.external_identities e
              where e.user_id=p_user and e.is_active and e.is_verified),'[]'::jsonb),
            'workspaces',coalesce((select jsonb_agg(jsonb_build_object(
                'id',w.id,'name',w.name,'kind',w.kind,'role',m.role,'membership_status',m.status)
              order by w.id) from public.workspaces w join public.workspace_memberships m
                on m.workspace_id=w.id and m.user_id=p_user where w.owner_user_id=p_user or m.status='active'),'[]'::jsonb),
            'subscription',(select jsonb_build_object(
                'workspace_id',s.workspace_id,'billing_owner_id',s.billing_owner_id,'state',s.state,
                'plan_code',s.plan_code,'cycle',s.cycle,'paid_through',s.paid_through,
                'trial_ends_at',s.trial_ends_at,'recurring_allowed',s.recurring_allowed,
                'schedule_version',s.schedule_version,'application_version',s.application_version)
              from public.workspace_subscriptions s where s.workspace_id=v_workspace_id),
            'payments',case when money then coalesce((select jsonb_agg(jsonb_build_object(
                'id',i.id,'safe_number',i.safe_number,'workspace_id',i.workspace_id,
                'amount_minor',i.amount_minor,'currency',i.currency,'status',i.status,'created_at',i.created_at)
              order by i.created_at desc) from public.billing_invoices i where i.workspace_id=v_workspace_id),'[]'::jsonb)
              else '[]'::jsonb end,
            'adjustments',case when money then coalesce((select jsonb_agg(jsonb_build_object(
                'id',a.id,'workspace_id',a.workspace_id,'kind',a.kind,'feature_key',a.feature_key,
                'value',a.value,'unit',a.unit,'starts_at',a.starts_at,'ends_at',a.ends_at,
                'source_kind',a.source_kind,'reason',a.reason,'created_at',a.created_at)
              order by a.created_at desc) from public.billing_access_adjustments a where a.workspace_id=v_workspace_id),'[]'::jsonb)
              else '[]'::jsonb end,
            'financial_fields_available',money
          );
        end
        $$
        """
    )
    op.execute("revoke all on function system_control.get_user_detail(uuid) from public")
    op.execute(f"alter function system_control.get_user_detail(uuid) owner to {AUTHORITY}")
    op.execute(f"grant execute on function system_control.get_user_detail(uuid) to {SYSTEM}")

    # Smoke cleanup must not regain a broad DELETE grant after promotion RLS
    # hardening. Keep the destructive path database-owned and limited to the
    # synthetic smoke namespace; the maintenance login can only invoke this
    # helper while the allowlisted cleanup operation is active.
    op.execute(
        """
        create or replace function public.rec_smoke_cleanup_promotion_redemptions(
          p_workspace_id uuid,
          p_organization_id uuid
        ) returns integer
        language plpgsql security definer
        set search_path=pg_catalog,public,pg_temp
        as $$
        declare removed integer;
        begin
          if session_user <> 'twobrain_rec_maintenance'
             or not public.rec_maintenance_allowed()
             or public.rec_setting('app.maintenance_operation') <> 'production_smoke_cleanup'
             or p_workspace_id is null or p_organization_id is null then
            raise insufficient_privilege using message = 'smoke cleanup context required';
          end if;
          if not exists (
            select 1 from public.workspaces where id = p_workspace_id
          ) then
            return 0;
          end if;
          if not exists (
            select 1
            from public.workspaces w
            join public.organizations o on o.id = w.organization_id
            where w.id = p_workspace_id
              and w.organization_id = p_organization_id
              and w.slug like 'internal-smoke-workspace-%'
              and o.slug like 'internal-smoke-org-%'
          ) then
            raise invalid_parameter_value using message = 'smoke workspace identity is invalid';
          end if;
          delete from public.promotion_redemptions
           where workspace_id = p_workspace_id;
          get diagnostics removed = row_count;
          return removed;
        end
        $$
        """
    )
    op.execute(
        "revoke all on function public.rec_smoke_cleanup_promotion_redemptions(uuid,uuid) from public"
    )
    op.execute(
        f"alter function public.rec_smoke_cleanup_promotion_redemptions(uuid,uuid) owner to {AUTHORITY}"
    )
    op.execute(
        f"grant delete on public.promotion_redemptions to {AUTHORITY}"
    )
    op.execute(f"grant select on public.organizations to {AUTHORITY}")
    op.execute(
        "grant execute on function public.rec_smoke_cleanup_promotion_redemptions(uuid,uuid) "
        "to twobrain_rec_maintenance"
    )


def downgrade() -> None:
    op.execute(f"revoke delete on public.promotion_redemptions from {AUTHORITY}")
    op.execute(f"revoke select on public.organizations from {AUTHORITY}")
    op.execute(
        "revoke all on function public.rec_smoke_cleanup_promotion_redemptions(uuid,uuid) from public"
    )
    op.execute("drop function if exists public.rec_smoke_cleanup_promotion_redemptions(uuid,uuid)")
    op.execute("drop function if exists system_control.get_user_detail(uuid)")
    op.execute("drop function if exists system_control.record_admin_mutation(text,text,text,uuid,text)")
