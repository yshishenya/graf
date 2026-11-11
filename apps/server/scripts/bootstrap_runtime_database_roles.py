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
            await _verify_runtime_roles(connection, database_name=database_name)
    finally:
        await connection.close()


def main() -> None:
    asyncio.run(_bootstrap())
    print("runtime_database_roles_result=pass")


if __name__ == "__main__":
    main()
