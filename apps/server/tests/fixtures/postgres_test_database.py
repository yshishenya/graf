from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.base import Base

TEST_DATABASE_PREFIX = "twobrain_rec_test_"
TEST_DATABASE_PREFIX_ENV = "GRAF_TEST_DATABASE_PREFIX"
TEST_POSTGRES_ADMIN_URL_ENV = "GRAF_TEST_POSTGRES_ADMIN_URL"
TEST_POSTGRES_MEDIA_PASSWORD_ENV = "GRAF_TEST_POSTGRES_MEDIA_PASSWORD"
TEST_MEDIA_ROLE = "twobrain_rec_media"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DATABASE_NAME_PATTERN = re.compile(r"^twobrain_rec_test_[a-z0-9_]+$")
MAX_POSTGRES_IDENTIFIER_LENGTH = 63
SERVER_ROOT = Path(__file__).resolve().parents[2]
MEDIA_READ_ONLY_TABLES = (
    "alembic_version",
    "meetings",
    "media_revisions",
    "workspaces",
)
MEDIA_READ_WRITE_TABLES = (
    "playback_backfill_runs",
    "playback_normalization_attempts",
    "playback_normalization_jobs",
    "support_incidents",
    "track_artifacts",
)
MEDIA_INSERT_ONLY_TABLES = ("ingest_audit_events",)
MEDIA_LOCK_COLUMNS = (("meetings", "updated_at"), ("media_revisions", "updated_at"))
MEDIA_ROLE_BOOTSTRAP_LOCK_KEY = 110_202_607_18


def _database_name(url: str) -> str:
    return urlparse(url).path.lstrip("/")


def _validate_disposable_database_name(database_name: str) -> None:
    if (
        not DATABASE_NAME_PATTERN.fullmatch(database_name)
        or len(database_name) > MAX_POSTGRES_IDENTIFIER_LENGTH
    ):
        pytest.fail("PostgreSQL test database name must be a bounded generated disposable name")


def _validate_loopback_postgres_url(url: str, *, expected_database: str | None = None) -> str:
    parsed = urlparse(url)
    database_name = _database_name(url)
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname not in LOOPBACK_HOSTS
        or (expected_database is not None and database_name != expected_database)
    ):
        pytest.fail("PostgreSQL test URL must target loopback-only PostgreSQL")
    return database_name


def disposable_postgres_database_url() -> str:
    database_url = os.getenv("TWOBRAIN_DATABASE_URL")
    if not database_url:
        pytest.fail(
            "TWOBRAIN_DATABASE_URL is required; run "
            "bash apps/server/scripts/run_local_postgres_tests.sh"
        )

    parsed = urlparse(database_url)
    database_name = _database_name(database_url)
    if parsed.scheme != "postgresql+asyncpg" or parsed.hostname not in LOOPBACK_HOSTS:
        pytest.fail("TWOBRAIN_DATABASE_URL must target a disposable local PostgreSQL database")
    _validate_disposable_database_name(database_name)
    run_prefix = os.getenv(TEST_DATABASE_PREFIX_ENV)
    if run_prefix:
        _validate_disposable_database_name(run_prefix)
        if database_name != run_prefix and not database_name.startswith(f"{run_prefix}_"):
            pytest.fail("TWOBRAIN_DATABASE_URL must belong to this generated PostgreSQL test run")
    return database_url


def disposable_postgres_admin_url() -> str:
    admin_url = os.getenv(TEST_POSTGRES_ADMIN_URL_ENV)
    if not admin_url:
        pytest.fail(
            "GRAF_TEST_POSTGRES_ADMIN_URL is required; run "
            "bash apps/server/scripts/run_local_postgres_tests.sh"
        )
    _validate_loopback_postgres_url(admin_url, expected_database="postgres")
    return admin_url


def _worker_suffix(worker_id: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]", "_", worker_id.lower())
    return normalized or "master"


def _database_url_for_name(base_url: str, database_name: str) -> str:
    _validate_disposable_database_name(database_name)
    return make_url(base_url).set(database=database_name).render_as_string(hide_password=False)


