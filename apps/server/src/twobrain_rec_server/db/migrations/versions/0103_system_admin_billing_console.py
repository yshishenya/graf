"""Expose a bounded billing/catalog surface to the isolated system console.

The application role never receives direct access to customer billing tables.
Security-definer projections and commands are owned by the existing authority
role and validate the authenticated system context before touching rows.
"""

from alembic import op

revision = "0103_system_admin_billing_console"
down_revision = "0102_worker_workspace_locks"
branch_labels = None
depends_on = None

AUTHORITY = "twobrain_rec_system_authority"
SYSTEM = "twobrain_rec_system"


def _fn(signature: str, returns: str, body: str, *, grant: bool = True) -> None:
    op.execute(
        f"create or replace function system_control.{signature} returns {returns} "
        "language plpgsql security definer set search_path=pg_catalog,public,pg_temp as $$ "
        f"{body} $$"
    )
    op.execute(f"revoke all on function system_control.{signature} from public")
    op.execute(f"alter function system_control.{signature} owner to {AUTHORITY}")
    if grant:
        op.execute(f"grant execute on function system_control.{signature} to {SYSTEM}")


def upgrade() -> None:
    # Campaigns created before the console remain valid discount campaigns.
    op.execute("alter table promotion_campaigns add column if not exists status varchar(16) not null default 'draft'")
    op.execute("alter table promotion_campaigns add column if not exists version integer not null default 1")
    op.execute("alter table promotion_campaigns add column if not exists benefit_kind varchar(16) not null default 'discount'")
    op.execute("alter table promotion_campaigns add column if not exists gift_days integer")
    op.execute("alter table promotion_campaigns add column if not exists audience varchar(32) not null default 'all'")
    op.execute("alter table promotion_campaigns add column if not exists target_user_id uuid references user_identities(id)")
    op.execute("alter table promotion_campaigns add column if not exists budget_minor bigint")
    op.execute("alter table promotion_campaigns add column if not exists budget_used_minor bigint not null default 0")
    op.execute("alter table promotion_campaigns add column if not exists display_name varchar(120)")
    op.execute("update promotion_campaigns set status=case when enabled then 'active' else 'draft' end where status='draft'")
    op.execute("""create table if not exists promotion_codes (
        id uuid primary key default gen_random_uuid(),
        campaign_id uuid not null references promotion_campaigns(id),
        code_hash varchar(64) not null unique,
        state varchar(16) not null default 'available'
          check(state in ('available','reserved','redeemed','revoked')),
        target_user_id uuid references user_identities(id),
        reserved_at timestamptz, redeemed_at timestamptz, revoked_at timestamptz,
        created_at timestamptz not null default now())""")
    op.execute("create index if not exists ix_promotion_codes_campaign on promotion_codes(campaign_id,state)")
    op.execute("""create table if not exists promotion_code_batches (
        id uuid primary key default gen_random_uuid(), campaign_id uuid not null references promotion_campaigns(id),
        idempotency_key varchar(240) not null, code_ids json not null default '[]', code_count integer not null,
        created_at timestamptz not null default now(), unique(campaign_id,idempotency_key))""")
    # A workspace may try another code after a failed/expired attempt. The
    # reservation key remains the idempotency boundary.
    op.execute("alter table promotion_redemptions drop constraint if exists uq_promotion_redemptions_workspace_campaign")

    for table in ("billing_plans", "billing_plan_versions", "billing_plan_prices",
                  "promotion_campaigns", "promotion_codes", "promotion_redemptions",
                  "promotion_code_batches",
                  "billing_invoices", "billing_operations", "billing_entitlement_grants",
                  "observed_provider_refunds", "workspace_subscriptions"):
        op.execute(f"grant usage on schema public to {AUTHORITY}")
        op.execute(f"grant select on {table} to {AUTHORITY}")
        op.execute(f"drop policy if exists system_admin_authority_read on {table}")
        # The function executes with ``current_user=AUTHORITY`` while the
        # connection's session_user remains the isolated system login.  A
        # public policy guarded by current_user works with FORCE RLS even when
        # the authority role is deliberately NOLOGIN/NOBYPASSRLS.
        op.execute(f"create policy system_admin_authority_read on {table} for select using (current_user='{AUTHORITY}')")
    for table in ("billing_plans", "billing_plan_versions", "billing_plan_prices",
                  "promotion_campaigns", "promotion_codes", "promotion_code_batches"):
        op.execute(f"drop policy if exists system_admin_authority_write on {table}")
        op.execute(f"create policy system_admin_authority_write on {table} for all using (current_user='{AUTHORITY}') with check (current_user='{AUTHORITY}')")
    op.execute("grant insert,update on billing_plans,billing_plan_versions,billing_plan_prices to " + AUTHORITY)
    op.execute("grant insert,update on promotion_campaigns,promotion_codes to " + AUTHORITY)
    # The idempotency lookup uses FOR UPDATE, which requires UPDATE in
    # addition to SELECT even though the function never exposes a direct row
    # update path.
    op.execute("grant insert,update on promotion_code_batches to " + AUTHORITY)

    _fn("list_billing_subscriptions(p_after uuid,p_plan text,p_state text)", "jsonb", """
        declare a record; result jsonb;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null or not system_control.permission_allowed('billing.read',null,null) then return null; end if;
          if length(coalesce(p_plan,''))>32 or length(coalesce(p_state,''))>32 then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select s.workspace_id,s.billing_owner_id,s.state,s.plan_code,s.cycle,s.capacity_bytes,
              s.trial_ends_at,s.paid_through,s.recurring_allowed,s.next_charge_at,s.schedule_version,
              s.pin_state,s.pinned_plan_version_id,s.pinned_price_id,
              coalesce(inv.invoice_count,0) invoice_count,coalesce(inv.paid_amount_minor_rub,0) paid_amount_minor_rub,
              coalesce(ref.refunded_amount_minor_rub,0) refunded_amount_minor_rub,
              inv.last_payment_at
            from public.workspace_subscriptions s
            left join lateral (select count(*) invoice_count,
              sum(case when i.status='succeeded' and i.currency='RUB' then i.amount_minor else 0 end) paid_amount_minor_rub,
              max(case when i.status='succeeded' then i.created_at end) last_payment_at
              from public.billing_invoices i where i.workspace_id=s.workspace_id) inv on true
            left join lateral (select sum(case when r.status='succeeded' and r.currency='RUB' then r.amount_minor else 0 end) refunded_amount_minor_rub
              from public.observed_provider_refunds r where r.workspace_id=s.workspace_id) ref on true
            where (p_after is null or s.workspace_id>p_after)
              and (p_plan is null or s.plan_code=p_plan) and (p_state is null or s.state=p_state)
            order by s.workspace_id limit 101) rows;
          return result;
        end""")

    _fn("list_billing_invoices(p_after uuid,p_workspace uuid,p_status text)", "jsonb", """
        declare a record; result jsonb;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null or not system_control.permission_allowed('billing.read',null,null) then return null; end if;
          if length(coalesce(p_status,''))>32 then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select i.id,i.safe_number,i.workspace_id,i.operation_id,i.amount_minor,i.currency,i.status,
              i.created_at, o.kind operation_kind,o.state operation_state,
              case when i.plan_snapshot ? 'catalog_snapshot' then i.plan_snapshot->'catalog_snapshot'->>'plan_code'
                   else i.plan_snapshot->>'plan_code' end plan_code
            from public.billing_invoices i join public.billing_operations o on o.id=i.operation_id
            where (p_after is null or i.id>p_after) and (p_workspace is null or i.workspace_id=p_workspace)
              and (p_status is null or i.status=p_status)
            order by i.id limit 101) rows;
          return result;
        end""")

    _fn("list_billing_refunds(p_after uuid,p_workspace uuid)", "jsonb", """
        declare a record; result jsonb;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null or not system_control.permission_allowed('billing.read',null,null) then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select id,workspace_id,invoice_id,shop_environment,provider_refund_id,amount_minor,currency,status,observed_at
            from public.observed_provider_refunds where (p_after is null or id>p_after)
              and (p_workspace is null or workspace_id=p_workspace) order by id limit 101) rows;
          return result;
        end""")

    _fn("list_catalog_plans(p_after uuid)", "jsonb", """
        declare result jsonb;
        begin
          if not system_control.permission_allowed('catalog.read',null,null) then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select p.id,p.code,p.display_name,p.sales_state,p.version,p.current_version_id,
              v.id version_id,v.version version_number,v.status version_status,v.publication_revision,
              v.capabilities,v.display_terms,v.storage_bytes,v.processing_mode,v.enabled_for_checkout,
              v.effective_from,v.effective_until,
              coalesce(jsonb_object_agg(pr.cycle,pr.amount_minor) filter (where pr.id is not null),'{}'::jsonb) prices
            from public.billing_plans p left join public.billing_plan_versions v on v.id=p.current_version_id
              left join public.billing_plan_prices pr on pr.version_id=v.id
            where p_after is null or p.id>p_after group by p.id,v.id order by p.id limit 101) rows;
          return result;
        end""")

    _fn("list_campaigns(p_after uuid)", "jsonb", """
        declare result jsonb;
        begin
          if not system_control.permission_allowed('promotions.read',null,null) then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select c.id,c.campaign_version,c.plan_code,c.cycle,c.discount_percent,c.max_redemptions,
              c.redeemed_count,c.reserved_count,c.status,c.version,c.benefit_kind,c.gift_days,c.audience,
              c.target_user_id,c.budget_minor,c.budget_used_minor,c.display_name,c.starts_at,c.ends_at,c.enabled,
              (select count(*) from public.promotion_codes pc where pc.campaign_id=c.id) code_count
            from public.promotion_campaigns c where p_after is null or c.id>p_after order by c.id limit 101) rows;
          return result;
        end""")

    _fn("create_catalog_plan(p_code text,p_display_name text,p_capabilities jsonb,p_terms jsonb,p_month bigint,p_year bigint)", "jsonb", """
        declare p public.billing_plans; v public.billing_plan_versions; result jsonb;
        begin
          if not system_control.permission_allowed('catalog.draft',null,null) then return jsonb_build_object('error','access_denied'); end if;
          if p_code is null or p_code !~ '^[a-z][a-z0-9_]{2,31}$' or p_display_name is null or length(btrim(p_display_name)) not between 1 and 80
             or p_capabilities is null or p_terms is null then return jsonb_build_object('error','invalid_catalog'); end if;
          if exists(select 1 from public.billing_plans where code=p_code) then return jsonb_build_object('error','already_exists'); end if;
          insert into public.billing_plans(code,display_name,sales_state,version) values(p_code,btrim(p_display_name),'closed',1) returning * into p;
          insert into public.billing_plan_versions(id,plan_id,plan_code,version,status,capability_schema_version,capabilities,display_terms,
            storage_bytes,processing_mode,cycle,currency,policy_snapshot)
            values(gen_random_uuid(),p.id,p_code,1,'draft',1,p_capabilities,p_terms,coalesce((p_capabilities->>'storage_bytes')::bigint,1),
              case when coalesce((p_capabilities->>'processing_unlimited')::boolean,false) then 'unlimited' else 'quota' end,'none','RUB',jsonb_build_object('offer_version','admin-draft')) returning * into v;
          if p_month is not null then insert into public.billing_plan_prices(version_id,cycle,currency,amount_minor) values(v.id,'month','RUB',p_month); end if;
          if p_year is not null then insert into public.billing_plan_prices(version_id,cycle,currency,amount_minor) values(v.id,'year','RUB',p_year); end if;
          return jsonb_build_object('id',p.id,'code',p.code,'version_id',v.id,'version',v.version,'status',v.status);
        exception when unique_violation then return jsonb_build_object('error','already_exists');
        end""")

    _fn("publish_catalog_plan(p_plan uuid,p_version uuid)", "jsonb", """
        declare p public.billing_plans; v public.billing_plan_versions; result jsonb;
        begin
          if not system_control.permission_allowed('catalog.publish',null,null) then return jsonb_build_object('error','access_denied'); end if;
          select * into p from public.billing_plans where id=p_plan for update;
          select * into v from public.billing_plan_versions where id=p_version and plan_id=p_plan for update;
          if p.id is null or v.id is null or v.status<>'draft' or exists(select 1 from public.billing_plan_prices where version_id=v.id) = false
             or (v.plan_code not in ('free','trial') and (select count(*) from public.billing_plan_prices where version_id=v.id and cycle in ('month','year'))<>2) then
            return jsonb_build_object('error','invalid_catalog'); end if;
          update public.billing_plan_versions set status='retired',enabled_for_checkout=false,publication_revision=publication_revision+1
            where plan_id=p.id and status='published';
          update public.billing_plan_versions set status='published',enabled_for_checkout=true,publication_revision=publication_revision+1 where id=v.id;
          update public.billing_plans set current_version_id=v.id,sales_state='open',version=version+1 where id=p.id;
          return jsonb_build_object('id',p.id,'version_id',v.id,'status','published','version',p.version+1);
        end""")

    _fn("set_catalog_plan_state(p_plan uuid,p_state text)", "jsonb", """
        declare p public.billing_plans;
        begin
          if not system_control.permission_allowed('catalog.publish',null,null) then return jsonb_build_object('error','access_denied'); end if;
          if p_state not in ('closed','archived','open') then return jsonb_build_object('error','invalid_state'); end if;
          select * into p from public.billing_plans where id=p_plan for update;
          if p.id is null or p.current_version_id is null and p_state='open' then return jsonb_build_object('error','invalid_catalog'); end if;
          update public.billing_plans set sales_state=p_state,version=version+1 where id=p_plan;
          if p_state<>'open' then update public.billing_plan_versions set enabled_for_checkout=false where id=p.current_version_id; end if;
          return jsonb_build_object('id',p.id,'sales_state',p_state,'version',p.version+1);
        end""")

    _fn("create_promotion_campaign(p_code_hash text,p_version text,p_plan text,p_cycle text,p_kind text,p_discount integer,p_gift_days integer,p_audience text,p_target uuid,p_max integer,p_budget bigint,p_starts timestamptz,p_ends timestamptz,p_name text)", "jsonb", """
        declare c public.promotion_campaigns;
        begin
          if not system_control.permission_allowed('promotions.draft',null,null) then return jsonb_build_object('error','access_denied'); end if;
          if p_code_hash is null or p_code_hash !~ '^[0-9a-f]{64}$' or p_version is null or length(trim(p_version)) not between 1 and 64
             or p_plan is null or p_kind not in ('discount','gift') or p_max is null or p_max<1
             or (p_kind='discount' and (p_discount is null or p_discount<1 or p_discount>99))
             or (p_kind='gift' and (p_gift_days is null or p_gift_days<1 or p_gift_days>365))
             or p_audience not in ('all','never_paid','first_purchase','selected','former_paid')
             or (p_ends is not null and p_starts is not null and p_ends<=p_starts) then return jsonb_build_object('error','invalid_campaign'); end if;
          insert into public.promotion_campaigns(id,code_hash,campaign_version,plan_code,cycle,discount_percent,max_redemptions,
            starts_at,ends_at,enabled,status,benefit_kind,gift_days,audience,target_user_id,budget_minor,display_name)
            values(gen_random_uuid(),p_code_hash,p_version,p_plan,p_cycle,coalesce(p_discount,0),p_max,p_starts,p_ends,false,'draft',p_kind,p_gift_days,p_audience,p_target,p_budget,p_name) returning * into c;
          return jsonb_build_object('id',c.id,'version',c.version,'status',c.status);
        exception when unique_violation then return jsonb_build_object('error','already_exists');
        end""")

    _fn("set_promotion_campaign_state(p_id uuid,p_state text)", "jsonb", """
        declare c public.promotion_campaigns;
        begin
          if not system_control.permission_allowed('promotions.publish',null,null) then return jsonb_build_object('error','access_denied'); end if;
          if p_state not in ('active','paused','finished','archived') then return jsonb_build_object('error','invalid_state'); end if;
          select * into c from public.promotion_campaigns where id=p_id for update;
          if c.id is null then return jsonb_build_object('error','not_found'); end if;
          update public.promotion_campaigns set status=p_state,enabled=(p_state='active'),version=version+1 where id=p_id;
          return jsonb_build_object('id',p_id,'status',p_state,'version',c.version+1);
        end""")

    _fn("issue_promotion_codes(p_campaign uuid,p_key text,p_hashes jsonb,p_targets jsonb)", "jsonb", """
        declare c public.promotion_campaigns; b public.promotion_code_batches; item text; target uuid;
                ids jsonb := '[]'::jsonb; n integer := 0; idx integer := 0;
        begin
          if not system_control.permission_allowed('promotions.manage',null,null) then return jsonb_build_object('error','access_denied'); end if;
          if p_key is null or length(trim(p_key))<1 or length(p_key)>240 or jsonb_typeof(p_hashes)<>'array'
             or jsonb_array_length(p_hashes)<1 or jsonb_array_length(p_hashes)>1000 then return jsonb_build_object('error','invalid_batch'); end if;
          select * into c from public.promotion_campaigns where id=p_campaign for update;
          if c.id is null or c.status in ('archived','finished') then return jsonb_build_object('error','campaign_unavailable'); end if;
          select * into b from public.promotion_code_batches where campaign_id=p_campaign and idempotency_key=p_key for update;
          if b.id is not null then return jsonb_build_object('duplicate',true,'batch_id',b.id,'code_count',b.code_count,'code_ids',b.code_ids); end if;
          if c.redeemed_count+c.reserved_count+jsonb_array_length(p_hashes)>c.max_redemptions then return jsonb_build_object('error','promotion_exhausted'); end if;
          for item in select jsonb_array_elements_text(p_hashes) loop
            if item !~ '^[0-9a-f]{64}$' then return jsonb_build_object('error','invalid_batch'); end if;
            target := null;
            if jsonb_typeof(p_targets)='array' and idx < jsonb_array_length(p_targets) and (p_targets->idx) is not null
              and (p_targets->idx)::text <> 'null' then target := (p_targets->>idx)::uuid; end if;
            insert into public.promotion_codes(campaign_id,code_hash,target_user_id) values(p_campaign,item,target) returning id into target;
            ids := ids || jsonb_build_array(target); n := n+1; idx := idx+1;
          end loop;
          insert into public.promotion_code_batches(campaign_id,idempotency_key,code_ids,code_count)
            values(p_campaign,p_key,ids,n) returning * into b;
          return jsonb_build_object('batch_id',b.id,'code_count',n,'code_ids',ids,'duplicate',false);
        exception when unique_violation then return jsonb_build_object('error','code_already_exists');
        end""")


