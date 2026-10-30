-- F273/T113: native dump and metadata from ONE exported PostgreSQL snapshot.
-- Run psql -XqAt -v ON_ERROR_STOP=1; its shell inherits umask 077.
-- No event payload, account identifier, password or meeting content is selected.
\set ON_ERROR_STOP on
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL row_security = off;
SELECT current_database() = :'expected_db'
       AND (rolsuper OR rolbypassrls)
       AND :'staging' ~ '^/tmp/twobrain-rec-backup\.[A-Za-z0-9]+$'
       AND to_regclass('public.product_activation_milestones') IS NOT NULL AS valid_source
FROM pg_roles WHERE rolname = current_user \gset
\if :valid_source
\else
  DO $$BEGIN RAISE EXCEPTION 'graf_backup_validation_failed'; END$$;
\endif
SELECT pg_export_snapshot() AS exported_snapshot \gset
\setenv GRAF_DB_SNAPSHOT :exported_snapshot
\setenv GRAF_DB_STAGING :staging
\setenv GRAF_DB_NAME :expected_db
SELECT current_user AS backup_role \gset
\setenv GRAF_DB_ROLE :backup_role
\if :capture_dump
  \! pg_dump -U "$GRAF_DB_ROLE" -d "$GRAF_DB_NAME" --snapshot="$GRAF_DB_SNAPSHOT" --format=custom --file="$GRAF_DB_STAGING/postgres.dump"
  \if :SHELL_ERROR
    DO $$BEGIN RAISE EXCEPTION 'graf_backup_validation_failed'; END$$;
  \endif
\endif
\! pg_dump -U "$GRAF_DB_ROLE" -d "$GRAF_DB_NAME" --snapshot="$GRAF_DB_SNAPSHOT" --schema-only --file="$GRAF_DB_STAGING/schema.sql"
\if :SHELL_ERROR
  DO $$BEGIN RAISE EXCEPTION 'graf_backup_validation_failed'; END$$;
\endif
-- Reject unsupported settings without writing their potentially secret values.
SELECT NOT EXISTS (
    SELECT FROM pg_db_role_setting s LEFT JOIN pg_roles r ON r.oid=s.setrole,
        unnest(s.setconfig) value
    WHERE (s.setdatabase=0 OR s.setdatabase=(SELECT oid FROM pg_database WHERE datname=current_database()))
      AND (s.setrole=0 OR r.rolname IN ('twobrain_rec','twobrain_rec_app','twobrain_rec_maintenance','twobrain_rec_media'))
      AND value NOT IN ('row_security=on','row_security=off')) AS valid_settings \gset
\if :valid_settings
\else
  DO $$BEGIN RAISE EXCEPTION 'graf_backup_validation_failed'; END$$;
\endif
\set inventory_path :staging '/inventory.jsonl'
\o :inventory_path
SELECT json_build_object('kind','snapshot','format_version',2,
    'database',current_database(),'role',current_user,
    'snapshot',:'exported_snapshot','server_version',current_setting('server_version_num'));
SELECT json_build_object('kind','role','name',rolname,'superuser',rolsuper,
    'inherit',rolinherit,'create_role',rolcreaterole,'create_db',rolcreatedb,
    'login',rolcanlogin,'replication',rolreplication,'bypass_rls',rolbypassrls,
    'connection_limit',rolconnlimit,'valid_until',rolvaliduntil::text)
FROM pg_roles ORDER BY rolname;
SELECT json_build_object('kind','role_setting','role',coalesce(r.rolname,'PUBLIC'),
    'scope',CASE WHEN s.setdatabase=0 THEN 'global' ELSE 'current' END,
    'name','row_security','value',split_part(value,'=',2))
FROM pg_db_role_setting s LEFT JOIN pg_roles r ON r.oid=s.setrole,unnest(s.setconfig) value
WHERE (s.setdatabase=0 OR s.setdatabase=(SELECT oid FROM pg_database WHERE datname=current_database()))
    AND (s.setrole=0 OR r.rolname IN ('twobrain_rec','twobrain_rec_app','twobrain_rec_maintenance','twobrain_rec_media'))
ORDER BY r.rolname,s.setdatabase,value;
SELECT json_build_object('kind','membership','role',r.rolname,'member',m.rolname,
    'grantor',g.rolname,'admin',a.admin_option,'inherit',a.inherit_option,'set',a.set_option)
FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.roleid
JOIN pg_roles m ON m.oid=a.member JOIN pg_roles g ON g.oid=a.grantor
ORDER BY r.rolname,m.rolname,g.rolname;
SELECT json_build_object('kind','relation','schema',n.nspname,'name',c.relname,
    'type',c.relkind,'persistence',c.relpersistence,'owner',pg_get_userbyid(c.relowner),'acl',c.relacl::text,
    'rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity,
    'public_access',EXISTS(SELECT FROM aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) WHERE grantee=0))
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_'
ORDER BY n.nspname,c.relname;
SELECT json_build_object('kind','constraint','schema',n.nspname,'relation',c.relname,
    'name',k.conname,'definition',pg_get_constraintdef(k.oid),
    'validated',k.convalidated,'deferrable',k.condeferrable,'deferred',k.condeferred,
    'type',k.contype,'columns',ARRAY(SELECT a.attname FROM unnest(k.conkey) WITH ORDINALITY x(num,ord)
        JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=x.num ORDER BY ord),
    'index',(SELECT relname FROM pg_class WHERE oid=k.conindid),
    'referenced_relation',(SELECT rn.nspname||'.'||rc.relname FROM pg_class rc
        JOIN pg_namespace rn ON rn.oid=rc.relnamespace WHERE rc.oid=k.confrelid),
    'referenced_columns',ARRAY(SELECT a.attname FROM unnest(k.confkey) WITH ORDINALITY x(num,ord)
        JOIN pg_attribute a ON a.attrelid=k.confrelid AND a.attnum=x.num ORDER BY ord),
    'on_delete',k.confdeltype)
FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_'
ORDER BY n.nspname,c.relname,k.conname;
SELECT json_build_object('kind','index','schema',n.nspname,'name',c.relname,
    'valid',i.indisvalid,'ready',i.indisready,'live',i.indislive,
    'unique',i.indisunique,'primary',i.indisprimary)
FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_'
ORDER BY n.nspname,c.relname;
SELECT json_build_object('kind','trigger','schema',n.nspname,'relation',c.relname,
    'name',t.tgname,'enabled',t.tgenabled,'type',t.tgtype,
    'function_schema',pn.nspname,'function',p.proname,'function_md5',md5(p.prosrc),
    'security_definer',p.prosecdef)
FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace pn ON pn.oid=p.pronamespace
WHERE NOT t.tgisinternal AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_'
ORDER BY n.nspname,c.relname,t.tgname;
SELECT json_build_object('kind','policy','schema',schemaname,'relation',tablename,
    'name',policyname,'permissive',permissive,'roles',roles,'command',cmd,
    'using',qual,'check',with_check)
FROM pg_policies ORDER BY schemaname,tablename,policyname;
SELECT json_build_object('kind','ledger_column','name',a.attname,
    'type',format_type(a.atttypid,a.atttypmod),'not_null',a.attnotnull,
    'default_md5',md5(pg_get_expr(d.adbin,d.adrelid)),'identity',a.attidentity,
    'generated',a.attgenerated,'acl',a.attacl::text)
FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
WHERE a.attrelid='public.product_activation_milestones'::regclass AND a.attnum>0 AND NOT a.attisdropped
ORDER BY a.attname;
SELECT json_build_object('kind','ledger_access','role',r.rolname,
    'select',has_table_privilege(r.oid,'public.product_activation_milestones','SELECT'),
    'insert',has_table_privilege(r.oid,'public.product_activation_milestones','INSERT'),
    'update',has_table_privilege(r.oid,'public.product_activation_milestones','UPDATE'),
    'delete',has_table_privilege(r.oid,'public.product_activation_milestones','DELETE'),
    'truncate',has_table_privilege(r.oid,'public.product_activation_milestones','TRUNCATE'),
    'references',has_table_privilege(r.oid,'public.product_activation_milestones','REFERENCES'),
    'trigger',has_table_privilege(r.oid,'public.product_activation_milestones','TRIGGER'),
    'maintain',has_table_privilege(r.oid,'public.product_activation_milestones','MAINTAIN'),
    'grant_option',EXISTS(SELECT FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN']) p
        WHERE has_table_privilege(r.oid,'public.product_activation_milestones',p||' WITH GRANT OPTION')))
FROM pg_roles r WHERE rolname IN ('twobrain_rec_app','twobrain_rec_maintenance','twobrain_rec_media') ORDER BY rolname;
SELECT to_regclass('public.alembic_version') IS NOT NULL AS has_revision \gset
\if :has_revision
  SELECT json_build_object('kind','revision','name',version_num) FROM public.alembic_version ORDER BY version_num;
\endif
SELECT format('SELECT json_build_object(''kind'',''count'',''relation'',%L,''rows'',count(*)) FROM %I.%I;',
    n.nspname||'.'||c.relname,n.nspname,c.relname)
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','p','m') AND n.nspname NOT IN ('pg_catalog','information_schema')
    AND n.nspname !~ '^pg_'
ORDER BY n.nspname,c.relname \gexec
-- Sequence state is not MVCC: differing counters read by pg_dump and this
-- inventory fail source/restore comparison; they are not exported snapshot proof.
SELECT format('SELECT json_build_object(''kind'',''sequence_state'',''schema'',%L,''name'',%L,''last_value'',last_value,''is_called'',is_called) FROM %I.%I;',
    n.nspname,c.relname,n.nspname,c.relname)
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind = 'S' AND n.nspname NOT IN ('pg_catalog','information_schema')
    AND n.nspname !~ '^pg_'
ORDER BY n.nspname,c.relname \gexec
-- Do not copy arbitrary corrupt state text into the inventory.
SELECT NOT EXISTS (SELECT FROM public.product_activation_milestones
    WHERE posthog_state NOT IN ('not_requested','pending','pre_send_retry','dispatching',
      'submitted','ambiguous','confirmed','cancelled','rejected')
       OR yandex_state NOT IN ('not_requested','pending','pre_send_retry','dispatching',
      'submitted','ambiguous','confirmed','cancelled','rejected')
       OR posthog_state IS NULL OR yandex_state IS NULL) AS valid_states \gset
\if :valid_states
\else
  DO $$BEGIN RAISE EXCEPTION 'graf_backup_validation_failed'; END$$;
\endif
SELECT json_build_object('kind','activation_states','posthog_state',posthog_state,
    'yandex_state',yandex_state,'rows',count(*))
FROM public.product_activation_milestones GROUP BY posthog_state,yandex_state
ORDER BY posthog_state,yandex_state;
COMMIT;
\o
\if :capture_dump
  \! cd "$GRAF_DB_STAGING" && sha256sum postgres.dump schema.sql inventory.jsonl > checksums.sha256
  \if :SHELL_ERROR
    DO $$BEGIN RAISE EXCEPTION 'graf_backup_validation_failed'; END$$;
  \endif
\endif
