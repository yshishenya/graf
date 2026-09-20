"""Contract proofs for the level 1 aggregate, the level 2 tables and the migrations.

These tests run against a real PostgreSQL schema built by ``alembic upgrade
head``: they prove the storage rules rather than the in-process rules only.
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.models.product_analytics import (
    AnonymousPageAggregateBucket,
    ClientAcquisitionAttribute,
    PublicVisitAttribution,
)
from twobrain_rec_server.product_analytics.acquisition import (
    build_client_acquisition_attribute,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    ANONYMOUS_AGGREGATE_SURFACES,
    MINIMUM_AGGREGATE_BUCKET_SIZE,
    build_anonymous_aggregate_bucket,
    record_anonymous_aggregate_bucket,
    reportable_aggregate_criteria,
    select_reportable_aggregate_buckets,
)
from twobrain_rec_server.product_analytics.forbidden_fields import FORBIDDEN_FIELD_NAMES
from twobrain_rec_server.product_analytics.retention import retention_days_for_category
from twobrain_rec_server.product_analytics.traffic_class import REPORTED_TRAFFIC_CLASSES

SERVER_ROOT = Path(__file__).resolve().parents[2]
AGGREGATE_TABLE = "anonymous_page_aggregate_buckets"
VISIT_TABLE = "public_visit_attributions"
ACQUISITION_TABLE = "client_acquisition_attributes"

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def _run_alembic(database_url: str, *, downgrade_to: str | None = None) -> None:
    previous_url = os.environ.get("TWOBRAIN_DATABASE_URL")
    try:
        os.environ["TWOBRAIN_DATABASE_URL"] = database_url
        get_settings.cache_clear()
        config = Config(str(SERVER_ROOT / "alembic.ini"))
        config.set_main_option(
            "script_location", str(SERVER_ROOT / "src/twobrain_rec_server/db/migrations")
        )
        if downgrade_to is None:
            command.upgrade(config, "head")
        else:
            command.downgrade(config, downgrade_to)
    finally:
        if previous_url is None:
            os.environ.pop("TWOBRAIN_DATABASE_URL", None)
        else:
            os.environ["TWOBRAIN_DATABASE_URL"] = previous_url
        get_settings.cache_clear()


async def _reset_measurement_tables(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            for table in (AGGREGATE_TABLE, VISIT_TABLE, ACQUISITION_TABLE):
                await connection.execute(sa.text(f'delete from "{table}"'))
    finally:
        await engine.dispose()


async def _record(database_url: str, bucket) -> int:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            return await record_anonymous_aggregate_bucket(session, bucket)
    finally:
        await engine.dispose()


async def _rows(database_url: str, table: str) -> list[dict]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(sa.text(f'select * from "{table}"'))
            return [dict(row._mapping) for row in result]
    finally:
        await engine.dispose()


async def _table_names(database_url: str) -> set[str]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(
                lambda sync_connection: set(sa.inspect(sync_connection).get_table_names())
            )
    finally:
        await engine.dispose()


async def _columns(database_url: str, table: str) -> set[str]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(
                lambda sync_connection: {
                    column["name"] for column in sa.inspect(sync_connection).get_columns(table)
                }
            )
    finally:
        await engine.dispose()


async def _unique_constraint_names(database_url: str, table: str) -> set[str]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            constraints = await connection.run_sync(
                lambda sync_connection: sa.inspect(sync_connection).get_unique_constraints(table)
            )
        return {constraint["name"] for constraint in constraints}
    finally:
        await engine.dispose()


async def _report(database_url: str, **kwargs) -> list[dict]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            return await select_reportable_aggregate_buckets(session, **kwargs)
    finally:
        await engine.dispose()


@pytest.fixture
def aggregate_database_url(postgres_schema_database_url: str) -> str:
    asyncio.run(_reset_measurement_tables(postgres_schema_database_url))
    return postgres_schema_database_url


def test_measurement_migrations_apply_and_roll_back(
    postgres_schema_database_url: str,
) -> None:
    present = asyncio.run(_table_names(postgres_schema_database_url))
    assert {AGGREGATE_TABLE, VISIT_TABLE, ACQUISITION_TABLE} <= present

    try:
        _run_alembic(postgres_schema_database_url, downgrade_to="0092_recording_origin_cancel")
        rolled_back = asyncio.run(_table_names(postgres_schema_database_url))
        assert AGGREGATE_TABLE not in rolled_back
        assert VISIT_TABLE not in rolled_back
        assert ACQUISITION_TABLE not in rolled_back
    finally:
        _run_alembic(postgres_schema_database_url)

    restored = asyncio.run(_table_names(postgres_schema_database_url))
    assert {AGGREGATE_TABLE, VISIT_TABLE, ACQUISITION_TABLE} <= restored


def test_aggregate_table_has_no_identifier_column(aggregate_database_url: str) -> None:
    columns = asyncio.run(_columns(aggregate_database_url, AGGREGATE_TABLE))

    assert columns == {
        "id",
        "bucket_date",
        "bucket_hour",
        "surface",
        "landing_path",
        "source",
        "medium",
        "campaign",
        "content",
        "term",
        "device_class",
        "referrer_category",
        "traffic_class",
        "visits",
        "created_at",
        "updated_at",
    }
    for forbidden in (
        "ip_address",
        "device_address",
        "session_id",
        "visit_id",
        "user_agent",
        "device_fingerprint",
        "anonymous_id",
        "account_id",
        "user_id",
        "pseudonym",
        "yclid",
    ):
        assert forbidden not in columns


def test_level_two_tables_keep_only_their_declared_columns(aggregate_database_url: str) -> None:
    visit_columns = asyncio.run(_columns(aggregate_database_url, VISIT_TABLE))
    acquisition_columns = asyncio.run(_columns(aggregate_database_url, ACQUISITION_TABLE))

    assert {
        "attribution_ref",
        "source",
        "medium",
        "campaign",
        "content",
        "term",
        "yclid",
        "landing_path",
        "first_seen_at",
        "expires_at",
    } <= visit_columns
    assert "device_fingerprint" not in visit_columns
    assert "user_agent" not in visit_columns
    assert {
        "account_id",
        "attribution_rule",
        "attribution_confidence",
        "captured_at",
        "landing_path",
    } <= acquisition_columns
    assert "device_fingerprint" not in acquisition_columns
    assert "user_agent" not in acquisition_columns


def test_aggregate_tables_match_the_registered_retention_categories(
    aggregate_database_url: str,
) -> None:
    assert retention_days_for_category("anonymous_page_aggregate") == 1095
    assert retention_days_for_category("client_acquisition_attribute") == 1095
    assert retention_days_for_category("visit_attribution") == 90


def test_repeated_visit_increments_the_same_bucket(aggregate_database_url: str) -> None:
    bucket = build_anonymous_aggregate_bucket(
        path="/download", source="yandex_direct", medium="cpc", occurred_at=NOW
    )

    first = asyncio.run(_record(aggregate_database_url, bucket))
    second = asyncio.run(_record(aggregate_database_url, bucket))
    third = asyncio.run(_record(aggregate_database_url, bucket))

    assert (first, second, third) == (1, 2, 3)
    rows = asyncio.run(_rows(aggregate_database_url, AGGREGATE_TABLE))
    assert len(rows) == 1
    assert rows[0]["visits"] == 3
    assert rows[0]["source"] == "yandex_direct"
    assert rows[0]["surface"] == "public_download"


def test_missing_campaign_labels_update_one_bucket_instead_of_creating_rows(
    aggregate_database_url: str,
) -> None:
    bucket = build_anonymous_aggregate_bucket(path="/", occurred_at=NOW)

    asyncio.run(_record(aggregate_database_url, bucket))
    asyncio.run(_record(aggregate_database_url, bucket))

    rows = asyncio.run(_rows(aggregate_database_url, AGGREGATE_TABLE))
    assert len(rows) == 1
    assert rows[0]["visits"] == 2
    assert rows[0]["campaign"] is None


def test_distinct_dimensions_create_distinct_buckets(aggregate_database_url: str) -> None:
    desktop = build_anonymous_aggregate_bucket(path="/", device_class="desktop", occurred_at=NOW)
    mobile = build_anonymous_aggregate_bucket(path="/", device_class="mobile", occurred_at=NOW)
    internal = build_anonymous_aggregate_bucket(
        path="/", device_class="desktop", traffic_class="internal", occurred_at=NOW
    )

    for bucket in (desktop, mobile, internal):
        asyncio.run(_record(aggregate_database_url, bucket))

    rows = asyncio.run(_rows(aggregate_database_url, AGGREGATE_TABLE))
    assert len(rows) == 3
    assert {row["device_class"] for row in rows} == {"desktop", "mobile"}
    assert {row["traffic_class"] for row in rows} == {"external", "internal"}


def test_aggregate_unique_constraint_is_registered(aggregate_database_url: str) -> None:
    names = asyncio.run(_unique_constraint_names(aggregate_database_url, AGGREGATE_TABLE))

    assert "uq_anonymous_page_aggregate_bucket" in names


def test_report_excludes_internal_traffic_and_keeps_its_marker(
    aggregate_database_url: str,
) -> None:
    external = build_anonymous_aggregate_bucket(path="/", occurred_at=NOW, visits=10)
    internal = build_anonymous_aggregate_bucket(
        path="/", occurred_at=NOW, traffic_class="internal", visits=10
    )
    support = build_anonymous_aggregate_bucket(
        path="/", occurred_at=NOW, traffic_class="support", visits=10
    )

    for bucket in (external, internal, support):
        asyncio.run(_record(aggregate_database_url, bucket))

    report = asyncio.run(_report(aggregate_database_url))
    assert [row["visits"] for row in report] == [10]
    assert {row["traffic_class"] for row in report} == set(REPORTED_TRAFFIC_CLASSES)

    stored = asyncio.run(_rows(aggregate_database_url, AGGREGATE_TABLE))
    assert {row["traffic_class"] for row in stored} == {"external", "internal", "support"}
    assert sum(row["visits"] for row in stored) == 30


def test_report_hides_buckets_below_the_minimum_size(aggregate_database_url: str) -> None:
    small = build_anonymous_aggregate_bucket(
        path="/", occurred_at=NOW, source="yandex_direct", visits=MINIMUM_AGGREGATE_BUCKET_SIZE - 1
    )
    large = build_anonymous_aggregate_bucket(
        path="/download", occurred_at=NOW, source="yandex_direct", visits=MINIMUM_AGGREGATE_BUCKET_SIZE
    )

    for bucket in (small, large):
        asyncio.run(_record(aggregate_database_url, bucket))

    report = asyncio.run(_report(aggregate_database_url))
    assert [row["landing_path"] for row in report] == ["/download"]

    all_rows = asyncio.run(_rows(aggregate_database_url, AGGREGATE_TABLE))
    assert len(all_rows) == 2, "a small bucket is stored, but it is not disclosed"

    criteria = [str(criteria) for criteria in reportable_aggregate_criteria()]
    assert any("traffic_class" in criteria for criteria in criteria)
    assert any("visits" in criteria for criteria in criteria)


def test_report_can_be_limited_by_bucket_date(aggregate_database_url: str) -> None:
    older = build_anonymous_aggregate_bucket(
        path="/", occurred_at=NOW - timedelta(days=5), visits=5
    )
    newer = build_anonymous_aggregate_bucket(path="/", occurred_at=NOW, visits=5)

    for bucket in (older, newer):
        asyncio.run(_record(aggregate_database_url, bucket))

    report = asyncio.run(
        _report(aggregate_database_url, bucket_date_from=NOW.date(), bucket_date_to=NOW.date())
    )
    assert [row["bucket_date"] for row in report] == [NOW.date().isoformat()]


def test_visit_attribution_window_is_enforced_by_the_database(
    aggregate_database_url: str,
) -> None:
    async def insert(expires_at: datetime) -> None:
        engine = create_async_engine(aggregate_database_url, poolclass=NullPool)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                session.add(
                    PublicVisitAttribution(
                        id=uuid4(),
                        attribution_ref=f"graf_visit_{uuid4().hex}",
                        landing_path="/",
                        first_seen_at=NOW,
                        expires_at=expires_at,
                    )
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(insert(NOW + timedelta(days=90)))
    with pytest.raises(sa.exc.IntegrityError):
        asyncio.run(insert(NOW + timedelta(days=91)))

    stored = asyncio.run(_rows(aggregate_database_url, VISIT_TABLE))
    assert len(stored) == 1
    assert (stored[0]["expires_at"] - stored[0]["first_seen_at"]).days == 90


def test_client_attribute_requires_an_existing_account(aggregate_database_url: str) -> None:
    attribute = build_client_acquisition_attribute(
        account_id=uuid4(),
        landing_path="/download",
        source="yandex_direct",
        medium="cpc",
        captured_at=NOW,
        linked_automatically=True,
    )

    async def insert() -> None:
        engine = create_async_engine(aggregate_database_url, poolclass=NullPool)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                session.add(
                    ClientAcquisitionAttribute(
                        id=uuid4(),
                        account_id=attribute.account_id,
                        source=attribute.source,
                        medium=attribute.medium,
                        campaign=attribute.campaign,
                        content=attribute.content,
                        term=attribute.term,
                        yclid=attribute.yclid,
                        landing_path=attribute.landing_path,
                        attribution_rule=attribute.attribution_rule,
                        attribution_confidence=attribute.attribution_confidence,
                        captured_at=attribute.captured_at,
                    )
                )
                await session.commit()
        finally:
            await engine.dispose()

    with pytest.raises(sa.exc.IntegrityError):
        asyncio.run(insert())

    names = asyncio.run(_unique_constraint_names(aggregate_database_url, ACQUISITION_TABLE))
    assert "uq_client_acquisition_account" in names


def test_aggregate_dimensions_are_not_forbidden_field_names() -> None:
    table_columns = set(AnonymousPageAggregateBucket.__table__.columns.keys())

    assert table_columns & set(FORBIDDEN_FIELD_NAMES) == set()
    assert {"id", "created_at", "updated_at"} <= table_columns


def test_public_surfaces_are_the_documented_public_routes() -> None:
    """FR-009, FR-027: sign-up and login are public pages and are counted too."""
    assert set(ANONYMOUS_AGGREGATE_SURFACES) == {
        "public_landing",
        "public_download",
        "public_signup",
        "public_login",
        "public_privacy",
        "public_cookies",
        "public_terms",
        "public_offer",
        "public_analytics_consent",
    }
