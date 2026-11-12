from __future__ import annotations

import asyncio
import os
import re
from importlib import import_module
from pathlib import Path

import asyncpg

OWNER_ROLE = "twobrain_rec"
APP_ROLE = "twobrain_rec_app"
MAINTENANCE_ROLE = "twobrain_rec_maintenance"
MEDIA_ROLE = "twobrain_rec_media"
DATABASE_NAME = "twobrain_rec"
DATABASE_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
MEDIA_READ_ONLY_TABLES = (
    "alembic_version",
    "meetings",
    "media_revisions",
    "upload_sessions",
    "workspace_subscriptions",
    "workspaces",
)
MEDIA_WORKFLOW_COLUMNS = ("workflow_id", "workspace_id", "meeting_id", "media_revision_id", "purpose", "status", "attempt_ordinal", "created_at")
MEDIA_STORAGE_COLUMNS = {
    "time_credit_ledger_entries": (
        "workspace_id", "state", "applied_start", "applied_end", "capacity_snapshot_bytes",
    ),
    "billing_storage_entitlement_grants": (
        "id", "workspace_id", "starts_at", "ends_at", "capacity_bytes",
    ),
    "billing_entitlement_grants": ("invoice_id", "workspace_id", "starts_at", "ends_at"),
    "billing_invoices": ("id", "workspace_id", "plan_snapshot"),
}
MEDIA_READ_WRITE_TABLES = (
    "playback_backfill_runs",
    "playback_normalization_attempts",
    "playback_normalization_jobs",
    "storage_reservations",
    "support_incidents",
    "track_artifacts",
)
MEDIA_INSERT_ONLY_TABLES = ("ingest_audit_events",)
MEDIA_LOCK_COLUMNS = (
    ("meetings", "updated_at"),
    ("media_revisions", "updated_at"),
)


def _table_list(table_names: tuple[str, ...]) -> str:
    return ", ".join(f"public.{table_name}" for table_name in table_names)


def _read_secret(environment_name: str) -> str:
    raw_path = os.environ.get(environment_name, "").strip()
    if not raw_path:
        raise RuntimeError("runtime database role secret path is missing")
    path = Path(raw_path)
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError("runtime database role secret is unreadable") from exc
    if not value:
        raise RuntimeError("runtime database role secret is empty")
    return value


async def _ensure_login_role(
    connection: asyncpg.Connection,
    *,
    role_name: str,
    password: str,
) -> None:
    exists = await connection.fetchval(
        "select exists(select 1 from pg_roles where rolname = $1)",
        role_name,
    )
    if not exists:
        await connection.execute(f"create role {role_name}")
    quoted_password = await connection.fetchval(
        "select pg_catalog.quote_literal($1::text)",
        password,
    )
    await connection.execute(
        f"alter role {role_name} with login password {quoted_password} "
        "nosuperuser nocreatedb nocreaterole noinherit noreplication nobypassrls"
    )
    await connection.execute(f"alter role {role_name} set row_security = on")


