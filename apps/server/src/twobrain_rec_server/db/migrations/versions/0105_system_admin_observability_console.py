"""Read-only operational and analytics projections for the system console.

The isolated system role receives no broad table access.  Each projection is a
small security-definer function with an explicit permission check and bounded
result set; raw reports, credentials and payloads stay outside the console.
"""

from alembic import op

revision: str = "0105_system_admin_observability_console"
down_revision: str | None = "0104_system_admin_subscription_commands"
branch_labels: str | None = None
depends_on: str | None = None

AUTHORITY = "twobrain_rec_system_authority"
SYSTEM = "twobrain_rec_system"


def _fn(signature: str, returns: str, body: str) -> None:
    op.execute(
        f"create or replace function system_control.{signature} returns {returns} "
        "language plpgsql security definer set search_path=pg_catalog,public,pg_temp as $$ "
        f"{body} $$"
    )
    op.execute(f"revoke all on function system_control.{signature} from public")
    op.execute(f"alter function system_control.{signature} owner to {AUTHORITY}")
    op.execute(f"grant execute on function system_control.{signature} to {SYSTEM}")


def upgrade() -> None:
    # The authority is deliberately admitted through a named policy instead of
    # a superuser or BYPASSRLS grant.  Existing tenant policies remain intact.
    for table in (
        "user_identities",
        "workspaces",
        "meetings",
        "processing_workflows",
        "processing_dependency_states",
        "registered_devices",
        "support_incidents",
        "calendar_sources",
        "storage_reservations",
        "temporary_upload_objects",
    ):
        op.execute(f"grant usage on schema public to {AUTHORITY}")
        op.execute(f"grant select on public.{table} to {AUTHORITY}")
        op.execute(f"drop policy if exists system_admin_observer_read on public.{table}")
        op.execute(
            f"create policy system_admin_observer_read on public.{table} for select "
            f"using (current_user='{AUTHORITY}')"
        )

    _fn("system_overview()", "jsonb", """
        declare result jsonb;
        begin
          if not system_control.permission_allowed('operations.read',null,null) then return null; end if;
          select jsonb_build_object(
            'observed_at',clock_timestamp(),
            'users',(select count(*) from public.user_identities),
            'workspaces',(select count(*) from public.workspaces),
            'meetings',(select count(*) from public.meetings),
            'processing_active',(select count(*) from public.processing_workflows where status in ('starting','workflow_started','submitting','submitted','polling','importing')),
            'processing_failed',(select count(*) from public.processing_workflows where status in ('failed_terminal','blocked')),
            'queued_operations',(select count(*) from system_control.operations where state in ('queued','running','awaiting_reconciliation')),
            'open_incidents',(select count(*) from public.support_incidents where status not in ('resolved','closed')),
            'storage_reserved_bytes',(select coalesce(sum(declared_bytes),0) from public.storage_reservations where state in ('active','reserved'))
          ) into result;
          return result;
        end""")

    _fn("list_system_operations(p_after uuid,p_state text)", "jsonb", """
        declare result jsonb;
        begin
          if not system_control.permission_allowed('operations.read',null,null) then return null; end if;
          if length(coalesce(p_state,''))>32 then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select o.id,o.kind,o.permission,o.state,o.created_at,o.updated_at,
              t.target_type,t.target_id,t.state target_state,t.domain_ref,t.error_code,
              left(o.command->>'reason',500) reason
            from system_control.operations o
            join system_control.operation_targets t on t.operation_id=o.id
            where (p_after is null or o.id>p_after) and (p_state is null or o.state=p_state)
            order by o.id limit 101
          ) rows;
          return result;
        end""")

    _fn("list_support_incidents(p_after uuid,p_status text)", "jsonb", """
        declare result jsonb;
        begin
          if not system_control.permission_allowed('support.read',null,null) then return null; end if;
          if length(coalesce(p_status,''))>64 then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select id,incident_number,workspace_id,reporter_user_id,device_id,problem_code,
              failure_category,retry_class,status,affected_count,redaction_result,
              first_received_at,last_received_at,github_issue_number,github_issue_state,
              github_last_synced_at,github_failure_code,updated_at
            from public.support_incidents
            where (p_after is null or id>p_after) and (p_status is null or status=p_status)
            order by id limit 101
          ) rows;
          return result;
        end""")

    _fn("list_system_devices(p_after uuid,p_status text)", "jsonb", """
        declare result jsonb;
        begin
          if not system_control.permission_allowed('devices.read',null,null) then return null; end if;
          if length(coalesce(p_status,''))>32 then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select id,workspace_id,user_id,platform,client_version,status,registration_state,
              last_seen_at,created_at,updated_at
            from public.registered_devices
            where (p_after is null or id>p_after) and (p_status is null or status=p_status)
            order by id limit 101
          ) rows;
          return result;
        end""")

    _fn("list_system_dependencies(p_after uuid)", "jsonb", """
        declare result jsonb;
        begin
          if not system_control.permission_allowed('operations.read',null,null) then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select id,workspace_id,meeting_id,media_revision_id,dependency,state,
              last_verified_at,created_at,updated_at
            from public.processing_dependency_states
            where p_after is null or id>p_after order by id limit 101
          ) rows;
          return result;
        end""")

    _fn("list_system_integrations(p_after uuid)", "jsonb", """
        declare result jsonb;
        begin
          if not system_control.permission_allowed('integrations.read',null,null) then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows)),'[]'::jsonb) into result from (
            select id,workspace_id,provider_family,connection_state,credential_state,sync_state,
              last_successful_sync_at,last_safe_error_code,created_at,updated_at
            from public.calendar_sources where p_after is null or id>p_after order by id limit 101
          ) rows;
          return result;
        end""")

    _fn("list_system_metrics(p_start timestamptz,p_end timestamptz)", "jsonb", """
        declare result jsonb; started timestamptz; finished timestamptz; observed timestamptz := clock_timestamp();
        begin
          if not system_control.permission_allowed('analytics.read',null,null) then return null; end if;
          started := coalesce(p_start, observed - interval '30 days');
          finished := coalesce(p_end, observed);
          if finished<=started or finished-started>interval '366 days' then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows) order by metric_key),'[]'::jsonb) into result from (
            select * from (values
              ('users_created','Новые пользователи',(select count(*)::numeric from public.user_identities where created_at>=started and created_at<finished),'count'),
              ('meetings_created','Созданные встречи',(select count(*)::numeric from public.meetings where created_at>=started and created_at<finished),'count'),
              ('processing_succeeded','Успешная обработка',(select count(*)::numeric from public.processing_workflows where status='processed' and updated_at>=started and updated_at<finished),'count'),
              ('processing_failed','Ошибки обработки',(select count(*)::numeric from public.processing_workflows where status in ('failed_terminal','blocked') and updated_at>=started and updated_at<finished),'count'),
              ('incidents_created','Обращения в поддержку',(select count(*)::numeric from public.support_incidents where created_at>=started and created_at<finished),'count'),
              ('storage_reserved_bytes','Зарезервированное хранилище',(select coalesce(sum(declared_bytes),0)::numeric from public.storage_reservations
                where state in ('active','reserved') and (expires_at is null or expires_at > started)),'bytes')
            ) as metric(metric_key,label,value,unit)
          ) rows;
          return jsonb_build_object('definition_version','system-metrics.v1','interval_start',started,
            'interval_end',finished,'timezone','UTC','scope','all','observed_at',observed,'items',result);
        end""")

    _fn("system_storage_status()", "jsonb", """
        begin
          if not system_control.permission_allowed('operations.read',null,null) then return null; end if;
          return jsonb_build_object(
            'observed_at',clock_timestamp(),
            'active_reservations',(select count(*) from public.storage_reservations where state in ('active','reserved')),
            'declared_bytes',(select coalesce(sum(declared_bytes),0) from public.storage_reservations where state in ('active','reserved')),
            'committed_bytes',(select coalesce(sum(committed_bytes),0) from public.storage_reservations where state in ('active','reserved')),
            'temporary_objects',(select count(*) from public.temporary_upload_objects where cleanup_status not in ('purged','deleted')),
            'temporary_bytes',(select coalesce(sum(byte_length),0) from public.temporary_upload_objects where cleanup_status not in ('purged','deleted'))
          );
        end""")

    _fn("list_system_alerts()", "jsonb", """
        declare result jsonb;
        begin
          if not system_control.permission_allowed('operations.read',null,null) then return null; end if;
          select coalesce(jsonb_agg(to_jsonb(rows) order by severity desc,code),'[]'::jsonb) into result from (
            select * from (
              select 'dependency_unavailable' code,'high' severity,'Зависимость недоступна' title,
                dependency detail,state,updated_at observed_at
              from public.processing_dependency_states where state in ('failed','unavailable','expired')
              union all
              select 'operation_failed','medium','Системная операция завершилась ошибкой',o.kind,
                o.state,o.updated_at from system_control.operations o where o.state='failed'
            ) events order by observed_at desc limit 200
          ) rows;
          return jsonb_build_object('observed_at',clock_timestamp(),'items',result);
        end""")

    _fn("system_settings()", "jsonb", """
        begin
          if not system_control.permission_allowed('settings.read',null,null) then return null; end if;
          return jsonb_build_object(
            'version',1,
            'observed_at',clock_timestamp(),
            'items',jsonb_build_array(
              jsonb_build_object('key','audit_required','value',true,'mutable',false),
              jsonb_build_object('key','metadata_only_diagnostics','value',true,'mutable',false),
              jsonb_build_object('key','default_report_timezone','value','Europe/Moscow','mutable',false),
              jsonb_build_object('key','content_retention_controlled','value',true,'mutable',false)
            )
          );
        end""")


def downgrade() -> None:
    for signature in (
        "list_system_metrics(timestamptz,timestamptz)",
        "list_system_alerts()",
        "system_storage_status()",
        "system_settings()",
        "list_system_integrations(uuid)",
        "list_system_dependencies(uuid)",
        "list_system_devices(uuid,text)",
        "list_support_incidents(uuid,text)",
        "list_system_operations(uuid,text)",
        "system_overview()",
    ):
        op.execute(f"drop function if exists system_control.{signature}")
    for table in (
        "user_identities",
        "workspaces",
        "meetings",
        "processing_workflows",
        "processing_dependency_states",
        "registered_devices",
        "support_incidents",
        "calendar_sources",
        "storage_reservations",
        "temporary_upload_objects",
    ):
        op.execute(f"drop policy if exists system_admin_observer_read on public.{table}")
