"""Bounded user and payer projection with field-level financial permissions."""

from collections.abc import Sequence

from alembic import op

revision: str = "0091_system_user_projection"
down_revision: str | None = "0090_system_admin_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
OWNER = "twobrain_rec_system_authority"
COLUMNS = {
    "user_identities": "id,organization_id,display_name,status,created_at,merged_into_user_id",
    "external_identities": "id,user_id,email,is_active,is_verified",
    "workspaces": "id,organization_id,owner_user_id,kind,name",
    "workspace_subscriptions": "workspace_id,billing_owner_id,state,plan_code,cycle,paid_through,trial_ends_at,recurring_allowed",
    "billing_invoices": "id,workspace_id,amount_minor,currency,status,created_at",
    "billing_entitlement_grants": "workspace_id,created_at,source",
    "observed_provider_refunds": "workspace_id,amount_minor,currency,status",
}


def upgrade() -> None:
    for table, columns in COLUMNS.items():
        op.execute(f"grant select({columns}) on public.{table} to {OWNER}")
        op.execute(f"create policy system_projection_owner on public.{table} for select to {OWNER} using(true)")
    op.execute("""create index ix_external_identity_system_user
        on public.external_identities(user_id,id) where is_active and is_verified""")
    op.execute("""create index ix_external_identity_system_email
        on public.external_identities(lower(email)) where is_active and is_verified""")
    op.execute(f"grant create on schema system_control to {OWNER}")
    # Legacy public RLS SQL helpers resolve rec_setting() in public. Keep that
    # trusted namespace ahead of pg_temp; every relation in this query remains
    # explicitly qualified. Runtime bootstrap rejects CREATE in public.
    op.execute("""create function system_control.list_users(p_after uuid,p_email text,p_plan text,p_status text)
        returns jsonb language plpgsql stable security definer set search_path=pg_catalog,public,pg_temp as $$
        declare a record; result jsonb; money boolean;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null or not system_control.permission_allowed('users.read',null,null) then return null; end if;
          if length(p_email)>240 or length(p_plan)>32 or length(p_status)>32 then return null; end if;
          money := system_control.principal_permission('billing.read',null,null);
          select coalesce(jsonb_agg(row_to_json(rows)),'[]'::jsonb) into result from (
            select u.id,u.display_name,u.status,u.created_at,u.merged_into_user_id,
              email.email,w.id as personal_workspace_id,
              coalesce(s.plan_code,'free') as assigned_plan_code,coalesce(s.state,'free') as subscription_state,
              s.paid_through,s.trial_ends_at,s.recurring_allowed,
              case when money then coalesce(paid.amount,0) end as paid_amount_minor_rub,
              case when money then coalesce(refunds.amount,0) end as refunded_amount_minor_rub,
              case when money then payments.confirmed_at end as last_entitlement_confirmation_at,
              money as financial_fields_available
            from public.user_identities u
            left join public.workspaces w on w.owner_user_id=u.id and w.organization_id=u.organization_id and w.kind='personal'
            left join public.workspace_subscriptions s on s.workspace_id=w.id
            left join lateral(select e.email from public.external_identities e where e.user_id=u.id
              and e.is_active and e.is_verified order by e.id limit 1) email on true
            left join lateral(select sum(i.amount_minor) as amount from public.billing_invoices i
              where money and i.workspace_id=w.id and i.status='succeeded' and i.currency='RUB') paid on true
            left join lateral(select sum(r.amount_minor) as amount from public.observed_provider_refunds r
              where money and r.workspace_id=w.id and r.status='succeeded' and r.currency='RUB') refunds on true
            left join lateral(select max(g.created_at) as confirmed_at from public.billing_entitlement_grants g
              where money and g.workspace_id=w.id and g.source='provider_confirmed') payments on true
            where (p_after is null or u.id>p_after)
              and (p_email is null or exists(select 1 from public.external_identities e
                where e.user_id=u.id and e.is_active and e.is_verified and lower(e.email)=p_email))
              and (p_plan is null or coalesce(s.plan_code,'free')=p_plan)
              and (p_status is null or u.status=p_status)
            order by u.id limit 101
          ) rows;
          return result;
        end $$""")
    op.execute("revoke all on function system_control.list_users(uuid,text,text,text) from public")
    op.execute(f"alter function system_control.list_users(uuid,text,text,text) owner to {OWNER}")
    op.execute("grant execute on function system_control.list_users(uuid,text,text,text) to twobrain_rec_system")
    op.execute(f"revoke create on schema system_control from {OWNER}")


def downgrade() -> None:
    op.execute("drop function system_control.list_users(uuid,text,text,text)")
    op.execute("drop index public.ix_external_identity_system_email")
    op.execute("drop index public.ix_external_identity_system_user")
    for table, columns in COLUMNS.items():
        op.execute(f"drop policy system_projection_owner on public.{table}")
        op.execute(f"revoke select({columns}) on public.{table} from {OWNER}")