async def _verify_runtime_roles(
    connection: asyncpg.Connection,
    *,
    database_name: str,
) -> None:
    role_rows = await connection.fetch(
        """
        select rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
               rolinherit, rolreplication, rolbypassrls
        from pg_roles
        where rolname = any($1::text[])
        order by rolname
        """,
        [APP_ROLE, MAINTENANCE_ROLE, MEDIA_ROLE],
    )
    if len(role_rows) != 3:
        raise RuntimeError("runtime database roles are missing")
    for row in role_rows:
        if (
            not row["rolcanlogin"]
            or row["rolsuper"]
            or row["rolcreatedb"]
            or row["rolcreaterole"]
            or row["rolinherit"]
            or row["rolreplication"]
            or row["rolbypassrls"]
        ):
            raise RuntimeError("runtime database role attributes are unsafe")

    membership_count = await connection.fetchval(
        """
        select count(*)
        from pg_auth_members as memberships
        join pg_roles as member_roles on member_roles.oid = memberships.member
        join pg_roles as granted_roles on granted_roles.oid = memberships.roleid
        where member_roles.rolname = any($1::text[])
           or granted_roles.rolname = any($1::text[])
        """,
        [APP_ROLE, MAINTENANCE_ROLE, MEDIA_ROLE],
    )
    if membership_count:
        raise RuntimeError("runtime database role membership is unsafe")

    app_workspace_execute = await connection.fetchval(
        "select has_function_privilege($1::name, $2::text, 'EXECUTE')",
        APP_ROLE,
        "public.rec_playback_normalization_workspace_page(uuid, integer)",
    )
    app_cleanup_execute = await connection.fetchval(
        "select has_function_privilege($1::name, $2::text, 'EXECUTE')",
        APP_ROLE,
        "public.rec_playback_normalization_cleanup_page(integer)",
    )
    maintenance_workspace_execute = await connection.fetchval(
        "select has_function_privilege($1::name, $2::text, 'EXECUTE')",
        MAINTENANCE_ROLE,
        "public.rec_playback_normalization_workspace_page(uuid, integer)",
    )
    maintenance_cleanup_execute = await connection.fetchval(
        "select has_function_privilege($1::name, $2::text, 'EXECUTE')",
        MAINTENANCE_ROLE,
        "public.rec_playback_normalization_cleanup_page(integer)",
    )
    media_workspace_execute = await connection.fetchval(
        "select has_function_privilege($1::name, $2::text, 'EXECUTE')",
        MEDIA_ROLE,
        "public.rec_playback_normalization_workspace_page(uuid, integer)",
    )
    media_cleanup_execute = await connection.fetchval(
        "select has_function_privilege($1::name, $2::text, 'EXECUTE')",
        MEDIA_ROLE,
        "public.rec_playback_normalization_cleanup_page(integer)",
    )
    app_account_merge_execute = await connection.fetchval(
        "select has_function_privilege($1::name, $2::text, 'EXECUTE')",
        APP_ROLE,
        "public.rec_account_merge_context_valid()",
    )
    maintenance_account_merge_execute = await connection.fetchval(
        "select has_function_privilege($1::name, $2::text, 'EXECUTE')",
        MAINTENANCE_ROLE,
        "public.rec_account_merge_context_valid()",
    )
    if (
        app_workspace_execute
        or app_cleanup_execute
        or maintenance_workspace_execute
        or maintenance_cleanup_execute
        or not app_account_merge_execute
        or not maintenance_account_merge_execute
        or not media_workspace_execute
        or not media_cleanup_execute
    ):
        raise RuntimeError("runtime database function privileges are unsafe")

    for role_name in (APP_ROLE, MAINTENANCE_ROLE, MEDIA_ROLE):
        has_database = await connection.fetchval(
            "select has_database_privilege($1::name, $2::text, 'CONNECT')",
            role_name,
            database_name,
        )
        has_schema = await connection.fetchval(
            "select has_schema_privilege($1::name, 'public', 'USAGE')",
            role_name,
        )
        if not has_database or not has_schema:
            raise RuntimeError("runtime database role privileges are incomplete")

    app_has_meeting_dml = await connection.fetchval(
        "select has_table_privilege($1::name, 'public.meetings', 'SELECT,INSERT,UPDATE,DELETE')",
        APP_ROLE,
    )
    if not app_has_meeting_dml:
        raise RuntimeError("application database role privileges are incomplete")
    maintenance_has_meeting_dml = await connection.fetchval(
        "select has_table_privilege($1::name, 'public.meetings', 'SELECT,INSERT,UPDATE,DELETE')",
        MAINTENANCE_ROLE,
    )
    if not maintenance_has_meeting_dml:
        raise RuntimeError("maintenance database role privileges are incomplete")

    media_table_grants = await connection.fetch(
        """
        select table_name, privilege_type
        from information_schema.role_table_grants
        where grantee = $1
          and table_schema = 'public'
        order by table_name, privilege_type
        """,
        MEDIA_ROLE,
    )
    expected_media_table_grants = {
        *((table_name, "SELECT") for table_name in MEDIA_READ_ONLY_TABLES),
        *(
            (table_name, privilege_type)
            for table_name in MEDIA_READ_WRITE_TABLES
            for privilege_type in ("INSERT", "SELECT", "UPDATE")
        ),
        *((table_name, "INSERT") for table_name in MEDIA_INSERT_ONLY_TABLES),
    }
    actual_media_table_grants = {
        (row["table_name"], row["privilege_type"]) for row in media_table_grants
    }
    if actual_media_table_grants != expected_media_table_grants:
        raise RuntimeError("media database role table privileges are unsafe")
    workflow_grants = await connection.fetch(
        "select column_name, privilege_type from information_schema.role_column_grants "
        "where grantee = $1 and table_schema = 'public' and table_name = 'processing_workflows'",
        MEDIA_ROLE,
    )
    if {(row["column_name"], row["privilege_type"]) for row in workflow_grants} != {
        (name, "SELECT") for name in MEDIA_WORKFLOW_COLUMNS
    }:
        raise RuntimeError("media workflow metadata privileges are unsafe")

    storage_grants = await connection.fetch(
        "select table_name, column_name, privilege_type, is_grantable "
        "from information_schema.role_column_grants "
        "where grantee = $1 and table_schema = 'public' and table_name = any($2::text[])",
        MEDIA_ROLE,
        list(MEDIA_STORAGE_COLUMNS),
    )
    if {
        (row["table_name"], row["column_name"], row["privilege_type"], row["is_grantable"])
        for row in storage_grants
    } != {
        (table, column, "SELECT", "NO")
        for table, columns in MEDIA_STORAGE_COLUMNS.items()
        for column in columns
    }:
        raise RuntimeError("media storage column privileges are unsafe")

    for table_name, column_name in MEDIA_LOCK_COLUMNS:
        has_lock_column = await connection.fetchval(
            "select has_column_privilege($1::name, $2::text, $3::text, 'UPDATE')",
            MEDIA_ROLE,
            f"public.{table_name}",
            column_name,
        )
        has_business_column = await connection.fetchval(
            "select has_column_privilege($1::name, $2::text, 'status', 'UPDATE')",
            MEDIA_ROLE,
            f"public.{table_name}",
        )
        if not has_lock_column or has_business_column:
            raise RuntimeError("media database role lock privileges are unsafe")


