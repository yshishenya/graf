"""Separate authentication primitives, encrypted MFA and version-bound challenges."""

from collections.abc import Sequence

from alembic import op

revision: str = "0089_system_auth"
down_revision: str | None = "0088_system_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
AUTH = "twobrain_rec_system_auth"


def function(signature: str, returns: str, body: str, *, public: bool = True) -> None:
    op.execute(f"""create function system_control.{signature} returns {returns}
        language plpgsql volatile security definer set search_path=pg_catalog as $$ {body} $$""")
    identity = signature.replace(" default gen_random_uuid()", "").replace(" default null", "")
    op.execute(f"revoke all on function system_control.{identity} from public")
    op.execute(f"alter function system_control.{identity} owner to {AUTH}")
    if public:
        op.execute(f"grant execute on function system_control.{identity} to twobrain_rec_system")


def upgrade() -> None:
    op.execute(f"""do $$ begin
        if not exists(select 1 from pg_roles where rolname='{AUTH}') then
          create role {AUTH} nologin nosuperuser nobypassrls noinherit;
        end if;
    end $$""")
    op.execute(f"grant usage,create on schema system_control to {AUTH}")
    op.execute("""create table system_control.credentials (
        principal_id uuid primary key references system_control.principals(id),
        credential_version integer not null default 1 check(credential_version > 0),
        encrypted_totp_seed bytea, key_id varchar(80), nonce bytea,
        last_totp_counter bigint not null default -1,
        recovery_code_hashes text[] not null default '{}',
        check(encrypted_totp_seed is null or (key_id is not null and octet_length(nonce)=12)),
        check(cardinality(recovery_code_hashes)<=10)
    )""")
    op.execute("""create table system_control.challenges (
        id uuid primary key default gen_random_uuid(),
        principal_id uuid not null references system_control.principals(id),
        kind varchar(24) not null check(kind in ('invitation','reset','preauth','enrolment')),
        token_hash varchar(64) not null unique check(token_hash ~ '^[0-9a-f]{64}$'),
        issued_auth_version integer not null, credential_version integer not null,
        expires_at timestamptz not null, consumed_at timestamptz,
        attempts integer not null default 0,
        encrypted_totp_seed bytea, key_id varchar(80), nonce bytea,
        delivery_state varchar(24) not null default 'not_attempted'
          check(delivery_state in ('not_attempted','sending','submitted','unknown','failed')),
        delivery_updated_at timestamptz,
        created_at timestamptz not null default now()
    )""")
    op.execute("create index ix_system_challenges_principal on system_control.challenges(principal_id,kind)")
    op.execute("""create table system_control.rate_limits (
        bucket_hash varchar(64) not null, kind varchar(24) not null,
        window_start timestamptz not null, attempts integer not null,
        attempt_id uuid not null default gen_random_uuid(),
        primary key(bucket_hash,kind,window_start)
    )""")
    for table in ("credentials", "challenges", "rate_limits"):
        op.execute(f"alter table system_control.{table} enable row level security")
        op.execute(f"alter table system_control.{table} force row level security")
        op.execute(f"revoke all on system_control.{table} from public")
        op.execute(f"grant select,insert,update,delete on system_control.{table} to {AUTH}")
        op.execute(f"create policy auth_only on system_control.{table} to {AUTH} using(true) with check(true)")
    for table in ("principals", "sessions"):
        op.execute(f"grant select,insert,update on system_control.{table} to {AUTH}")
        op.execute(f"create policy auth_access on system_control.{table} to {AUTH} using(true) with check(true)")
    op.execute(f"grant select on system_control.role_assignments to {AUTH}")
    op.execute(f"create policy auth_read on system_control.role_assignments for select to {AUTH} using(true)")
    op.execute("alter table system_control.audit_events alter column principal_id drop not null")
    op.execute("alter table system_control.audit_events alter column session_id drop not null")
    op.execute(f"grant insert on system_control.audit_events to {AUTH}")
    op.execute(f"create policy auth_audit on system_control.audit_events for insert to {AUTH} with check(true)")
    function("auth_audit(p_principal uuid, p_action text, p_result text)", "void", """
        begin
          insert into system_control.audit_events
            (id,principal_id,role,permission,action,result)
          values(gen_random_uuid(),p_principal,'authentication','admins.manage',p_action,p_result);
        end
    """, public=False)
    function("auth_delivery(p_hash text,p_state text)", "boolean", """
        begin
          if session_user<>'twobrain_rec_system' or p_state is null
            or p_state not in ('sending','submitted','unknown','failed') then return false; end if;
          update system_control.challenges set delivery_state=p_state,delivery_updated_at=clock_timestamp()
            where token_hash=p_hash and kind in ('invitation','reset')
              and ((p_state='sending' and delivery_state='not_attempted' and consumed_at is null
                and expires_at>clock_timestamp()) or
                (p_state in ('submitted','unknown','failed') and delivery_state='sending'));
          return found;
        end
    """)
    function("auth_rate_limit(p_bucket text, p_kind text, p_attempt uuid default gen_random_uuid())", "boolean", """
        declare count integer; ceiling integer;
        begin
          if session_user <> 'twobrain_rec_system' or p_bucket is null or p_bucket !~ '^[0-9a-f]{64}$'
            or p_kind is null or p_kind not in ('account','network','global') or p_attempt is null then return false; end if;
          ceiling := case p_kind when 'account' then 5 when 'network' then 30 else 300 end;
          perform pg_advisory_xact_lock(hashtextextended(p_bucket || ':' || p_kind,0));
          select coalesce(sum(attempts),0) into count from system_control.rate_limits
            where bucket_hash=p_bucket and kind=p_kind and window_start>clock_timestamp()-interval '15 minutes';
          if count>=ceiling then return false; end if;
          delete from system_control.rate_limits where bucket_hash=p_bucket and kind=p_kind
            and window_start<=clock_timestamp()-interval '15 minutes';
          insert into system_control.rate_limits(bucket_hash,kind,window_start,attempts,attempt_id)
            values(p_bucket,p_kind,clock_timestamp(),1,p_attempt);
          return true;
        end
    """)
    function("auth_login_result(p_email text, p_success boolean, p_attempt uuid default null)", "void", """
        declare actor uuid;
        begin
          if session_user <> 'twobrain_rec_system' then return; end if;
          select id into actor from system_control.principals where normalized_email=p_email;
          perform system_control.auth_audit(actor,'auth.password',case when p_success then 'allowed' else 'denied' end);
          if p_success then
            delete from system_control.rate_limits
              where bucket_hash=encode(sha256(convert_to(p_email,'UTF8')),'hex')
                and kind='account' and attempt_id=p_attempt;
          end if;
        end
    """)
    function("auth_lookup(p_email text)", "jsonb", """
        declare result jsonb;
        begin
          if session_user <> 'twobrain_rec_system' then return null; end if;
          select jsonb_build_object('principal_id',p.id,'password_hash',p.password_hash,
            'auth_version',p.auth_version,'credential_version',c.credential_version)
          into result from system_control.principals p
          join system_control.credentials c on c.principal_id=p.id
          where p.normalized_email=p_email and p.status='active';
          return result;
        end
    """)
    function("auth_issue_preauth(p_principal uuid, p_version integer, p_credential integer, p_hash text)", "boolean", """
        declare p system_control.principals; c system_control.credentials;
        begin
          if session_user <> 'twobrain_rec_system' then return false; end if;
          select * into p from system_control.principals where id=p_principal for update;
          select * into c from system_control.credentials where principal_id=p.id;
          if p.status is distinct from 'active' or p.auth_version is distinct from p_version
            or c.credential_version is distinct from p_credential then return false; end if;
          update system_control.challenges set consumed_at=clock_timestamp()
            where principal_id=p.id and kind='preauth' and consumed_at is null;
          insert into system_control.challenges
            (principal_id,kind,token_hash,issued_auth_version,credential_version,expires_at)
          values(p.id,'preauth',p_hash,p.auth_version,c.credential_version,clock_timestamp()+interval '5 minutes');
          perform system_control.auth_audit(p.id,'auth.password','allowed');
          return true;
        end
    """)
    function("auth_challenge(p_hash text)", "jsonb", """
        declare result jsonb; ch system_control.challenges; p system_control.principals;
        begin
          if session_user <> 'twobrain_rec_system' then return null; end if;
          select * into ch from system_control.challenges where token_hash=p_hash;
          if ch.id is null then return null; end if;
          select * into p from system_control.principals where id=ch.principal_id for update;
          select * into ch from system_control.challenges where id=ch.id for update;
          if ch.consumed_at is not null or ch.expires_at<=clock_timestamp() or ch.attempts>=5
            or ch.issued_auth_version<>p.auth_version
            or p.status in ('blocked','revoked')
            or (ch.kind='preauth' and p.status<>'active') then return null; end if;
          update system_control.challenges set attempts=attempts+1 where id=ch.id;
          select jsonb_build_object('principal_id',p.id,'challenge_id',ch.id,'kind',ch.kind,
            'auth_version',p.auth_version,'credential_version',c.credential_version,
            'last_counter',c.last_totp_counter,
            'seed',encode(case when ch.kind='enrolment' then ch.encrypted_totp_seed else c.encrypted_totp_seed end,'hex'),
            'nonce',encode(case when ch.kind='enrolment' then ch.nonce else c.nonce end,'hex'),
            'key_id',case when ch.kind='enrolment' then ch.key_id else c.key_id end)
          into result from system_control.credentials c
          where c.principal_id=p.id and c.credential_version=ch.credential_version;
          return result;
        end
    """)
    function("auth_finish_totp(p_hash text, p_counter bigint, p_session_hash text)", "jsonb", """
        declare ch system_control.challenges; p system_control.principals; c system_control.credentials; sid uuid; issued timestamptz;
        begin
          if session_user <> 'twobrain_rec_system' then return null; end if;
          select * into ch from system_control.challenges where token_hash=p_hash;
          if ch.id is null then return null; end if;
          select * into p from system_control.principals where id=ch.principal_id for update;
          select * into ch from system_control.challenges where id=ch.id for update;
          select * into c from system_control.credentials where principal_id=p.id for update;
          if ch.kind<>'preauth' or ch.consumed_at is not null or ch.expires_at<=clock_timestamp()
            or ch.attempts>5 or ch.issued_auth_version<>p.auth_version
            or c.credential_version<>ch.credential_version or p.status<>'active'
            or p_counter is null or p_counter<=c.last_totp_counter
            or abs(p_counter-floor(extract(epoch from clock_timestamp())/30))>1 then
            perform system_control.auth_audit(p.id,'auth.mfa','denied'); return null; end if;
          update system_control.credentials set last_totp_counter=p_counter where principal_id=p.id;
          update system_control.challenges set consumed_at=clock_timestamp() where id=ch.id;
          sid := gen_random_uuid();
          issued := clock_timestamp();
          insert into system_control.sessions(id,principal_id,token_hash,auth_version,issued_at,
            last_interaction_at,absolute_expires_at,mfa_at)
          values(sid,p.id,p_session_hash,p.auth_version,issued,issued,
            issued+interval '12 hours',issued);
          perform system_control.auth_audit(p.id,'auth.mfa','allowed');
          return jsonb_build_object('principal_id',p.id,'session_id',sid);
        end
    """)
    function("auth_session(p_hash text)", "jsonb", """
        declare result jsonb;
        begin
          if session_user <> 'twobrain_rec_system' then return null; end if;
          select jsonb_build_object('principal_id',p.id,'session_id',s.id,'role',r.role,
            'expires_at',s.absolute_expires_at,'mfa_at',s.mfa_at)
          into result from system_control.sessions s
          join system_control.principals p on p.id=s.principal_id
          join system_control.role_assignments r on r.principal_id=p.id
          where s.token_hash=p_hash and p.status='active' and p.auth_version=s.auth_version
            and s.revoked_at is null and s.issued_at<=clock_timestamp()
            and s.last_interaction_at<=clock_timestamp() and s.mfa_at<=clock_timestamp()
            and s.last_interaction_at>clock_timestamp()-interval '30 minutes'
            and s.absolute_expires_at>clock_timestamp() and r.revoked_at is null
            and r.starts_at<=clock_timestamp() and (r.expires_at is null or r.expires_at>clock_timestamp());
          return result;
        end
    """)
    function("auth_session_action(p_hash text, p_action text)", "boolean", """
        declare s system_control.sessions; p system_control.principals;
        begin
          if session_user <> 'twobrain_rec_system' or p_action not in ('logout','activity') then return false; end if;
          select * into s from system_control.sessions where token_hash=p_hash;
          if s.id is null then return false; end if;
          select * into p from system_control.principals where id=s.principal_id for update;
          if system_control.auth_session(p_hash) is null then return false; end if;
          if p_action='logout' then
            update system_control.sessions set revoked_at=clock_timestamp() where id=s.id;
            perform system_control.auth_audit(p.id,'auth.logout','allowed');
          else update system_control.sessions set last_interaction_at=clock_timestamp() where id=s.id;
          end if;
          return true;
        end
    """)
    function("auth_recover(p_hash text, p_code_hash text, p_new_hash text)", "boolean", """
        declare ch system_control.challenges; p system_control.principals; c system_control.credentials;
        begin
          if session_user <> 'twobrain_rec_system' then return false; end if;
          select * into ch from system_control.challenges where token_hash=p_hash;
          if ch.id is null then return false; end if;
          select * into p from system_control.principals where id=ch.principal_id for update;
          select * into ch from system_control.challenges where id=ch.id for update;
          select * into c from system_control.credentials where principal_id=p.id for update;
          if ch.kind<>'preauth' or ch.consumed_at is not null or ch.expires_at<=clock_timestamp()
            or ch.attempts>=5 or ch.issued_auth_version<>p.auth_version
            or c.credential_version<>ch.credential_version or p.status<>'active' then return false; end if;
          update system_control.challenges set attempts=attempts+1 where id=ch.id;
          if p_code_hash is null or not p_code_hash=any(c.recovery_code_hashes) then
            perform system_control.auth_audit(p.id,'auth.recovery','denied'); return false; end if;
          update system_control.principals set auth_version=auth_version+1,status='recovery_pending'
            where id=p.id returning * into p;
          update system_control.credentials set recovery_code_hashes='{}',credential_version=credential_version+1
            where principal_id=p.id returning * into c;
          update system_control.sessions set revoked_at=clock_timestamp() where principal_id=p.id and revoked_at is null;
          update system_control.challenges set consumed_at=clock_timestamp() where principal_id=p.id and consumed_at is null;
          insert into system_control.challenges
            (principal_id,kind,token_hash,issued_auth_version,credential_version,expires_at)
          values(p.id,'enrolment',p_new_hash,p.auth_version,c.credential_version,clock_timestamp()+interval '5 minutes');
          perform system_control.auth_audit(p.id,'auth.recovery','allowed');
          return true;
        end
    """)
    function("auth_begin_enrolment(p_hash text, p_password text, p_seed bytea, p_nonce bytea, p_key text, p_new_hash text)", "boolean", """
        declare ch system_control.challenges; p system_control.principals; c system_control.credentials;
        begin
          if session_user <> 'twobrain_rec_system' then return false; end if;
          select * into ch from system_control.challenges where token_hash=p_hash;
          if ch.id is null then return false; end if;
          select * into p from system_control.principals where id=ch.principal_id for update;
          select * into ch from system_control.challenges where id=ch.id for update;
          select * into c from system_control.credentials where principal_id=p.id for update;
          if ch.kind not in ('invitation','enrolment') or ch.consumed_at is not null
            or ch.expires_at<=clock_timestamp() or ch.issued_auth_version<>p.auth_version
            or c.credential_version<>ch.credential_version or p.status not in ('invited','recovery_pending')
            or octet_length(p_nonce) is distinct from 12 or p_seed is null or p_key is null
            or length(p_key) not between 1 and 80 or ch.encrypted_totp_seed is not null
            or p_new_hash is null then return false; end if;
          if ch.kind='invitation' then
            if p_password is null or p_password !~ '^scrypt\\$131072\\$8\\$1\\$[0-9a-f]{32}\\$[0-9a-f]{64}$' then return false; end if;
            update system_control.principals set password_hash=p_password,auth_version=auth_version+1
              where id=p.id returning * into p;
            update system_control.challenges set consumed_at=clock_timestamp()
              where principal_id=p.id and id<>ch.id and consumed_at is null;
          end if;
          update system_control.challenges set consumed_at=clock_timestamp() where id=ch.id;
          insert into system_control.challenges(principal_id,kind,token_hash,issued_auth_version,
            credential_version,encrypted_totp_seed,nonce,key_id,expires_at)
          values(p.id,'enrolment',p_new_hash,p.auth_version,c.credential_version,p_seed,p_nonce,p_key,
            least(ch.expires_at,clock_timestamp()+interval '5 minutes'));
          perform system_control.auth_audit(p.id,'auth.enrolment.begin','allowed');
          return true;
        end
    """)
    function("auth_confirm_enrolment(p_hash text, p_counter bigint, p_session text, p_codes text[])", "jsonb", """
        declare ch system_control.challenges; p system_control.principals; c system_control.credentials; sid uuid; issued timestamptz;
        begin
          if session_user <> 'twobrain_rec_system' then return null; end if;
          select * into ch from system_control.challenges where token_hash=p_hash;
          if ch.id is null then return null; end if;
          select * into p from system_control.principals where id=ch.principal_id for update;
          select * into ch from system_control.challenges where id=ch.id for update;
          select * into c from system_control.credentials where principal_id=p.id for update;
          if ch.kind<>'enrolment' or ch.consumed_at is not null or ch.expires_at<=clock_timestamp()
            or ch.attempts>5 or ch.issued_auth_version<>p.auth_version
            or c.credential_version<>ch.credential_version or p.status not in ('invited','recovery_pending')
            or p.password_hash is null or ch.encrypted_totp_seed is null or p_counter is null
            or abs(p_counter-floor(extract(epoch from clock_timestamp())/30))>1
            or cardinality(p_codes) is distinct from 10
            or (select count(distinct code) from unnest(p_codes) code where code ~ '^[0-9a-f]{64}$')<>10
            then return null; end if;
          update system_control.principals set status='active',auth_version=auth_version+1
            where id=p.id returning * into p;
          update system_control.credentials set encrypted_totp_seed=ch.encrypted_totp_seed,
            nonce=ch.nonce,key_id=ch.key_id,last_totp_counter=p_counter,
            credential_version=credential_version+1,recovery_code_hashes=p_codes where principal_id=p.id;
          update system_control.challenges set consumed_at=clock_timestamp()
            where principal_id=p.id and consumed_at is null;
          update system_control.sessions set revoked_at=clock_timestamp()
            where principal_id=p.id and revoked_at is null;
          sid := gen_random_uuid();
          issued := clock_timestamp();
          insert into system_control.sessions(id,principal_id,token_hash,auth_version,issued_at,
            last_interaction_at,absolute_expires_at,mfa_at)
          values(sid,p.id,p_session,p.auth_version,issued,issued,
            issued+interval '12 hours',issued);
          perform system_control.auth_audit(p.id,'auth.enrolment.confirm','allowed');
          return jsonb_build_object('principal_id',p.id,'session_id',sid);
        end
    """)
    function("auth_second_factor(p_hash text)", "jsonb", """
        declare identity jsonb; result jsonb;
        begin
          if session_user <> 'twobrain_rec_system' then return null; end if;
          identity := system_control.auth_session(p_hash);
          if identity is null then return null; end if;
          select jsonb_build_object('principal_id',principal_id,'seed',encode(encrypted_totp_seed,'hex'),
            'nonce',encode(nonce,'hex'),'key_id',key_id,'last_counter',last_totp_counter)
          into result from system_control.credentials where principal_id=(identity->>'principal_id')::uuid;
          return result;
        end
    """)
    function("auth_step_up(p_hash text, p_counter bigint)", "boolean", """
        declare identity jsonb; actor uuid; last_counter bigint;
        begin
          if session_user <> 'twobrain_rec_system' then return false; end if;
          identity := system_control.auth_session(p_hash);
          if identity is null then return false; end if;
          actor := (identity->>'principal_id')::uuid;
          perform id from system_control.principals where id=actor for update;
          if system_control.auth_session(p_hash) is null then return false; end if;
          select last_totp_counter into last_counter from system_control.credentials where principal_id=actor for update;
          if p_counter is null or p_counter<=last_counter
            or abs(p_counter-floor(extract(epoch from clock_timestamp())/30))>1 then
            perform system_control.auth_audit(actor,'auth.step_up','denied'); return false; end if;
          update system_control.credentials set last_totp_counter=p_counter where principal_id=actor;
          update system_control.sessions set mfa_at=clock_timestamp() where token_hash=p_hash;
          perform system_control.auth_audit(actor,'auth.step_up','allowed'); return true;
        end
    """)
    function("auth_request_reset(p_email text, p_hash text)", "uuid", """
        declare p system_control.principals; credential integer;
        begin
          if session_user <> 'twobrain_rec_system' then return null; end if;
          select * into p from system_control.principals where normalized_email=p_email for update;
          if p.status is distinct from 'active' then return null; end if;
          select credential_version into credential from system_control.credentials where principal_id=p.id;
          update system_control.challenges set consumed_at=clock_timestamp()
            where principal_id=p.id and kind='reset' and consumed_at is null;
          insert into system_control.challenges(principal_id,kind,token_hash,issued_auth_version,credential_version,expires_at)
            values(p.id,'reset',p_hash,p.auth_version,credential,clock_timestamp()+interval '15 minutes');
          perform system_control.auth_audit(p.id,'auth.reset.request','allowed'); return p.id;
        end
    """)
    function("auth_complete_reset(p_hash text, p_password text)", "boolean", """
        declare ch system_control.challenges; p system_control.principals; c system_control.credentials;
        begin
          if session_user <> 'twobrain_rec_system' then return false; end if;
          select * into ch from system_control.challenges where token_hash=p_hash;
          if ch.id is null then return false; end if;
          select * into p from system_control.principals where id=ch.principal_id for update;
          select * into ch from system_control.challenges where id=ch.id for update;
          select * into c from system_control.credentials where principal_id=p.id for update;
          if p.status<>'active' or ch.kind<>'reset' or ch.consumed_at is not null
            or ch.expires_at<=clock_timestamp() or ch.issued_auth_version<>p.auth_version
            or ch.credential_version<>c.credential_version
            or p_password is null or p_password !~ '^scrypt\\$131072\\$8\\$1\\$[0-9a-f]{32}\\$[0-9a-f]{64}$'
            then return false; end if;
          update system_control.principals set password_hash=p_password,auth_version=auth_version+1 where id=p.id;
          update system_control.credentials set credential_version=credential_version+1,recovery_code_hashes='{}' where principal_id=p.id;
          update system_control.sessions set revoked_at=clock_timestamp() where principal_id=p.id and revoked_at is null;
          update system_control.challenges set consumed_at=clock_timestamp() where principal_id=p.id and consumed_at is null;
          perform system_control.auth_audit(p.id,'auth.reset.complete','allowed'); return true;
        end
    """)
    function("auth_factor_attempt(p_hash text, p_attempt uuid, p_success boolean default null)", "boolean", """
        declare actor uuid; email text;
        begin
          if session_user <> 'twobrain_rec_system' then return false; end if;
          select p.id,p.normalized_email into actor,email from system_control.principals p
            where p.id=coalesce(
              (select principal_id from system_control.challenges where token_hash=p_hash),
              (select principal_id from system_control.sessions where token_hash=p_hash));
          if actor is null then return false; end if;
          if p_success is null then
            return system_control.auth_rate_limit(encode(sha256(convert_to(email,'UTF8')),'hex'),'account',p_attempt);
          end if;
          if p_success then
            delete from system_control.rate_limits where attempt_id=p_attempt and kind='account'
              and bucket_hash=encode(sha256(convert_to(email,'UTF8')),'hex');
          end if;
          perform system_control.auth_audit(actor,'auth.factor',case when p_success then 'allowed' else 'denied' end);
          return true;
        end
    """)
    op.execute(f"revoke create on schema system_control from {AUTH}")


