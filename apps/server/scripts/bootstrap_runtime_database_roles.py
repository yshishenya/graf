from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import asyncpg
from twobrain_rec_server.db.rls_validation import SYSTEM_CONTENT_COLUMNS

OWNER_ROLE = "twobrain_rec"
APP_ROLE = "twobrain_rec_app"
MAINTENANCE_ROLE = "twobrain_rec_maintenance"
MEDIA_ROLE = "twobrain_rec_media"
SYSTEM_ROLE = "twobrain_rec_system"
SYSTEM_AUTHORITY_ROLE = "twobrain_rec_system_authority"
DATABASE_NAME = "twobrain_rec"
DATABASE_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
MEDIA_READ_ONLY_TABLES = (
    "alembic_version",
    "meetings",
    "media_revisions",
    "upload_sessions",
    "workspace_subscriptions",
    "billing_plans",
    "billing_plan_versions",
    "billing_access_adjustments",
    "billing_access_revocations",
    "workspaces",
)
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
    ("workspaces", "id"),
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

    for table_name, column_name in MEDIA_LOCK_COLUMNS:
        has_lock_column = await connection.fetchval(
            "select has_column_privilege($1::name, $2::text, $3::text, 'UPDATE')",
            MEDIA_ROLE,
            f"public.{table_name}",
            column_name,
        )
        has_business_column = await connection.fetchval(
            "select has_column_privilege($1::name, $2::text, $3::text, 'UPDATE')",
            MEDIA_ROLE,
            f"public.{table_name}",
            "name" if table_name == "workspaces" else "status",
        )
        if not has_lock_column or has_business_column:
            raise RuntimeError("media database role lock privileges are unsafe")