def _asyncpg_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _media_database_url(
    database_url: str,
    *,
    media_database_url: str | None = None,
) -> tuple[str, str]:
    database_name = _validate_loopback_postgres_url(database_url)
    _validate_disposable_database_name(database_name)
    if media_database_url is not None:
        media_database_name = _validate_loopback_postgres_url(media_database_url)
        media_parts = make_url(media_database_url)
        if media_database_name != database_name or media_parts.username != TEST_MEDIA_ROLE:
            pytest.fail("PostgreSQL media test URL must match its disposable worker database")
        password = media_parts.password
        if not password:
            pytest.fail("PostgreSQL media test URL must include an ephemeral password")
        return media_database_url, password

    password = os.getenv(TEST_POSTGRES_MEDIA_PASSWORD_ENV) or uuid4().hex
    return (
        make_url(database_url)
        .set(username=TEST_MEDIA_ROLE, password=password)
        .render_as_string(hide_password=False),
        password,
    )


def _table_list(table_names: tuple[str, ...]) -> str:
    return ", ".join(f"public.{table_name}" for table_name in table_names)


async def ensure_disposable_media_role(
    database_url: str,
    *,
    media_database_url: str | None = None,
) -> str:
    """Create the exact media-worker role and grants inside a disposable run.

    Application tests retain their owner-backed API client, while direct worker
    calls use this narrowly granted role.  The role name is intentionally the
    production name because scheduler SQL functions verify ``session_user``.
    The surrounding test runner owns an isolated PostgreSQL container, and a
    cluster advisory lock makes concurrent xdist workers safe.
    """

    database_name = _validate_loopback_postgres_url(database_url)
    _validate_disposable_database_name(database_name)
    resolved_media_url, password = _media_database_url(
        database_url,
        media_database_url=media_database_url,
    )
    admin_connection = await asyncpg.connect(_asyncpg_url(disposable_postgres_admin_url()))
    try:
        await admin_connection.execute(
            "select pg_advisory_lock($1)", MEDIA_ROLE_BOOTSTRAP_LOCK_KEY
        )
        exists = await admin_connection.fetchval(
            "select exists(select 1 from pg_roles where rolname = $1)",
            TEST_MEDIA_ROLE,
        )
        quoted_password = await admin_connection.fetchval(
            "select quote_literal($1::text)", password
        )
        quoted_role = _quoted_identifier(TEST_MEDIA_ROLE)
        if not exists:
            await admin_connection.execute(f"create role {quoted_role}")
        await admin_connection.execute(
            f"alter role {quoted_role} with login password {quoted_password} "
            "nosuperuser nocreatedb nocreaterole noinherit noreplication nobypassrls"
        )
        await admin_connection.execute(f"alter role {quoted_role} set row_security = on")
    finally:
        try:
            await admin_connection.execute(
                "select pg_advisory_unlock($1)", MEDIA_ROLE_BOOTSTRAP_LOCK_KEY
            )
        finally:
            await admin_connection.close()

    owner_connection = await asyncpg.connect(_asyncpg_url(database_url))
    try:
        quoted_role = _quoted_identifier(TEST_MEDIA_ROLE)
        quoted_database = _quoted_identifier(database_name)
        statements = (
            f"grant connect on database {quoted_database} to {quoted_role}",
            f"grant usage on schema public to {quoted_role}",
            f"revoke all privileges on all tables in schema public from {quoted_role}",
            f"revoke all privileges on all sequences in schema public from {quoted_role}",
            f"grant select on {_table_list(MEDIA_READ_ONLY_TABLES)} to {quoted_role}",
            f"grant select, insert, update on {_table_list(MEDIA_READ_WRITE_TABLES)} "
            f"to {quoted_role}",
            f"grant insert on {_table_list(MEDIA_INSERT_ONLY_TABLES)} to {quoted_role}",
            *(
                f"grant update ({column_name}) on public.{table_name} to {quoted_role}"
                for table_name, column_name in MEDIA_LOCK_COLUMNS
            ),
            "revoke all privileges on function "
            "public.rec_playback_normalization_workspace_page(uuid, integer) from public",
            "revoke all privileges on function "
            "public.rec_playback_normalization_cleanup_page(integer) from public",
            "grant execute on function "
            "public.rec_playback_normalization_workspace_page(uuid, integer) "
            f"to {quoted_role}",
            "grant execute on function "
            "public.rec_playback_normalization_cleanup_page(integer) "
            f"to {quoted_role}",
        )
        for statement in statements:
            await owner_connection.execute(statement)
    finally:
        await owner_connection.close()
    return resolved_media_url


