"""What the public traffic measurement actually stores (T036, T039, T040).

These tests walk real public routes of the real application and then read the
actual rows of ``anonymous_page_aggregate_buckets``. Nothing here inspects the
implementation: SC-002 is proven by parsing stored records, SC-001 by counting
which public surfaces have a stored bucket, and FR-057 by asking the report
reader what it is willing to disclose.
"""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    ANONYMOUS_AGGREGATE_SURFACES,
    MINIMUM_AGGREGATE_BUCKET_SIZE,
    PUBLIC_PAGE_PATHS,
    select_reportable_aggregate_buckets,
    surface_for_public_path,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
)
from twobrain_rec_server.public.analytics import (
    PUBLIC_VISIT_ATTRIBUTION_COOKIE,
    build_public_consent_share_report,
)

AGGREGATE_TABLE = "anonymous_page_aggregate_buckets"
VISIT_COOKIE = PUBLIC_VISIT_ATTRIBUTION_COOKIE
# Column names that would mean an identifier reached level 1. The check runs over
# the live table, so a later migration cannot add one quietly.
IDENTIFIER_COLUMN_MARKERS = (
    "ip",
    "address",
    "session",
    "visit_id",
    "visitor",
    "user_agent",
    "agent",
    "fingerprint",
    "cookie",
    "pseudonym",
    "distinct",
    "client",
    "device_id",
)
IDENTIFIER_VALUE_MARKERS = (
    "session-",
    "token-",
    "secret-",
    "user-agent-",
    "referer-",
    "testclient",
)


def _stored_rows(database_url: str) -> list[dict]:
    async def _read() -> list[dict]:
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(sa.text(f'select * from "{AGGREGATE_TABLE}"'))
                return [dict(row._mapping) for row in result]
        finally:
            await engine.dispose()

    return asyncio.run(_read())


def _stored_columns(database_url: str) -> set[str]:
    async def _read() -> set[str]:
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(
                    sa.text(
                        "select column_name from information_schema.columns "
                        "where table_name = :table"
                    ),
                    {"table": AGGREGATE_TABLE},
                )
                return {str(row[0]) for row in result}
        finally:
            await engine.dispose()

    return asyncio.run(_read())


def _reportable_buckets(database_url: str) -> list[dict]:
    async def _read() -> list[dict]:
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                return await select_reportable_aggregate_buckets(session)
        finally:
            await engine.dispose()

    return asyncio.run(_read())


def _stored_download_visits(database_url: str) -> int:
    async def _read() -> int:
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(
                    sa.text(
                        f'select coalesce(sum(visits), 0) from "{AGGREGATE_TABLE}" '
                        "where surface = :surface"
                    ),
                    {"surface": "public_download"},
                )
                return int(result.scalar_one())
        finally:
            await engine.dispose()

    return asyncio.run(_read())