def downgrade() -> None:
    op.execute("""do $$ begin if exists(select 1 from system_control.credentials)
        or exists(select 1 from system_control.challenges)
        then raise exception 'system credentials exist; destructive downgrade refused'; end if; end $$""")
    for signature in ("auth_delivery(text,text)", "auth_factor_attempt(text,uuid,boolean)", "auth_complete_reset(text,text)", "auth_request_reset(text,text)",
                      "auth_step_up(text,bigint)", "auth_second_factor(text)", "auth_confirm_enrolment(text,bigint,text,text[])",
                      "auth_begin_enrolment(text,text,bytea,bytea,text,text)",
                      "auth_recover(text,text,text)", "auth_session_action(text,text)", "auth_session(text)",
                      "auth_finish_totp(text,bigint,text)", "auth_challenge(text)",
                      "auth_issue_preauth(uuid,integer,integer,text)", "auth_lookup(text)",
                      "auth_rate_limit(text,text,uuid)", "auth_login_result(text,boolean,uuid)", "auth_audit(uuid,text,text)"):
        op.execute(f"drop function system_control.{signature}")
    for table in ("challenges", "credentials", "rate_limits"):
        op.drop_table(table,schema="system_control")
    op.execute(f"revoke insert on system_control.audit_events from {AUTH}")
    op.execute("drop policy auth_audit on system_control.audit_events")
    op.execute("alter table system_control.audit_events alter column principal_id set not null")
    op.execute("alter table system_control.audit_events alter column session_id set not null")
    for table in ("principals", "sessions"):
        op.execute(f"drop policy auth_access on system_control.{table}")
        op.execute(f"revoke select,insert,update on system_control.{table} from {AUTH}")
    op.execute("drop policy auth_read on system_control.role_assignments")
    op.execute(f"revoke select on system_control.role_assignments from {AUTH}")
    op.execute(f"revoke usage on schema system_control from {AUTH}")
