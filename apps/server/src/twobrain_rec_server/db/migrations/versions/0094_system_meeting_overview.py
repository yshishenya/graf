"""Metadata-only meeting history and deletion reports for global support."""

from collections.abc import Sequence

from alembic import op

revision: str = "0094_system_meeting_overview"
down_revision: str | None = "0093_system_domain_lineage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
OWNER = "twobrain_rec_system_authority"
# Only new grants; downgrade must retain earlier authority projections.
COLUMNS = {
    "meetings": "created_by_user_id,device_id,status,processing_status,duration_seconds,created_at,started_at,ended_at,deletion_epoch",
    "media_revisions": "id,meeting_id,revision_number,status,source_kind,immutable,created_at,duration_seconds",
    "processing_workflows": "id,meeting_id,media_revision_id,workflow_id,workflow_run_id,status,stage,retry_class,retry_count,last_reason_code,attempt_ordinal,created_at,started_at,ended_at,next_attempt_at,deadline_at,system_operation_id",
    "meeting_deletion_requests": "id,meeting_id,state,request_source,reason_code,accepted_at,completed_at,created_at,system_operation_id",
    "meeting_deletion_reports": "id,meeting_id,deletion_request_id,overall_state,backup_state,local_purge_state,external_dependency_state,generated_at,updated_at",
}


def upgrade() -> None:
    op.execute(f"grant create on schema system_control to {OWNER}")
    for table, columns in COLUMNS.items():
        op.execute(f"grant select({columns}) on public.{table} to {OWNER}")
        op.execute(f"create policy system_overview_owner on public.{table} for select to {OWNER} using(true)")
    op.execute("""create function system_control.meeting_overview(p_id uuid) returns jsonb
        language sql stable security definer set search_path=pg_catalog,public,pg_temp as $$
        select jsonb_build_object('id',m.id,'workspace_id',m.workspace_id,'created_by_user_id',m.created_by_user_id,
          'device_id',m.device_id,'status',m.status,'processing_status',m.processing_status,
          'duration_seconds',m.duration_seconds,'created_at',m.created_at,'started_at',m.started_at,
          'ended_at',m.ended_at,'deletion_state',m.deletion_state,'deletion_epoch',m.deletion_epoch,
          'version',m.control_version,'observed_at',statement_timestamp(),'source','graf_database',
          'deletion',(select jsonb_build_object('request_id',d.id,'state',d.state,'source',d.request_source,
            'reason_code',d.reason_code,'accepted_at',d.accepted_at,'completed_at',d.completed_at,
            'system_operation_id',d.system_operation_id,'report',
              (select jsonb_build_object('state',r.overall_state,'backup_state',r.backup_state,
                'local_purge_state',r.local_purge_state,'external_dependency_state',r.external_dependency_state,
                'generated_at',r.generated_at,'updated_at',r.updated_at)
               from public.meeting_deletion_reports r where r.deletion_request_id=d.id
               order by r.generated_at desc,r.id desc limit 1))
            from public.meeting_deletion_requests d where d.meeting_id=m.id
            order by d.created_at desc,d.id desc limit 1))
        from public.meetings m where m.id=p_id
          and system_control.permission_allowed('meetings.metadata','meeting',p_id)
        $$""")
    op.execute("""create function system_control.meeting_history(p_id uuid,p_before uuid) returns jsonb
        language plpgsql stable security definer set search_path=pg_catalog,public,pg_temp as $$
        declare result jsonb;
        begin
          if not system_control.permission_allowed('processing.read','meeting',p_id) then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select w.id,w.media_revision_id,w.workflow_id,w.workflow_run_id,w.status,w.stage,w.retry_class,
              w.retry_count,w.last_reason_code,w.attempt_ordinal,w.created_at,w.started_at,w.ended_at,
              w.next_attempt_at,w.deadline_at,w.system_operation_id
            from public.processing_workflows w where w.meeting_id=p_id and (p_before is null or
              (w.created_at,w.id)<(select a.created_at,a.id from public.processing_workflows a
                where a.id=p_before and a.meeting_id=p_id))
            order by w.created_at desc,w.id desc limit 101) rows;
          return result;
        end $$""")
    op.execute("""create function system_control.meeting_revisions(p_id uuid,p_before integer) returns jsonb
        language plpgsql stable security definer set search_path=pg_catalog,public,pg_temp as $$
        declare result jsonb;
        begin
          if not system_control.permission_allowed('meetings.metadata','meeting',p_id) then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select id,revision_number,status,source_kind,immutable,created_at,duration_seconds
            from public.media_revisions where meeting_id=p_id
              and (p_before is null or revision_number<p_before)
            order by revision_number desc limit 101) rows;
          return result;
        end $$""")
    for signature in ("meeting_overview(uuid)", "meeting_history(uuid,uuid)", "meeting_revisions(uuid,integer)"):
        op.execute(f"revoke all on function system_control.{signature} from public")
        op.execute(f"alter function system_control.{signature} owner to {OWNER}")
        op.execute(f"grant execute on function system_control.{signature} to twobrain_rec_system")
    op.execute(f"revoke create on schema system_control from {OWNER}")


def downgrade() -> None:
    for signature in ("meeting_overview(uuid)", "meeting_history(uuid,uuid)", "meeting_revisions(uuid,integer)"):
        op.execute(f"drop function system_control.{signature}")
    for table, columns in COLUMNS.items():
        op.execute(f"drop policy system_overview_owner on public.{table}")
        op.execute(f"revoke select({columns}) on public.{table} from {OWNER}")