def test_stored_aggregate_records_hold_no_identifier(client, postgres_seeded_database_url: str) -> None:
    """SC-002, FR-010: parse the saved records, do not read the code."""
    unique = uuid4().hex
    headers = {
        "user-agent": f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) user-agent-{unique}",
        "referer": f"https://referer-{unique}.example.test/ads",
        "cookie": f"{VISIT_COOKIE}=; session=session-{unique}",
    }

    first = client.get(f"/?utm_source=yandex_direct&utm_medium=cpc&token=token-{unique}", headers=headers)
    second = client.get(f"/?utm_source=yandex_direct&utm_medium=cpc&token=token-{unique}", headers=headers)
    download = client.get(f"/download?utm_source=yandex_direct&token=token-{unique}", headers=headers)
    private = client.get(f"/cabinet?token=token-{unique}", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert download.status_code == 200
    assert private.status_code in {200, 307, 401, 403, 404}

    rows = _stored_rows(postgres_seeded_database_url)
    assert rows, "the public visits were not counted at all"

    columns = _stored_columns(postgres_seeded_database_url)
    assert columns == set(ANONYMOUS_AGGREGATE_ALLOWED_FIELDS) | {"id", "created_at", "updated_at"}
    for column in columns:
        for marker in IDENTIFIER_COLUMN_MARKERS:
            assert marker not in column, f"identifier-shaped column {column!r} in level 1 storage"

    serialized = json.dumps(
        [{key: str(value) for key, value in row.items()} for row in rows],
        ensure_ascii=False,
    )
    for marker in (*IDENTIFIER_VALUE_MARKERS, unique):
        assert marker not in serialized, f"{marker!r} was stored in the anonymous aggregate"

    landing_rows = [row for row in rows if row["surface"] == "public_landing"]
    assert len(landing_rows) == 1, "identical visits must collapse into one bucket, not one row each"
    assert landing_rows[0]["visits"] == 2
    assert landing_rows[0]["source"] == "yandex_direct"
    assert landing_rows[0]["medium"] == "cpc"
    assert landing_rows[0]["landing_path"] == "/"
    assert landing_rows[0]["referrer_category"] == "paid"

    download_rows = [row for row in rows if row["surface"] == "public_download"]
    assert len(download_rows) == 1
    assert download_rows[0]["visits"] == 1
    assert not [row for row in rows if row["landing_path"].startswith("/cabinet")]


def test_every_public_page_is_counted_without_consent(client, postgres_seeded_database_url: str) -> None:
    """SC-001, FR-009, FR-027: the share of public pages without measurement is zero."""
    for path in PUBLIC_PAGE_PATHS:
        response = client.get(path)
        assert response.status_code == 200, path
        # No optional consent is given anywhere in this test: level 1 counts the
        # visit anyway, on sign-up and login as on every other public page.

    measured = {
        str(row["surface"]): int(row["visits"])
        for row in _stored_rows(postgres_seeded_database_url)
        if row["surface"] in ANONYMOUS_AGGREGATE_SURFACES
    }
    assert set(measured) == set(ANONYMOUS_AGGREGATE_SURFACES)
    pages_without_measurement = [
        path
        for path in PUBLIC_PAGE_PATHS
        if measured.get(surface_for_public_path(path) or "", 0) < 1
    ]
    assert pages_without_measurement == []
    # Every public route measured exactly once, and no route measured twice.
    assert sum(measured.values()) == len(PUBLIC_PAGE_PATHS)
    assert len(measured) / len(PUBLIC_PAGE_PATHS) == 1.0

    # A route that is not a public page stays outside level 1, even though it is
    # reachable without a session.
    for path in ("/robots.txt", "/sitemap.xml", "/cabinet"):
        client.get(path)
    stored_surfaces = {str(row["surface"]) for row in _stored_rows(postgres_seeded_database_url)}
    assert stored_surfaces == set(ANONYMOUS_AGGREGATE_SURFACES)


def test_buckets_below_the_minimum_size_are_not_disclosed(client, postgres_seeded_database_url: str) -> None:
    """FR-057: a bucket smaller than the threshold never reaches a report."""
    for _ in range(MINIMUM_AGGREGATE_BUCKET_SIZE - 1):
        assert client.get("/privacy").status_code == 200

    rows = _stored_rows(postgres_seeded_database_url)
    private_rows = [row for row in rows if row["surface"] == "public_privacy"]
    assert len(private_rows) == 1
    assert private_rows[0]["visits"] == MINIMUM_AGGREGATE_BUCKET_SIZE - 1
    assert _reportable_buckets(postgres_seeded_database_url) == []

    # The same counter must not be published as a share either.
    suppressed = build_public_consent_share_report(
        aggregate_visits=private_rows[0]["visits"],
        consent_visits=1,
    )
    assert suppressed["published"] is False
    assert suppressed["blocked_reason"] == "below_minimum_bucket_size"

    assert client.get("/privacy").status_code == 200

    reported = _reportable_buckets(postgres_seeded_database_url)
    assert [row["surface"] for row in reported] == ["public_privacy"]
    assert reported[0]["visits"] == MINIMUM_AGGREGATE_BUCKET_SIZE

    published = build_public_consent_share_report(
        aggregate_visits=reported[0]["visits"],
        consent_visits=1,
    )
    assert published["published"] is True
    assert published["consent_share_label"] == "33 %"


def test_real_route_classifies_asgi_peer_for_internal_traffic_without_forwarded_spoofing(
    client,
    postgres_seeded_database_url: str,
) -> None:
    """FR-013: the route uses the ASGI peer, not a caller-controlled XFF header."""
    settings = client.app.state.settings
    settings.product_analytics_internal_hosts = ("198.51.100.24",)

    internal_client = TestClient(
        client.app,
        client=("198.51.100.24", 41000),
        headers={"x-forwarded-for": "203.0.113.9"},
    )
    external_client = TestClient(
        client.app,
        client=("203.0.113.9", 41001),
        headers={"x-forwarded-for": "198.51.100.24"},
    )
    try:
        for _ in range(MINIMUM_AGGREGATE_BUCKET_SIZE):
            assert internal_client.get("/?utm_source=yandex_direct").status_code == 200
        rows = _stored_rows(postgres_seeded_database_url)
        assert len(rows) == 1
        assert rows[0]["traffic_class"] == "internal"
        assert rows[0]["visits"] == MINIMUM_AGGREGATE_BUCKET_SIZE
        assert _reportable_buckets(postgres_seeded_database_url) == []

        for _ in range(MINIMUM_AGGREGATE_BUCKET_SIZE):
            assert external_client.get("/?utm_source=yandex_direct").status_code == 200
        rows = _stored_rows(postgres_seeded_database_url)
        assert {row["traffic_class"] for row in rows} == {"internal", "external"}
        report = _reportable_buckets(postgres_seeded_database_url)
        assert len(report) == 1
        assert report[0]["traffic_class"] == "external"
        assert report[0]["visits"] == MINIMUM_AGGREGATE_BUCKET_SIZE
    finally:
        internal_client.close()
        external_client.close()


@pytest.mark.parametrize("traffic_class", ["internal", "support", "test", "automated"])
def test_excluded_traffic_classes_never_reach_reports(
    client,
    postgres_seeded_database_url: str,
    traffic_class: str,
) -> None:
    """FR-013: the distinction is stored, the class itself is not reported."""
    # The header is only trusted on the configured operator/test network; a
    # normal public peer must not be able to remove its own paid visit.
    trusted_client = TestClient(
        client.app,
        client=("198.51.100.24", 41002),
        headers={"x-graf-traffic-class": traffic_class},
    )
    client.app.state.settings.product_analytics_internal_hosts = ("198.51.100.24",)
    try:
        for _ in range(MINIMUM_AGGREGATE_BUCKET_SIZE):
            response = trusted_client.get("/")
            assert response.status_code == 200
    finally:
        trusted_client.close()

    rows = _stored_rows(postgres_seeded_database_url)
    assert [row["traffic_class"] for row in rows] == [traffic_class]
    assert _reportable_buckets(postgres_seeded_database_url) == []


def test_a_public_visit_never_reaches_a_provider(
    client,
    postgres_seeded_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-007, T026: counting is one local upsert — no provider, no network."""
    deliveries: list[dict] = []

    import twobrain_rec_server.product_analytics.posthog_client as posthog_client

    monkeypatch.setattr(
        posthog_client.PostHogClientWrapper,
        "capture_event",
        lambda self, **kwargs: deliveries.append(kwargs),
    )
    monkeypatch.setattr(
        posthog_client.PostHogClientWrapper,
        "capture",
        lambda self, event: deliveries.append({"event": event}),
    )

    for path in PUBLIC_PAGE_PATHS:
        assert client.get(path).status_code == 200

    assert deliveries == []
    assert sum(int(row["visits"]) for row in _stored_rows(postgres_seeded_database_url)) == len(
        PUBLIC_PAGE_PATHS
    )


def test_an_unavailable_provider_leaves_the_page_and_the_count_intact(
    postgres_seeded_database_url: str,
) -> None:
    """FR-058: a disabled counter is a measurement gap, not an outage."""
    settings = Settings(
        database_url=postgres_seeded_database_url,
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="12345678",
        # No PostHog host, key and live delivery: the relay has nowhere to send.
        product_analytics_posthog_enabled=False,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/analytics/public-event",
            json={
                "event_name": "public_download_viewed",
                "page_path": "/download",
                "surface": "public_download",
                "view_id": "graf_public_view_0123456789abcdef",
                "consent_state": "accepted_all",
                "consent_categories": ["necessary", "analytics"],
            },
        )
        page = client.get("/download")
        repeated = client.get("/download")

    assert response.status_code == 202
    delivery = response.json()["delivery"]
    assert delivery["delivered"] is False
    assert delivery["provider"] == "posthog"
    assert delivery["status"] in {"disabled", "configuration_error", "dry_run", "unavailable"}
    assert page.status_code == 200
    assert repeated.status_code == 200
    assert _stored_download_visits(postgres_seeded_database_url) == 2
