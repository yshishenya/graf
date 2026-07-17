from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from urllib.parse import urlparse

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DATABASE_PREFIX = "twobrain_rec_test_"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def disposable_postgres_database_url() -> str:
    database_url = os.getenv("TWOBRAIN_DATABASE_URL")
    if not database_url:
        pytest.fail(
            "TWOBRAIN_DATABASE_URL is required; run "
            "bash apps/server/scripts/run_local_postgres_tests.sh"
        )

    parsed = urlparse(database_url)
    database_name = parsed.path.lstrip("/")
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname not in LOOPBACK_HOSTS
        or not database_name.startswith(TEST_DATABASE_PREFIX)
    ):
        pytest.fail("TWOBRAIN_DATABASE_URL must target a disposable local PostgreSQL database")
    return database_url


async def reset_database(database_url: str) -> None:
    engine = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text("drop schema if exists public cascade"))
            await connection.execute(text("create schema public"))
            await connection.execute(text("grant all on schema public to current_user"))
    finally:
        await engine.dispose()


@pytest.fixture
def postgres_test_database_url() -> Iterator[str]:
    database_url = disposable_postgres_database_url()
    asyncio.run(reset_database(database_url))
    try:
        yield database_url
    finally:
        asyncio.run(reset_database(database_url))