def downgrade() -> None:
    for signature in (
        "set_promotion_campaign_state(uuid,text)", "create_promotion_campaign(text,text,text,text,text,integer,integer,text,uuid,integer,bigint,timestamptz,timestamptz,text)",
        "issue_promotion_codes(uuid,text,jsonb,jsonb)",
        "set_catalog_plan_state(uuid,text)", "publish_catalog_plan(uuid,uuid)",
        "create_catalog_plan(text,text,jsonb,jsonb,bigint,bigint)", "list_campaigns(uuid)",
        "list_catalog_plans(uuid)", "list_billing_refunds(uuid,uuid)",
        "list_billing_invoices(uuid,uuid,text)", "list_billing_subscriptions(uuid,text,text)",
    ):
        op.execute(f"drop function if exists system_control.{signature}")
    op.execute("drop policy if exists system_admin_authority_read on promotion_codes")
    for table in ("billing_plans", "billing_plan_versions", "billing_plan_prices", "promotion_campaigns", "promotion_codes", "promotion_code_batches"):
        op.execute(f"drop policy if exists system_admin_authority_write on {table}")
    op.execute("drop table if exists promotion_code_batches")
    op.execute("drop index if exists ix_promotion_codes_campaign")
    op.execute("drop table if exists promotion_codes")
    for column in ("display_name","budget_used_minor","budget_minor","target_user_id","audience","gift_days","benefit_kind","version","status"):
        op.execute(f"alter table promotion_campaigns drop column if exists {column}")
