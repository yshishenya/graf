from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from queue import Queue
from threading import Event, Thread
from urllib.parse import urlparse

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.postgres_test_database import (
    LOOPBACK_HOSTS,
    TEST_DATABASE_PREFIX,
    TEST_DATABASE_PREFIX_ENV,
    disposable_postgres_admin_url,
)

STRICT_RLS_ADVISORY_LOCK_KEY = 110_202_607_17
STRICT_RLS_LOCK_TIMEOUT_SECONDS = 300


def validate_rls_test_database_url(url: str, *, variable_name: str) -> str:
    parsed = urlparse(url)
    database_name = parsed.path.lstrip("/")
    run_prefix = os.getenv(TEST_DATABASE_PREFIX_ENV)
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname not in LOOPBACK_HOSTS
        or not database_name.startswith(TEST_DATABASE_PREFIX)
        or (run_prefix is not None and not database_name.startswith(f"{run_prefix}_"))
    ):
        pytest.fail(f"{variable_name} must target this disposable loopback PostgreSQL test run")
    return url


def rls_test_database_url() -> str:
    url = os.getenv("RLS_TEST_DATABASE_URL")
    if not url:
        pytest.fail(
            "RLS_TEST_DATABASE_URL is required; run "
            "bash apps/server/scripts/run_local_postgres_tests.sh"
        )
    return validate_rls_test_database_url(url, variable_name="RLS_TEST_DATABASE_URL")


def optional_rls_test_database_url(variable_name: str) -> str | None:
    url = os.getenv(variable_name)
    if url is None:
        return None
    return validate_rls_test_database_url(url, variable_name=variable_name)


async def postgres_rls_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(rls_test_database_url(), pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


def _asyncpg_control_url() -> str:
    admin_url = disposable_postgres_admin_url()
    return admin_url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _hold_advisory_lock(
    *,
    acquired: Event,
    release: Event,
    errors: Queue[BaseException],
) -> None:
    connection: asyncpg.Connection | None = None
    try:
        connection = await asyncpg.connect(_asyncpg_control_url())
        await connection.execute("select pg_advisory_lock($1)", STRICT_RLS_ADVISORY_LOCK_KEY)
        acquired.set()
        await asyncio.to_thread(release.wait)
        await connection.execute("select pg_advisory_unlock($1)", STRICT_RLS_ADVISORY_LOCK_KEY)
    except BaseException as error:
        errors.put(error)
        acquired.set()
    finally:
        if connection is not None:
            await connection.close()


@pytest.fixture(scope="module")
def postgres_advisory_lock() -> Iterator[None]:
    """Serialize strict RLS modules that share the disposable PostgreSQL cluster."""

    acquired = Event()
    release = Event()
    errors: Queue[BaseException] = Queue()
    thread = Thread(
        target=lambda: asyncio.run(
            _hold_advisory_lock(acquired=acquired, release=release, errors=errors)
        ),
        name="graf-postgres-rls-advisory-lock",
        daemon=True,
    )
    thread.start()
    if not acquired.wait(timeout=STRICT_RLS_LOCK_TIMEOUT_SECONDS):
        release.set()
        thread.join(timeout=5)
        pytest.fail("timed out waiting for the PostgreSQL strict-RLS advisory lock")
    if not errors.empty():
        raise errors.get()
    try:
        yield
    finally:
        release.set()
        thread.join(timeout=STRICT_RLS_LOCK_TIMEOUT_SECONDS)
        if thread.is_alive():
            pytest.fail("PostgreSQL strict-RLS advisory lock did not release")
        if not errors.empty():
            raise errors.get()
