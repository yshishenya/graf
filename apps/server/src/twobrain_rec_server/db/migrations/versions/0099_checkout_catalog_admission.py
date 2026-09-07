"""Serialize invoice admission with closing/replacing the selected public offer."""

from alembic import op

revision = "0099_checkout_catalog_admission"
down_revision = "0098_processing_quota_allocations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A narrow lock capability does not grant catalog UPDATE to the application.
    # Published price rows are immutable; locking the parent/version protects
    # the pointer, visibility and time boundaries until the invoice commits.
    op.execute("""create function billing_lock_checkout_catalog(p_code text)
        returns boolean language plpgsql security definer
        set search_path=pg_catalog,public,pg_temp as $$
        declare p public.billing_plans%rowtype;
        begin
          if session_user <> 'twobrain_rec_app' or public.rec_context_kind() is distinct from 'request'
              or p_code is null or p_code !~ '^[a-z][a-z0-9_]{2,31}$' then
            raise exception 'checkout catalog context required' using errcode='42501';
          end if;
          select * into p from public.billing_plans where code=p_code for share;
          if not found then return false; end if;
          if p.current_version_id is not null then
            perform id from public.billing_plan_versions where id=p.current_version_id for share;
          elsif p_code='personal' then
            perform id from public.billing_plan_versions where plan_code=p_code and status='legacy'
                order by id for share;
          end if;
          return true;
        end $$""")
    op.execute("revoke all on function billing_lock_checkout_catalog(text) from public")
    op.execute("""do $$ begin
        if exists(select 1 from pg_roles where rolname='twobrain_rec_app') then
          grant execute on function billing_lock_checkout_catalog(text) to twobrain_rec_app;
        end if;
        end $$""")


def downgrade() -> None:
    op.execute("drop function billing_lock_checkout_catalog(text)")
