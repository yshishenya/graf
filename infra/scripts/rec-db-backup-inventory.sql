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
  \! pg_dump -U "$GRAF_DB_ROLE" -d "$GRAF_DB_NAME" --snapshot="$GRAF_DB_SNAPSHOT" --schema-only --file="$GRAF_DB_STAGING/schema.sql"
  \if :SHELL_ERROR
    DO $$BEGIN RAISE EXCEPTION 'graf_backup_validation_failed'; END$$;
  \endif
\endif
\set inventory_path :staging '/inventory.jsonl'
\o :inventory_path
SELECT json_build_object('kind','snapshot','format_version',1,
    'database',current_database(),'role',current_user,
    'snapshot',:'exported_snapshot','server_version',current_setting('server_version_num'));
SELECT json_build_object('kind','role','name',rolname,'superuser',rolsuper,
    'inherit',rolinherit,'create_role',rolcreaterole,'create_db',rolcreatedb,
    'login',rolcanlogin,'replication',rolreplication,'bypass_rls',rolbypassrls)
FROM pg_roles ORDER BY rolname;
SELECT json_build_object('kind','membership','role',r.rolname,'member',m.rolname,
    'grantor',g.rolname,'admin',a.admin_option,'inherit',a.inherit_option,'set',a.set_option)
FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.roleid
JOIN pg_roles m ON m.oid=a.member JOIN pg_roles g ON g.oid=a.grantor
ORDER BY r.rolname,m.rolname,g.rolname;
SELECT json_build_object('kind','relation','schema',n.nspname,'name',c.relname,
    'type',c.relkind,'owner',pg_get_userbyid(c.relowner),'acl',c.relacl::text,
    'rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity)
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_'
ORDER BY n.nspname,c.relname;
SELECT json_build_object('kind','constraint','schema',n.nspname,'relation',c.relname,
    'name',k.conname,'definition',pg_get_constraintdef(k.oid),
    'validated',k.convalidated,'deferrable',k.condeferrable,'deferred',k.condeferred)
FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_'
ORDER BY n.nspname,c.relname,k.conname;
SELECT json_build_object('kind','policy','schema',schemaname,'relation',tablename,
    'name',policyname,'permissive',permissive,'roles',roles,'command',cmd,
    'using',qual,'check',with_check)
FROM pg_policies ORDER BY schemaname,tablename,policyname;
SELECT format('SELECT json_build_object(''kind'',''count'',''relation'',%L,''rows'',count(*)) FROM %I.%I;',
    n.nspname||'.'||c.relname,n.nspname,c.relname)
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','p','m') AND n.nspname NOT IN ('pg_catalog','information_schema')
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
