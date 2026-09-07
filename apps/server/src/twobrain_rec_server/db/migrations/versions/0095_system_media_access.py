"""Single-use media activation, session-bound Range lease and source pinning."""

from collections.abc import Sequence

from alembic import op

revision: str = "0095_system_media_access"
down_revision: str | None = "0094_system_meeting_overview"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
OWNER = "twobrain_rec_system_authority"
COLUMNS = {
    "media_revisions": "workspace_id",
    "track_artifacts": "id,workspace_id,meeting_id,media_revision_id,track_role,codec,sample_rate_hz,channel_count,duration_seconds,byte_length,sha256,storage_object_key,status,normalization_profile_version,validated_at,derivation_kind,source_fingerprint_sha256,validation_version",
    "playback_normalization_jobs": "id,workspace_id,meeting_id,media_revision_id,state,canonical_track_artifact_id,profile_version,validation_version,source_fingerprint_sha256",
}


def upgrade() -> None:
    op.execute(f"grant create on schema system_control to {OWNER}")
    for table, columns in COLUMNS.items():
        op.execute(f"grant select({columns}) on public.{table} to {OWNER}")
        op.execute(f"create policy system_media_owner on public.{table} for select to {OWNER} using(true)")
    op.execute(f"grant insert(id,workspace_id,meeting_id,actor_user_id,device_id,event_type,artifact_class,policy_reason,outcome,metadata_json) on public.meeting_egress_audit_events to {OWNER}")
    op.execute(f"create policy system_media_egress_insert on public.meeting_egress_audit_events for insert to {OWNER} with check(true)")
    op.execute("""create table system_control.media_tickets (
        id uuid primary key default gen_random_uuid(), token_hash varchar(64) not null unique,
        principal_id uuid not null references system_control.principals(id),
        session_id uuid not null references system_control.sessions(id),
        meeting_id uuid not null, revision_id uuid not null,
        case_context_id uuid not null references system_control.case_contexts(id),
        permission varchar(40) not null check(permission in ('audio.listen','audio.download')),
        source_hash varchar(64) not null, created_at timestamptz not null default now(),
        expires_at timestamptz not null default now()+interval '60 seconds',
        consumed_at timestamptz, lease_hash varchar(64), lease_expires_at timestamptz,
        check(token_hash ~ '^[0-9a-f]{64}$'), check(source_hash ~ '^[0-9a-f]{64}$'),
        check((consumed_at is null and lease_hash is null and lease_expires_at is null) or
          (consumed_at is not null and lease_hash ~ '^[0-9a-f]{64}$' and lease_expires_at is not null)),
        check(expires_at>created_at and expires_at<=created_at+interval '60 seconds'))""")
    op.execute("create index ix_system_media_ticket_actor on system_control.media_tickets(principal_id,created_at)")
    op.execute("alter table system_control.media_tickets enable row level security")
    op.execute("alter table system_control.media_tickets force row level security")
    op.execute("revoke all on system_control.media_tickets from public")
    op.execute(f"grant select,insert,update,delete on system_control.media_tickets to {OWNER}")
    op.execute(f"create policy authority_only on system_control.media_tickets to {OWNER} using(true) with check(true)")
    op.execute("""create function system_control.media_source(p_meeting uuid,p_revision uuid) returns jsonb
        language sql stable security definer set search_path=pg_catalog,public,pg_temp as $$
        select jsonb_build_object('artifact',jsonb_build_object(
            'id',a.id,'workspace_id',a.workspace_id,'meeting_id',a.meeting_id,'media_revision_id',a.media_revision_id,
            'track_role',a.track_role,'codec',a.codec,'sample_rate_hz',a.sample_rate_hz,'channel_count',a.channel_count,
            'duration_seconds',a.duration_seconds,'byte_length',a.byte_length,'sha256',a.sha256,
            'storage_object_key',a.storage_object_key,'status',a.status,
            'normalization_profile_version',a.normalization_profile_version,'validated_at',a.validated_at,
            'derivation_kind',a.derivation_kind,'source_fingerprint_sha256',a.source_fingerprint_sha256,
            'validation_version',a.validation_version),'job',jsonb_build_object(
            'state',j.state,'canonical_track_artifact_id',j.canonical_track_artifact_id,
            'workspace_id',j.workspace_id,'meeting_id',j.meeting_id,'media_revision_id',j.media_revision_id,
            'profile_version',j.profile_version,'validation_version',j.validation_version,
            'source_fingerprint_sha256',j.source_fingerprint_sha256))
        from public.meetings m join public.media_revisions r on r.meeting_id=m.id and r.workspace_id=m.workspace_id
        join public.playback_normalization_jobs j on j.media_revision_id=r.id and j.meeting_id=m.id and j.workspace_id=m.workspace_id
        join public.track_artifacts a on a.id=j.canonical_track_artifact_id and a.media_revision_id=r.id
          and a.meeting_id=m.id and a.workspace_id=m.workspace_id
        where m.id=p_meeting and m.deleted_at is null and m.deletion_state='none'
          and r.status='accepted' and r.immutable and r.id=coalesce(p_revision,
            (select v.id from public.media_revisions v where v.meeting_id=m.id and v.status='accepted' and v.immutable
             order by v.revision_number desc limit 1))
          and j.state='ready' and a.status='stored' and a.track_role='playback'
          and current_setting('app.system_permission',true) in ('audio.listen','audio.download')
          and system_control.content_allowed(current_setting('app.system_permission',true),'meeting',m.id)
        order by j.id limit 1
        $$""")
    op.execute("""create function system_control.create_media_ticket(p_hash text,p_meeting uuid,p_revision uuid) returns jsonb
        language plpgsql security definer set search_path=pg_catalog,public,pg_temp as $$
        declare a record; source jsonb; t system_control.media_tickets;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null or p_hash is null or p_hash !~ '^[0-9a-f]{64}$' then return null; end if;
          perform id from system_control.principals where id=a.principal_id for update;
          if (select count(*) from system_control.media_tickets where principal_id=a.principal_id
              and created_at>clock_timestamp()-interval '1 minute')>=10 then return null; end if;
          source:=system_control.media_source(p_meeting,p_revision);
          if source is null then return null; end if;
          insert into system_control.media_tickets(token_hash,principal_id,session_id,meeting_id,revision_id,
              case_context_id,permission,source_hash)
          values(p_hash,a.principal_id,a.session_id,p_meeting,(source->'artifact'->>'media_revision_id')::uuid,
              current_setting('app.system_case_context_id')::uuid,current_setting('app.system_permission'),
              encode(sha256(convert_to(source::text,'UTF8')),'hex')) returning * into t;
          return jsonb_build_object('id',t.id,'expires_at',t.expires_at,'source',source);
        end $$""")
    op.execute("""create function system_control.describe_media_ticket(p_hash text) returns jsonb
        language sql stable security definer set search_path=pg_catalog,public,pg_temp as $$
        select jsonb_build_object('id',t.id,'meeting_id',t.meeting_id,'revision_id',t.revision_id,
          'permission',t.permission,'case_context_id',t.case_context_id)
        from system_control.media_tickets t join system_control.current_authority() a
          on a.principal_id=t.principal_id and a.session_id=t.session_id
        where t.token_hash=p_hash and ((t.consumed_at is null and t.expires_at>statement_timestamp())
          or (t.consumed_at is not null and t.lease_expires_at>statement_timestamp()))
        $$""")
    op.execute("""create function system_control.media_ticket_source(p_hash text,p_lease text,p_new_lease text) returns jsonb
        language plpgsql security definer set search_path=pg_catalog,public,pg_temp as $$
        declare t system_control.media_tickets; source jsonb; a record;
        begin
          select * into a from system_control.current_authority();
          if a.principal_id is null then return null; end if;
          select * into t from system_control.media_tickets where token_hash=p_hash
            and principal_id=a.principal_id and session_id=a.session_id for update;
          if t.id is null or t.permission is distinct from current_setting('app.system_permission',true)
            or t.case_context_id::text is distinct from current_setting('app.system_case_context_id',true)
            then return null; end if;
          if t.consumed_at is null then
            if t.expires_at<=clock_timestamp() or p_new_lease is null or p_new_lease !~ '^[0-9a-f]{64}$' then return null; end if;
          elsif t.lease_expires_at<=clock_timestamp() or p_lease is distinct from t.lease_hash then return null;
          end if;
          source:=system_control.media_source(t.meeting_id,t.revision_id);
          if source is null or encode(sha256(convert_to(source::text,'UTF8')),'hex')<>t.source_hash then return null; end if;
          if t.consumed_at is null then
            insert into public.meeting_egress_audit_events
              (id,workspace_id,meeting_id,actor_user_id,device_id,event_type,artifact_class,policy_reason,outcome,metadata_json)
            values(current_setting('app.system_audit_event_id')::uuid,
              (source->'artifact'->>'workspace_id')::uuid,t.meeting_id,null,null,
              case t.permission when 'audio.download' then 'download_stream_prepared' else 'playback_stream_prepared' end,
              'audio','system_admin_audio','prepared',json_build_object('artifact_class','audio','stream_state','prepared'));
            update system_control.media_tickets set consumed_at=clock_timestamp(),lease_hash=p_new_lease,
              lease_expires_at=clock_timestamp()+interval '15 minutes' where id=t.id;
          end if;
          return source;
        end $$""")
    signatures = ("media_source(uuid,uuid)","create_media_ticket(text,uuid,uuid)",
                  "describe_media_ticket(text)","media_ticket_source(text,text,text)")
    for signature in signatures:
        op.execute(f"revoke all on function system_control.{signature} from public")
        op.execute(f"alter function system_control.{signature} owner to {OWNER}")
        op.execute(f"grant execute on function system_control.{signature} to twobrain_rec_system")
    op.execute("""create function system_control.expire_media_tickets() returns void
        language plpgsql security definer set search_path=pg_catalog as $$ begin
          if session_user<>'twobrain_rec_maintenance' then return; end if;
          delete from system_control.media_tickets where created_at<clock_timestamp()-interval '1 hour';
        end $$""")
    op.execute("revoke all on function system_control.expire_media_tickets() from public")
    op.execute(f"alter function system_control.expire_media_tickets() owner to {OWNER}")
    op.execute("grant execute on function system_control.expire_media_tickets() to twobrain_rec_maintenance")
    op.execute(f"revoke create on schema system_control from {OWNER}")


def downgrade() -> None:
    for signature in ("expire_media_tickets()","media_ticket_source(text,text,text)",
                      "describe_media_ticket(text)","create_media_ticket(text,uuid,uuid)","media_source(uuid,uuid)"):
        op.execute(f"drop function system_control.{signature}")
    op.execute("drop table system_control.media_tickets")
    op.execute("drop policy system_media_egress_insert on public.meeting_egress_audit_events")
    op.execute(f"revoke insert(id,workspace_id,meeting_id,actor_user_id,device_id,event_type,artifact_class,policy_reason,outcome,metadata_json) on public.meeting_egress_audit_events from {OWNER}")
    for table, columns in COLUMNS.items():
        op.execute(f"drop policy system_media_owner on public.{table}")
        op.execute(f"revoke select({columns}) on public.{table} from {OWNER}")
