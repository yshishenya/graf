"""Append-only non-monetary grants; exact scopes, intervals and revocation sources."""

from collections.abc import Sequence

from alembic import op

revision: str = "0097_billing_access_adjustments"
down_revision: str | None = "0096_billing_version_pins"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
AUTHORITY = "twobrain_rec_system_authority"


def upgrade() -> None:
    op.execute("""create table billing_access_adjustments (
        id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id),
        subject_user_id uuid references user_identities(id), kind varchar(24) not null
          check(kind in ('plan_interval','allow','deny','extra_quota','exact_limit')),
        feature_key varchar(40), plan_version_id uuid references billing_plan_versions(id),
        plan_mode varchar(16), value json, unit varchar(16), timezone varchar(64) not null default 'UTC',
        starts_at timestamptz not null, ends_at timestamptz not null check(ends_at>starts_at),
        source_kind varchar(16) not null check(source_kind in ('admin','promotion','migration')),
        source_ref varchar(160) not null check(source_ref ~ '^[A-Za-z0-9:_-]{1,160}$'),
        admin_operation_id uuid references system_control.operations(id),
        reason varchar(500) not null check(length(trim(reason)) between 10 and 500),
        created_at timestamptz not null default now(),
        constraint uq_access_adjustment_source unique(source_kind,source_ref),
        constraint uq_access_adjustment_scope unique(id,workspace_id),
        check((source_kind='admin')=(admin_operation_id is not null)),
        check((kind='plan_interval' and plan_version_id is not null and plan_mode is not null and plan_mode in ('append','overlay')
               and feature_key is null and unit is null and (value is null or json_typeof(value)='null'))
          or (kind<>'plan_interval' and plan_version_id is null and plan_mode is null and feature_key is not null
               and unit is not null and value is not null and
             ((kind in ('allow','deny') and unit='boolean' and json_typeof(value)='boolean'
                and value::text=case when kind='allow' then 'true' else 'false' end
                and feature_key in ('audio_archive','audio_download','content_export','meeting_sharing','ai_summary','ai_outcomes'))
              or (kind in ('extra_quota','exact_limit') and value::text ~ '^[0-9]+$'
                and (value::text)::numeric between case when kind='extra_quota' or feature_key='storage_bytes' then 1 else 0 end and 9000000000000000
                and ((feature_key='storage_bytes' and unit='bytes') or (feature_key='processing_seconds' and unit='seconds'))))))
    )""")
    op.execute("""create index ix_access_adjustments_active on billing_access_adjustments(workspace_id,ends_at,starts_at)""")
    op.execute("""create table billing_access_revocations (
        id uuid primary key default gen_random_uuid(), workspace_id uuid not null references workspaces(id),
        adjustment_id uuid not null unique references billing_access_adjustments(id),
        source_kind varchar(16) not null check(source_kind in ('admin','promotion','migration')),
        source_ref varchar(160) not null check(source_ref ~ '^[A-Za-z0-9:_-]{1,160}$'),
        admin_operation_id uuid references system_control.operations(id),
        reason varchar(500) not null check(length(trim(reason)) between 10 and 500),
        created_at timestamptz not null default now(),
        constraint uq_access_revocation_source unique(source_kind,source_ref),
        foreign key(adjustment_id,workspace_id) references billing_access_adjustments(id,workspace_id),
        check((source_kind='admin')=(admin_operation_id is not null)))""")
    for table in ("billing_access_adjustments", "billing_access_revocations"):
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"alter table {table} force row level security")
        op.execute(f"revoke all on {table} from public")
        subject = "(subject_user_id is null or subject_user_id=rec_current_user_id())" if table == "billing_access_adjustments" else "exists(select 1 from billing_access_adjustments a where a.id=adjustment_id)"
        op.execute(f"""create policy access_adjustments_read on {table} for select using
            ((rec_context_kind() in ('request','worker') and workspace_id=rec_current_workspace_id() and {subject}) or rec_maintenance_allowed())""")
        op.execute(f"create policy access_adjustments_insert on {table} for insert with check(rec_maintenance_allowed())")
        op.execute(f"create policy system_direct_denied on {table} as restrictive to twobrain_rec_system using(false) with check(false)")
    op.execute(f"grant create on schema system_control to {AUTHORITY}")
    op.execute("""create function system_control.access_adjustment_command_valid(p_operation uuid,p_workspace uuid,p_ref uuid,p_kind text)
        returns boolean language sql security definer set search_path=pg_catalog as $$
        select session_user='twobrain_rec_maintenance' and exists(
          select 1 from system_control.operations o join system_control.operation_targets t on t.operation_id=o.id
          where o.id=p_operation and o.kind=p_kind and o.permission='billing.manage'
            and o.state='running' and t.state='running' and t.target_type='subscription'
            and t.target_id=p_workspace and t.domain_ref=p_ref and t.effect_started_at is not null)
        $$""")
    op.execute("revoke all on function system_control.access_adjustment_command_valid(uuid,uuid,uuid,text) from public")
    op.execute(f"alter function system_control.access_adjustment_command_valid(uuid,uuid,uuid,text) owner to {AUTHORITY}")
    op.execute("grant execute on function system_control.access_adjustment_command_valid(uuid,uuid,uuid,text) to twobrain_rec_maintenance")
    op.execute(f"revoke create on schema system_control from {AUTHORITY}")
    op.execute("""create function billing_guard_access_adjustment() returns trigger language plpgsql
        set search_path=pg_catalog,public,pg_temp as $$
        begin
          if tg_op<>'INSERT' then raise exception 'access ledger is immutable'; end if;
          -- Serialize overlapping assignments and revocations on the same domain lock.
          perform id from workspaces where id=new.workspace_id for update;
          if new.source_kind='admin' and not system_control.access_adjustment_command_valid(
              new.admin_operation_id,new.workspace_id,new.id,
              case when tg_table_name='billing_access_adjustments' then 'subscription.adjust' else 'subscription.adjustment.revoke' end) then
            raise insufficient_privilege using message='claimed billing command required'; end if;
          if tg_table_name='billing_access_revocations' then return new; end if;
          if not exists(select 1 from pg_timezone_names where name=new.timezone) then
            raise exception 'invalid billing timezone'; end if;
          if new.subject_user_id is not null and not exists(select 1 from workspace_memberships
              where workspace_id=new.workspace_id and user_id=new.subject_user_id and status='active') then
            raise exception 'access subject outside workspace'; end if;
          if new.plan_version_id is not null and not exists(select 1 from billing_plan_versions
              where id=new.plan_version_id and status in ('published','retired')) then
            raise exception 'published plan required'; end if;
          if new.kind='plan_interval' and new.plan_mode='append' and exists(select 1 from workspace_subscriptions
              where workspace_id=new.workspace_id and greatest(paid_through,trial_ends_at)>new.starts_at) then
            raise exception 'append overlaps existing access'; end if;
          if new.kind<>'extra_quota' and exists(select 1 from billing_access_adjustments a
              where a.workspace_id=new.workspace_id and a.subject_user_id is not distinct from new.subject_user_id
                and a.kind=new.kind and a.feature_key is not distinct from new.feature_key
                and a.starts_at<new.ends_at and new.starts_at<a.ends_at
                and not exists(select 1 from billing_access_revocations r where r.adjustment_id=a.id)) then
            raise exception 'overlapping access assignment'; end if;
          return new;
        end $$""")
    op.execute("revoke all on function billing_guard_access_adjustment() from public")
    for table in ("billing_access_adjustments", "billing_access_revocations"):
        op.execute(f"create trigger billing_guard_access_adjustment before insert or update or delete on {table} for each row execute function billing_guard_access_adjustment()")


def downgrade() -> None:
    op.execute("""do $$ begin if exists(select 1 from billing_access_adjustments) then
        raise exception 'access ledger exists; destructive downgrade refused'; end if; end $$""")
    op.execute("drop table billing_access_revocations")
    op.execute("drop table billing_access_adjustments")
    op.execute("drop function billing_guard_access_adjustment()")
    op.execute("drop function system_control.access_adjustment_command_valid(uuid,uuid,uuid,text)")
