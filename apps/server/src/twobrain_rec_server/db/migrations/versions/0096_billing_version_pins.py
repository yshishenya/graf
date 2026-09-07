"""Add versioned offers and resumable exact subscription pins; no sales activation."""

from collections.abc import Sequence

from alembic import op

revision: str = "0096_billing_version_pins"
down_revision: str | None = "0095_system_media_access"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY_COLUMNS = (
    ("billing_plan_versions", "amount_minor"),
    ("billing_invoices", "amount_minor"),
    ("billing_entitlement_grants", "amount_minor"),
    ("promotion_redemptions", "list_amount_minor"),
    ("promotion_redemptions", "payable_amount_minor"),
    ("observed_provider_refunds", "amount_minor"),
)


def upgrade() -> None:
    for table, column in MONEY_COLUMNS:
        op.execute(f"alter table {table} alter column {column} type bigint")
    op.execute("""create table billing_plans (
        id uuid primary key default gen_random_uuid(), code varchar(32) not null unique,
        display_name varchar(80) not null, sales_state varchar(16) not null default 'closed',
        current_version_id uuid references billing_plan_versions(id),
        version integer not null default 1, created_at timestamptz not null default now(),
        check(code ~ '^[a-z][a-z0-9_]{2,31}$'), check(length(trim(display_name)) between 1 and 80),
        check(sales_state in ('closed','open','archived')), check(version>0), unique(id,code))""")
    op.execute("""alter table billing_plan_versions
        add column plan_id uuid references billing_plans(id),
        add column status varchar(16) not null default 'legacy',
        add column capability_schema_version integer,
        add column capabilities json,
        add column display_terms json,
        add column publication_revision integer not null default 0,
        add constraint ck_billing_version_status check(status in ('legacy','draft','scheduled','published','retired')),
        add constraint ck_billing_version_definition check(status='legacy' or
          (plan_id is not null and capability_schema_version is not null and capability_schema_version=1 and capabilities is not null
           and json_typeof(capabilities)='object' and display_terms is not null
           and json_typeof(display_terms)='object')),
        add constraint uq_billing_version_plan unique(id,plan_id),
        add constraint uq_billing_version_code unique(id,plan_code),
        add constraint fk_billing_version_code foreign key(plan_id,plan_code) references billing_plans(id,code)""")
    op.execute("""alter table billing_plans add constraint fk_billing_plan_current_version
        foreign key(current_version_id,id) references billing_plan_versions(id,plan_id)""")
    op.execute("""create table billing_plan_prices (
        id uuid primary key default gen_random_uuid(),
        version_id uuid not null references billing_plan_versions(id),
        cycle varchar(16) not null check(cycle in ('month','year')),
        currency varchar(3) not null default 'RUB' check(currency='RUB'),
        amount_minor bigint not null check(amount_minor>0),
        constraint uq_billing_plan_price_cycle unique(version_id,cycle,currency),
        constraint uq_billing_plan_price_version unique(id,version_id))""")
    op.execute("""alter table workspace_subscriptions
        add column pinned_plan_version_id uuid references billing_plan_versions(id),
        add column pinned_price_id uuid references billing_plan_prices(id),
        add column timezone varchar(64) not null default 'UTC',
        add column next_charge_at timestamptz,
        add column schedule_version integer not null default 0 check(schedule_version>=0),
        add column pin_state varchar(24) not null default 'pending'
          check(pin_state in ('pending','pinned','legacy_pinned','not_applicable')),
        add column pin_checked_application_version integer,
        add column legacy_pinned_snapshot json,
        add constraint fk_subscription_price_version foreign key(pinned_price_id,pinned_plan_version_id)
          references billing_plan_prices(id,version_id),
        add constraint ck_subscription_price_has_version check(pinned_price_id is null or pinned_plan_version_id is not null),
        add constraint ck_subscription_pin_state check(pin_state<>'pinned' or pinned_plan_version_id is not null)""")
    op.execute("""create index ix_subscription_pin_catchup on workspace_subscriptions(workspace_id)
        where pin_checked_application_version is distinct from application_version or pin_state='pending'""")
    op.execute("""alter table billing_entitlement_grants
        add column plan_version_id uuid references billing_plan_versions(id),
        add constraint fk_billing_grant_version_code foreign key(plan_version_id,plan_code)
          references billing_plan_versions(id,plan_code)""")
    op.execute("create index ix_subscription_pinned_version on workspace_subscriptions(pinned_plan_version_id) where pinned_plan_version_id is not null")
    op.execute("create index ix_paid_grant_plan_version on billing_entitlement_grants(plan_version_id) where plan_version_id is not null")
    # Preserve each old row and its period. Do not merge month/year historical identities.
    op.execute("""insert into billing_plans(code,display_name)
        select distinct plan_code,plan_code from billing_plan_versions
        where plan_code ~ '^[a-z][a-z0-9_]{2,31}$' on conflict(code) do nothing""")
    op.execute("""update billing_plan_versions v set plan_id=p.id from billing_plans p
        where p.code=v.plan_code and v.plan_id is null""")
    op.execute("""insert into billing_plan_prices(version_id,cycle,currency,amount_minor)
        select id,cycle,currency,amount_minor from billing_plan_versions
        where cycle in ('month','year') and currency='RUB' and amount_minor>0""")
    for table in ("billing_plans", "billing_plan_prices"):
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"alter table {table} force row level security")
        op.execute(f"revoke all on {table} from public")
        op.execute(f"""create policy catalog_read on {table} for select using
            (rec_context_kind() in ('request','worker') or rec_maintenance_allowed())""")
        op.execute(f"""create policy catalog_write on {table} for all
            using(rec_maintenance_allowed()) with check(rec_maintenance_allowed())""")
        op.execute(f"""create policy system_direct_denied on {table} as restrictive
            to twobrain_rec_system using(false) with check(false)""")
    # Row locks serialize editing a price with publication/pinning its parent version.
    op.execute("""create function billing_guard_offer() returns trigger language plpgsql
        set search_path=pg_catalog,public,pg_temp as $$
        declare v billing_plan_versions%rowtype; protected boolean;
        begin
          if tg_table_name='billing_plans' then
            if tg_op='DELETE' then raise exception 'billing plan identity is immutable'; end if;
            if tg_op='UPDATE' and (new.id,new.code) is distinct from (old.id,old.code) then
              raise exception 'billing plan identity is immutable'; end if;
            if new.sales_state='open' and not exists(select 1 from billing_plan_versions
                where id=new.current_version_id and plan_id=new.id and status='published') then
              raise exception 'published offer required'; end if;
            return new;
          end if;
          if tg_table_name='billing_plan_prices' then
            if tg_op='UPDATE' and (new.id,new.version_id) is distinct from (old.id,old.version_id) then
              raise exception 'billing price identity is immutable'; end if;
            select * into v from billing_plan_versions where id=case when tg_op='DELETE' then old.version_id else new.version_id end for update;
            if tg_op<>'DELETE' and v.plan_code in ('free','trial') then
              raise exception 'reserved billing plan cannot have a price'; end if;
          else
            if tg_op='INSERT' then return new; end if;
            v:=old;
          end if;
          protected:=v.status in ('scheduled','published','retired')
            or exists(select 1 from workspace_subscriptions where pinned_plan_version_id=v.id)
            or exists(select 1 from billing_entitlement_grants where plan_version_id=v.id);
          if protected then
            if tg_table_name='billing_plan_prices' or tg_op='DELETE' then
              raise exception 'billing offer is immutable'; end if;
            if (to_jsonb(new)-array['status','enabled_for_checkout','effective_until','publication_revision'])
                is distinct from (to_jsonb(old)-array['status','enabled_for_checkout','effective_until','publication_revision']) then
              raise exception 'billing offer is immutable'; end if;
            if (new.status='draft' and old.status<>'scheduled') or (old.status<>'legacy' and new.status='legacy') then
              raise exception 'billing offer is immutable'; end if;
          end if;
          if tg_op='DELETE' then return old; end if;
          return new;
        end $$""")
    for table in ("billing_plans", "billing_plan_versions", "billing_plan_prices"):
        op.execute(f"create trigger billing_guard_offer before insert or update or delete on {table} for each row execute function billing_guard_offer()")
    op.execute("revoke all on function billing_guard_offer() from public")
    op.execute("""create function billing_guard_subscription_pin() returns trigger language plpgsql
        set search_path=pg_catalog,public,pg_temp as $$
        declare v billing_plan_versions%rowtype; p billing_plan_prices%rowtype;
        begin
          if tg_op='UPDATE' then
            if (new.plan_code,new.cycle,new.paid_through,new.capacity_bytes,new.billing_owner_id)
                is distinct from (old.plan_code,old.cycle,old.paid_through,old.capacity_bytes,old.billing_owner_id) then
              new.pin_checked_application_version:=null;
            end if;
            if (new.paid_through,new.next_charge_at,new.timezone,
                new.pinned_plan_version_id,new.pinned_price_id)
                is distinct from (old.paid_through,old.next_charge_at,old.timezone,
                old.pinned_plan_version_id,old.pinned_price_id) then
              new.schedule_version:=old.schedule_version+1;
            elsif new.schedule_version<old.schedule_version then
              raise exception 'billing schedule version cannot decrease';
            end if;
          end if;
          if not exists(select 1 from pg_timezone_names where name=new.timezone) then
            raise exception 'invalid billing timezone'; end if;
          if new.pinned_plan_version_id is not null then
            select * into v from billing_plan_versions where id=new.pinned_plan_version_id for update;
            if v.id is null or v.status not in ('legacy','published','retired')
              or (new.plan_code not in ('free','trial') and v.plan_code<>new.plan_code) then
              raise exception 'subscription pin plan mismatch'; end if;
            if new.pinned_price_id is not null then
              select * into p from billing_plan_prices where id=new.pinned_price_id;
              if p.id is null or p.version_id<>v.id or (new.cycle<>'none' and p.cycle<>new.cycle) then
                raise exception 'subscription pin price mismatch'; end if;
            end if;
          end if;
          return new;
        end $$""")
    op.execute("""create trigger billing_guard_subscription_pin before insert or update on workspace_subscriptions
        for each row execute function billing_guard_subscription_pin()""")
    op.execute("revoke all on function billing_guard_subscription_pin() from public")


