from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DATABASE_NAME_PATTERN = re.compile(r"^twobrain_rec_test_[a-z0-9_]+_rls$")


def rls_test_database_url() -> str:
    url = os.getenv("RLS_TEST_DATABASE_URL")
    if not url:
        pytest.fail(
            "RLS_TEST_DATABASE_URL is required for the full PostgreSQL lane; run "
            "apps/server/scripts/run_local_postgres_tests.sh"
        )
    parsed = urlparse(url)
    database_name = parsed.path.lstrip("/")
    prefix = os.getenv("GRAF_TEST_DATABASE_PREFIX")
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname not in LOOPBACK_HOSTS
        or not DATABASE_NAME_PATTERN.fullmatch(database_name)
        or (prefix and not database_name.startswith(f"{prefix}_"))
    ):
        pytest.fail("RLS_TEST_DATABASE_URL must target this run's loopback disposable PostgreSQL")
    return url


async def postgres_rls_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(rls_test_database_url(), pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()