async def _restrict_receipt_observation_source(connection: asyncpg.Connection) -> None:
    table = "public.billing_receipt_observation_deltas"
    if not await connection.fetchval("select to_regclass($1)", table):
        return  # The role bootstrap also runs before the migration is installed.
    sequence = table + "_id_seq"
    trigger = "public.rec_append_receipt_observation()"
    bases = "public.rec_receipt_observation_bases(jsonb)"
    writer = "twobrain_rec_receipt_observation_writer"
    runtime = f"public, {APP_ROLE}, {MAINTENANCE_ROLE}, {MEDIA_ROLE}"
    for statement in (
        f"revoke all on {table} from {runtime}",
        f"revoke all on sequence {sequence} from {runtime}",
        f"revoke all on function {trigger}, {bases} from {runtime}",
        f"grant select on {table} to {MAINTENANCE_ROLE}",
    ):
        await connection.execute(statement)
    safe = await connection.fetchval(
        """
        select not (r.rolcanlogin or r.rolinherit or r.rolsuper or r.rolbypassrls
                    or r.rolcreatedb or r.rolcreaterole or r.rolreplication)
            and not exists (select from pg_auth_members m where r.oid in (m.roleid, m.member))
            and not has_schema_privilege(r.oid, 'public', 'CREATE')
            and has_schema_privilege(r.oid, 'public', 'USAGE')
            and p.proowner = r.oid and p.prosecdef
            and has_table_privilege(r.oid, $2, 'INSERT')
            and not has_any_column_privilege(r.oid, $2, 'SELECT,UPDATE,REFERENCES')
            and not has_table_privilege(r.oid, $2, 'DELETE,TRUNCATE,TRIGGER')
            and has_sequence_privilege(r.oid, $3, 'USAGE')
            and not has_sequence_privilege(r.oid, $3, 'SELECT,UPDATE')
            and has_function_privilege(r.oid, $5, 'EXECUTE')
            and not exists (
                select from pg_class c join pg_namespace n on n.oid = c.relnamespace
                where n.nspname !~ '^pg_' and n.nspname <> 'information_schema'
                  and c.oid not in ($2::text::regclass, $3::text::regclass)
                  and case
                    when c.relkind = 'S' then has_sequence_privilege(r.oid, c.oid, 'USAGE,SELECT,UPDATE')
                    when c.relkind in ('r','p','v','m','f') then
                        has_table_privilege(r.oid, c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                        or has_any_column_privilege(r.oid, c.oid, 'SELECT,INSERT,UPDATE,REFERENCES')
                    else false
                  end
            )
        from pg_roles r join pg_proc p on p.oid = $4::text::regprocedure
        where r.rolname = $1
        """,
        writer, table, sequence, trigger, bases,
    )
    if not safe:
        raise RuntimeError("receipt observation writer role is unsafe")
    for role in (APP_ROLE, MAINTENANCE_ROLE, MEDIA_ROLE):
        safe = await connection.fetchval(
            """
            select has_table_privilege($1::name, $2, 'SELECT') = $6
               and ($6 or not has_any_column_privilege($1::name, $2, 'SELECT'))
               and not has_any_column_privilege($1::name, $2, 'INSERT,UPDATE,REFERENCES')
               and not has_table_privilege($1::name, $2, 'DELETE,TRUNCATE,TRIGGER')
               and not has_sequence_privilege($1::name, $3, 'USAGE,SELECT,UPDATE')
               and not has_function_privilege($1::name, $4, 'EXECUTE')
               and not has_function_privilege($1::name, $5, 'EXECUTE')
            """,
            role, table, sequence, trigger, bases, role == MAINTENANCE_ROLE,
        )
        if not safe:
            raise RuntimeError("receipt observation runtime privileges are unsafe")


