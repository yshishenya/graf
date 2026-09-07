"""Close direct application access to issued promotion codes and batches."""

from alembic import op

revision: str = "0107_promotion_code_rls"
down_revision: str | None = "0106_promotion_gift_redemptions"
branch_labels: str | None = None
depends_on: str | None = None

APP = "twobrain_rec_app"
MAINTENANCE = "twobrain_rec_maintenance"
AUTHORITY = "twobrain_rec_system_authority"


def upgrade() -> None:
    # Issued codes are global lookup data for checkout, but state changes must
    # go through one transition helper.  The authority role is the only role
    # allowed to write the tables; app and maintenance receive read access to
    # promotion_codes so checkout/reconciliation can inspect a code.
    for table in ("promotion_codes", "promotion_code_batches"):
        op.execute(f"alter table public.{table} enable row level security")
        op.execute(f"alter table public.{table} force row level security")
    op.execute(
        """
        do $$
        begin
          if exists (select 1 from pg_roles where rolname = 'twobrain_rec_app') then
            execute 'revoke all on public.promotion_codes, public.promotion_code_batches from twobrain_rec_app';
            execute 'grant select on public.promotion_codes to twobrain_rec_app';
          end if;
          if exists (select 1 from pg_roles where rolname = 'twobrain_rec_maintenance') then
            execute 'revoke all on public.promotion_codes, public.promotion_code_batches from twobrain_rec_maintenance';
            execute 'grant select on public.promotion_codes to twobrain_rec_maintenance';
          end if;
        end
        $$;
        """
    )
    op.execute("drop policy if exists promotion_codes_request_read on public.promotion_codes")
    op.execute("create policy promotion_codes_request_read on public.promotion_codes for select using (rec_context_kind() in ('request','worker'))")
    op.execute("drop policy if exists promotion_codes_maintenance_read on public.promotion_codes")
    op.execute("create policy promotion_codes_maintenance_read on public.promotion_codes for select using (rec_maintenance_allowed())")

    op.execute(
        """
        create or replace function public.billing_transition_promotion_code(
          p_redemption_id uuid,
          p_to_state text
        ) returns boolean
        language plpgsql
        security definer
        set search_path = pg_catalog, public, pg_temp
        as $$
        begin
          if not (
            (session_user = 'twobrain_rec_app' and public.rec_context_kind() = 'request')
            or (session_user = 'twobrain_rec_maintenance' and public.rec_maintenance_allowed())
          ) then
            raise insufficient_privilege using message = 'promotion code transition context required';
          end if;
          if p_redemption_id is null or p_to_state not in ('reserved', 'redeemed', 'available') then
            raise invalid_parameter_value using message = 'promotion code transition is invalid';
          end if;
          if session_user = 'twobrain_rec_app' and not exists (
            select 1 from public.promotion_redemptions r
             where r.id = p_redemption_id and r.workspace_id = public.rec_current_workspace_id()
          ) then
            raise insufficient_privilege using message = 'promotion redemption is outside the current workspace';
          end if;
          update public.promotion_codes pc
             set state = p_to_state,
                 reserved_at = case when p_to_state = 'reserved' then coalesce(pc.reserved_at, now()) else null end,
                 redeemed_at = case when p_to_state = 'redeemed' then coalesce(pc.redeemed_at, now()) else pc.redeemed_at end
            from public.promotion_redemptions r
            join public.promotion_campaigns c on c.id = r.campaign_id
           where r.id = p_redemption_id
             and pc.campaign_id = r.campaign_id
             and pc.code_hash = r.code_hash
             and (
               (p_to_state = 'reserved' and pc.state = 'available' and r.state = 'reserved'
                and c.status in ('active','draft') and c.enabled
                and (c.starts_at is null or c.starts_at <= clock_timestamp())
                and (c.ends_at is null or c.ends_at > clock_timestamp())
                -- The insert trigger has already counted this reservation.
                and c.redeemed_count + c.reserved_count <= c.max_redemptions
                and (pc.target_user_id is null or pc.target_user_id = public.rec_current_user_id())
                and (c.target_user_id is null or c.target_user_id = public.rec_current_user_id())
                and (c.audience <> 'selected' or c.target_user_id = public.rec_current_user_id())
                and (c.budget_minor is null or c.budget_used_minor +
                     coalesce((select sum(case when rr.state = 'reserved'
                       then case when c.benefit_kind = 'gift' then c.gift_days
                                 else greatest(0, rr.list_amount_minor - rr.payable_amount_minor) end else 0 end)
                       from public.promotion_redemptions rr where rr.campaign_id = c.id and rr.id <> r.id), 0) +
                     case when c.benefit_kind = 'gift' then c.gift_days
                          else greatest(0, r.list_amount_minor - r.payable_amount_minor) end <= c.budget_minor)
               )
               or (p_to_state = 'redeemed' and pc.state = 'reserved' and r.state = 'redeemed'
                   and ((r.invoice_id is not null and exists (
                         select 1 from public.billing_invoices i where i.id = r.invoice_id
                           and i.workspace_id = r.workspace_id and i.status = 'succeeded'))
                        or (r.invoice_id is null and c.benefit_kind = 'gift' and exists (
                         select 1 from public.billing_access_adjustments a
                          where a.source_kind = 'promotion'
                            and a.source_ref = r.reservation_key
                            and a.workspace_id = r.workspace_id))))
               or (p_to_state = 'available' and pc.state = 'reserved' and r.state in ('released','expired'))
             );
          return found;
        end
        $$;
        """
    )
    op.execute(
        """
        create or replace function public.billing_reserve_promotion_redemption(
          p_campaign_id uuid,
          p_workspace_id uuid,
          p_invoice_id uuid,
          p_reservation_key text,
          p_code_hash text,
          p_list_amount bigint,
          p_payable_amount bigint,
          p_discount_percent integer,
          p_expires_at timestamptz
        ) returns uuid
        language plpgsql
        security definer
        set search_path = pg_catalog, public, pg_temp
        as $$
        declare
          c record;
          pc record;
          inv record;
          redemption_id uuid;
          expected_payable bigint;
        begin
          if session_user <> 'twobrain_rec_app'
             or public.rec_context_kind() <> 'request'
             or p_workspace_id is null
             or p_workspace_id is distinct from public.rec_current_workspace_id() then
            raise insufficient_privilege using message = 'promotion reservation context required';
          end if;
          if p_campaign_id is null or p_code_hash is null
             or p_code_hash !~ '^[0-9a-f]{64}$'
             or p_list_amount < 0 or p_payable_amount < 0
             or p_payable_amount > p_list_amount
             or p_discount_percent < 0 or p_discount_percent > 99
             or p_expires_at is null or p_expires_at <= clock_timestamp()
             or p_expires_at > clock_timestamp() + interval '1 day'
             or length(btrim(coalesce(p_reservation_key, ''))) not between 1 and 240 then
            raise invalid_parameter_value using message = 'promotion reservation parameters are invalid';
          end if;
          select * into c from public.promotion_campaigns where id=p_campaign_id for update;
          if c.id is null or c.status not in ('active','draft') or not c.enabled
             or (c.starts_at is not null and c.starts_at > clock_timestamp())
             or (c.ends_at is not null and c.ends_at <= clock_timestamp())
             or c.redeemed_count + c.reserved_count >= c.max_redemptions
             or (c.audience = 'selected' and (c.target_user_id is null or c.target_user_id <> public.rec_current_user_id()))
             or (c.target_user_id is not null and c.target_user_id <> public.rec_current_user_id()) then
            raise insufficient_privilege using message = 'promotion campaign is not eligible';
          end if;
          if c.benefit_kind = 'gift' then
            if p_invoice_id is not null or p_discount_percent <> 0 or p_payable_amount <> 0 then
              raise invalid_parameter_value using message = 'gift reservation parameters are invalid';
            end if;
          else
            if p_invoice_id is null or p_discount_percent <> c.discount_percent then
              raise invalid_parameter_value using message = 'discount reservation parameters are invalid';
            end if;
            select i.* into inv from public.billing_invoices i
             where i.id=p_invoice_id and i.workspace_id=p_workspace_id and i.status='pending'
             ;
            if inv.id is null
               or inv.amount_minor <> p_payable_amount
               or (inv.plan_snapshot::jsonb->>'list_amount_minor')::bigint <> p_list_amount
               or (inv.plan_snapshot::jsonb->>'payable_amount_minor')::bigint <> p_payable_amount
               or (inv.plan_snapshot::jsonb->>'promo_code_hash') <> p_code_hash
               or coalesce((inv.plan_snapshot::jsonb->>'discount_percent')::integer, -1) <> p_discount_percent then
              raise insufficient_privilege using message = 'promotion invoice is not pending';
            end if;
            expected_payable := greatest(0, p_list_amount * (100 - p_discount_percent) / 100);
            if p_payable_amount <> expected_payable then
              raise invalid_parameter_value using message = 'discount amount is invalid';
            end if;
          end if;
          select * into pc from public.promotion_codes
           where campaign_id=p_campaign_id and code_hash=p_code_hash for update;
          if pc.id is null and c.code_hash <> p_code_hash then
            raise invalid_parameter_value using message = 'promotion code is invalid';
          end if;
          if pc.id is not null and (pc.state <> 'available'
             or (pc.target_user_id is not null and pc.target_user_id <> public.rec_current_user_id())) then
            raise insufficient_privilege using message = 'promotion code is unavailable';
          end if;
          insert into public.promotion_redemptions(
            id,campaign_id,workspace_id,invoice_id,reservation_key,code_hash,
            list_amount_minor,payable_amount_minor,discount_percent,state,expires_at
          ) values (
            gen_random_uuid(),p_campaign_id,p_workspace_id,p_invoice_id,p_reservation_key,p_code_hash,
            p_list_amount,p_payable_amount,p_discount_percent,'reserved',p_expires_at
          ) returning id into redemption_id;
          if pc.id is not null and not public.billing_transition_promotion_code(redemption_id,'reserved') then
            raise insufficient_privilege using message = 'promotion code is unavailable';
          end if;
          return redemption_id;
        end
        $$;
        """
    )
    op.execute(
        """
        create or replace function public.billing_finalize_promotion_redemption(
          p_redemption_id uuid,
          p_to_state text,
          p_at timestamptz
        ) returns boolean
        language plpgsql
        security definer
        set search_path = pg_catalog, public, pg_temp
        as $$
        declare
          r record;
          c record;
          cost bigint;
        begin
          if p_redemption_id is null or p_to_state not in ('redeemed','released','expired')
             or p_at is null or p_at > clock_timestamp() + interval '5 minutes' then
            raise invalid_parameter_value using message = 'promotion redemption transition is invalid';
          end if;
          if not (
            (session_user = 'twobrain_rec_app' and public.rec_context_kind() = 'request'
             and exists (select 1 from public.promotion_redemptions x
                          where x.id=p_redemption_id and x.workspace_id=public.rec_current_workspace_id()))
            or (session_user = 'twobrain_rec_maintenance' and public.rec_maintenance_allowed())
          ) then
            raise insufficient_privilege using message = 'promotion redemption transition context required';
          end if;
          select * into r from public.promotion_redemptions where id=p_redemption_id for update;
          if r.id is null or r.state <> 'reserved' then
            return false;
          end if;
          select * into c from public.promotion_campaigns where id=r.campaign_id for update;
          if c.id is null then
            return false;
          end if;
          if c.redeemed_count + c.reserved_count > c.max_redemptions then
            return false;
          end if;
          if p_to_state = 'redeemed' then
            if r.invoice_id is not null then
              if not exists (select 1 from public.billing_invoices i
                              where i.id=r.invoice_id and i.workspace_id=r.workspace_id and i.status='succeeded') then
                return false;
              end if;
            elsif c.benefit_kind <> 'gift'
               or r.expires_at is null or r.expires_at <= clock_timestamp()
               or not exists (select 1 from public.billing_access_adjustments a
                               where a.source_kind='promotion' and a.source_ref=r.reservation_key
                                 and a.workspace_id=r.workspace_id) then
              return false;
            end if;
            update public.promotion_redemptions
               set state='redeemed', redeemed_at=p_at
             where id=p_redemption_id and state='reserved';
            if c.budget_minor is not null then
              cost := case when c.benefit_kind='gift' then c.gift_days
                           else greatest(0, r.list_amount_minor-r.payable_amount_minor) end;
              update public.promotion_campaigns
                 set budget_used_minor=budget_used_minor+cost
               where id=c.id;
            end if;
            if exists (select 1 from public.promotion_codes pc
                        where pc.campaign_id=r.campaign_id and pc.code_hash=r.code_hash)
               and not public.billing_transition_promotion_code(p_redemption_id,'redeemed') then
              raise insufficient_privilege using message = 'promotion code confirmation failed';
            end if;
            return true;
          end if;
          if p_to_state = 'expired' and (r.expires_at is null or r.expires_at > clock_timestamp()) then
            return false;
          end if;
          if session_user = 'twobrain_rec_app' and r.invoice_id is not null
             and not exists (select 1 from public.billing_invoices i
                              where i.id=r.invoice_id and i.workspace_id=r.workspace_id
                                and i.status in ('pending','canceled')) then
            return false;
          end if;
          update public.promotion_redemptions
             set state=p_to_state, released_at=p_at
           where id=p_redemption_id and state='reserved';
          if exists (select 1 from public.promotion_codes pc
                      where pc.campaign_id=r.campaign_id and pc.code_hash=r.code_hash)
             and not public.billing_transition_promotion_code(p_redemption_id,'available') then
            raise insufficient_privilege using message = 'promotion code release failed';
          end if;
          return true;
        end
        $$;
        """
    )
    for signature in (
        "billing_reserve_promotion_redemption(uuid,uuid,uuid,text,text,bigint,bigint,integer,timestamptz)",
        "billing_finalize_promotion_redemption(uuid,text,timestamptz)",
    ):
        op.execute(f"revoke all on function public.{signature} from public")
        op.execute(f"alter function public.{signature} owner to {AUTHORITY}")
    op.execute(
        "revoke all on function public.billing_transition_promotion_code(uuid,text) from public"
    )
    op.execute(
        f"alter function public.billing_transition_promotion_code(uuid,text) owner to {AUTHORITY}"
    )
    # The code transition helper is an implementation detail of the guarded
    # reservation/finalization functions and is intentionally not executable
    # by either runtime login.
    op.execute(
        f"""
        do $$
        begin
          if exists (select 1 from pg_roles where rolname = '{APP}') then
            execute 'revoke insert, update, delete on public.promotion_campaigns, public.promotion_redemptions from {APP}';
            execute 'grant select on public.promotion_campaigns, public.promotion_redemptions to {APP}';
          end if;
          if exists (select 1 from pg_roles where rolname = '{MAINTENANCE}') then
            execute 'revoke insert, update, delete on public.promotion_campaigns, public.promotion_redemptions from {MAINTENANCE}';
            execute 'grant select on public.promotion_campaigns, public.promotion_redemptions to {MAINTENANCE}';
          end if;
        end
        $$;
        """
    )
    # Guarded functions perform the only redemption and gift-adjustment
    # writes.  The authority role receives exactly those table privileges;
    # runtime logins remain read-only on the redemption ledger.
    op.execute(f"grant insert, update on public.promotion_redemptions to {AUTHORITY}")
    # The idempotency lookup uses SELECT ... FOR UPDATE before the guarded
    # insert, which PostgreSQL treats as requiring UPDATE on the relation.
    op.execute(f"grant insert, update on public.billing_access_adjustments to {AUTHORITY}")
    # Gift redemption validates the subject's active membership while running
    # under FORCE RLS.  Keep this lookup narrow and read-only for the authority
    # role; the system console never receives membership data through this
    # function.
    op.execute("grant select on public.workspace_memberships to " + AUTHORITY)
    op.execute("drop policy if exists system_admin_authority_read on public.workspace_memberships")
    op.execute(
        "create policy system_admin_authority_read on public.workspace_memberships "
        f"for select using (current_user='{AUTHORITY}')"
    )
    # The append-only access trigger serializes grants with SELECT ... FOR
    # UPDATE on the workspace row, which requires UPDATE privilege for the
    # lock even though no workspace column is changed.
    op.execute("grant update on public.workspaces to " + AUTHORITY)
    op.execute(
        """
        do $$
        begin
          if exists (select 1 from pg_roles where rolname = 'twobrain_rec_app') then
            execute 'grant execute on function public.billing_reserve_promotion_redemption(uuid,uuid,uuid,text,text,bigint,bigint,integer,timestamptz) to twobrain_rec_app';
            execute 'grant execute on function public.billing_finalize_promotion_redemption(uuid,text,timestamptz) to twobrain_rec_app';
          end if;
          if exists (select 1 from pg_roles where rolname = 'twobrain_rec_maintenance') then
            execute 'grant execute on function public.billing_finalize_promotion_redemption(uuid,text,timestamptz) to twobrain_rec_maintenance';
          end if;
        end
        $$;
        """
    )


def downgrade() -> None:
    # Re-enabling direct DML would restore a billing-integrity vulnerability.
    # Permit rollback only for an empty issued-code store; production data must
    # be migrated or retired before removing this boundary.
    op.execute(
        """
        do $$
        begin
          if exists (select 1 from public.promotion_codes)
             or exists (select 1 from public.promotion_code_batches) then
            raise exception 'cannot downgrade promotion code RLS while issued codes exist';
          end if;
        end
        $$;
        """
    )
    op.execute("drop policy if exists promotion_codes_request_read on public.promotion_codes")
    op.execute("drop policy if exists promotion_codes_maintenance_read on public.promotion_codes")
    op.execute("drop function if exists public.billing_transition_promotion_code(uuid,text)")
    op.execute("drop function if exists public.billing_finalize_promotion_redemption(uuid,text,timestamptz)")
    op.execute("drop function if exists public.billing_reserve_promotion_redemption(uuid,uuid,uuid,text,text,bigint,bigint,integer,timestamptz)")
    for table in ("promotion_codes", "promotion_code_batches"):
        op.execute(f"alter table public.{table} no force row level security")
        op.execute(f"alter table public.{table} disable row level security")
    op.execute("drop policy if exists system_admin_authority_read on public.workspace_memberships")
