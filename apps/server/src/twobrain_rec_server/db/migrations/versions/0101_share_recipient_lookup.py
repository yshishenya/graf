"""Permit meeting-bound membership checks without exposing membership rows."""

from alembic import op

revision: str = "0101_share_recipient_lookup"
down_revision: str | None = "0100_merge_admin_settings"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("""create function rec_share_recipient_is_member(p_meeting uuid, p_user uuid)
        returns boolean language sql stable security definer
        set search_path=pg_catalog,public,pg_temp set row_security=off as $$
        select public.rec_context_kind() is not distinct from 'request'
          and exists (
            select 1 from public.meetings m
            join public.workspaces w on w.id=m.workspace_id
            join public.workspace_memberships actor on actor.workspace_id=w.id
              and actor.user_id=public.rec_current_user_id() and actor.status='active'
            join public.user_identities actor_user on actor_user.id=actor.user_id
              and actor_user.organization_id=w.organization_id and actor_user.status='active'
            join public.workspace_memberships target on target.workspace_id=w.id
              and target.user_id=p_user and target.status='active'
            join public.user_identities target_user on target_user.id=target.user_id
              and target_user.organization_id=w.organization_id and target_user.status='active'
            where m.id=p_meeting and w.id=public.rec_current_workspace_id()
              and w.organization_id=public.rec_current_organization_id()
              and m.deleted_at is null and coalesce(m.deletion_state,'none')='none'
              and (m.created_by_user_id=actor.user_id or (
                actor.role in ('owner','admin') and (
                  lower(m.visibility) in ('team','team_visible','workspace','workspace_visible')
                  or exists (
                    select 1 from public.meeting_share_grants g
                    where g.workspace_id=w.id and g.meeting_id=m.id and g.status='active'
                      and (g.expires_at is null or g.expires_at>now())
                      and ((g.audience_type='workspace' and g.audience_id=w.id)
                        or (g.audience_type='user' and g.audience_id=actor.user_id))
                  )
                )
              ))
          )
        $$""")
    op.execute("revoke all on function rec_share_recipient_is_member(uuid,uuid) from public")
    op.execute("""do $$ begin
        if exists(select 1 from pg_roles where rolname='twobrain_rec_app') then
          grant execute on function rec_share_recipient_is_member(uuid,uuid) to twobrain_rec_app;
        end if;
        end $$""")


def downgrade() -> None:
    op.execute("drop function rec_share_recipient_is_member(uuid,uuid)")