def downgrade() -> None:
    op.execute("""do $$ begin
        if exists(select 1 from workspace_subscriptions where pin_state in ('pinned','legacy_pinned'))
          or exists(select 1 from billing_plan_versions where status<>'legacy') then
          raise exception 'billing pin records exist; compatible forward fix required';
        end if;
        end $$""")
    op.execute("drop trigger billing_guard_subscription_pin on workspace_subscriptions")
    op.execute("drop function billing_guard_subscription_pin()")
    for table in ("billing_plans", "billing_plan_versions", "billing_plan_prices"):
        op.execute(f"drop trigger billing_guard_offer on {table}")
    op.execute("drop function billing_guard_offer()")
    op.execute("alter table billing_entitlement_grants drop column plan_version_id")
    for column in ("pinned_price_id", "pinned_plan_version_id", "timezone", "next_charge_at", "schedule_version", "pin_state", "pin_checked_application_version", "legacy_pinned_snapshot"):
        op.execute(f"alter table workspace_subscriptions drop column {column} cascade")
    op.execute("drop table billing_plan_prices")
    op.execute("alter table billing_plans drop constraint fk_billing_plan_current_version")
    for column in ("plan_id", "status", "capability_schema_version", "capabilities", "display_terms", "publication_revision"):
        op.execute(f"alter table billing_plan_versions drop column {column} cascade")
    op.execute("drop table billing_plans")
    op.execute("alter table billing_plan_versions drop constraint uq_billing_version_code")
    for table, column in MONEY_COLUMNS:
        op.execute(f"alter table {table} alter column {column} type integer")