async def _verify_fair_use_definitions(connection: asyncpg.Connection, schema) -> None:
    # Parse the expected SQL with this PostgreSQL version, rather than comparing formatting.
    policy_query = """
        select polname,polcmd,polpermissive,polroles,
            pg_get_expr(polqual,polrelid) as using_expression,
            pg_get_expr(polwithcheck,polrelid) as check_expression
        from pg_policy where polrelid=to_regclass($1) order by polname
    """
    for table, policies in schema.POLICIES.items():
        await connection.execute(f"CREATE TEMP TABLE {table} (LIKE public.{table}) ON COMMIT DROP")
        for name, definition in policies.items():
            await connection.execute(f"CREATE POLICY {name} ON pg_temp.{table} {definition}")
        actual = await connection.fetch(policy_query, f"public.{table}")
        expected = await connection.fetch(policy_query, f"pg_temp.{table}")
        if actual != expected:
            raise RuntimeError("fair-use policy definition is unsafe")
    await connection.execute(
        f"CREATE UNIQUE INDEX {schema.INDEX} ON pg_temp.billing_audit_events {schema.INDEX_DEFINITION}"
    )
    index_query = """
        select i.indisunique,i.indisvalid,i.indisready,i.indislive,i.indisprimary,
            i.indisexclusion,i.indnullsnotdistinct,i.indnkeyatts,i.indnatts,
            i.indkey,i.indclass,i.indcollation,i.indoption,c.relam,
            pg_get_expr(i.indexprs,i.indrelid) as expressions,
            pg_get_expr(i.indpred,i.indrelid) as predicate
        from pg_index i join pg_class c on c.oid=i.indexrelid
        where i.indexrelid=to_regclass($1) and i.indrelid=to_regclass($2)
    """
    actual = await connection.fetchrow(index_query, f"public.{schema.INDEX}", "public.billing_audit_events")
    expected = await connection.fetchrow(index_query, f"pg_temp.{schema.INDEX}", "pg_temp.billing_audit_events")
    if actual != expected:
        raise RuntimeError("fair-use history index is unsafe")
    for table in schema.POLICIES:
        await connection.execute(f"DROP TABLE pg_temp.{table}")


