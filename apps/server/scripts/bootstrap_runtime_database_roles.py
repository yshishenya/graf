from __future__ import annotations

import asyncio
import os
import re
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
    "workspace_subscriptions",
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
    if (
        app_workspace_execute
        or app_cleanup_execute
        or maintenance_workspace_execute
        or maintenance_cleanup_execute
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
            "select has_column_privilege($1::name, $2::text, 'status', 'UPDATE')",
            MEDIA_ROLE,
            f"public.{table_name}",
        )
        if not has_lock_column or has_business_column:
            raise RuntimeError("media database role lock privileges are unsafe")


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
            await _verify_runtime_roles(connection, database_name=database_name)
    finally:
        await connection.close()


def main() -> None:
    asyncio.run(_bootstrap())
    print("runtime_database_roles_result=pass")


if __name__ == "__main__":
    main()
