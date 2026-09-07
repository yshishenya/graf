"""Bind real domain effects to a claimed system actor, never a product identity."""

from collections.abc import Sequence

from alembic import op

revision: str = "0093_system_domain_lineage"
down_revision: str | None = "0092_system_meeting_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
AUTHORITY = "twobrain_rec_system_authority"


def upgrade() -> None:
    op.execute(f"grant create on schema system_control to {AUTHORITY}")
    for table in ("processing_workflows", "meeting_deletion_requests"):
        op.execute(f"""alter table public.{table} add column system_operation_id uuid
            references system_control.operations(id)""")
        op.execute(f"""create unique index uq_{table}_system_operation on public.{table}(system_operation_id)
            where system_operation_id is not null""")
    op.execute("""create function system_control.guard_domain_lineage() returns trigger
        language plpgsql security definer set search_path=pg_catalog,public,pg_temp as $$
        begin
          if new.system_operation_id is not null and tg_table_name='meeting_deletion_requests' then
            if new.requested_by_user_id is not null or new.requested_by_device_id is not null then
              raise insufficient_privilege using message='system actor cannot impersonate a product identity';
            end if;
          end if;
          if tg_op='UPDATE' then
            if old.system_operation_id is distinct from new.system_operation_id
              or (old.system_operation_id is not null and
                (old.id is distinct from new.id or old.meeting_id is distinct from new.meeting_id
                 or old.workspace_id is distinct from new.workspace_id)) then
              raise insufficient_privilege using message='system domain lineage is immutable';
            end if;
            return new;
          end if;
          if new.system_operation_id is null then return new; end if;
          if session_user<>'twobrain_rec_maintenance' or not exists(
            select 1 from system_control.operation_targets t join system_control.operations o on o.id=t.operation_id
            join public.meetings m on m.id=t.target_id and m.workspace_id=new.workspace_id
            where t.operation_id=new.system_operation_id and t.domain_ref=new.id
              and t.target_type='meeting' and t.target_id=new.meeting_id
              and t.effect_started_at is not null and t.state='running'
              and ((tg_table_name='processing_workflows' and o.kind='meeting.reprocess')
                or (tg_table_name='meeting_deletion_requests' and o.kind='meeting.delete'))
          ) then raise insufficient_privilege using message='claimed system operation required'; end if;
          return new;
        end $$""")
    op.execute("revoke all on function system_control.guard_domain_lineage() from public")
    op.execute(f"alter function system_control.guard_domain_lineage() owner to {AUTHORITY}")
    for table in ("processing_workflows", "meeting_deletion_requests"):
        op.execute(f"""create trigger guard_system_domain_lineage before insert or update on public.{table}
            for each row execute function system_control.guard_domain_lineage()""")
    op.execute("""create function system_control.resume_system_operation(p_id uuid,p_target uuid) returns jsonb
        language plpgsql security definer set search_path=pg_catalog,public,pg_temp as $$
        declare t system_control.operation_targets; o system_control.operations;
        begin
          if session_user<>'twobrain_rec_maintenance' then return null; end if;
          select * into t from system_control.operation_targets where operation_id=p_id and target_id=p_target
            and effect_started_at is not null and state in ('running','awaiting_reconciliation') for update;
          if t.operation_id is null then return null; end if;
          select * into o from system_control.operations where id=p_id;
          return jsonb_build_object('operation_id',p_id,'target_id',p_target,'command',o.command,
            'actor_id',o.principal_id,'domain_ref',t.domain_ref,'attempt_fence',t.attempt_fence,'mode','observe');
        end $$""")
    op.execute("revoke all on function system_control.resume_system_operation(uuid,uuid) from public")
    op.execute(f"alter function system_control.resume_system_operation(uuid,uuid) owner to {AUTHORITY}")
    op.execute("grant execute on function system_control.resume_system_operation(uuid,uuid) to twobrain_rec_maintenance")
    op.execute("""create function system_control.record_system_operation_failure(
        p_id uuid,p_target uuid,p_fence bigint,p_ref uuid,p_error text) returns boolean
        language plpgsql security definer set search_path=pg_catalog as $$
        begin
          if session_user<>'twobrain_rec_maintenance' or p_error is null or p_error not in (
            'meeting_not_found','deletion_closed','source_unavailable','stale_meeting_view','not_terminal',
            'not_eligible','unknown_outcome','already_in_flight','configuration_failure','source_expired',
            'quota_exceeded','processing_failed','deletion_failed') then return false; end if;
          if not system_control.record_system_operation_result(p_id,p_target,p_fence,p_ref,'failed')
            then return false; end if;
          update system_control.operation_targets set error_code=coalesce(error_code,p_error)
            where operation_id=p_id and target_id=p_target;
          return true;
        end $$""")
    op.execute("revoke all on function system_control.record_system_operation_failure(uuid,uuid,bigint,uuid,text) from public")
    op.execute(f"alter function system_control.record_system_operation_failure(uuid,uuid,bigint,uuid,text) owner to {AUTHORITY}")
    op.execute("grant execute on function system_control.record_system_operation_failure(uuid,uuid,bigint,uuid,text) to twobrain_rec_maintenance")
    op.execute(f"revoke create on schema system_control from {AUTHORITY}")


def downgrade() -> None:
    op.execute("""do $$ begin if exists(select 1 from public.processing_workflows where system_operation_id is not null)
        or exists(select 1 from public.meeting_deletion_requests where system_operation_id is not null)
        then raise exception 'system domain effects exist; destructive downgrade refused'; end if; end $$""")
    op.execute("drop function system_control.record_system_operation_failure(uuid,uuid,bigint,uuid,text)")
    op.execute("drop function system_control.resume_system_operation(uuid,uuid)")
    for table in ("processing_workflows", "meeting_deletion_requests"):
        op.execute(f"drop trigger guard_system_domain_lineage on public.{table}")
        op.execute(f"alter table public.{table} drop column system_operation_id")
    op.execute("drop function system_control.guard_domain_lineage()")