async def _restrict_fair_use_history(connection: asyncpg.Connection) -> None:
    """Keep migration-owned transition/audit protection after broad runtime grants."""
    names = ("rec_guard_fair_use_review", "rec_append_fair_use_audit",
             "rec_guard_fair_use_audit", "rec_guard_fair_use_truncate")
    functions = await connection.fetch(
        "select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
        "where n.nspname='public' and p.proname=any($1::text[])", list(names),
    )
    if not functions:
        partial = await connection.fetchval("""
            select to_regclass('public.uq_fair_use_audit_transition') is not null
                or exists(select from pg_policy where polrelid='public.fair_use_reviews'::regclass
                          and polname='fair_use_review_read')
                or exists(select from public.alembic_version where version_num='0113_fair_use_operator_history')
        """)
        if partial:
            raise RuntimeError("fair-use history schema is incomplete")
        return  # Bootstrap also runs before 0113 is installed.
    if len(functions) != len(names):
        raise RuntimeError("fair-use history schema is incomplete")
    schema = import_module("twobrain_rec_server.db.migrations.versions.0113_fair_use_operator_history")
    for role in ("PUBLIC", *schema.RUNTIME):
        for statement in schema.runtime_grants(role):
            await connection.execute(statement)
    owner = await connection.fetchval("select relowner from pg_class where oid='public.fair_use_reviews'::regclass")
    writer = await connection.fetchval("select oid from pg_roles where rolname=$1", schema.WRITER)
    if not writer:
        raise RuntimeError("fair-use audit writer is missing")
    for signature, (returns, body) in schema.CONTEXT_HELPERS.items():
        valid = await connection.fetchval("""
            select prosrc=$2 and proowner=$3 and not prosecdef and provolatile='s'
                and prorettype=$4::regtype and prolang=(select oid from pg_language where lanname='sql')
                and proconfig is null
            from pg_proc where oid=to_regprocedure($1)
        """, f"public.{signature.replace('(name text)', '(text)')}", body, owner, returns)
        if not valid:
            raise RuntimeError("fair-use context helper is unsafe")
    for name, body in schema.FUNCTIONS.items():
        row = await connection.fetchrow("""
            select prosrc,proowner,prosecdef,proconfig,prorettype='trigger'::regtype as is_trigger,
                prolang=(select oid from pg_language where lanname='plpgsql') as plpgsql
            from pg_proc where oid=to_regprocedure($1)
        """, f"public.{name}()")
        definer = name == "rec_append_fair_use_audit"
        if not row or (row["prosrc"] != body or row["proowner"] != (writer if definer else owner)
                       or row["prosecdef"] != definer or not row["is_trigger"] or not row["plpgsql"]
                       or set(row["proconfig"] or ()) != {"search_path=pg_catalog, pg_temp", "row_security=on"}):
            raise RuntimeError("fair-use protection function is unsafe")
    for table, name, function, _events, flags in schema.TRIGGERS:
        valid = await connection.fetchval("""
            select count(*)=1 and bool_and(tgtype=$4 and tgenabled='A' and not tgisinternal
                and tgnargs=0 and tgqual is null and tgfoid=to_regprocedure($3))
            from pg_trigger where tgrelid=to_regclass($1) and tgname=$2
        """, f"public.{table}", name, f"public.{function}()", flags)
        if not valid:
            raise RuntimeError("fair-use protection trigger is unsafe")
    safe = await connection.fetchval("""
        select not (r.rolcanlogin or r.rolinherit or r.rolsuper or r.rolbypassrls
            or r.rolcreatedb or r.rolcreaterole or r.rolreplication)
            and not exists(select from pg_auth_members m where r.oid in (m.roleid,m.member))
            and has_schema_privilege(r.oid,'public','USAGE')
            and not has_schema_privilege(r.oid,'public','CREATE')
            and not has_table_privilege(r.oid,'public.billing_audit_events','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
            and not has_any_column_privilege(r.oid,'public.billing_audit_events','SELECT,UPDATE,REFERENCES')
            and not exists(select from information_schema.columns c
                where c.table_schema='public' and c.table_name='billing_audit_events'
                and not has_column_privilege(r.oid,'public.billing_audit_events',c.column_name,'INSERT'))
            and not exists(select from pg_proc p where p.proowner=r.oid
                and p.oid <> 'public.rec_append_fair_use_audit()'::regprocedure)
            and not exists(select from pg_class c join pg_namespace n on n.oid=c.relnamespace
                where n.nspname !~ '^pg_' and n.nspname <> 'information_schema' and (
                    c.relowner=r.oid or case when c.relkind='S' then has_sequence_privilege(r.oid,c.oid,'USAGE,SELECT,UPDATE')
                    when c.relkind in ('r','p','v','m','f') and c.oid <> 'public.billing_audit_events'::regclass then
                        has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                        or has_any_column_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,REFERENCES') else false end))
        from pg_roles r where r.oid=$1
    """, writer)
    if not safe:
        raise RuntimeError("fair-use audit writer is unsafe")
    tables = await connection.fetchval("""
        select count(*)=2 and bool_and(relrowsecurity and relforcerowsecurity and relowner=$1)
        from pg_class where oid in ('public.fair_use_reviews'::regclass,'public.billing_audit_events'::regclass)
    """, owner)
    if not tables:
        raise RuntimeError("fair-use row protection is unsafe")
    await _verify_fair_use_definitions(connection, schema)
    for role in schema.RUNTIME:
        for name in schema.FUNCTIONS:
            if await connection.fetchval("select has_function_privilege($1::name,$2,'EXECUTE')", role, f"public.{name}()"):
                raise RuntimeError("fair-use runtime function privilege is unsafe")
        if await connection.fetchval("select has_parameter_privilege($1::name,'session_replication_role','SET')", role):
            raise RuntimeError("fair-use runtime parameter privilege is unsafe")
        rights = await connection.fetchval("""
            select has_table_privilege($1::name,'public.fair_use_reviews','SELECT')=$2
                and not has_table_privilege($1::name,'public.fair_use_reviews','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                and not has_any_column_privilege($1::name,'public.fair_use_reviews','REFERENCES')
        """, role, role != MEDIA_ROLE)
        if not rights:
            raise RuntimeError("fair-use runtime table privilege is unsafe")
        columns = await connection.fetch("select attname from pg_attribute where attrelid='public.fair_use_reviews'::regclass and attnum>0 and not attisdropped")
        inserts = set(schema.REVIEW_INSERT.split(",")) if role == MAINTENANCE_ROLE else set()
        updates = set((schema.APP_UPDATE if role == APP_ROLE else schema.OPERATOR_UPDATE).split(",")) if role != MEDIA_ROLE else set()
        for column in columns:
            for privilege, expected in [("INSERT", inserts), ("UPDATE", updates)]:
                granted = await connection.fetchval("select has_column_privilege($1::name,'public.fair_use_reviews',$2,$3)", role, column["attname"], privilege)
                if granted != (column["attname"] in expected):
                    raise RuntimeError("fair-use runtime column privilege is unsafe")


