"""Superadministrator-only assignments, serialized last-admin protection."""

from collections.abc import Sequence

from alembic import op

revision: str = "0090_system_admin_management"
down_revision: str | None = "0089_system_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
AUTH = "twobrain_rec_system_auth"


def function(signature: str, returns: str, body: str, *, public: bool = True) -> None:
    op.execute(f"""create function system_control.{signature} returns {returns}
        language plpgsql volatile security definer set search_path=pg_catalog,public,pg_temp as $$ {body} $$""")
    op.execute(f"revoke all on function system_control.{signature} from public")
    op.execute(f"alter function system_control.{signature} owner to {AUTH}")
    if public:
        op.execute(f"grant execute on function system_control.{signature} to twobrain_rec_system")


def upgrade() -> None:
    op.execute(f"grant create on schema system_control to {AUTH}")
    op.execute("""create table system_control.governance_lock (
        id integer primary key check(id=1)
    )""")
    op.execute("insert into system_control.governance_lock values(1)")
    op.execute("alter table system_control.governance_lock enable row level security")
    op.execute("alter table system_control.governance_lock force row level security")
    op.execute(f"grant select,update on system_control.governance_lock to {AUTH}")
    op.execute(f"create policy auth_only on system_control.governance_lock to {AUTH} using(true) with check(true)")
    op.execute(f"grant execute on function system_control.current_authority() to {AUTH}")
    op.execute(f"grant insert,update on system_control.role_assignments to {AUTH}")
    op.execute(f"create policy auth_assignments on system_control.role_assignments to {AUTH} using(true) with check(true)")
    op.execute(f"grant execute on function system_control.audit_identity() to {AUTH}")
    function("admin_denial(p_target uuid,p_reason text,p_code text)","jsonb","""
        declare a record;
        begin
          select * into a from system_control.audit_identity();
          if a.principal_id is not null then
            insert into system_control.audit_events(id,principal_id,session_id,role,permission,
              action,target_type,target_id,result,reason)
            values(gen_random_uuid(),a.principal_id,a.session_id,a.role,'admins.manage',
              'admin.denied','system',p_target,'denied',left(p_reason,1000));
          end if;
          return jsonb_build_object('error',p_code);
        end
    """,public=False)
    function("list_administrators(p_after uuid)", "jsonb", """
        declare a record; result jsonb;
        begin
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' then return null; end if;
          select coalesce(jsonb_agg(row_to_json(rows)),'[]'::jsonb) into result from (
            select p.id,p.normalized_email,p.status,p.auth_version as version,
              r.role,r.starts_at,r.expires_at,
              (select jsonb_build_object('state',c.delivery_state,'updated_at',c.delivery_updated_at,
                'expires_at',c.expires_at) from system_control.challenges c
                where c.principal_id=p.id and c.kind='invitation'
                order by c.created_at desc,c.id desc limit 1) as invitation
            from system_control.principals p left join system_control.role_assignments r
              on r.principal_id=p.id and r.revoked_at is null
            where p_after is null or p.id>p_after order by p.id limit 100
          ) rows;
          return result;
        end
    """)
    function("invite_administrator(p_email text, p_role text, p_expiry timestamptz, p_reason text, p_hash text)", "uuid", """
        declare a record; actor uuid;
        begin
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' or a.mfa_at<clock_timestamp()-interval '5 minutes'
            or p_role is null or p_role not in ('superadmin','system_admin','support','billing_manager','analyst','auditor')
            or p_email is null or length(p_email) not between 3 and 240
            or p_reason is null or length(btrim(p_reason)) not between 1 and 1000
            or p_expiry<=clock_timestamp() then return null; end if;
          perform id from system_control.governance_lock where id=1 for update;
          perform id from system_control.principals where id=a.principal_id for update;
          if not exists(select 1 from system_control.current_authority() v
            where v.role='superadmin' and v.mfa_at>=clock_timestamp()-interval '5 minutes') then return null; end if;
          if exists(select 1 from system_control.principals where normalized_email=p_email) then return null; end if;
          actor := gen_random_uuid();
          insert into system_control.principals(id,normalized_email,status,auth_version)
            values(actor,p_email,'invited',1);
          insert into system_control.credentials(principal_id) values(actor);
          insert into system_control.role_assignments(id,principal_id,role,starts_at,expires_at,granted_by,reason)
            values(gen_random_uuid(),actor,p_role,clock_timestamp(),p_expiry,a.principal_id,p_reason);
          insert into system_control.challenges(principal_id,kind,token_hash,issued_auth_version,credential_version,expires_at)
            values(actor,'invitation',p_hash,1,1,clock_timestamp()+interval '24 hours');
          insert into system_control.audit_events(id,principal_id,session_id,role,permission,action,
            target_type,target_id,result,reason)
            values(gen_random_uuid(),a.principal_id,a.session_id,a.role,'admins.manage','admin.invite',
              'system',actor,'allowed',p_reason);
          return actor;
        end
    """)
    function("update_administrator(p_id uuid, p_version integer, p_role text, p_status text, p_expiry timestamptz, p_reason text)", "jsonb", """
        declare a record; target system_control.principals; r system_control.role_assignments;
        begin
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' or a.mfa_at<clock_timestamp()-interval '5 minutes'
            or p_id=a.principal_id then return system_control.admin_denial(p_id,p_reason,'access_denied'); end if;
          if p_role is null or p_role not in ('superadmin','system_admin','support','billing_manager','analyst','auditor')
            or p_status is null or p_status not in ('active','invited','recovery_pending','blocked','revoked')
            or p_reason is null or length(btrim(p_reason)) not between 1 and 1000
            or p_expiry<=clock_timestamp() then return system_control.admin_denial(p_id,p_reason,'invalid_input'); end if;
          perform id from system_control.governance_lock where id=1 for update;
          perform id from system_control.principals where id in(a.principal_id,p_id) order by id for update;
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' or a.mfa_at<clock_timestamp()-interval '5 minutes' then return system_control.admin_denial(p_id,p_reason,'access_denied'); end if;
          select * into target from system_control.principals where id=p_id;
          if target.auth_version is distinct from p_version then return system_control.admin_denial(p_id,p_reason,'version_conflict'); end if;
          if p_status in ('invited','recovery_pending') and target.status is distinct from p_status then
            return system_control.admin_denial(p_id,p_reason,'invalid_input'); end if;
          if p_status='active' and (target.status in ('invited','recovery_pending') or not exists(
            select 1 from system_control.credentials where principal_id=p_id and encrypted_totp_seed is not null))
            then return system_control.admin_denial(p_id,p_reason,'enrolment_required'); end if;
          select * into r from system_control.role_assignments where principal_id=p_id and revoked_at is null;
          if not exists(select 1 from system_control.principals p
            join system_control.role_assignments roles on roles.principal_id=p.id
            where p.id<>p_id and p.status in ('active','recovery_pending') and roles.role='superadmin'
              and roles.revoked_at is null and roles.expires_at is null and roles.starts_at<=clock_timestamp())
            and not(p_status='active' and p_role='superadmin' and p_expiry is null)
            then return system_control.admin_denial(p_id,p_reason,'last_superadmin'); end if;
          update system_control.principals set status=p_status,auth_version=auth_version+1
            where id=p_id returning * into target;
          update system_control.role_assignments set revoked_at=clock_timestamp() where id=r.id;
          insert into system_control.role_assignments(id,principal_id,role,starts_at,expires_at,granted_by,reason)
            values(gen_random_uuid(),p_id,p_role,clock_timestamp(),p_expiry,a.principal_id,p_reason);
          update system_control.sessions set revoked_at=clock_timestamp() where principal_id=p_id and revoked_at is null;
          update system_control.challenges set consumed_at=clock_timestamp() where principal_id=p_id and consumed_at is null;
          update system_control.credentials set recovery_code_hashes='{}' where principal_id=p_id;
          insert into system_control.audit_events(id,principal_id,session_id,role,permission,action,
            target_type,target_id,result,reason)
            values(gen_random_uuid(),a.principal_id,a.session_id,a.role,'admins.manage','admin.update',
              'system',p_id,'allowed',p_reason);
          return jsonb_build_object('id',p_id,'version',target.auth_version);
        end
    """)
    op.execute(f"grant select(target_id,action,occurred_at) on system_control.audit_events to {AUTH}")
    op.execute(f"create policy auth_delivery_history on system_control.audit_events for select to {AUTH} using(true)")
    function("resend_administrator_invitation(p_id uuid,p_version integer,p_reason text,p_hash text)","jsonb","""
        declare a record; target system_control.principals; credential integer;
        begin
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' or a.mfa_at<clock_timestamp()-interval '5 minutes'
            or p_id=a.principal_id then return system_control.admin_denial(p_id,p_reason,'access_denied'); end if;
          if p_reason is null or length(btrim(p_reason)) not between 1 and 1000 then
            return system_control.admin_denial(p_id,p_reason,'invalid_input'); end if;
          perform id from system_control.governance_lock where id=1 for update;
          perform id from system_control.principals where id in(a.principal_id,p_id) order by id for update;
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' or a.mfa_at<clock_timestamp()-interval '5 minutes' then return system_control.admin_denial(p_id,p_reason,'access_denied'); end if;
          select * into target from system_control.principals where id=p_id;
          if target.auth_version is distinct from p_version or target.status<>'invited' then
            return system_control.admin_denial(p_id,p_reason,'version_conflict'); end if;
          if not exists(select 1 from system_control.role_assignments where principal_id=p_id
            and revoked_at is null and starts_at<=clock_timestamp() and (expires_at is null or expires_at>clock_timestamp())) then
            return system_control.admin_denial(p_id,p_reason,'assignment_expired'); end if;
          if exists(select 1 from system_control.audit_events where target_id=p_id
            and action in('admin.invite','admin.resend') and occurred_at>clock_timestamp()-interval '1 minute')
            or (select count(*) from system_control.audit_events where target_id=p_id
              and action in('admin.invite','admin.resend') and occurred_at>clock_timestamp()-interval '1 day')>=5 then
            return system_control.admin_denial(p_id,p_reason,'rate_limited'); end if;
          update system_control.principals set auth_version=auth_version+1 where id=p_id returning * into target;
          update system_control.credentials set credential_version=credential_version+1,recovery_code_hashes='{}'
            where principal_id=p_id returning credential_version into credential;
          update system_control.challenges set consumed_at=clock_timestamp() where principal_id=p_id and consumed_at is null;
          update system_control.sessions set revoked_at=clock_timestamp() where principal_id=p_id and revoked_at is null;
          insert into system_control.challenges(principal_id,kind,token_hash,issued_auth_version,credential_version,expires_at)
            values(p_id,'invitation',p_hash,target.auth_version,credential,clock_timestamp()+interval '24 hours');
          insert into system_control.audit_events(id,principal_id,session_id,role,permission,action,target_type,target_id,result,reason)
            values(gen_random_uuid(),a.principal_id,a.session_id,a.role,'admins.manage','admin.resend','system',p_id,'allowed',p_reason);
          return jsonb_build_object('id',p_id,'version',target.auth_version,'email',target.normalized_email);
        end
    """)
    op.execute(f"grant select,insert,update on system_control.permission_grants to {AUTH}")
    op.execute(f"create policy auth_grants on system_control.permission_grants to {AUTH} using(true) with check(true)")
    for table in ("meetings","user_identities","workspaces","billing_invoices","billing_plan_versions","promotion_campaigns"):
        op.execute(f"grant select(id) on public.{table} to {AUTH}")
        op.execute(f"create policy system_grant_target_lookup on public.{table} for select to {AUTH} using(true)")
    function("administrator_grants(p_id uuid)","jsonb","""
        declare a record; result jsonb;
        begin
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' then return null; end if;
          select coalesce(jsonb_agg(row_to_json(rows)),'[]'::jsonb) into result from (
            select id,version,permission,target_type,target_id,starts_at,expires_at,revoked_at,reason
            from system_control.permission_grants where principal_id=p_id
            order by starts_at desc limit 100
          ) rows;
          return result;
        end
    """)
    function("create_administrator_grant(p_id uuid,p_version integer,p_permission text,p_type text,p_target uuid,p_expiry timestamptz,p_reason text)","jsonb","""
        declare a record; target system_control.principals; r system_control.role_assignments; grant_id uuid; valid boolean;
        begin
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' or a.mfa_at<clock_timestamp()-interval '5 minutes'
            or p_id=a.principal_id then return system_control.admin_denial(p_id,p_reason,'access_denied'); end if;
          if p_expiry is null or p_expiry<=clock_timestamp() or p_expiry>clock_timestamp()+interval '24 hours'
            or p_reason is null or length(btrim(p_reason)) not between 1 and 1000 then
            return system_control.admin_denial(p_id,p_reason,'invalid_input'); end if;
          perform id from system_control.governance_lock where id=1 for update;
          perform id from system_control.principals where id in(a.principal_id,p_id) order by id for update;
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' or a.mfa_at<clock_timestamp()-interval '5 minutes' then return system_control.admin_denial(p_id,p_reason,'access_denied'); end if;
          select * into target from system_control.principals where id=p_id;
          select * into r from system_control.role_assignments where principal_id=p_id and revoked_at is null
            and starts_at<=clock_timestamp() and (expires_at is null or expires_at>clock_timestamp());
          if target.auth_version is distinct from p_version or target.status<>'active' or r.id is null then
            return system_control.admin_denial(p_id,p_reason,'version_conflict'); end if;
          valid := (r.role in('support','system_admin') and p_type='meeting'
              and p_permission in('content.read','audio.listen','audio.download','content.export','diagnostics.content'))
            or (r.role='billing_manager' and (
              (p_permission='billing.manage' and p_type in('user','workspace','subscription','invoice'))
              or (p_permission='catalog.publish' and p_type='plan_version')
              or (p_permission in('promotions.manage','promotions.publish') and p_type='campaign')));
          if valid is not true then return system_control.admin_denial(p_id,p_reason,'permission_not_grantable'); end if;
          case p_type
            when 'meeting' then select exists(select 1 from public.meetings where id=p_target) into valid;
            when 'user' then select exists(select 1 from public.user_identities where id=p_target) into valid;
            when 'workspace' then select exists(select 1 from public.workspaces where id=p_target) into valid;
            when 'subscription' then select exists(select 1 from public.workspaces where id=p_target) into valid;
            when 'invoice' then select exists(select 1 from public.billing_invoices where id=p_target) into valid;
            when 'plan_version' then select exists(select 1 from public.billing_plan_versions where id=p_target) into valid;
            when 'campaign' then select exists(select 1 from public.promotion_campaigns where id=p_target) into valid;
            else valid := false;
          end case;
          if not valid then return system_control.admin_denial(p_id,p_reason,'target_unavailable'); end if;
          grant_id := gen_random_uuid();
          insert into system_control.permission_grants(id,principal_id,assignment_id,assignment_version,
            permission,target_type,target_id,starts_at,expires_at,granted_by,reason)
          values(grant_id,p_id,r.id,r.version,p_permission,p_type,p_target,clock_timestamp(),p_expiry,a.principal_id,p_reason);
          insert into system_control.audit_events(id,principal_id,session_id,role,permission,action,target_type,target_id,result,reason)
            values(gen_random_uuid(),a.principal_id,a.session_id,a.role,'admins.manage','grant.create','system',p_id,'allowed',p_reason);
          return jsonb_build_object('id',grant_id,'version',1);
        end
    """)
    function("revoke_administrator_grant(p_id uuid,p_version integer,p_reason text)","jsonb","""
        declare a record; g system_control.permission_grants;
        begin
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' or a.mfa_at<clock_timestamp()-interval '5 minutes' then
            return system_control.admin_denial(p_id,p_reason,'access_denied'); end if;
          if p_reason is null or length(btrim(p_reason)) not between 1 and 1000 then
            return system_control.admin_denial(p_id,p_reason,'invalid_input'); end if;
          perform id from system_control.governance_lock where id=1 for update;
          select * into g from system_control.permission_grants where id=p_id;
          if g.id is null or g.principal_id=a.principal_id then return system_control.admin_denial(p_id,p_reason,'access_denied'); end if;
          perform id from system_control.principals where id in(a.principal_id,g.principal_id) order by id for update;
          select * into a from system_control.current_authority();
          if a.role is distinct from 'superadmin' or a.mfa_at<clock_timestamp()-interval '5 minutes' then return system_control.admin_denial(p_id,p_reason,'access_denied'); end if;
          select * into g from system_control.permission_grants where id=p_id for update;
          if g.version<>p_version then return system_control.admin_denial(p_id,p_reason,'version_conflict'); end if;
          if g.revoked_at is null then
            update system_control.permission_grants set revoked_at=clock_timestamp(),version=version+1 where id=p_id returning * into g;
            insert into system_control.audit_events(id,principal_id,session_id,role,permission,action,target_type,target_id,result,reason)
              values(gen_random_uuid(),a.principal_id,a.session_id,a.role,'admins.manage','grant.revoke','system',g.principal_id,'allowed',p_reason);
          end if;
          return jsonb_build_object('id',g.id,'version',g.version);
        end
    """)
    op.execute(f"revoke create on schema system_control from {AUTH}")


