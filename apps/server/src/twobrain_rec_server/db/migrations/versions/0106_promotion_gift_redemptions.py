"""Allow a promotion redemption to represent a non-monetary gift."""

from alembic import op

revision: str = "0106_promotion_gift_redemptions"
down_revision: str | None = "0105_system_admin_observability_console"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column("promotion_redemptions", "invoice_id", nullable=True)
    op.execute(
        """
        create policy access_adjustments_promotion_insert on billing_access_adjustments
          for insert
          with check (
            rec_context_kind() = 'request'
            and workspace_id = rec_current_workspace_id()
            and source_kind = 'promotion'
            and admin_operation_id is null
          )
        """
    )
    op.execute(
        """
        create function billing_redeem_promotion_access(
          p_workspace_id uuid,
          p_subject_user_id uuid,
          p_plan_version_id uuid,
          p_starts_at timestamptz,
          p_ends_at timestamptz,
          p_timezone text,
          p_source_ref text,
          p_reason text
        ) returns uuid
        language plpgsql
        security definer
        set search_path = pg_catalog, public, pg_temp
        as $$
        declare
          adjustment_id uuid;
          existing_workspace_id uuid;
          existing_subject_user_id uuid;
          existing_plan_version_id uuid;
          existing_starts_at timestamptz;
          existing_ends_at timestamptz;
          lookup_campaign_id uuid;
          lookup_code_hash text;
          source_workspace_id uuid;
          campaign record;
          redemption record;
          code record;
          expected_ends timestamptz;
        begin
          if session_user <> 'twobrain_rec_app'
             or public.rec_context_kind() <> 'request'
             or p_workspace_id is distinct from public.rec_current_workspace_id()
             or p_subject_user_id is distinct from public.rec_current_user_id() then
            raise insufficient_privilege using message = 'promotion access context is invalid';
          end if;
          if p_workspace_id is null or p_subject_user_id is null or p_plan_version_id is null
             or p_starts_at is null or p_ends_at is null or p_ends_at <= p_starts_at
             or length(btrim(coalesce(p_source_ref, ''))) not between 1 and 160
             or length(btrim(coalesce(p_reason, ''))) not between 10 and 500
             or p_source_ref !~ '^promotion:[0-9a-f-]{36}:[0-9a-f]{64}:[0-9a-f-]{36}$' then
            raise invalid_parameter_value using message = 'promotion access parameters are invalid';
          end if;
          lookup_campaign_id := split_part(p_source_ref, ':', 2)::uuid;
          lookup_code_hash := split_part(p_source_ref, ':', 3);
          source_workspace_id := split_part(p_source_ref, ':', 4)::uuid;
          if source_workspace_id <> p_workspace_id then
            raise insufficient_privilege using message = 'promotion source workspace is invalid';
          end if;
          select * into campaign from public.promotion_campaigns
           where id=lookup_campaign_id for update;
          select pc.state, pc.target_user_id into code
            from public.promotion_codes pc
           where pc.campaign_id=lookup_campaign_id and pc.code_hash=lookup_code_hash
           for update;
          if campaign.id is null or campaign.benefit_kind <> 'gift' or campaign.gift_days is null
             or campaign.gift_days not between 1 and 365 or campaign.status <> 'active' or not campaign.enabled
             or (campaign.starts_at is not null and campaign.starts_at > clock_timestamp())
             or (campaign.ends_at is not null and campaign.ends_at <= clock_timestamp())
             or (code.state is null and campaign.code_hash <> lookup_code_hash)
             or (code.state is not null and code.state <> 'reserved')
             or (code.target_user_id is not null and code.target_user_id <> p_subject_user_id)
             or (campaign.target_user_id is not null and campaign.target_user_id <> p_subject_user_id)
             or (campaign.audience = 'selected' and campaign.target_user_id is distinct from p_subject_user_id)
             or campaign.redeemed_count + campaign.reserved_count > campaign.max_redemptions then
            raise insufficient_privilege using message = 'promotion campaign is not eligible';
          end if;
          if not exists (
            select 1 from public.workspace_memberships
             where workspace_id = p_workspace_id and user_id = p_subject_user_id and status = 'active'
          ) then
            raise insufficient_privilege using message = 'promotion subject is not an active workspace member';
          end if;
          if campaign.audience = 'never_paid' and exists (
            select 1 from public.billing_invoices i
             join public.workspace_memberships wm on wm.workspace_id=i.workspace_id
              and wm.user_id=p_subject_user_id and wm.role='owner' and wm.status='active'
             where i.status='succeeded'
          ) then
            raise insufficient_privilege using message = 'promotion audience is not eligible';
          end if;
          if campaign.audience = 'first_purchase' and exists (
            select 1 from public.billing_invoices i
             join public.workspace_memberships wm on wm.workspace_id=i.workspace_id
              and wm.user_id=p_subject_user_id and wm.role='owner' and wm.status='active'
             where i.status='succeeded'
               and (i.plan_snapshot::jsonb->>'plan_code' = campaign.plan_code
                    or i.plan_snapshot::jsonb->'catalog_snapshot'->>'plan_code' = campaign.plan_code)
          ) then
            raise insufficient_privilege using message = 'promotion audience is not eligible';
          end if;
          if campaign.audience = 'former_paid' and (
            not exists (select 1 from public.billing_invoices i
             join public.workspace_memberships wm on wm.workspace_id=i.workspace_id
              and wm.user_id=p_subject_user_id and wm.role='owner' and wm.status='active'
             where i.status='succeeded')
            or exists (select 1 from public.workspace_subscriptions s
             where s.workspace_id=p_workspace_id and s.paid_through > clock_timestamp()
               and s.plan_code not in ('free','trial'))
          ) then
            raise insufficient_privilege using message = 'promotion audience is not eligible';
          end if;
          if not exists (
            select 1 from public.billing_plan_versions v
             where v.id=p_plan_version_id and v.plan_code=campaign.plan_code
               and v.status='published' and v.enabled_for_checkout
               and (v.effective_from is null or v.effective_from <= clock_timestamp())
               and (v.effective_until is null or v.effective_until > clock_timestamp())
          ) then
            raise invalid_parameter_value using message = 'published gift plan is required';
          end if;
          if campaign.cycle is not null and not exists (
            select 1 from public.billing_plan_prices pr
             where pr.version_id=p_plan_version_id and pr.cycle=campaign.cycle and pr.currency='RUB'
          ) then
            raise invalid_parameter_value using message = 'gift plan cycle is invalid';
          end if;
          if not exists (select 1 from pg_timezone_names where name=p_timezone) then
            raise invalid_parameter_value using message = 'gift timezone is invalid';
          end if;
          expected_ends := ((p_starts_at at time zone p_timezone) + make_interval(days => campaign.gift_days)) at time zone p_timezone;
          if p_starts_at < clock_timestamp() - interval '1 minute' or p_ends_at <> expected_ends then
            raise invalid_parameter_value using message = 'gift interval is invalid';
          end if;
          -- A gift budget is measured in calendar days, never in money.
          if campaign.budget_minor is not null and
             campaign.budget_used_minor + campaign.gift_days > campaign.budget_minor then
            raise insufficient_privilege using message = 'promotion budget is exhausted';
          end if;
          select * into redemption from public.promotion_redemptions r
           where r.campaign_id=lookup_campaign_id and r.code_hash=lookup_code_hash
             and r.workspace_id=p_workspace_id and r.reservation_key=p_source_ref
             and r.state='reserved' and r.invoice_id is null
           for update;
          if redemption.id is null or redemption.expires_at is null
             or redemption.expires_at <= clock_timestamp() then
            raise insufficient_privilege using message = 'promotion redemption is not confirmed';
          end if;
          select id, workspace_id, subject_user_id
            into adjustment_id, existing_workspace_id, existing_subject_user_id
            from public.billing_access_adjustments
           where source_kind = 'promotion' and source_ref = p_source_ref
           for update;
          if adjustment_id is not null then
            select plan_version_id, starts_at, ends_at into existing_plan_version_id, existing_starts_at, existing_ends_at
              from public.billing_access_adjustments where id=adjustment_id;
            if existing_workspace_id is distinct from p_workspace_id
               or existing_subject_user_id is distinct from p_subject_user_id
               or existing_plan_version_id is distinct from p_plan_version_id
               or existing_starts_at is distinct from p_starts_at
               or existing_ends_at is distinct from p_ends_at then
              raise unique_violation using message = 'promotion source reference is already bound';
            end if;
            return adjustment_id;
          end if;
          insert into public.billing_access_adjustments(
            id, workspace_id, subject_user_id, kind, plan_version_id, plan_mode,
            timezone, starts_at, ends_at, source_kind, source_ref, reason
          ) values (
            gen_random_uuid(), p_workspace_id, p_subject_user_id, 'plan_interval',
            p_plan_version_id, 'append', p_timezone, p_starts_at, p_ends_at,
            'promotion', p_source_ref, p_reason
          ) returning id into adjustment_id;
          return adjustment_id;
        end
        $$
        """
    )
    op.execute(
        "alter function public.billing_redeem_promotion_access(uuid,uuid,uuid,timestamptz,timestamptz,text,text,text) "
        "owner to twobrain_rec_system_authority"
    )
    op.execute("revoke all on function billing_redeem_promotion_access(uuid,uuid,uuid,timestamptz,timestamptz,text,text,text) from public")
    op.execute(
        """
        do $$
        begin
          if exists (select 1 from pg_roles where rolname = 'twobrain_rec_app') then
            grant execute on function billing_redeem_promotion_access(uuid,uuid,uuid,timestamptz,timestamptz,text,text,text)
              to twobrain_rec_app;
          end if;
        end $$
        """
    )


def downgrade() -> None:
    # Never silently discard a gift redemption while rolling back.
    op.execute(
        """
        do $$
        begin
          if exists (select 1 from promotion_redemptions where invoice_id is null) then
            raise exception 'cannot make promotion_redemptions.invoice_id required while gift redemptions exist';
          end if;
        end $$
        """
    )
    op.execute("drop policy if exists access_adjustments_promotion_insert on billing_access_adjustments")
    op.execute("drop function if exists billing_redeem_promotion_access(uuid,uuid,uuid,timestamptz,timestamptz,text,text,text)")
    op.alter_column("promotion_redemptions", "invoice_id", nullable=False)