async def _bootstrap() -> None:
    owner_password = _read_secret("TWOBRAIN_DB_OWNER_PASSWORD_FILE")
    app_password = _read_secret("TWOBRAIN_DB_APP_PASSWORD_FILE")
    maintenance_password = _read_secret("TWOBRAIN_DB_MAINTENANCE_PASSWORD_FILE")
    media_password = _read_secret("TWOBRAIN_DB_MEDIA_PASSWORD_FILE")
    database_name = os.environ.get("TWOBRAIN_DB_NAME", DATABASE_NAME).strip()
    if not DATABASE_NAME_RE.fullmatch(database_name):
        raise RuntimeError("runtime database name is invalid")
    connection = await asyncpg.connect(
        host=os.environ.get("TWOBRAIN_DB_HOST", "rec-postgres"),
        port=int(os.environ.get("TWOBRAIN_DB_PORT", "5432")),
        database=database_name,
        user=OWNER_ROLE,
        password=owner_password,
    )
    try:
        async with connection.transaction():
            await _ensure_login_role(connection, role_name=APP_ROLE, password=app_password)
            await _ensure_login_role(
                connection,
                role_name=MAINTENANCE_ROLE,
                password=maintenance_password,
            )
            await _ensure_login_role(connection, role_name=MEDIA_ROLE, password=media_password)
            for statement in (
                f"grant connect on database {database_name} "
                f"to {APP_ROLE}, {MAINTENANCE_ROLE}, {MEDIA_ROLE}",
                f"grant usage on schema public to {APP_ROLE}, {MAINTENANCE_ROLE}, {MEDIA_ROLE}",
                "grant select, insert, update, delete on all tables in schema public "
                f"to {APP_ROLE}, {MAINTENANCE_ROLE}",
                "grant usage, select on all sequences in schema public "
                f"to {APP_ROLE}, {MAINTENANCE_ROLE}",
                "grant execute on function "
                "public.rec_account_merge_context_valid() "
                f"to {APP_ROLE}, {MAINTENANCE_ROLE}",
                f"alter default privileges for role {OWNER_ROLE} in schema public "
                "grant select, insert, update, delete on tables "
                f"to {APP_ROLE}, {MAINTENANCE_ROLE}",
                f"alter default privileges for role {OWNER_ROLE} in schema public "
                f"grant usage, select on sequences to {APP_ROLE}, {MAINTENANCE_ROLE}",
                f"revoke all privileges on all tables in schema public from {MEDIA_ROLE}",
                f"revoke all privileges on all sequences in schema public from {MEDIA_ROLE}",
                f"alter default privileges for role {OWNER_ROLE} in schema public "
                f"revoke all privileges on tables from {MEDIA_ROLE}",
                f"alter default privileges for role {OWNER_ROLE} in schema public "
                f"revoke all privileges on sequences from {MEDIA_ROLE}",
                f"grant select on {_table_list(MEDIA_READ_ONLY_TABLES)} to {MEDIA_ROLE}",
                f"grant select ({', '.join(MEDIA_WORKFLOW_COLUMNS)}) on public.processing_workflows to {MEDIA_ROLE}",
                f"grant select, insert, update on {_table_list(MEDIA_READ_WRITE_TABLES)} "
                f"to {MEDIA_ROLE}",
                f"grant insert on {_table_list(MEDIA_INSERT_ONLY_TABLES)} to {MEDIA_ROLE}",
                *(
                    f"grant update ({column_name}) on public.{table_name} to {MEDIA_ROLE}"
                    for table_name, column_name in MEDIA_LOCK_COLUMNS
                ),
                "revoke all privileges on function "
                "public.rec_playback_normalization_workspace_page(uuid, integer) from public",
                "revoke all privileges on function "
                f"public.rec_playback_normalization_workspace_page(uuid, integer) from {APP_ROLE}",
                "revoke all privileges on function "
                "public.rec_playback_normalization_workspace_page(uuid, integer) "
                f"from {MAINTENANCE_ROLE}",
                "grant execute on function "
                f"public.rec_playback_normalization_workspace_page(uuid, integer) to {MEDIA_ROLE}",
                "revoke all privileges on function "
                "public.rec_playback_normalization_cleanup_page(integer) from public",
                "revoke all privileges on function "
                f"public.rec_playback_normalization_cleanup_page(integer) from {APP_ROLE}",
                "revoke all privileges on function "
                f"public.rec_playback_normalization_cleanup_page(integer) "
                f"from {MAINTENANCE_ROLE}",
                "grant execute on function "
                f"public.rec_playback_normalization_cleanup_page(integer) to {MEDIA_ROLE}",
            ):
                await connection.execute(statement)
            for table in ("storage_notification_states", "storage_notification_scan"):
                if await connection.fetchval("select to_regclass($1)", f"public.{table}"):
                    await connection.execute(
                        f"revoke all privileges on public.{table} "
                        f"from public, {APP_ROLE}, {MAINTENANCE_ROLE}, {MEDIA_ROLE}"
                    )
                    grants = "select, insert, update, delete" if table.endswith("states") else "select, insert, update"
                    await connection.execute(f"grant {grants} on public.{table} to {MAINTENANCE_ROLE}")
            receipt_identities = "public.billing_receipt_identities"
            if await connection.fetchval("select to_regclass($1)", receipt_identities):
                await connection.execute(
                    f"revoke all privileges on {receipt_identities} "
                    f"from public, {APP_ROLE}, {MAINTENANCE_ROLE}, {MEDIA_ROLE}"
                )
                await connection.execute(
                    f"grant select, insert on {receipt_identities} to {MAINTENANCE_ROLE}"
                )
            for table, columns in MEDIA_STORAGE_COLUMNS.items():
                # Table-level REVOKE does not remove separately granted column rights.
                all_columns = await connection.fetch(
                    "select quote_ident(column_name) as name from information_schema.columns "
                    "where table_schema = 'public' and table_name = $1 order by ordinal_position",
                    table,
                )
                await connection.execute(
                    f"revoke all privileges ({', '.join(row['name'] for row in all_columns)}) "
                    f"on public.{table} from {MEDIA_ROLE}"
                )
                await connection.execute(
                    f"grant select ({', '.join(columns)}) on public.{table} to {MEDIA_ROLE}"
                )
            await _restrict_receipt_observation_source(connection)
            await _restrict_fair_use_history(connection)
            await _verify_runtime_roles(connection, database_name=database_name)
    finally:
        await connection.close()


def main() -> None:
    asyncio.run(_bootstrap())
    print("runtime_database_roles_result=pass")


if __name__ == "__main__":
    main()