def downgrade() -> None:
    for signature in ("revoke_administrator_grant(uuid,integer,text)",
                      "create_administrator_grant(uuid,integer,text,text,uuid,timestamptz,text)",
                      "administrator_grants(uuid)", "resend_administrator_invitation(uuid,integer,text,text)", "update_administrator(uuid,integer,text,text,timestamptz,text)",
                      "invite_administrator(text,text,timestamptz,text,text)", "list_administrators(uuid)", "admin_denial(uuid,text,text)"):
        op.execute(f"drop function system_control.{signature}")
    op.execute("drop policy auth_delivery_history on system_control.audit_events")
    op.execute(f"revoke select(target_id,action,occurred_at) on system_control.audit_events from {AUTH}")
    op.execute("drop policy auth_grants on system_control.permission_grants")
    op.execute(f"revoke select,insert,update on system_control.permission_grants from {AUTH}")
    for table in ("meetings","user_identities","workspaces","billing_invoices","billing_plan_versions","promotion_campaigns"):
        op.execute(f"drop policy system_grant_target_lookup on public.{table}")
        op.execute(f"revoke select(id) on public.{table} from {AUTH}")
    op.drop_table("governance_lock", schema="system_control")
    op.execute(f"revoke execute on function system_control.audit_identity() from {AUTH}")
    op.execute(f"revoke execute on function system_control.current_authority() from {AUTH}")
    op.execute("drop policy auth_assignments on system_control.role_assignments")
    op.execute(f"revoke insert,update on system_control.role_assignments from {AUTH}")
