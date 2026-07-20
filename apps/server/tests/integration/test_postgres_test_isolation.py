from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tests.fixtures.postgres_test_database import (
    TEST_DATABASE_PREFIX_ENV,
    clean_database_name,
    reset_mapped_tables,
    worker_database_name,
    worker_postgres_database_url,
)
from twobrain_rec_server.db.models import Organization


def test_worker_names_are_distinct_and_belong_to_the_same_generated_run(
    monkeypatch,
) -> None:
    run_prefix = "twobrain_rec_test_isolation_run"
    monkeypatch.setenv(TEST_DATABASE_PREFIX_ENV, run_prefix)
    monkeypatch.setenv(
        "TWOBRAIN_DATABASE_URL",
        "postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:54329/"
        f"{run_prefix}",
    )

    first = worker_database_name("gw0")
    second = worker_database_name("gw1")

    assert first != second
    assert first.startswith(f"{run_prefix}_")
    assert second.startswith(f"{run_prefix}_")
    assert worker_postgres_database_url("gw0").endswith(f"/{first}")
    assert clean_database_name("gw0").startswith(f"{run_prefix}_clean_gw0_")


def test_clean_fixture_keeps_the_schema_empty(postgres_clean_database_url: str) -> None:
    async def load_table() -> object:
        engine = create_async_engine(postgres_clean_database_url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                return await connection.scalar(text("select to_regclass('public.organizations')"))
        finally:
            await engine.dispose()

    assert asyncio.run(load_table()) is None


def test_bounded_reset_removes_data_without_recreating_the_schema(
    postgres_schema_database_url: str,
) -> None:
    async def exercise_reset() -> tuple[int, object]:
        engine = create_async_engine(postgres_schema_database_url, poolclass=NullPool)
        sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessionmaker() as session:
                session.add(
                    Organization(
                        id=uuid4(),
                        slug="fast-reset-isolation",
                        name="Fast reset isolation",
                    )
                )
                await session.commit()
            await reset_mapped_tables(postgres_schema_database_url)
            async with sessionmaker() as session:
                rows = list(await session.scalars(select(Organization)))
            async with engine.connect() as connection:
                table = await connection.scalar(text("select to_regclass('public.organizations')"))
            return len(rows), table
        finally:
            await engine.dispose()

    row_count, table = asyncio.run(exercise_reset())

    assert row_count == 0
    assert table == "organizations"
