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
        begin
          if session_user <> 'twobrain_rec_app'
             or public.rec_context_kind() <> 'request'
             or p_workspace_id is distinct from public.rec_current_workspace_id() then
            raise insufficient_privilege using message = 'promotion access context is invalid';
          end if;
          if p_workspace_id is null or p_subject_user_id is null or p_plan_version_id is null
             or p_starts_at is null or p_ends_at is null or p_ends_at <= p_starts_at
             or length(btrim(coalesce(p_source_ref, ''))) not between 1 and 160
             or length(btrim(coalesce(p_reason, ''))) not between 1 and 500 then
            raise invalid_parameter_value using message = 'promotion access parameters are invalid';
          end if;
          if not exists (
            select 1 from public.workspace_memberships
             where workspace_id = p_workspace_id
               and user_id = p_subject_user_id
               and status = 'active'
          ) then
            raise insufficient_privilege using message = 'promotion subject is not an active workspace member';
          end if;
          perform id from public.workspaces where id = p_workspace_id for update;
          select id, workspace_id, subject_user_id
            into adjustment_id, existing_workspace_id, existing_subject_user_id
            from public.billing_access_adjustments
           where source_kind = 'promotion' and source_ref = p_source_ref
           for update;
          if adjustment_id is not null then
            if existing_workspace_id is distinct from p_workspace_id
               or existing_subject_user_id is distinct from p_subject_user_id then
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