async def _verify_system_boundary(connection: asyncpg.Connection) -> None:
    """Verify the additive boundary even when console login is not enabled."""
    exists = await connection.fetchval(
        "select to_regnamespace('system_control') is not null"
    )
    if not exists:
        return
    for runtime_role in (APP_ROLE, MAINTENANCE_ROLE, MEDIA_ROLE, SYSTEM_ROLE):
        if await connection.fetchval("select has_schema_privilege($1::name,'public','CREATE')",runtime_role):
            raise RuntimeError("runtime role can create objects in the trusted public schema")
    system_roles = [SYSTEM_ROLE, SYSTEM_AUTHORITY_ROLE]
    if await connection.fetchval("select exists(select 1 from pg_roles where rolname='twobrain_rec_system_auth')"):
        system_roles.append('twobrain_rec_system_auth')
    roles = await connection.fetch(
        """
        select oid, rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
               rolinherit, rolreplication, rolbypassrls
        from pg_roles where rolname = any($1::text[])
        """, system_roles,
    )
    if len(roles) != len(system_roles):
        raise RuntimeError("system database roles are missing")
    for role in roles:
        if any(role[key] for key in (
            'rolsuper', 'rolcreatedb', 'rolcreaterole', 'rolinherit',
            'rolreplication', 'rolbypassrls',
        )) or (role['rolname'] != SYSTEM_ROLE and role['rolcanlogin']):
            raise RuntimeError("system database role privileges are unsafe")
        if await connection.fetchval(
            'select exists(select 1 from pg_auth_members where member = $1 or roleid = $1)',
            role['oid'],
        ):
            raise RuntimeError("system database role membership is unsafe")
    for role in (APP_ROLE, MEDIA_ROLE):
        if await connection.fetchval(
            "select has_schema_privilege($1::name, 'system_control', 'USAGE')", role,
        ):
            raise RuntimeError("ordinary database role can access system schema")
    unsafe_tables = await connection.fetchval(
        """
        select exists (
            select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace
            where n.nspname in ('public', 'system_control') and c.relkind in ('r','p','v','m')
              and (has_table_privilege($1::name, c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                   or (has_table_privilege($1::name, c.oid, 'SELECT')
                       and (n.nspname, c.relname) != ('system_control', 'audit_events'))
                   or c.relowner = (select oid from pg_roles where rolname = $1))
        )
        """, SYSTEM_ROLE,
    )
    if unsafe_tables:
        raise RuntimeError("system database table privileges are unsafe")
    columns = await connection.fetch(
        """
        select table_schema, table_name, column_name, privilege_type
        from information_schema.column_privileges where grantee = $1
        """, SYSTEM_ROLE,
    )
    expected = {
        ('public', 'meetings', name, 'SELECT') for name in (
            'id', 'workspace_id', 'created_by_user_id', 'device_id', 'started_at', 'ended_at',
            'duration_seconds', 'status', 'processing_status', 'deletion_state', 'deletion_epoch',
            'created_at', 'updated_at',
        )
    }
    if await connection.fetchval("select to_regclass('system_control.audit_events') is not null"):
        expected |= {
            ('system_control', 'audit_events', name, 'SELECT') for name in (
                'id', 'principal_id', 'session_id', 'role', 'permission', 'action',
                'target_type', 'target_id', 'case_context_id', 'result', 'reason', 'occurred_at', 'writer_transaction',
            )
        }
    if await connection.fetchval("select to_regclass('system_control.operations') is not null"):
        expected |= {('public', 'meetings', 'control_version', 'SELECT'),
                     ('system_control', 'audit_events', 'operation_id', 'SELECT')}
        if await connection.fetchval("""
            select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
              where n.nspname='system_control' and c.relkind in ('r','p','v','m')
              and has_table_privilege($1::name,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE'))
        """, MAINTENANCE_ROLE):
            raise RuntimeError("maintenance can access system tables directly")
    if await connection.fetchval("select to_regprocedure('system_control.meeting_content_allowed(uuid)') is not null"):
        expected |= {('public', table, name, 'SELECT')
                     for table, names in SYSTEM_CONTENT_COLUMNS.items() for name in names.split(',')}
        for table in SYSTEM_CONTENT_COLUMNS:
            if not await connection.fetchval("""select exists(select 1 from pg_policy p
                join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace
                where n.nspname='public' and c.relname=$1 and c.relrowsecurity and c.relforcerowsecurity
                  and p.polname='system_content_gate' and not p.polpermissive and p.polcmd='r'
                  and (select oid from pg_roles where rolname=$2)=any(p.polroles))""", table, SYSTEM_ROLE):
                raise RuntimeError("system content mandatory RLS gate is missing")
    if {tuple(row.values()) for row in columns} != expected:
        raise RuntimeError("system database column privileges are unsafe")
    gate = await connection.fetchval(
        """
        select exists (select 1 from pg_policy p join pg_class c on c.oid = p.polrelid
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relname = 'meetings'
              and c.relrowsecurity and c.relforcerowsecurity
              and p.polname = 'system_metadata_gate' and not p.polpermissive
              and p.polcmd = 'r'
              and (select oid from pg_roles where rolname = $1) = any(p.polroles))
        """, SYSTEM_ROLE,
    )
    if not gate:
        raise RuntimeError("system database mandatory RLS gate is missing")


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
                f"revoke insert on public.billing_access_adjustments from {APP_ROLE}",
                "grant usage, select on all sequences in schema public "
                f"to {APP_ROLE}, {MAINTENANCE_ROLE}",
                "grant execute on function "
                "public.rec_account_merge_context_valid() "
                f"to {APP_ROLE}, {MAINTENANCE_ROLE}",
                f"grant execute on function public.billing_lock_checkout_catalog(text) to {APP_ROLE}",
                f"grant execute on function public.rec_share_recipient_is_member(uuid,uuid) to {APP_ROLE}",
                f"grant execute on function public.billing_redeem_promotion_access(uuid,uuid,uuid,timestamptz,timestamptz,text,text,text) to {APP_ROLE}",
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
            if os.environ.get("TWOBRAIN_DB_SYSTEM_PASSWORD_FILE", "").strip():
                if not await connection.fetchval(
                    "select to_regnamespace('system_control') is not null"
                ):
                    raise RuntimeError("system database migration is required before login setup")
                await _ensure_login_role(
                    connection, role_name=SYSTEM_ROLE,
                    password=_read_secret("TWOBRAIN_DB_SYSTEM_PASSWORD_FILE"),
                )
                await connection.execute(f"grant connect on database {database_name} to {SYSTEM_ROLE}")
            await _verify_runtime_roles(connection, database_name=database_name)
            await _verify_system_boundary(connection)
    finally:
        await connection.close()


def main() -> None:
    asyncio.run(_bootstrap())
    print("runtime_database_roles_result=pass")


if __name__ == "__main__":
    main()
