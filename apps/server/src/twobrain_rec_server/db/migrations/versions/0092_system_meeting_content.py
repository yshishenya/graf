"""Audited, target-bound content projections without storage credentials."""

from collections.abc import Sequence

from alembic import op

revision: str = "0092_system_meeting_content"
down_revision: str | None = "0091_system_user_projection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
SYSTEM = "twobrain_rec_system"
AUTHORITY = "twobrain_rec_system_authority"
COLUMNS = {
    "media_revisions": "id,workspace_id,meeting_id,revision_number,status,immutable,updated_at",
    "processing_workflows": "id,workspace_id,meeting_id,media_revision_id,attempt_ordinal",
    "processing_results": "id,workspace_id,meeting_id,media_revision_id,processing_workflow_id,status,transcript_status,diarization_status,segment_count,diarization_segment_count,result_version,imported_at,created_at",
    "diarization_segments": "id,workspace_id,meeting_id,processing_result_id,sequence,start_seconds,end_seconds,speaker_label,text,source_role",
}


def upgrade() -> None:
    op.execute(f"grant create on schema system_control to {AUTHORITY}")
    op.execute(f"grant select(workspace_id,title,deleted_at) on public.meetings to {AUTHORITY}")
    op.execute("""create function system_control.meeting_content_allowed(p_id uuid) returns boolean
        language sql stable security definer set search_path=pg_catalog,public,pg_temp as $$
          select coalesce(current_setting('app.system_permission',true) in ('content.read','content.export')
            and system_control.content_allowed(current_setting('app.system_permission',true),'meeting',p_id)
            and exists(select 1 from public.meetings where id=p_id and deletion_state='none'
              and deleted_at is null),false)
        $$""")
    op.execute("""create function system_control.meeting_content_header(p_id uuid) returns jsonb
        language sql stable security definer set search_path=pg_catalog,public,pg_temp as $$
          select jsonb_build_object('id',id,'workspace_id',workspace_id,'title',title,'version',control_version)
            from public.meetings where id=p_id and system_control.meeting_content_allowed(p_id)
        $$""")
    for function in ("meeting_content_allowed(uuid)","meeting_content_header(uuid)"):
        op.execute(f"revoke all on function system_control.{function} from public")
        op.execute(f"alter function system_control.{function} owner to {AUTHORITY}")
        op.execute(f"grant execute on function system_control.{function} to {SYSTEM}")
    for table, columns in COLUMNS.items():
        op.execute(f"grant select({columns}) on public.{table} to {SYSTEM}")
        for modifier,name in (("", "system_content_read"),("as restrictive", "system_content_gate")):
            op.execute(f"""create policy {name} on public.{table} {modifier} for select to {SYSTEM}
                using(system_control.meeting_content_allowed(meeting_id))""")
        op.execute(f"create policy system_no_update on public.{table} as restrictive for update to {SYSTEM} using(false) with check(false)")
        op.execute(f"create policy system_no_delete on public.{table} as restrictive for delete to {SYSTEM} using(false)")
        op.execute(f"create policy system_no_insert on public.{table} as restrictive for insert to {SYSTEM} with check(false)")
    op.execute(f"revoke create on schema system_control from {AUTHORITY}")


def downgrade() -> None:
    for table, columns in COLUMNS.items():
        for policy in ("system_content_read","system_content_gate","system_no_update","system_no_delete","system_no_insert"):
            op.execute(f"drop policy {policy} on public.{table}")
        op.execute(f"revoke select({columns}) on public.{table} from {SYSTEM}")
    op.execute("drop function system_control.meeting_content_header(uuid)")
    op.execute("drop function system_control.meeting_content_allowed(uuid)")
    op.execute(f"revoke select(workspace_id,title,deleted_at) on public.meetings from {AUTHORITY}")