def worker_database_name(worker_id: str) -> str:
    run_prefix = _database_name(disposable_postgres_database_url())
    database_name = f"{run_prefix}_{_worker_suffix(worker_id)}"
    _validate_disposable_database_name(database_name)
    return database_name


def clean_database_name(worker_id: str) -> str:
    run_prefix = _database_name(disposable_postgres_database_url())
    database_name = f"{run_prefix}_clean_{_worker_suffix(worker_id)}_{uuid4().hex[:8]}"
    _validate_disposable_database_name(database_name)
    return database_name


def worker_postgres_database_url(worker_id: str) -> str:
    return _database_url_for_name(disposable_postgres_database_url(), worker_database_name(worker_id))


async def _create_database(database_name: str) -> None:
    _validate_disposable_database_name(database_name)
    engine = create_async_engine(
        disposable_postgres_admin_url(),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'create database "{database_name}"'))
    finally:
        await engine.dispose()


async def _drop_database(database_name: str) -> None:
    _validate_disposable_database_name(database_name)
    engine = create_async_engine(
        disposable_postgres_admin_url(),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'drop database if exists "{database_name}" with (force)'))
    finally:
        await engine.dispose()


def prepare_schema(database_url: str) -> None:
    """Bring a disposable worker database to the real application schema head.

    ``Base.metadata.create_all`` is intentionally insufficient here: the
    production schema also contains migration-managed PostgreSQL functions,
    policies, and grants.  Each xdist worker owns a separate disposable
    database, so upgrading it once per worker preserves isolation without
    recreating the schema for every test.
    """

    previous_database_url = os.environ.get("TWOBRAIN_DATABASE_URL")
    try:
        os.environ["TWOBRAIN_DATABASE_URL"] = database_url
        get_settings.cache_clear()
        config = Config(str(SERVER_ROOT / "alembic.ini"))
        config.set_main_option(
            "script_location",
            str(SERVER_ROOT / "src/twobrain_rec_server/db/migrations"),
        )
        command.upgrade(config, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("TWOBRAIN_DATABASE_URL", None)
        else:
            os.environ["TWOBRAIN_DATABASE_URL"] = previous_database_url
        get_settings.cache_clear()


def _quoted_metadata_tables() -> str:
    tables = sorted(
        Base.metadata.tables.values(),
        key=lambda table: (table.schema or "public", table.name),
    )
    if not tables:
        raise RuntimeError("PostgreSQL test baseline has no mapped tables")
    return ", ".join(
        f'"{table.schema or "public"}"."{table.name}"' for table in tables
    )


async def reset_mapped_tables(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(f"truncate table {_quoted_metadata_tables()} restart identity cascade")
            )
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def postgres_test_worker_id(pytestconfig: pytest.Config) -> str:
    worker_input = getattr(pytestconfig, "workerinput", {})
    return str(worker_input.get("workerid", "master"))


@pytest.fixture(scope="session")
def postgres_worker_database_url(postgres_test_worker_id: str) -> Iterator[str]:
    database_name = worker_database_name(postgres_test_worker_id)
    database_url = worker_postgres_database_url(postgres_test_worker_id)
    asyncio.run(_create_database(database_name))
    try:
        yield database_url
    finally:
        asyncio.run(_drop_database(database_name))

@pytest.fixture
def postgres_clean_database_url(postgres_test_worker_id: str) -> Iterator[str]:
    database_name = clean_database_name(postgres_test_worker_id)
    database_url = _database_url_for_name(disposable_postgres_database_url(), database_name)
    asyncio.run(_create_database(database_name))
    try:
        yield database_url
    finally:
        asyncio.run(_drop_database(database_name))
