from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def rls_test_database_url() -> str:
    url = os.getenv("RLS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("RLS_TEST_DATABASE_URL is required for PostgreSQL RLS proof")
    return url


async def postgres_rls_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(rls_test_database_url(), pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()
