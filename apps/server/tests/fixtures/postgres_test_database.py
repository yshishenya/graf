from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

import twobrain_rec_server.db.models  # noqa: F401
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.base import Base

TEST_DATABASE_URL_ENV = "GRAF_TEST_DATABASE_URL"
TEST_DATABASE_PREFIX_ENV = "GRAF_TEST_DATABASE_PREFIX"
TEST_POSTGRES_ADMIN_URL_ENV = "GRAF_TEST_POSTGRES_ADMIN_URL"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DATABASE_NAME_PATTERN = re.compile(r"^twobrain_rec_test_[a-z0-9_]+$")
MAX_POSTGRES_IDENTIFIER_LENGTH = 63
SERVER_ROOT = Path(__file__).resolve().parents[2]


def _database_name(url: str) -> str:
    return urlparse(url).path.lstrip("/")


def _fail(message: str) -> None:
    pytest.fail(message)


def _validate_database_name(database_name: str) -> None:
    if (
        not DATABASE_NAME_PATTERN.fullmatch(database_name)
        or len(database_name) > MAX_POSTGRES_IDENTIFIER_LENGTH
    ):
        _fail("PostgreSQL test database name must be generated and disposable")


def _validate_loopback_url(url: str, *, expected_database: str | None = None) -> str:
    parsed = urlparse(url)
    database_name = _database_name(url)
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname not in LOOPBACK_HOSTS
        or (expected_database is not None and database_name != expected_database)
    ):
        _fail("PostgreSQL test URL must target loopback-only PostgreSQL")
    return database_name


def disposable_postgres_database_url() -> str:
    url = os.getenv(TEST_DATABASE_URL_ENV)
    if not url:
        _fail(
            f"{TEST_DATABASE_URL_ENV} is required; run "
            "apps/server/scripts/run_local_postgres_tests.sh"
        )
    database_name = _validate_loopback_url(url)
    _validate_database_name(database_name)
    prefix = os.getenv(TEST_DATABASE_PREFIX_ENV)
    if prefix:
        _validate_database_name(prefix)
        if database_name != prefix and not database_name.startswith(f"{prefix}_"):
            _fail("PostgreSQL test URL is outside this generated test run")
    return url


def disposable_postgres_admin_url() -> str:
    url = os.getenv(TEST_POSTGRES_ADMIN_URL_ENV)
    if not url:
        _fail(
            f"{TEST_POSTGRES_ADMIN_URL_ENV} is required; run "
            "apps/server/scripts/run_local_postgres_tests.sh"
        )
    _validate_loopback_url(url, expected_database="postgres")
    return url


def _worker_suffix(worker_id: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]", "_", worker_id.lower())
    return normalized or "master"


def _database_url_for_name(base_url: str, database_name: str) -> str:
    _validate_database_name(database_name)
    return make_url(base_url).set(database=database_name).render_as_string(hide_password=False)


def worker_database_name(worker_id: str) -> str:
    prefix = _database_name(disposable_postgres_database_url())
    name = f"{prefix}_{_worker_suffix(worker_id)}"
    _validate_database_name(name)
    return name


def clean_database_name(worker_id: str) -> str:
    prefix = _database_name(disposable_postgres_database_url())
    name = f"{prefix}_clean_{_worker_suffix(worker_id)}_{uuid4().hex[:8]}"
    _validate_database_name(name)
    return name


def worker_postgres_database_url(worker_id: str) -> str:
    return _database_url_for_name(
        disposable_postgres_database_url(), worker_database_name(worker_id)
    )


async def _create_database(database_name: str) -> None:
    _validate_database_name(database_name)
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
    _validate_database_name(database_name)
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
    previous_url = os.environ.get("TWOBRAIN_DATABASE_URL")
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
        if previous_url is None:
            os.environ.pop("TWOBRAIN_DATABASE_URL", None)
        else:
            os.environ["TWOBRAIN_DATABASE_URL"] = previous_url
        get_settings.cache_clear()


def _quoted_metadata_tables() -> str:
    tables = sorted(
        (
            table
            for table in Base.metadata.tables.values()
            if table.name != "alembic_version"
        ),
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


def postgres_test_worker_id(pytestconfig: pytest.Config) -> str:
    worker_input = getattr(pytestconfig, "workerinput", {})
    return str(worker_input.get("workerid", "master"))


@pytest.fixture(scope="session")
def postgres_worker_database_url(pytestconfig: pytest.Config) -> Iterator[str]:
    worker_id = postgres_test_worker_id(pytestconfig)
    database_name = worker_database_name(worker_id)
    database_url = worker_postgres_database_url(worker_id)
    asyncio.run(_create_database(database_name))
    try:
        yield database_url
    finally:
        asyncio.run(_drop_database(database_name))


@pytest.fixture(scope="session")
def postgres_schema_database_url(postgres_worker_database_url: str) -> str:
    prepare_schema(postgres_worker_database_url)
    return postgres_worker_database_url


@pytest.fixture
def postgres_clean_database_url(pytestconfig: pytest.Config) -> Iterator[str]:
    worker_id = postgres_test_worker_id(pytestconfig)
    database_name = clean_database_name(worker_id)
    database_url = _database_url_for_name(disposable_postgres_database_url(), database_name)
    asyncio.run(_create_database(database_name))
    try:
        yield database_url
    finally:
        asyncio.run(_drop_database(database_name))

